# EvidenceLens

Check factual text against user-supplied PDF documents, with document and page citations.

## First-slice plan and boundaries

1. Define typed domain models and API contracts.
2. Extract page-local passages from PDFs and store them in memory.
3. Split submitted text into sentence candidates, retrieve passages with deterministic hashed bag-of-words cosine vectors, and verify only those passages.
4. Connect a Next.js upload and verification UI.
5. Test document isolation, citations, conservative decisions, and API failures.

This slice is a runnable development baseline, not a complete semantic fact checker. Sentence candidates are not full atomic decomposition (compound statements remain intact). The deterministic verifier returns `supported` only for an exact complete sentence match after whitespace normalization; all other claims return `insufficient_evidence`. It cannot interpret paraphrases, detect contradictions, or resolve conflicting sources. `partially_supported` and `contradicted` are reserved in the contract for a future evidence-only semantic verifier. An exact match establishes that a passage states the claim, not that the source is true or that other passages agree.

No external model or knowledge source is called. Retrieval similarity only ranks passages; it is never a confidence or reliability score. Claim extraction, retrieval, and verification have separate Python protocols for future providers.

Documents live in process memory, disappear on restart, and belong to a single local workspace. Run one backend worker. Do not expose this development slice as a shared public service. Authentication, accounts, payments, persistent storage, OCR, and semantic AI integration are outside this slice.

## Run

Requires Python 3.11+ and Node.js 20.9+.

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -e "./backend[dev]"
.\venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The frontend proxies `/api/*` to `http://127.0.0.1:8000`; set `BACKEND_URL` before starting Next.js to change this. FastAPI's interactive contract is at http://127.0.0.1:8000/docs.

Generate an example PDF with `venv\Scripts\python.exe sample_data/generate_sample.py`. Upload `sample_data/observatory.pdf`, then paste “The observatory opened in 1998.” (supported) and “The observatory has ten telescopes.” (insufficient evidence).

## API and models

- `Document`: UUID, original file name, page count, passage count.
- `Passage`: UUID, document UUID/name, one-based page number, extracted text.
- `Claim`: UUID and sentence text.
- `Evidence`: a cited passage, without any reliability score.
- `VerificationResult`: claim, classification, explanation, retrieved evidence.
- `POST /api/documents`: multipart `files` (one or more PDFs); returns `201 {documents: Document[]}`. Upload batches are atomic. Limits: 10 files per batch, 10 MiB per file, 200 pages per file, 100 documents per process, and 2 million extracted characters per file. Image-only and encrypted PDFs are rejected.
- `POST /api/verifications`: JSON `{text: string, document_ids: UUID[]}`; returns `{results: VerificationResult[]}`. Requires at least one known document, at most 100 IDs, 20,000 text characters, and 100 sentence candidates. Only selected documents participate in retrieval.
- Errors: `413` size/capacity limits, `422` invalid inputs/PDFs or too many claims, `404` unknown document. No document is committed when a batch fails.

## Validate

```powershell
.\venv\Scripts\python.exe -m pytest backend/tests -q
cd frontend
npm run typecheck
npm run build
```

Next slice: introduce tested atomic claim extraction and an evidence-only semantic verifier, including contradiction/partial-support fixtures and citation validation, without changing the transport contract.
