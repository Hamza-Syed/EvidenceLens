# Showcase drafts

## Short summary

I built EvidenceLens to check AI-generated factual claims against user-supplied
PDFs. It separates semantic retrieval from local-model verification and shows
validated document/page citations, including contradictions and abstentions.

## Project description

I built a Next.js/TypeScript interface and a modular FastAPI backend that extracts
page-preserving PDF text, identifies atomic claims, and retrieves relevant passages
using local embeddings. A replaceable local Qwen verifier assesses only those
candidate passages. A separate validation layer checks structured assessments,
source quotes, document scope, and decisive citation provenance before displaying
results. The system distinguishes support, partial support, contradiction, and
insufficient evidence; detected source conflicts cause conservative abstention.

I also built deterministic regression tests, an opt-in live-model benchmark that
records failures and timing, and a real-pipeline sample flow. See the linked
[evaluation record](../evaluation/README.md) for measured results rather than a
general accuracy claim.

## 30-second demo script

Prepare the model and run `scripts/warm_verifier.py` first. Load Try sample and
complete verification before presenting; say explicitly these are results from
that real run. Do not imply the CPU finished inference in 30 seconds.

“AI text can sound convincing without evidence. I built EvidenceLens to check it
against documents you choose. This fictional PDF says 312 participants: the
paraphrase ‘more than 300’ is supported. It says the survey was online, but gives
no duration, so that claim is only partly supported. The blood-pressure claim
reverses the source, and the unrelated claim gets an abstention. Every decisive
passage includes its filename and page.” Use the actual displayed results; if a
verdict differs, describe that model limitation instead of reading an expected label.

## 60-second demo script

Use the same preparation. Spend 10 seconds showing the selected synthetic PDF and
four input claims, then 30 seconds walking through the real results and expanded
citations. Explain that retrieval finds candidates; it does not establish truth.
Spend the final 20 seconds showing the architecture and actual benchmark failures.
Mention local CPU latency, imperfect extraction/retrieval/model reasoning, and the
fact that quote validation establishes provenance rather than proof. If starting a
fresh check, show the real elapsed-time state and explain it can take minutes; the
full inference need not fit within this narrated walkthrough.

## Technical highlights

- Page-local chunks and canonical source metadata survive the full pipeline.
- Replaceable embedding and verifier interfaces separate AI providers from domain logic.
- Document-scoped vector ranking is isolated from evidentiary decisions.
- Strict schemas, exact quotes, candidate assessments and final citation checks.
- Conservative handling of absent evidence, detected source conflicts and obvious instructions.
- Public raw evaluation artifacts distinguish live results from mocked test coverage.

## Limitations

Small synthetic benchmark, not representative validation across domains. CPU
inference is slow, document storage is temporary, and extraction is heuristic.
Models can produce plausible but incorrect interpretations despite valid citations.
Prompt injection defenses are incomplete. No authentication or formal guarantees.

## Suggested resume bullet

Built EvidenceLens, a Next.js/FastAPI application combining page-cited PDF extraction,
document-scoped semantic retrieval and local LLM verification; added strict citation
validation, conservative abstention, and a reproducible 26-case live evaluation.

## Suggested Handshake project description

EvidenceLens checks factual claims in AI-generated text against uploaded PDFs. I
built the frontend, modular Python verification pipeline, source-preserving citations,
and tests/evaluation tooling. The app makes support, partial support, contradiction,
and missing evidence visible while keeping the default inference path local. The
repository documents measured results, model errors, privacy boundaries and latency.
