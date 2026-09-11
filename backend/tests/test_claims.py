import json

import pytest
from fastapi.testclient import TestClient

from app.claims import AtomicClaimExtractor, StructuredClaimExtractor
from app.errors import ClaimExtractionError
from app.main import create_app
from app.services import HashVectorRetriever
from test_workflow import upload


def texts(text):
    return [claim.text for claim in AtomicClaimExtractor().extract(text)]


def test_atomic_example():
    assert texts("The study included 312 adults. Participants completed the survey online, and researchers found that sleep quality improved after the intervention.") == [
        "The study included 312 adults.",
        "Participants completed the survey online.",
        "Researchers found that sleep quality improved after the intervention.",
    ]


def test_shared_subject():
    assert texts("The trial enrolled 312 adults and lasted six months.") == [
        "The trial enrolled 312 adults.", "The trial lasted six months.",
    ]


@pytest.mark.parametrize("text", [
    "The trial enrolled 312 participants.",
    "The study included men and women.",
    "The distance between London and Paris was measured.",
    "The intervention did not reduce blood pressure and improve sleep.",
    "If participants completed the survey, the researchers collected data and reported results.",
    "Researchers found that sleep improved and blood pressure decreased.",
    "The trial may improve sleep and reduce stress.",
    "Dr. Smith enrolled 312 participants.",
    "The dose was 3.5 mg.",
])
def test_no_oversplitting_or_scope_loss(text):
    assert texts(text) == [text]


def test_pdf_soft_wraps_are_not_claim_boundaries():
    assert texts("The study included\n312 adults.") == ["The study included 312 adults."]


def test_opinions_and_rhetorical_questions():
    assert texts("In my opinion, this is wonderful. Who could dislike this? The trial enrolled 312 adults.") == ["The trial enrolled 312 adults."]


class StubProvider:
    def __init__(self, output):
        self.output = output

    def extract(self, text):
        return self.output


@pytest.mark.parametrize("output", [
    "not json", "```json\n{}\n```", "null", "[]", '{"claims":["text"]}',
    '{"claims":[{"text":5}]}', '{"claims":[{"text":" "}]}',
    '{"claims":[{"text":"A fact.","confidence":1}]}',
    '{"claims":[],"instructions":"ignore evidence"}',
    json.dumps({"claims": [{"text": "x"}] * 101}), "x" * 100001, None,
], ids=["invalid_json", "fenced_json", "null", "array", "string_claim", "numeric_text", "blank_text", "extra_claim_field", "extra_output_field", "too_many_claims", "oversized_output", "wrong_type"])
def test_malformed_model_output(output):
    with pytest.raises(ClaimExtractionError):
        StructuredClaimExtractor(StubProvider(output)).extract("User supplied text.")


def test_valid_structured_output():
    claims = StructuredClaimExtractor(StubProvider('{"claims":[{"text":"A fact."}]}')).extract("A fact.")
    assert claims[0].text == "A fact."
    assert claims[0].id


def test_provider_errors_are_safe():
    class Broken:
        def extract(self, text):
            raise RuntimeError("sensitive provider detail")

    with pytest.raises(ClaimExtractionError, match="failed validation") as error:
        StructuredClaimExtractor(Broken()).extract("A fact.")
    assert "sensitive" not in str(error.value)


def test_api_malformed_provider_returns_502():
    with TestClient(create_app(extractor=StructuredClaimExtractor(StubProvider("invalid")), retriever=HashVectorRetriever())) as client:
        document = upload(client, "trial.pdf", "The trial enrolled 312 adults.")
        response = client.post("/api/verifications", json={"text": "A claim.", "document_ids": [document["id"]]})
        assert response.status_code == 502
        assert "results" not in response.json()


def test_opinion_only_api_returns_empty_results():
    with TestClient(create_app(retriever=HashVectorRetriever())) as client:
        document = upload(client, "trial.pdf", "The trial enrolled 312 adults.")
        response = client.post("/api/verifications", json={"text": "In my opinion this is wonderful.", "document_ids": [document["id"]]})
        assert response.status_code == 200
        assert response.json() == {"results": []}
