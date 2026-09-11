from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Classification(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class Document(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    page_count: int = Field(ge=1)
    passage_count: int = Field(ge=1)


class Passage(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    document_name: str
    page_number: int = Field(ge=1)
    text: str


class ChunkedPassage(Passage):
    # Internal context for the temporary exact verifier; never added to API evidence.
    complete_sentences: tuple[str, ...] = Field(exclude=True)


class Claim(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    text: str


class Evidence(Passage):
    pass


class VerificationResult(DomainModel):
    claim: Claim
    classification: Classification
    explanation: str
    evidence: list[Evidence]


class UploadResponse(DomainModel):
    documents: list[Document]


class VerificationRequest(DomainModel):
    text: str = Field(min_length=1, max_length=20_000)
    document_ids: list[UUID] = Field(min_length=1, max_length=100)

    @field_validator("text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text must not be blank.")
        return value


class VerificationResponse(DomainModel):
    results: list[VerificationResult]
