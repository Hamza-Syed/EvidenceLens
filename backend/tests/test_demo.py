from fastapi.testclient import TestClient

from app.claims import AtomicClaimExtractor
from app.demo import DEMO_NAME, DEMO_PAGES, DEMO_TEXT
from app.main import create_app
from app.services import HashVectorRetriever


def test_sample_uses_real_pdf_upload_and_document_scoping():
    client = TestClient(create_app(retriever=HashVectorRetriever()))
    sample = client.get('/api/demo').json()
    assert 'results' not in sample
    pdf = client.get(sample['pdf_url'])
    assert pdf.headers['content-type'] == 'application/pdf'
    uploaded = client.post('/api/documents', files={'files': (sample['name'], pdf.content, 'application/pdf')})
    assert uploaded.status_code == 201
    document = uploaded.json()['documents'][0]
    assert document['name'] == DEMO_NAME
    assert document['page_count'] == 3
    for page, text in enumerate(DEMO_PAGES, 1):
        response = client.post('/api/verifications', json={'document_ids': [document['id']], 'text': text})
        result = response.json()['results'][0]
        assert result['classification'] == 'supported'
        assert result['evidence'][0]['page_number'] == page
        assert result['evidence'][0]['document_id'] == document['id']


def test_demo_preserves_four_atomic_claims():
    assert [c.text for c in AtomicClaimExtractor().extract(DEMO_TEXT)] == DEMO_TEXT.splitlines()
