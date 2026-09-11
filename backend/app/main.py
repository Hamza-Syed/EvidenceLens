from fastapi import FastAPI, File, HTTPException, UploadFile

from .documents import DocumentError, DocumentStore, extract_pdf
from .claims import AtomicClaimExtractor
from .config import Settings
from .embeddings import FastEmbedProvider
from .errors import ClaimExtractionError, EmbeddingError, EvidenceScopeError
from .models import UploadResponse, VerificationRequest, VerificationResponse
from .retrieval import PassageIndexer, SemanticRetriever, scoped_evidence
from .services import ClaimExtractor, ExactSentenceVerifier, Retriever, Verifier

MAX_FILE_BYTES = 10 * 1024 * 1024


def create_app(*, store: DocumentStore | None = None,
               extractor: ClaimExtractor | None = None,
               retriever: Retriever | None = None,
               verifier: Verifier | None = None,
               settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings.from_env()
    app = FastAPI(title="EvidenceLens", version="0.2.0")
    documents = store if store is not None else DocumentStore()
    claim_extractor = extractor if extractor is not None else AtomicClaimExtractor()
    evidence_retriever = retriever if retriever is not None else SemanticRetriever(
        FastEmbedProvider(config), top_k=config.retrieval_top_k,
        min_similarity=config.retrieval_min_similarity,
    )
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
                    batch.append(extract_pdf(name, content, max_chars=config.chunk_max_chars,
                                             overlap_chars=config.chunk_overlap_chars))
                except DocumentError as exc:
                    raise HTTPException(422, str(exc)) from exc
            try:
                if isinstance(evidence_retriever, PassageIndexer):
                    evidence_retriever.index([passage for _, passages in batch for passage in passages])
                documents.add_batch(batch)
            except EmbeddingError as exc:
                raise HTTPException(503, str(exc)) from exc
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
        except ClaimExtractionError as exc:
            raise HTTPException(502, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        try:
            return VerificationResponse(results=[
                evidence_verifier.verify(claim, scoped_evidence(
                    evidence_retriever.retrieve(claim, passages), passages))
                for claim in claims
            ])
        except EmbeddingError as exc:
            raise HTTPException(503, str(exc)) from exc
        except EvidenceScopeError as exc:
            raise HTTPException(502, str(exc)) from exc

    return app


app = create_app()
