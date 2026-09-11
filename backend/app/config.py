import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_cache_dir: str = str(Path(__file__).resolve().parents[2] / ".cache" / "fastembed")
    embedding_threads: int = Field(default=2, ge=1, le=32)
    retrieval_top_k: int = Field(default=5, ge=1, le=50)
    retrieval_min_similarity: float = Field(default=0.45, ge=-1, le=1, allow_inf_nan=False)
    chunk_max_chars: int = Field(default=1000, ge=100, le=2000)
    chunk_overlap_chars: int = Field(default=150, ge=0, le=500)
    verifier_mode: Literal["model", "exact"] = "model"
    verifier_base_url: str = "http://127.0.0.1:8081/v1"
    verifier_model: str = "evidencelens-verifier"
    verifier_api_key: SecretStr = SecretStr("")
    verifier_timeout_seconds: float = Field(default=120, gt=0, le=600, allow_inf_nan=False)
    verifier_max_input_chars: int = Field(default=16000, ge=1000, le=100000)
    debug_pipeline: bool = False

    @model_validator(mode="after")
    def check_overlap(self) -> "Settings":
        if self.chunk_overlap_chars >= self.chunk_max_chars:
            raise ValueError("Chunk overlap must be smaller than chunk size.")
        url = urlsplit(self.verifier_base_url)
        if (url.scheme not in {"http", "https"} or not url.hostname or url.username
                or url.password or url.query or url.fragment):
            raise ValueError("Verifier endpoint must be an HTTP(S) base URL without credentials or query parameters.")
        return self

    @classmethod
    def from_env(cls) -> "Settings":
        return cls.model_validate({
            field: os.environ[f"EVIDENCELENS_{field.upper()}"]
            for field in cls.model_fields
            if f"EVIDENCELENS_{field.upper()}" in os.environ
        })
