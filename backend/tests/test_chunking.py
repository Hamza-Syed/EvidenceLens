import random
import string

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.documents import extract_pdf
from app.models import Claim, ChunkedPassage
from app.services import ExactSentenceVerifier
from app.text import chunk_page
from test_workflow import pdf_bytes


@pytest.mark.parametrize("text", [
    "A short sentence.",
    " ".join(f"Sentence {index} describes trial {index} and its participants." for index in range(100)),
    "".join(random.Random(42).choices(string.ascii_letters, k=2400)),
    "\n".join(f"line number {index} has text" for index in range(200)),
], ids=["short", "sentences", "long_token", "soft_wraps"])
def test_chunks_bounded_lossless_substrings(text):
    chunks = chunk_page(text, 150, 30)
    assert all(0 < len(chunk) <= 150 and chunk in text for chunk in chunks)
    # Every non-whitespace character is represented by at least one source window.
    coverage = [False] * len(text)
    offset = 0
    for chunk in chunks:
        start = text.index(chunk, offset)
        for index in range(start, start + len(chunk)):
            coverage[index] = True
        offset = start + 1
    assert all(covered or character.isspace() for covered, character in zip(coverage, text))


def test_chunks_never_cross_pages():
    document, passages = extract_pdf("trial.pdf", pdf_bytes("The trial enrolled 312 adults.", "The survey was online."), max_chars=100, overlap_chars=20)
    assert document.page_count == 2
    assert [(passage.page_number, passage.text) for passage in passages] == [
        (1, "The trial enrolled 312 adults."), (2, "The survey was online."),
    ]
    assert all(passage.document_name == "trial.pdf" and passage.document_id == document.id for passage in passages)


def test_invalid_settings(monkeypatch):
    monkeypatch.setenv("EVIDENCELENS_RETRIEVAL_TOP_K", "0")
    with pytest.raises(ValidationError):
        Settings.from_env()
    with pytest.raises(ValidationError):
        Settings(chunk_max_chars=100, chunk_overlap_chars=150)


def test_environment_configuration(monkeypatch):
    monkeypatch.setenv("EVIDENCELENS_RETRIEVAL_TOP_K", "2")
    monkeypatch.setenv("EVIDENCELENS_RETRIEVAL_MIN_SIMILARITY", "0.75")
    assert Settings.from_env().retrieval_top_k == 2
    assert Settings.from_env().retrieval_min_similarity == 0.75


def test_chunk_fragment_cannot_become_exact_support():
    # Truncating a qualified sentence must not turn its tail into a standalone fact.
    document, passages = extract_pdf("qualified.pdf", pdf_bytes(
        "It is false that the trial enrolled 312 participants."), max_chars=30, overlap_chars=5)
    last = passages[-1]
    assert isinstance(last, ChunkedPassage)
    assert not last.complete_sentences
    result = ExactSentenceVerifier().verify(Claim(text=last.text), [last])
    assert result.classification == "insufficient_evidence"
    assert "complete_sentences" not in result.model_dump_json()
