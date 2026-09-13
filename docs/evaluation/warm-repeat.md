# Live verification benchmark

Verifier plus validation; supplied fixture passages, no extraction/retrieval.

Model: Qwen3-4B-Instruct-2507 Q3_K_S; runtime: llama.cpp b10809; threads: 4.
Run started: 2026-09-13T16:51:05.581482+00:00. One run per case, no expectation changes.

**1/1 passed (100.0%).**

Median all cases: 28.92s; warm model median: 28.92s.

Citations valid means canonical source/page/text and backend quote checks passed; it does not establish correct entailment.
Empty-evidence and injection controls abstain without a model call. Raw inputs, outputs, prompt/fixture hashes and runtime timings are in the adjacent JSON file.

## Verdict class

| Group | Passed / total | Accuracy |
| --- | --- | --- |
| supported | 1 / 1 | 100.0% |

## Reasoning category

| Group | Passed / total | Accuracy |
| --- | --- | --- |
| paraphrase | 1 / 1 | 100.0% |

## Every case

| ID / category | Claim | Expected | Actual | Pass | Seconds | Citations valid | Failure |
| --- | --- | --- | --- | --- | --- | --- | --- |
| paraphrase / paraphrase | The study recruited 312 adult participants. | supported | supported | yes | 28.92 | True | — |
