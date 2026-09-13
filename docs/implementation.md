# Pipeline implementation reference

### Claim extraction

`AtomicClaimExtractor` implements the existing `ClaimExtractor` protocol with deterministic English heuristics. It recognizes common predicates, splits independent clauses and simple shared-subject predicates, preserves reporting phrases, and skips obvious opinions and questions. It does not split every occurrence of “and.” Conditions, negation, modality, quotes, and reported clauses are conservatively retained when splitting could change meaning.

For example:

> The study included 312 adults. Participants completed the survey online, and researchers found that sleep quality improved after the intervention.

becomes three typed claims: “The study included 312 adults.”, “Participants completed the survey online.”, and “Researchers found that sleep quality improved after the intervention.”

All output passes a bounded Pydantic schema. `StructuredClaimExtractor` is an optional injection adapter for a future `StructuredClaimProvider`; it accepts only JSON `{ "claims": [{ "text": "..." }] }`, rejects extra fields, wrong types, blank text, oversized responses, and more than 100 claims, and reports malformed output as HTTP 502. Claim extraction still uses heuristics by default; semantic verification uses a separate local model. Schema validation checks structure, not whether a model preserved the input's meaning.

### Chunking and embeddings

PDF text is split into verbatim page-local windows, default maximum **1,000 characters**, with up to **150 characters of overlap**. The splitter prefers sentence boundaries, then word boundaries. Long sentences or tokens can require a hard cut. Whitespace trimming is the only change to citation text. Chunks never cross pages; every chunk retains its own document UUID, filename, one-based page number, and passage UUID.

The smaller windows reduce topic dilution and overlap retains some surrounding context. Internal chunk metadata tracks which original page sentences remain complete, so a hard-cut sentence fragment cannot become exact-match support. This metadata does not change the evidence API. Character limits are a practical English approximation, not a tokenizer limit: unusual text can still exceed a model's token budget, and tables, complex PDF reading order, and sentences spanning pages remain limitations. Overlapping passages may both be retrieved.

`FastEmbedProvider` implements a replaceable `EmbeddingProvider` with separate document and query methods. The default is **`sentence-transformers/all-MiniLM-L6-v2`**, a local CPU embedding model run through FastEmbed/ONNX. The model was chosen after comparing it with BGE-small on the committed fixtures; MiniLM ranked the intended source first for every positive fixture. This small evaluation is not a general quality benchmark. See [FastEmbed retrieval usage](https://qdrant.github.io/fastembed/qdrant/Retrieval_with_FastEmbed/) and [supported models](https://qdrant.github.io/fastembed/examples/Supported_Models/).

Uploads generate chunk embeddings before documents become available. Vectors are validated for count, dimensions, finite values, and nonzero norm. `SemanticRetriever` caches up to 4,096 content-keyed vectors in memory, reuses them for subsequent requests, and recomputes evicted entries as needed. It ranks only the selected passages by cosine similarity using a simple linear scan; no vector database is required for this local milestone. Query and document vectors always use the same provider instance/model.

### Verification and trust boundaries

**Retrieval determines relevance. Verification determines evidentiary relationship.**

The existing `Verifier` interface now has two implementations: `EvidenceGroundedVerifier` (the default) and `ExactSentenceVerifier` (an explicitly selected development baseline). The semantic verifier depends on a provider protocol; `ChatCompletionProvider` handles a compatible chat-completions HTTP endpoint. Local llama.cpp is the prepared deployment, with no tools or network searches available to the model. A hosted compatible provider can be configured explicitly; that would transmit the claim and candidate passages to that provider.

| Verdict | Meaning |
| --- | --- |
| `supported` | All material factual components and qualifiers are established, including by paraphrase or joint evidence. |
| `partially_supported` | A meaningful portion is established; another material component is missing, and none is directly contradicted. Topic overlap alone does not qualify. |
| `contradicted` | At least one material component directly conflicts with evidence for the same entity, event, and temporal scope. |
| `insufficient_evidence` | Evidence cannot establish the claim or a meaningful portion, cannot directly contradict it, or materially conflicting sources require abstention. |

For example, 312 participants supports “more than 300”; adults without a count partially supports “312 adults”; 212 contradicts an asserted exact total of 312. Possibility does not establish actuality, association does not establish causation, and some does not establish all. The benchmark distinguishes numeric ranges, date precision, before/after, entity identity, and comparison direction.

The verifier receives **only the atomic claim, selected retrieved passages, and their metadata**. Selected-document scoping is checked before verification and every returned citation is checked again afterward. The provider has no document store, unselected passages, browsing tools, or retrieval scores. Similarity is never supplied as proof or displayed as confidence.

Each model result must satisfy `VerifierOutput`: verdict, concise explanation, decisive evidence labels, conflict flag, and one assessment per candidate. Non-irrelevant assessments require verbatim source quotes. The backend rejects extra fields (including confidence), unknown or duplicate labels, omitted assessments, invented quotes, inconsistent decisions, and unsupported sentence fragments. Stable UUIDs and original filenames/page numbers are restored from canonical candidates; the model never supplies citation metadata to the UI. Quote and schema validation establish provenance and structure, not entailment correctness.

The transport requests structural schema constraints; length and collection bounds are enforced locally by the full Pydantic schema to avoid excessive grammar expansion in local runtimes. HTTP output bytes and generation tokens are also bounded. The frontend proxy allows up to 180 seconds for local inference; large multi-claim requests can exceed that budget and should be split into smaller submissions.

**Conflicts:** the model must inspect every candidate and flag material source disagreement. A conflict flag, or whole-claim support alongside a materially contradictory assessment, forces `insufficient_evidence` with an explicit conflict explanation and citations from both sides. No authority ranking is invented. Supporting one clause while contradicting a different clause is a contradicted compound claim, not automatically source disagreement. Disagreement in passages that retrieval misses cannot be detected.

**Prompt injection:** instructions live in a system message; claim, filenames, and evidence are serialized separately as untrusted JSON data. A small deterministic guard abstains before calling the provider when content contains obvious verifier-directed instructions such as ignoring previous instructions, forcing a verdict, or requesting evidence IDs. It conservatively abstains on the entire claim, including when a suspicious passage also contains facts. Other content remains untrusted data under the model prompt. Legitimate discussion of these instructions can trigger abstention, and the pattern guard is not a complete injection detector. The initial local-model evaluation demonstrated that prompting alone was insufficient; the application does not rely on that alone.

**Fail closed:** empty evidence abstains without a provider call. Malformed, incomplete, oversized, ungrounded, or inconsistent model output returns HTTP 502; timeouts, unavailable providers, and excessive model inputs return HTTP 503. The API returns no partial batch of verdicts when one fails. There is no automatic fallback to exact-match support. Logs distinguish transport and validation failures without raw prompts, responses, credentials, or chain-of-thought.

**Observability:** set `EVIDENCELENS_DEBUG_PIPELINE=true` to log claim UUIDs, candidate UUIDs/ranks/cosine values, selected UUIDs, and final verdicts. Match claim UUIDs to the response for local debugging. Candidate lists remain internal; the UI shows only decisive passages, which may support, contradict, or demonstrate conflict.

**Limitations:** local models are fallible and may misinterpret quantities, qualifiers, causality, conflicts, or malicious text despite a valid schema. The checks cannot prove that an explanation follows logically from its quotes or that the model ignored all prior knowledge. Atomic extraction remains a conservative English heuristic; pronouns, uncommon verbs, complex syntax, and non-English text can remain compound or be missed. Retrieval can omit evidence. Model context/input limits bound each request; long inputs fail explicitly rather than being silently truncated. Document truth and source authority are not independently established. Documents and vectors remain in memory.
