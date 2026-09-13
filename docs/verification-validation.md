# Semantic verification milestone validation

Historical record for the previous milestone. The subsequent complete 26-case
evaluation and performance results are in [evaluation/README.md](evaluation/README.md).

Validated on Windows with Python 3.14, Next.js 16.3.4, llama.cpp b10809, and
Qwen3-4B-Instruct-2507 Q3_K_S. The configured model alias is
`evidencelens-verifier`; embeddings remain local MiniLM through FastEmbed.

## Results

| Check | Result |
| --- | --- |
| Complete backend suite, with real embedding tests enabled | 142 passed; 26 optional live-verifier cases skipped |
| Selected live pipeline benchmark: missing detail, unrelated evidence, joint support, document instruction | 4 passed; 22 deselected |
| Final live source-disagreement check | 1 passed; 25 deselected |
| TypeScript: `npm run typecheck` | Passed |
| Production frontend: `npm run build` | Passed |
| Production frontend proxy smoke test | All three cases passed with expected citations |
| Git whitespace check | Passed |

The existing 78 backend cases are retained. There are 64 additional offline
checks for structured outputs, all verdict categories, citation validation,
provider transport/failures, scope, conflicts, and injection handling. The
26-case human-readable benchmark covers the requested reasoning categories;
mocked responses validate application behavior and do not establish model accuracy.
Only the five named benchmark cases were rerun live on the final implementation;
the other 21 benchmark cases were not evaluated live in this milestone. The
document-instruction case exercises the deterministic guard without a model call.

## Production end-to-end examples

`scripts/smoke_verification.py` uploaded a synthetic PDF through the running
Next.js proxy, using the real backend, embeddings, and local verifier:

| Claim | Verdict | Decisive evidence |
| --- | --- | --- |
| More than 300 people participated in the trial. | supported | “The trial enrolled 312 participants.” — verification-smoke.pdf, page 1 |
| The intervention significantly reduced blood pressure. | contradicted | “The intervention did not significantly reduce blood pressure.” — verification-smoke.pdf, page 2 |
| Jupiter has ninety-five moons. | insufficient_evidence | No candidate evidence; no citations or provider call |

The selected benchmark additionally established partial support for a missing
count, support from two passages jointly, abstention despite related but irrelevant
evidence, and abstention for materially conflicting sources.

## Findings and limitations

- The first live evaluation exposed incorrect partial/joint labels and a dangerous
  response to document instructions. The final implementation assesses passages
  before emitting the final verdict, clarifies partial/joint semantics, and abstains
  before inference on obvious verifier-directed instructions. Fixture expectations
  were not weakened. Unknown injection patterns can still evade this small guard;
  legitimate discussion of instructions can trigger false abstention.
- The local grammar engine rejected deeply repeated length constraints. Generation
  now uses structural schema constraints; full Pydantic, byte, token, and citation
  limits remain mandatory after generation. The original failure returned HTTP 503,
  never support.
- The larger weight download exhausted available disk space. Its incomplete file
  was removed; the smaller quantization was downloaded and checksum-verified. Setup
  now checks disk capacity and supports resuming partial downloads.
- An initial uncached request took about 95 seconds; observed warm examples took
  roughly 27–50 seconds. This is not a formal latency benchmark. Long requests can
  exceed provider or frontend time budgets; the frontend proxy allows 180 seconds.
- Models remain fallible. A matching quote proves provenance, not correct inference.
  Numeric, temporal, causal, entity, and qualifier reasoning need broader live
  evaluation. Conflict detection cannot inspect passages omitted by retrieval.
- One existing Starlette/AnyIO deprecation warning remains. The model loader also
  warns about reclassifying a control-looking token and proceeds. Next.js identifies
  the configured proxy timeout as experimental; its production build passes.

No authentication, persistence, accounts, payments, or web search were added.
Documents and vectors remain in memory; downloaded runtime/model assets are ignored
by Git. See README.md for setup, exact verdict definitions, and test commands.
