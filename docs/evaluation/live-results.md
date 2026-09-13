# Live verification benchmark

Verifier plus validation; supplied fixture passages, no extraction/retrieval.

Model: Qwen3-4B-Instruct-2507 Q3_K_S; runtime: llama.cpp b10809; threads: 4.
Run started: 2026-09-13T16:32:20.755325+00:00. One run per case, no expectation changes.

**22/26 passed (84.6%).**

Median all cases: 38.99s; warm model median: 39.31s.

Citations valid means canonical source/page/text and backend quote checks passed; it does not establish correct entailment.
Empty-evidence and injection controls abstain without a model call. Raw inputs, outputs, prompt/fixture hashes and runtime timings are in the adjacent JSON file.

## Verdict class

| Group | Passed / total | Accuracy |
| --- | --- | --- |
| contradicted | 7 / 8 | 87.5% |
| insufficient_evidence | 4 / 7 | 57.1% |
| partially_supported | 5 / 5 | 100.0% |
| supported | 6 / 6 | 100.0% |

## Reasoning category

| Group | Passed / total | Accuracy |
| --- | --- | --- |
| causality | 0 / 1 | 0.0% |
| comparison | 1 / 1 | 100.0% |
| compound | 1 / 2 | 50.0% |
| conflict | 1 / 1 | 100.0% |
| direction | 1 / 1 | 100.0% |
| empty evidence | 1 / 1 | 100.0% |
| entity | 0 / 1 | 0.0% |
| injection | 1 / 1 | 100.0% |
| irrelevance | 1 / 1 | 100.0% |
| joint evidence | 1 / 1 | 100.0% |
| missing detail | 1 / 1 | 100.0% |
| modality | 0 / 1 | 0.0% |
| negation | 1 / 1 | 100.0% |
| paraphrase | 1 / 1 | 100.0% |
| quantity | 6 / 6 | 100.0% |
| scope | 2 / 2 | 100.0% |
| temporal | 3 / 3 | 100.0% |

## Every case

| ID / category | Claim | Expected | Actual | Pass | Seconds | Citations valid | Failure |
| --- | --- | --- | --- | --- | --- | --- | --- |
| paraphrase / paraphrase | The study recruited 312 adult participants. | supported | supported | yes | 102.98 | True | — |
| negation / negation | The intervention significantly reduced blood pressure. | contradicted | contradicted | yes | 31.51 | True | — |
| number_equal / quantity | The trial enrolled 312 participants. | supported | supported | yes | 32.25 | True | — |
| number_conflict / quantity | The trial enrolled 312 participants. | contradicted | contradicted | yes | 26.29 | True | — |
| greater_than / quantity | More than 300 people participated in the trial. | supported | supported | yes | 40.95 | True | — |
| less_than / quantity | Fewer than 300 people participated in the trial. | contradicted | contradicted | yes | 39.48 | True | — |
| range_support / quantity | The trial enrolled between 300 and 350 participants. | supported | supported | yes | 34.42 | True | — |
| range_uncertainty / quantity | The trial enrolled exactly 312 participants. | partially_supported | partially_supported | yes | 41.50 | True | — |
| date_precision / temporal | The spacecraft launched in March 2025. | supported | supported | yes | 33.31 | True | — |
| date_conflict / temporal | The spacecraft launched in April 2025. | contradicted | contradicted | yes | 45.33 | True | — |
| before_after / temporal | The survey occurred before the intervention. | contradicted | contradicted | yes | 55.82 | True | — |
| modality / modality | The treatment reduces symptoms. | insufficient_evidence | partially_supported | no | 39.31 | True | model reasoning error |
| some_all / scope | All participants improved. | partially_supported | partially_supported | yes | 43.71 | True | — |
| correlation / causality | Exercise causes lower stress. | insufficient_evidence | partially_supported | no | 45.48 | True | model reasoning error |
| direction / direction | Blood pressure increased after the intervention. | contradicted | contradicted | yes | 33.79 | True | — |
| comparison / comparison | Group A had higher scores than Group B. | contradicted | contradicted | yes | 38.66 | True | — |
| missing_qualifier / scope | The treatment improved sleep in all patients. | partially_supported | partially_supported | yes | 38.06 | True | — |
| unsupported_detail / missing detail | The trial enrolled 312 adults. | partially_supported | partially_supported | yes | 39.93 | True | — |
| entity_mismatch / entity | Trial Alpha enrolled 312 participants. | insufficient_evidence | contradicted | no | 34.89 | True | model reasoning error |
| source_disagreement / conflict | The trial enrolled 312 participants. | insufficient_evidence | insufficient_evidence | yes | 57.81 | True | — |
| lexical_overlap / irrelevance | The intervention reduced mortality. | insufficient_evidence | insufficient_evidence | yes | 32.24 | True | — |
| joint_support / joint evidence | The trial enrolled 312 adults who completed an online survey. | supported | supported | yes | 65.92 | True | — |
| partial_clause / compound | The trial enrolled adults and provided free transport. | partially_supported | partially_supported | yes | 30.31 | True | — |
| contradicted_clause / compound | The trial enrolled adults and provided free transport. | contradicted | insufficient_evidence | no | 55.96 | True | conflict-handling issue |
| no_evidence / empty evidence | The spacecraft landed on Mars. | insufficient_evidence | insufficient_evidence | yes | 0.00 | True | — |
| prompt_injection / injection | The trial enrolled 312 participants. | insufficient_evidence | insufficient_evidence | yes | 0.00 | True | — |
