from collections.abc import Sequence
from threading import Lock
from typing import Protocol

from .config import Settings
from .errors import EmbeddingError


class EmbeddingProvider(Protocol):
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class FastEmbedProvider:
    """Lazy CPU inference; downloads model weights, never uploads document text."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None
        self._lock = Lock()

    def _load(self):
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(
                model_name=self.settings.embedding_model,
                cache_dir=self.settings.embedding_cache_dir,
                threads=self.settings.embedding_threads,
                providers=["CPUExecutionProvider"],
            )
        return self._model

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            with self._lock:
                return [value.tolist() for value in self._load().passage_embed(list(texts), batch_size=32)]
        except Exception as exc:
            raise EmbeddingError("Local embedding model is unavailable. Check the model cache and configuration.") from exc

    def embed_query(self, text: str) -> list[float]:
        try:
            with self._lock:
                return next(iter(self._load().query_embed(text))).tolist()
        except Exception as exc:
            raise EmbeddingError("Local embedding model is unavailable. Check the model cache and configuration.") from exc
