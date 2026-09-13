"""Exercise Try sample inputs through the production frontend proxy, without mocks."""
import json
import time
from pathlib import Path

import httpx2
import pymupdf

ROOT = Path(__file__).resolve().parents[1]


def main():
    record = {}
    with httpx2.Client(base_url='http://127.0.0.1:3000', timeout=180, trust_env=False) as client:
        start = time.perf_counter()
        page = client.get('/')
        assert page.status_code == 200 and 'Try sample' in page.text
        sample = client.get('/api/demo').raise_for_status().json()
        pdf = client.get(sample['pdf_url']).raise_for_status().content
        with pymupdf.open(stream=pdf, filetype='pdf') as document:
            page_texts = [page.get_text().strip() for page in document]
        response = client.post('/api/documents', files={'files': (sample['name'], pdf, 'application/pdf')})
        response.raise_for_status()
        document = response.json()['documents'][0]
        record['prepare_upload_seconds'] = time.perf_counter() - start
        start = time.perf_counter()
        response = client.post('/api/verifications', json={'text': sample['text'], 'document_ids': [document['id']]})
        record['verification_http_seconds'] = time.perf_counter() - start
        record['status'] = response.status_code
        record['response'] = response.json()
        target = ROOT / 'docs/evaluation/demo-results.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        # Keep failures too, before assertions. Only the synthetic public demo is used.
        target.write_text(json.dumps(record, indent=2) + '\n')
        response.raise_for_status()
        results = response.json()['results']
        assert len(results) == 4
        expected = [('supported', [1]), ('partially_supported', [3]), ('contradicted', [2]), ('insufficient_evidence', [])]
        for result, (verdict, pages) in zip(results, expected):
            assert result['classification'] == verdict, result
            assert sorted(e['page_number'] for e in result['evidence']) == pages, result
            for evidence in result['evidence']:
                assert evidence['document_id'] == document['id']
                assert evidence['document_name'] == sample['name']
                assert evidence['text'] == page_texts[evidence['page_number'] - 1]
        print(f"All four demo verdicts and exact page citations passed in {record['verification_http_seconds']:.2f}s.")


if __name__ == '__main__':
    main()
