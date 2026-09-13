# Privacy and threat model

EvidenceLens is a single-user local development application, not a hosted secure
document vault. There is no authentication or tenant boundary. Keep the frontend,
backend and verifier bound to loopback; do not expose their ports to a network.

## Data flow

- In the default setup, the browser uploads PDFs to the local FastAPI process.
  PyMuPDF extracts text locally, preserving filenames and one-based page numbers.
- Local FastEmbed creates embeddings. Selected document IDs restrict retrieval.
  The verifier receives one atomic claim and its retrieved passages, with source
  metadata and the system instructions. It cannot access the document store or
  invoke web search. It still has pretrained knowledge: prompting cannot formally
  prove that none influences a decision.
- The prepared Qwen verifier listens on `127.0.0.1:8081`. An explicitly configured
  remote verifier or backend changes this privacy boundary. Check configuration
  before using sensitive material. Public model downloads require network access;
  subsequent local inference can run offline.
- Documents and vectors live in backend memory. The model server also holds input
  tokens in its in-memory prompt/KV cache. Restarting the backend drops its document
  store, but does not clear the separate verifier cache. Restart that process too
  when ending a sensitive session. There is no secure-erasure guarantee: OS paging,
  crash dumps, browser state, and normal runtime behavior may retain data.
- Debug logs contain identifiers, ranking values and verdicts, not document text.
  The evaluation recorder deliberately stores public synthetic fixture inputs and
  model responses; do not adapt it to private documents without reviewing output.

## Controls and residual risks

| Threat | Control | Limitation |
| --- | --- | --- |
| Evidence from another document | Candidate and final citation checks against selected canonical passages | Local users of the unauthenticated process share one store; IDs are not access control |
| Invented citations | Every assessment and exact quote validated; metadata restored from original passages | Valid provenance does not prove semantic correctness |
| Document prompt injection | Separate system/data messages; obvious verifier-directed instructions trigger abstention | Novel instructions may evade the small guard; legitimate discussion may trigger it |
| Misleading agreement | All candidates assessed; detected source conflicts force abstention | Retrieval may miss a conflicting source; model may misread one |
| Unavailable or malformed inference | Explicit 502/503; no fabricated fallback results | A whole verification batch fails if one claim fails |
| Excessive input | File, page, character, candidate, token and output bounds | Limits do not make a public deployment safe against denial of service |

No formal security, factual correctness, or complete prompt-injection immunity is
claimed. Source accuracy and authority are outside the verification boundary.
