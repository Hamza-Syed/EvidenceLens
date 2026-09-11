from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.documents import DocumentStore
from app.errors import EmbeddingError
from app.main import create_app
from app.models import Claim, Passage
from app.retrieval import SemanticRetriever
from app.services import ExactSentenceVerifier
from test_workflow import pdf_bytes, upload


def passage(text, **kwargs):
    return Passage(document_id=uuid4(), document_name="trial.pdf", page_number=2, text=text, **kwargs)


class StubEmbeddings:
    """Explicit test vectors for index math; real model quality is tested separately."""
    def __init__(self):
        self.documents = []

    def embed_documents(self, texts):
        self.documents.extend(texts)
        return [[1., 0.] if "trial" in text else [0., 1.] for text in texts]

    def embed_query(self, text):
        return [1., 0.]


def test_cached_document_vectors_and_configured_top_k():
    provider = StubEmbeddings()
    retriever = SemanticRetriever(provider, top_k=1, min_similarity=.5)
    passages = [passage("The trial enrolled 312 adults."), passage("Oranges grow on trees.")]
    retriever.index(passages)
    assert retriever.retrieve(Claim(text="More than 300 people took part in the trial."), passages) == passages[:1]
    assert retriever.retrieve(Claim(text="The trial enrolled 312 adults."), passages) == passages[:1]
    assert len(provider.documents) == 2


def test_threshold_empty_inputs_and_bounded_cache():
    retriever = SemanticRetriever(StubEmbeddings(), cache_size=1)
    assert retriever.retrieve(Claim(text="A fact."), [passage("Oranges.")]) == []
    assert retriever.retrieve(Claim(text="A fact."), []) == []
    retriever.index([passage("trial one"), passage("trial two")])
    assert len(retriever._cache) == 1


def test_cache_is_not_candidate_scope():
    retriever = SemanticRetriever(StubEmbeddings())
    foreign = passage("The trial enrolled 312 adults.")
    selected = passage("Oranges grow on trees.")
    retriever.index([foreign, selected])
    assert retriever.retrieve(Claim(text=foreign.text), [selected]) == []


@pytest.mark.parametrize("bad_vector", [[], [0., 0.], [float("nan"), 1.], [float("inf"), 1.], [True, 1.]])
def test_invalid_embedding_vectors(bad_vector):
    class Bad(StubEmbeddings):
        def embed_documents(self, texts):
            return [bad_vector] * len(texts)

    with pytest.raises(EmbeddingError):
        SemanticRetriever(Bad()).index([passage("trial")])


def test_bad_query_dimension():
    class Bad(StubEmbeddings):
        def embed_query(self, text):
            return [1., 0., 0.]

    with pytest.raises(EmbeddingError, match="dimensions"):
        SemanticRetriever(Bad()).retrieve(Claim(text="trial"), [passage("trial")])


def test_embedding_count_mismatch():
    class Bad(StubEmbeddings):
        def embed_documents(self, texts):
            return []

    with pytest.raises(EmbeddingError, match="number"):
        SemanticRetriever(Bad()).index([passage("trial")])


def test_relevant_negation_is_not_support():
    source = passage("The trial intervention did not significantly reduce blood pressure.")
    claim = Claim(text="The trial intervention significantly reduced blood pressure.")
    candidates = SemanticRetriever(StubEmbeddings()).retrieve(claim, [source])
    assert candidates == [source]
    assert ExactSentenceVerifier().verify(claim, candidates).classification == "insufficient_evidence"


@pytest.mark.parametrize("forgery", ["foreign_document", "changed_text", "changed_page"])
def test_adversarial_retriever_is_rejected_before_verifier(forgery):
    class MaliciousRetriever:
        foreign = None

        def retrieve(self, claim, passages):
            if forgery == "foreign_document":
                return [self.foreign]
            change = {"text": claim.text} if forgery == "changed_text" else {"page_number": 99}
            return [passages[0].model_copy(update=change)]

    class SpyVerifier:
        called = False

        def verify(self, claim, evidence):
            self.called = True
            raise AssertionError("Untrusted evidence reached the verifier")

    store, retriever, verifier = DocumentStore(), MaliciousRetriever(), SpyVerifier()
    with TestClient(create_app(store=store, retriever=retriever, verifier=verifier)) as client:
        allowed = upload(client, "allowed.pdf", "The trial enrolled 12 adults.")
        forbidden = upload(client, "forbidden.pdf", "The trial enrolled 312 adults.")
        from uuid import UUID
        retriever.foreign = store.passages([UUID(forbidden["id"])])[0]
        response = client.post("/api/verifications", json={"text": "The trial enrolled 312 adults.", "document_ids": [allowed["id"]]})
        assert response.status_code == 502
        assert "forbidden.pdf" not in response.text
        assert not verifier.called


def test_embedding_failure_does_not_commit_upload():
    class Broken(StubEmbeddings):
        def embed_documents(self, texts):
            raise RuntimeError("secret provider details")

    store = DocumentStore()
    with TestClient(create_app(store=store, retriever=SemanticRetriever(Broken()))) as client:
        response = client.post("/api/documents", files={"files": ("trial.pdf", pdf_bytes("A trial."), "application/pdf")})
        assert response.status_code == 503
        assert "secret" not in response.text
        assert store._items == {}
