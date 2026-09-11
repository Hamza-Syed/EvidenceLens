import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_cache_dir: str = str(Path(__file__).resolve().parents[2] / ".cache" / "fastembed")
    embedding_threads: int = Field(default=2, ge=1, le=32)
    retrieval_top_k: int = Field(default=5, ge=1, le=50)
    retrieval_min_similarity: float = Field(default=0.45, ge=-1, le=1, allow_inf_nan=False)
    chunk_max_chars: int = Field(default=1000, ge=100, le=2000)
    chunk_overlap_chars: int = Field(default=150, ge=0, le=500)

    @model_validator(mode="after")
    def check_overlap(self) -> "Settings":
        if self.chunk_overlap_chars >= self.chunk_max_chars:
            raise ValueError("Chunk overlap must be smaller than chunk size.")
        return self

    @classmethod
    def from_env(cls) -> "Settings":
        return cls.model_validate({
            field: os.environ[f"EVIDENCELENS_{field.upper()}"]
            for field in cls.model_fields
            if f"EVIDENCELENS_{field.upper()}" in os.environ
        })
