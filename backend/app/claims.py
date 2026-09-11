"""Conservative English atomic extraction plus a strict model-output boundary."""

import re
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .errors import ClaimExtractionError
from .models import Claim
from .text import sentences


class ExtractedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str = Field(min_length=1, max_length=20_000)

    @field_validator("text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Claim must not be blank.")
        return value


class ClaimExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    claims: list[ExtractedClaim] = Field(max_length=100)


class StructuredClaimProvider(Protocol):
    def extract(self, text: str) -> str:
        """Return JSON {claims: [{text: ...}]}; input is data, never instructions."""
        ...


class StructuredClaimExtractor:
    """An injectable model adapter; never repairs, evaluates, or trusts raw output."""

    def __init__(self, provider: StructuredClaimProvider):
        self.provider = provider

    def extract(self, text: str) -> list[Claim]:
        try:
            raw = self.provider.extract(text)
            if not isinstance(raw, str) or len(raw) > 100_000:
                raise ValueError("Unexpected provider response.")
            output = ClaimExtractionOutput.model_validate_json(raw)
        except Exception as exc:
            raise ClaimExtractionError("Claim extraction failed validation. Please retry.") from exc
        return [Claim(text=claim.text) for claim in output.claims]


# Restrict splitting to recognizable predicates rather than every 'and'. This
# leaves difficult conjunctions intact instead of inventing missing subjects.
_VERB = r"(?:is|are|was|were|has|have|had|can|could|will|would|may|might|did|does|do|included|enrolled|completed|found|reported|opened|closed|lasted|received|showed|measured|improved|reduced|increased|decreased|collected|took|used|contains|contain|costs|cost|weighs|weigh|lives|live|works|work)"
_CLAUSE = re.compile(rf"^(?P<subject>[\w][\w\s'-]*?)\s+(?P<predicate>{_VERB})\b", re.I)
_SUBJECTIVE = re.compile(
    r"^(?:I (?:think|believe|feel|love|hate|prefer)|in my opinion|personally|"
    r"who (?:would|could)|isn't it|how (?:wonderful|amazing)|what a)\b|"
    r"\b(?:is|was|are|were) (?:absolutely |really |so )?(?:wonderful|beautiful|amazing|boring|awful|the best)\b",
    re.I,
)


def _split_clause(text: str) -> list[str]:
    # Do not detach conditions, quotations, reported clauses, or ambiguous
    # negation/modality from the propositions whose meaning they constrain.
    if re.search(r'\b(?:if|unless|either|neither|not|never|may|might|could|would|can|will|that)\b|["“”]', text, re.I):
        return [text]
    left_match = _CLAUSE.match(text)
    if not left_match:
        return [text]
    for join in re.finditer(r",?\s+(?:and|but)\s+|;\s*", text, re.I):
        left, right = text[:join.start()].rstrip(", "), text[join.end():].strip()
        if not _CLAUSE.match(left):
            continue
        # Reported finding as the RHS is okay: its reporting verb stays attached.
        if _CLAUSE.match(right):
            return _split_clause(left) + _split_clause(right)
        if re.match(rf"{_VERB}\b", right, re.I):
            return _split_clause(left) + _split_clause(f"{left_match['subject']} {right}")
    return [text]


class AtomicClaimExtractor:
    def extract(self, text: str) -> list[Claim]:
        candidates = sentences(text)
        # Preserve the original input limit even when repeated or nonfactual.
        if len(candidates) > 100:
            raise ValueError("Provide at most 100 sentence candidates.")
        claims = []
        for sentence in candidates:
            normalized = " ".join(sentence.split())
            if normalized.endswith("?") or _SUBJECTIVE.search(normalized):
                continue
            # The RHS may include 'found that'; only protect scoping in the LHS.
            # Split independent subjects before recursively considering the parts.
            pieces = [normalized]
            for join in re.finditer(r",\s+and\s+", normalized, re.I):
                left, right = normalized[:join.start()], normalized[join.end():]
                if (_CLAUSE.match(left) and _CLAUSE.match(right)
                        and not re.search(r'\b(?:if|unless|not|never|may|might|could|would|that)\b|["“”]', left, re.I)):
                    pieces = _split_clause(left) + _split_clause(right)
                    break
            else:
                pieces = _split_clause(normalized)
            for piece in pieces:
                if _SUBJECTIVE.search(piece):
                    continue
                if len(pieces) > 1:
                    piece = piece[0].upper() + piece[1:]
                    if not piece.endswith((".", "!", "?")):
                        piece += "."
                claims.append({"text": piece})
        if len(claims) > 100:
            raise ValueError("Extraction exceeds the limit of 100 atomic claims.")
        try:
            output = ClaimExtractionOutput.model_validate({"claims": claims})
        except ValidationError as exc:
            raise ClaimExtractionError("Claim extraction failed validation.") from exc
        return [Claim(text=claim.text) for claim in output.claims]
