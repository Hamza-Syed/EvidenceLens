"""Profile local extraction/retrieval and replay validation of public benchmark outputs."""
import json
import argparse
import statistics
import time
from pathlib import Path
from uuid import uuid4

import httpx2

from app.claims import AtomicClaimExtractor
from app.config import Settings
from app.demo import DEMO_NAME, DEMO_TEXT, demo_pdf
from app.documents import extract_pdf
from app.embeddings import FastEmbedProvider
from app.models import Claim, Passage
from app.retrieval import SemanticRetriever
from app.verification import EvidenceGroundedVerifier

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--http', action='store_true', help='Also measure running backend/frontend metadata round trips')
    args = parser.parse_args()
    report = {}
    def measure(name, call):
        start = time.perf_counter()
        result = call()
        report[name] = time.perf_counter() - start
        return result
    pdf = demo_pdf()
    _, passages = measure('pdf_extraction_seconds', lambda: extract_pdf(DEMO_NAME, pdf))
    claims = measure('claim_extraction_seconds', lambda: AtomicClaimExtractor().extract(DEMO_TEXT))
    retriever = SemanticRetriever(FastEmbedProvider(Settings.from_env()))
    measure('embedding_initialization_and_index_seconds', lambda: retriever.index(passages))
    measure('first_retrieval_seconds', lambda: retriever.retrieve(claims[0], passages))
    measure('four_warm_retrievals_seconds', lambda: [retriever.retrieve(c, passages) for c in claims])
    report['candidate_pages'] = [[p.page_number for p in retriever.retrieve(c, passages)] for c in claims]
    recorded = json.loads((ROOT / 'docs/evaluation/live-results.json').read_text())
    latencies = []
    for row in recorded['rows']:
        if not row['raw_response'] or row['actual'] is None:
            continue
        raw = row['raw_response']['choices'][0]['message']['content']
        class Replay:
            def complete(self, **kwargs):
                return raw
        sources = [Passage(document_id=uuid4(), document_name=f'source-{i}.pdf', page_number=i + 1, text=text)
                   for i, text in enumerate(row['sources'])]
        verifier = EvidenceGroundedVerifier(Replay())
        start = time.perf_counter()
        verifier.verify(Claim(text=row['claim']), sources)
        latencies.append(time.perf_counter() - start)
    report['replay_validation_cases'] = len(latencies)
    report['replay_adapter_validation_median_seconds'] = statistics.median(latencies)
    report['replay_adapter_validation_max_seconds'] = max(latencies)
    if args.http:
        for name, port in [('backend', 8000), ('frontend_proxy', 3000)]:
            samples = []
            with httpx2.Client(timeout=10, trust_env=False) as client:
                for _ in range(10):
                    start = time.perf_counter()
                    client.get(f'http://127.0.0.1:{port}/api/demo').raise_for_status()
                    samples.append(time.perf_counter() - start)
            report[f'{name}_metadata_http_median_seconds'] = statistics.median(samples)
    report['note'] = 'Replay includes serialization, Pydantic parsing and full verifier validation; no inference. Embedding initialization includes cached disk weight loading. HTTP samples measure a small metadata GET, not verification overhead.'
    (ROOT / 'docs/evaluation/pipeline-profile.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
