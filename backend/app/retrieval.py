"""In-memory cosine index. Only the supplied passages are retrieval candidates."""

import hashlib
import math
from collections import OrderedDict
from collections.abc import Sequence
from threading import Lock
from typing import Protocol, runtime_checkable

from .embeddings import EmbeddingProvider
from .errors import EmbeddingError, EvidenceScopeError
from .models import Claim, Passage


@runtime_checkable
class PassageIndexer(Protocol):
    def index(self, passages: Sequence[Passage]) -> None: ...


def _unit_vector(values: Sequence[float]) -> tuple[float, ...]:
    if not values or any(isinstance(value, bool) or not isinstance(value, (float, int))
                         or not math.isfinite(value) for value in values):
        raise EmbeddingError("Embedding provider returned an invalid vector.")
    norm = math.sqrt(sum(value * value for value in values))
    if not math.isfinite(norm) or norm == 0:
        raise EmbeddingError("Embedding provider returned an invalid vector.")
    return tuple(value / norm for value in values)


class SemanticRetriever:
    def __init__(self, provider: EmbeddingProvider, *, top_k: int = 5,
                 min_similarity: float = 0.45, cache_size: int = 4096):
        if top_k < 1 or cache_size < 1 or not math.isfinite(min_similarity) or not -1 <= min_similarity <= 1:
            raise ValueError("Invalid retrieval configuration.")
        self.provider = provider
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.cache_size = cache_size
        self._cache: OrderedDict[str, tuple[float, ...]] = OrderedDict()
        self._dimensions: int | None = None
        self._lock = Lock()

    def _vectors(self, passages: Sequence[Passage]) -> list[tuple[float, ...]]:
        keys = [hashlib.sha256(passage.text.encode()).hexdigest() for passage in passages]
        with self._lock:
            missing = {key: passage.text for key, passage in zip(keys, passages) if key not in self._cache}
            computed: dict[str, tuple[float, ...]] = {}
            entries = list(missing.items())
            # Validate all vectors before changing the cache; batch size bounds inference memory.
            for start in range(0, len(entries), 32):
                batch = entries[start:start + 32]
                try:
                    raw = self.provider.embed_documents([text for _, text in batch])
                    if len(raw) != len(batch):
                        raise EmbeddingError("Embedding provider returned the wrong number of vectors.")
                    for (key, _), vector in zip(batch, raw):
                        computed[key] = _unit_vector(vector)
                except EmbeddingError:
                    raise
                except Exception as exc:
                    raise EmbeddingError("Document embedding failed.") from exc
            dimensions = {len(vector) for vector in computed.values()}
            if self._dimensions is not None:
                dimensions.add(self._dimensions)
            if len(dimensions) > 1:
                raise EmbeddingError("Embedding dimensions are inconsistent.")
            if dimensions:
                self._dimensions = next(iter(dimensions))
            vectors = [computed[key] if key in computed else self._cache[key] for key in keys]
            for key, vector in zip(keys, vectors):
                self._cache[key] = vector
                self._cache.move_to_end(key)
            while len(self._cache) > self.cache_size:
                self._cache.popitem(last=False)
            return vectors

    def index(self, passages: Sequence[Passage]) -> None:
        self._vectors(passages)

    def retrieve(self, claim: Claim, passages: Sequence[Passage]) -> list[Passage]:
        if not passages or not any(character.isalnum() for character in claim.text):
            return []
        # Never search the cache itself: the caller's selected passages define scope.
        vectors = self._vectors(passages)
        try:
            query = _unit_vector(self.provider.embed_query(claim.text))
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError("Claim embedding failed.") from exc
        if len(query) != len(vectors[0]):
            raise EmbeddingError("Query and document embedding dimensions differ.")
        ranked = []
        for passage, vector in zip(passages, vectors):
            score = sum(left * right for left, right in zip(query, vector))
            if score >= self.min_similarity:
                ranked.append((score, passage))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [passage for _, passage in ranked[:self.top_k]]


def scoped_evidence(candidates: Sequence[Passage], allowed: Sequence[Passage]) -> list[Passage]:
    """Reject altered text, forged attribution, or foreign passage IDs before verification."""
    by_id = {passage.id: passage for passage in allowed}
    result = []
    seen = set()
    for candidate in candidates:
        if by_id.get(candidate.id) != candidate:
            raise EvidenceScopeError("Retrieved evidence failed document scope validation.")
        if candidate.id not in seen:
            result.append(by_id[candidate.id])
            seen.add(candidate.id)
    return result
