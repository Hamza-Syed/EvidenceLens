"""Opt-in live benchmark. Records every outcome, including rejected responses.

Uses the production provider and validation; fixture passages bypass retrieval and
claim extraction deliberately. Never use this recorder with private documents.
"""
import argparse
import hashlib
import json
import math
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx2

from app.config import Settings
from app.errors import VerifierOutputError, VerifierUnavailableError
from app.models import Claim, Passage
from app.verification import EvidenceGroundedVerifier, SYSTEM_PROMPT
from app.verifier_provider import ChatCompletionProvider

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = {
    'paraphrase': 'paraphrase', 'negation': 'negation',
    **dict.fromkeys(['number_equal', 'number_conflict', 'greater_than', 'less_than', 'range_support', 'range_uncertainty'], 'quantity'),
    **dict.fromkeys(['date_precision', 'date_conflict', 'before_after'], 'temporal'),
    'modality': 'modality', 'some_all': 'scope', 'correlation': 'causality',
    'direction': 'direction', 'comparison': 'comparison', 'missing_qualifier': 'scope',
    'unsupported_detail': 'missing detail', 'entity_mismatch': 'entity',
    'source_disagreement': 'conflict', 'lexical_overlap': 'irrelevance',
    'joint_support': 'joint evidence', 'partial_clause': 'compound',
    'contradicted_clause': 'compound', 'no_evidence': 'empty evidence',
    'prompt_injection': 'injection',
}


class RecordingTransport(httpx2.BaseTransport):
    def __init__(self):
        self.inner = httpx2.HTTPTransport()
        self.envelope = None
        self.seconds = 0.0
        self.called = False

    def handle_request(self, request):
        start = time.perf_counter()
        self.called = True
        try:
            response = self.inner.handle_request(request)
            response.read()
        finally:
            self.seconds = time.perf_counter() - start
        try:
            self.envelope = response.json()
        except ValueError:
            self.envelope = None
        return response

    def close(self):
        self.inner.close()


def summarize(rows):
    def accuracy(items):
        passed = sum(row['passed'] for row in items)
        return {'total': len(items), 'passed': passed, 'accuracy': passed / len(items) if items else None}
    warm = [r['seconds'] for r in rows if r['provider_called'] and not r['cold_request']]
    all_times = [r['seconds'] for r in rows]
    return {**accuracy(rows),
            'model_calls': accuracy([r for r in rows if r['provider_called']]),
            'no_call_controls': accuracy([r for r in rows if not r['provider_called']]),
            'median_seconds': statistics.median(all_times) if all_times else None,
            'p90_seconds': sorted(all_times)[math.ceil(.9 * len(all_times)) - 1] if len(all_times) >= 10 else None,
            'by_verdict': {key: accuracy([r for r in rows if r['expected'] == key]) for key in sorted({r['expected'] for r in rows})},
            'by_category': {key: accuracy([r for r in rows if r['category'] == key]) for key in sorted({r['category'] for r in rows})},
            'warm_median_seconds': statistics.median(warm) if warm else None,
            'warm_p90_seconds': sorted(warm)[math.ceil(.9 * len(warm)) - 1] if len(warm) >= 10 else None}


def render_report(report):
    summary = report['summary']
    warm_label = f"{summary['warm_median_seconds']:.2f}s" if summary['warm_median_seconds'] is not None else 'not measured'
    lines = ['# Live verification benchmark', '', report['scope'], '',
             f"Model: {report['model']}; runtime: {report['runtime']}; threads: {report['threads']}.",
             f"Run started: {report['created_at']}. One run per case, no expectation changes.", '',
             f"**{summary['passed']}/{summary['total']} passed ({summary['accuracy']:.1%}).**", '',
             f"Median all cases: {summary['median_seconds']:.2f}s; warm model median: {warm_label}.", '',
             'Citations valid means canonical source/page/text and backend quote checks passed; it does not establish correct entailment.',
             'Empty-evidence and injection controls abstain without a model call. Raw inputs, outputs, prompt/fixture hashes and runtime timings are in the adjacent JSON file.', '']
    for label, groups in [('Verdict class', summary['by_verdict']), ('Reasoning category', summary['by_category'])]:
        lines += [f'## {label}', '', '| Group | Passed / total | Accuracy |', '| --- | --- | --- |']
        lines += [f"| {key} | {value['passed']} / {value['total']} | {value['accuracy']:.1%} |" for key, value in groups.items()]
        lines.append('')
    lines += ['## Every case', '', '| ID / category | Claim | Expected | Actual | Pass | Seconds | Citations valid | Failure |',
              '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for row in report['rows']:
        cells = [f"{row['id']} / {row['category']}", row['claim'], row['expected'], row['actual'] or 'no verdict',
                 'yes' if row['passed'] else 'no', f"{row['seconds']:.2f}", str(row['citations_valid']), row['failure'] or '—']
        lines.append('| ' + ' | '.join(str(c).replace('|', '\\|').replace('\n', ' ') for c in cells) + ' |')
    return '\n'.join(lines) + '\n'


def classify_record(row):
    """Refine the diagnostic from observed output, never from fixture wording."""
    if row.get('failure') != 'model reasoning error' or row.get('actual') != 'insufficient_evidence':
        return
    envelope = row.get('raw_response')
    if envelope:
        try:
            output = json.loads(envelope['choices'][0]['message']['content'])
            if output.get('conflict') is True:
                row['failure'] = 'conflict-handling issue'
                row['failure_detail'] = 'Model flagged source disagreement; conservative validation overrode the verdict. Inspect candidate assessments for clause/whole-claim confusion.'
        except (KeyError, IndexError, TypeError, ValueError):
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='docs/evaluation/live-results.json')
    parser.add_argument('--cases', nargs='*', help='Optional subset, never changes expectations')
    parser.add_argument('--cold-first', action='store_true', help='Only use immediately after starting the server')
    parser.add_argument('--report-only', action='store_true', help='Regenerate summary/Markdown from existing raw records; no inference')
    args = parser.parse_args()
    target = ROOT / args.output
    if args.report_only:
        report = json.loads(target.read_text(encoding='utf-8'))
        for row in report['rows']:
            classify_record(row)
        report['summary'] = summarize(report['rows'])
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        target.with_suffix('.md').write_text(render_report(report), encoding='utf-8')
        return
    settings = Settings.from_env()
    if not settings.verifier_base_url.startswith('http://127.0.0.1:'):
        raise SystemExit('This public-fixture evaluation requires the local loopback verifier.')
    fixture = ROOT / 'sample_data/verification_cases.json'
    cases = json.loads(fixture.read_text())
    if args.cases:
        if set(args.cases) - {c['id'] for c in cases}:
            raise SystemExit('Unknown case ID')
        cases = [c for c in cases if c['id'] in args.cases]
    report = {'created_at': datetime.now(timezone.utc).isoformat(),
              'model': 'Qwen3-4B-Instruct-2507 Q3_K_S', 'runtime': 'llama.cpp b10809',
              'threads': 4, 'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
              'prompt_sha256': hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
              'scope': 'Verifier plus validation; supplied fixture passages, no extraction/retrieval.',
              'rows': []}
    target.parent.mkdir(parents=True, exist_ok=True)
    for index, case in enumerate(cases):
        transport = RecordingTransport()
        verifier = EvidenceGroundedVerifier(ChatCompletionProvider(settings, transport=transport))
        sources = [Passage(document_id=uuid4(), document_name=f'source-{i}.pdf', page_number=i + 1, text=text)
                   for i, text in enumerate(case['sources'])]
        row = {'id': case['id'], 'category': CATEGORIES[case['id']], 'claim': case['claim'],
               'sources': case['sources'], 'expected': case['expected'], 'actual': None,
               'passed': False, 'citations_valid': None, 'failure': None,
               'cold_request': args.cold_first and index == 0}
        start = time.perf_counter()
        try:
            result = verifier.verify(Claim(text=case['claim']), sources)
            canonical = {p.id: p.model_dump() for p in sources}
            valid = all(canonical.get(e.id) == e.model_dump() for e in result.evidence)
            row.update(actual=result.classification.value, explanation=result.explanation,
                       citations_valid=valid, citations=[{'page': e.page_number, 'file': e.document_name, 'text': e.text} for e in result.evidence],
                       passed=result.classification.value == case['expected'] and valid)
            if not row['passed']:
                row['failure'] = 'model reasoning error' if valid else 'citation-selection issue'
        except (VerifierOutputError, VerifierUnavailableError) as exc:
            row.update(failure='validation rejection' if isinstance(exc, VerifierOutputError) else 'provider/runtime failure', error=str(exc))
        row.update(seconds=round(time.perf_counter() - start, 6), provider_called=transport.called,
                   http_seconds=round(transport.seconds, 6), raw_response=transport.envelope)
        row['non_http_seconds'] = round(row['seconds'] - row['http_seconds'], 6)
        classify_record(row)
        report['rows'].append(row)
        report['summary'] = summarize(report['rows'])
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(f"{case['id']}: {row['actual']} expected={row['expected']} passed={row['passed']} {row['seconds']:.2f}s {row['failure'] or ''}", flush=True)
    target.with_suffix('.md').write_text(render_report(report), encoding='utf-8')


if __name__ == '__main__':
    main()
