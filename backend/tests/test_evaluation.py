from pathlib import Path
import json
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[2]
evaluation = runpy.run_path(str(ROOT / 'scripts/evaluate_verifier.py'))
warmup = runpy.run_path(str(ROOT / 'scripts/warm_verifier.py'))


def test_summary_counts_failures_and_excludes_cold_and_no_call_from_warm_latency():
    rows = [dict(expected='supported', category='quantity', passed=i != 3,
                 seconds=i + 1, provider_called=i != 1, cold_request=i == 0) for i in range(12)]
    summary = evaluation['summarize'](rows)
    assert summary['total'] == 12 and summary['passed'] == 11
    assert summary['by_verdict']['supported']['accuracy'] == 11 / 12
    assert summary['warm_median_seconds'] == 7.5
    assert summary['warm_p90_seconds'] == 11


def test_small_samples_do_not_report_p90():
    assert evaluation['summarize']([])['warm_p90_seconds'] is None


def test_report_preserves_failed_verdict_and_claim():
    row = dict(id='modality', expected='insufficient_evidence', actual='partially_supported',
               claim='It may work.', category='modality', passed=False, seconds=3,
               provider_called=True, cold_request=True, citations_valid=True, failure='model reasoning error')
    report = dict(rows=[row], summary=evaluation['summarize']([row]), scope='Verifier only',
                  model='test', runtime='test', threads=4, created_at='test')
    text = evaluation['render_report'](report)
    assert '0/1 passed' in text and 'model reasoning error' in text and 'It may work.' in text
    assert 'not measured' in text


def test_warmup_refuses_remote_endpoint_before_network():
    with pytest.raises(ValueError, match='loopback'):
        warmup['wait_until_ready']('https://example.com/v1')


def test_conflict_failure_is_categorized_from_output_not_case_id():
    row = dict(actual='insufficient_evidence', failure='model reasoning error',
               raw_response={'choices': [{'message': {'content': json.dumps({'conflict': True})}}]})
    evaluation['classify_record'](row)
    assert row['failure'] == 'conflict-handling issue'
