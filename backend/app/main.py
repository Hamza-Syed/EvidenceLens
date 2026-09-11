from fastapi import FastAPI, File, HTTPException, UploadFile

from .documents import DocumentError, DocumentStore, extract_pdf
from .models import UploadResponse, VerificationRequest, VerificationResponse
from .services import (ClaimExtractor, ExactSentenceVerifier, HashVectorRetriever,
                       Retriever, SentenceClaimExtractor, Verifier)

MAX_FILE_BYTES = 10 * 1024 * 1024


def create_app(*, store: DocumentStore | None = None,
               extractor: ClaimExtractor | None = None,
               retriever: Retriever | None = None,
               verifier: Verifier | None = None) -> FastAPI:
    app = FastAPI(title="EvidenceLens", version="0.1.0")
    documents = store if store is not None else DocumentStore()
    claim_extractor = extractor if extractor is not None else SentenceClaimExtractor()
    evidence_retriever = retriever if retriever is not None else HashVectorRetriever()
    evidence_verifier = verifier if verifier is not None else ExactSentenceVerifier()

    @app.post("/api/documents", response_model=UploadResponse, status_code=201)
    def upload(files: list[UploadFile] = File(...)) -> UploadResponse:
        try:
            if not 1 <= len(files) <= 10:
                raise HTTPException(422, "Upload between 1 and 10 PDFs.")
            batch = []
            for file in files:
                name = (file.filename or "document.pdf").replace("\\", "/").rsplit("/", 1)[-1]
                if not name.lower().endswith(".pdf"):
                    raise HTTPException(422, "Only PDF files are supported.")
                content = file.file.read(MAX_FILE_BYTES + 1)
                if len(content) > MAX_FILE_BYTES:
                    raise HTTPException(413, "PDF exceeds the 10 MiB limit.")
                try:
                    batch.append(extract_pdf(name, content))
                except DocumentError as exc:
                    raise HTTPException(422, str(exc)) from exc
            try:
                documents.add_batch(batch)
            except DocumentError as exc:
                raise HTTPException(413, str(exc)) from exc
            return UploadResponse(documents=[document for document, _ in batch])
        finally:
            for file in files:
                file.file.close()

    @app.post("/api/verifications", response_model=VerificationResponse)
    def verify(request: VerificationRequest) -> VerificationResponse:
        try:
            passages = documents.passages(request.document_ids)
        except KeyError as exc:
            raise HTTPException(404, "Document not found. Upload it again if the backend restarted.") from exc
        try:
            claims = claim_extractor.extract(request.text)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return VerificationResponse(results=[
            evidence_verifier.verify(claim, evidence_retriever.retrieve(claim, passages))
            for claim in claims
        ])

    return app


app = create_app()
