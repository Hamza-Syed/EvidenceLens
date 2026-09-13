# Evaluation, performance and showcase milestone

Measured on September 13, 2026: Windows, Python 3.14, Next.js 16.3.4,
llama.cpp b10809, Qwen3-4B-Instruct-2507 Q3_K_S. The machine reports eight logical
processors; the verifier uses four threads, one slot and an 8,192-token context.
The model, verifier prompt, expectations and production validation rules were not
changed during this milestone.

## Complete live benchmark

**22 of 26 cases passed: 84.6%.** Of the 24 cases that invoked the model, 20 passed
(83.3%). Two controls—empty evidence and obvious document instructions—correctly
abstained before inference. They are application controls, not evidence of model
reasoning or injection resistance.

| Expected verdict | Passed / total | Accuracy |
| --- | --- | --- |
| Supported | 6 / 6 | 100% |
| Partially supported | 5 / 5 | 100% |
| Contradicted | 7 / 8 | 87.5% |
| Insufficient evidence | 4 / 7 | 57.1% |

Category performance: quantities 6/6, temporal 3/3, scope 2/2, compound claims 1/2;
modality, causality and entity identity each 0/1. Paraphrase, negation, comparison,
direction, missing detail, source conflict, unrelated evidence, joint evidence,
empty evidence and injection each passed their single case. These tiny category
samples are not estimates of general-domain accuracy.

The [per-case table](live-results.md) lists category, claim, expected/final actual
verdict, pass/fail, latency, citation validity and failure classification for every
case. [Raw JSON](live-results.json) preserves source inputs, full provider envelopes,
runtime token/timing data, final explanations/citations and fixture/prompt hashes.
There was one scored run per case, no expectation edits or selective reruns.
The separate warm repeat below is a performance probe and does not replace a score.

### Failures retained

| Case | Expected → actual | Classification and observed cause |
| --- | --- | --- |
| `modality` | insufficient → partial | Model reasoning error: possibility was counted as partial evidence of an actual effect. |
| `correlation` | insufficient → partial | Model reasoning error: association was counted as partial causal support. |
| `entity_mismatch` | insufficient → contradicted | Model reasoning error: Trial Beta's enrollment was treated as contradicting a statement about Trial Alpha. |
| `contradicted_clause` | contradicted → insufficient | Conflict-handling issue: the model mislabeled support for one clause as whole-claim support and set `conflict=true`. Its raw verdict was contradicted; mandatory conservative conflict validation produced abstention. |

All returned citations passed original source/page/text and exact-quote checks.
There were no validation rejections or provider failures in this benchmark. The
four semantic errors still passed those checks: provenance validation is not an
entailment proof. No guard or prompt was tailored to these failures.

This evaluates the verifier plus validation with **supplied fixture passages**.
It bypasses PDF extraction, claim extraction and retrieval; failures in those
stages cannot be inferred from this score. The real-pipeline demo below exercises
those stages separately. The suite is small, synthetic and previously used during
development, not a held-out generalization benchmark or safety certification.

## Performance profile

| Measurement | Observed time |
| --- | --- |
| Model process start → listening, including load/default warmup | 20.33 s |
| First uncached verifier request, excluding server startup | 102.98 s |
| All 26 cases median / p90, including two no-call controls | 38.99 / 57.81 s |
| 23 warm model calls median / p90 | 39.31 / 55.96 s |
| Three-page PDF extraction | 26 ms |
| Four atomic claims extracted | 0.67 ms |
| Embedding initialization from cached weights + three-page indexing | 2.39 s |
| First retrieval / four subsequent retrievals combined | 54 / 189 ms |
| Full adapter/validation replay median / maximum across 24 outputs | 1.55 / 16.74 ms |
| Metadata HTTP round trip median, backend / production frontend proxy | 2.96 / 6.13 ms |

P90 uses nearest rank; the small sample and varied cases limit interpretation.
The [pipeline profile](pipeline-profile.json) replays actual public model responses
through serialization, Pydantic and citation/conflict validation without inference.
Metadata GET measurements are only an overhead baseline, not an isolated measure
of verification-request overhead. The demo records its complete HTTP duration.

### Before/after: keep the server warm

| Same paraphrase case | Cold request | Warm repeat after prewarming |
| --- | --- | --- |
| Total adapter + HTTP time | 102.98 s | 28.92 s |
| Prompt processing | 59.84 s | 4.34 s |
| Generation | 42.82 s | 24.55 s |
| Prompt tokens processed / cached | 693 / 0 | 32 / 661 |
| Output tokens | 141 | 112 |

See [warm raw response](warm-repeat.json). Both runs returned supported with valid
citations. Prefix reuse is enabled by the pinned runtime already; no caching of
verdicts was added. Different output lengths and shared-machine load also affect
the comparison. These are observational wall-clock measurements, with intermittent
development work on the same machine, not a controlled throughput study.

New `scripts/warm_verifier.py` checks loopback `/health` and runs a synthetic claim
through the real provider and all validation. The executed readiness check took
0.26 s and its validated prewarm request took 41.48 s. This shifts cold work before
a presentation; it does not eliminate that cost or guarantee fast responses.
Keep `scripts/start_local_verifier.ps1` running between requests. Do not restart
the model for every claim. Restart it when ending a sensitive session to drop its
in-memory prompt cache, subject to normal OS/runtime behavior.

### Options investigated

- Runtime help and response timings confirm default empty warmup and prompt-cache
  reuse. Explicit application-prefix prewarming is the only added operational change.
- Four threads on eight logical CPUs are retained. This milestone did not establish
  a better thread count through a controlled sweep, so no threading speedup is claimed.
- Generation dominates warm requests. The 1,600-token cap, complete assessments,
  exact quotes and prompt rules are retained; reducing them risks incomplete output
  or weaker decisions. No larger model, quantization change or hosted service was used.
- The backend already reuses one embedding provider/index. Retrieval and validation
  are small relative to inference; neither warrants architectural changes here.
- Parallel/batched model requests were not introduced. One-slot CPU inference is
  slow; concurrent users can queue and exhaust timeouts. The app remains single-user.

## Validation and real demo

Final backend suite with real embeddings: **149 passed, 26 optional live tests
skipped**. The normal model-independent suite remains available without either
model running; the opt-in live recorder above executed all 26 benchmark cases.
TypeScript validation and the production frontend build passed.

Try sample generates a fictional three-page PDF, uploads it through the ordinary
document endpoint, selects only that document, and fills four input claims. It does
not supply expected verdicts to the UI or bypass any pipeline stage. The elapsed
timer reports real time, with no completion percentages. Final results show claim
counts, verdict totals, explanations, expanded evidence, filenames and page numbers.

The executable `scripts/smoke_demo.py` records the production-proxy response in
[demo-results.json](demo-results.json) and checks all four verdicts and exact page
citations. The browser walkthrough additionally checks the rendered loading/results
states.

The production-proxy smoke check **passed in 123.61 seconds** for verification:

| Claim | Actual verdict | Decisive page |
| --- | --- | --- |
| More than 300 people participated in the trial. | supported | 1: The trial enrolled 312 participants. |
| Participants completed the survey online in ten minutes. | partially_supported | 3: Participants completed the survey online. |
| The intervention significantly reduced blood pressure. | contradicted | 2: The intervention did not significantly reduce blood pressure. |
| Jupiter has ninety-five moons. | insufficient_evidence | None; no retrieved evidence |

Every citation used `evidencelens-sample.pdf`, the uploaded document ID, and the
exact original page text. This demonstrates the four statuses on these synthetic
inputs; it does not remedy the benchmark's four reasoning failures.

## Changed files

- `backend/app/demo.py`, `backend/app/main.py`: generated sample PDF/input routes.
- `frontend/app/page.tsx`, `frontend/lib/api.ts`: Try sample upload flow, elapsed
  loading state, source/claim/verdict counts, expanded citations and privacy copy.
- `backend/tests/test_demo.py`, `backend/tests/test_evaluation.py`: seven additional
  deterministic tests covering demo upload/citations/atomic claims and evaluation tooling.
- `scripts/evaluate_verifier.py`, `scripts/profile_pipeline.py`,
  `scripts/warm_verifier.py`, `scripts/smoke_demo.py`: live recording, profiling,
  readiness/prewarming and real production-proxy demo checks.
- `sample_data/generate_demo.py`: portable generator for the same synthetic PDF.
- `README.md`, `docs/implementation.md`, `docs/privacy.md`,
  `docs/showcase/README.md`, `docs/verification-validation.md`: project presentation,
  architecture, detailed boundaries, showcase drafts and historical linkage.
- `docs/evaluation/`: this report, complete raw/tabular benchmark, warm repeat,
  pipeline timings and actual demo response.

## Warnings and review

- Starlette/AnyIO emits its existing `BlockingPortal` deprecation warning.
- Some sandbox test runs could not update an existing pytest cache; tests passed.
  The final full run used a fresh ignored cache and emitted only the dependency warning.
- The model loader reclassifies one control-looking token. Next.js identifies its
  configured proxy timeout as experimental. Both continued successfully.
- Git may warn about line-ending conversion and a sandbox-inaccessible global ignore
  file. Repository ignore rules were checked explicitly.

Privacy boundaries, prompt-injection limitations, separate verifier cache lifetime,
and the lack of authentication/persistence are documented in [privacy.md](../privacy.md).
Showcase scripts require a completed real run for a 30–60 second presentation;
they do not claim inference completes within that time.

The final 23-file review found no accidental machine-specific paths or unintended
large files. The largest addition is the 66 KB public raw benchmark record.
Repository ignore rules explicitly exclude model weights/caches, generated PDFs,
virtual environments, dependencies, build outputs and secret environment files.
Clean-clone instructions retain dependency/model preparation and separate local
process startup. The original benchmark fixture and verification rules are unchanged.
