"""Real model evaluation. Enable explicitly; the normal suite needs no network."""
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.embeddings import FastEmbedProvider
from app.main import create_app
from app.models import Claim, Passage
from app.retrieval import SemanticRetriever
from app.services import ExactSentenceVerifier
from test_workflow import upload

FIXTURE = json.loads((Path(__file__).resolve().parents[2] / "sample_data" / "semantic_cases.json").read_text())
pytestmark = [pytest.mark.semantic_model, pytest.mark.skipif(os.environ.get("EVIDENCELENS_TEST_MODEL") != "1", reason="Set EVIDENCELENS_TEST_MODEL=1 to run real embedding evaluation.")]


@pytest.fixture(scope="module")
def retriever():
    config = Settings.from_env()
    return SemanticRetriever(FastEmbedProvider(config), top_k=1, min_similarity=config.retrieval_min_similarity)


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=[case["claim"] for case in FIXTURE["cases"]])
def test_real_semantic_ranking_and_verdict(retriever, case):
    passages = [Passage(document_id=uuid4(), document_name="trial.pdf", page_number=index + 1, text=text)
                for index, text in enumerate(FIXTURE["sources"])]
    claim = Claim(text=case["claim"])
    evidence = retriever.retrieve(claim, passages)
    if case["expected_source"] is not None:
        assert evidence and evidence[0] == passages[case["expected_source"]]
        assert evidence[0].document_name == "trial.pdf"
        assert evidence[0].page_number == case["expected_source"] + 1
    else:
        assert evidence == []
    assert ExactSentenceVerifier().verify(claim, evidence).classification == case["expected_verdict"]


def test_real_semantic_api_and_scope(retriever):
    with TestClient(create_app(retriever=retriever)) as client:
        document = upload(client, "trial.pdf", "Trial report.", FIXTURE["sources"][0])
        other = upload(client, "unselected.pdf", "More than 300 people took part in the trial.")
        response = client.post("/api/verifications", json={"text": "More than 300 people took part in the trial.", "document_ids": [document["id"]]})
        assert response.status_code == 200
        result = response.json()["results"][0]
        assert result["classification"] == "insufficient_evidence"
        assert result["evidence"][0]["page_number"] == 2
        assert result["evidence"][0]["document_name"] == "trial.pdf"
        assert all(item["document_id"] != other["id"] for item in result["evidence"])
