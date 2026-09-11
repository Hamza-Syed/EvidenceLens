"""Replaceable, evidence-only service boundaries and deterministic baseline."""

import hashlib
import math
import re
from collections import Counter
from typing import Protocol, Sequence

from .models import Claim, ChunkedPassage, Classification, Evidence, Passage, VerificationResult
from .text import sentences


class ClaimExtractor(Protocol):
    def extract(self, text: str) -> list[Claim]: ...


class Retriever(Protocol):
    def retrieve(self, claim: Claim, passages: Sequence[Passage]) -> list[Passage]: ...


class Verifier(Protocol):
    def verify(self, claim: Claim, evidence: Sequence[Passage]) -> VerificationResult: ...


class SentenceClaimExtractor:
    def extract(self, text: str) -> list[Claim]:
        parts = sentences(text)
        if len(parts) > 100:
            raise ValueError("Provide at most 100 sentence candidates.")
        return [Claim(text=part) for part in parts]


def vector(text: str) -> dict[int, float]:
    counts = Counter(
        int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big") % 4096
        for token in re.findall(r"\w+", text.casefold())
    )
    norm = math.sqrt(sum(value * value for value in counts.values()))
    return {key: value / norm for key, value in counts.items()} if norm else {}


class HashVectorRetriever:
    """Local lexical vectors; similarity is only used for retrieval ordering."""

    def retrieve(self, claim: Claim, passages: Sequence[Passage]) -> list[Passage]:
        query = vector(claim.text)
        ranked = []
        for passage in passages:
            embedding = vector(passage.text)
            similarity = sum(value * embedding.get(key, 0) for key, value in query.items())
            if similarity > 0:
                ranked.append((similarity, passage))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [passage for _, passage in ranked[:5]]


class ExactSentenceVerifier:
    def verify(self, claim: Claim, evidence: Sequence[Passage]) -> VerificationResult:
        def normalize(text: str) -> str:
            return " ".join(text.split())
        matched = any(
            normalize(claim.text) == normalize(sentence)
            for passage in evidence
            for sentence in (passage.complete_sentences if isinstance(passage, ChunkedPassage) else sentences(passage.text))
        )
        return VerificationResult(
            claim=claim,
            classification=Classification.SUPPORTED if matched else Classification.INSUFFICIENT_EVIDENCE,
            explanation=(
                "A retrieved passage states this exact sentence. This baseline does not resolve conflicting sources."
                if matched else
                "The retrieved evidence does not establish an exact sentence match. This baseline cannot assess semantic support or contradiction."
            ),
            evidence=[Evidence(**passage.model_dump()) for passage in evidence],
        )
