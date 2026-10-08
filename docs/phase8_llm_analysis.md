# Phase 8 — Generative AI / LLM Analysis

## Objective

**Phase 8A is preparation only.** The official LLM response is **not yet generated**.
Statistical development and final holdout evaluation are complete. This package
extracts existing results, freezes a self-contained interpretive prompt and
prepares empty response, comparison and hallucination-audit files. It adds no
model result or LLM-generated interpretation of the project.

## Why use an LLM?

The subsequent manual exercise will examine how an LLM formulates modeling
hypotheses from evidence, explains technical findings, provides a simulated
investment interpretation and critiques the study. Its usefulness and accuracy
are questions for the subsequent team comparison, not outcomes established by
this preparation. Since outcomes are supplied, this is retrospective
interpretation, not an independent prospective model-selection experiment.

## Inputs supplied to the LLM

[Verified project facts](../llm/prompts/phase8_project_facts.md) cover data and
chronology, TRAIN stationarity/correlations/tails, ARIMA identification and
internal validation, VAR/Granger/Johansen/FEVD, GARCH, neural validation and
costs, final holdout price metrics, Diebold-Mariano and the Naive recommendation.
Every numerical table identifies its CSV source; accompanying documentary
facts cite internal sections. Scope and units accompany the results.

[Source manifest](../llm/prompts/phase8_source_manifest.json) records the Phase 7
base commit/tag, normalized-text source fingerprints, selected CSV columns,
row filters and expected row counts. CSV row order is retained. The tables use
Python's six-significant-digit numeric formatting; NA denotes an empty source
cell, not zero. CRLF is normalized to LF only for manifest hashes, so those
hashes are distinct from historical raw-byte dataset/prediction fingerprints.
The package tests reconstruct every table from the frozen CSV summaries and
check that the complete facts block is embedded verbatim in the official prompt.
They do not fit or forecast anything.

The manual ChatGPT session receives the complete official prompt as one input.
No repository access, external browsing, additional tests or raw market data
are needed. Internal paths in the prompt are provenance labels. The full team
baseline texts are reserved for the later comparison, not silently presented
as additional empirical evidence to the model.

## Official prompt

Use [phase8_official_llm_prompt.md](../llm/prompts/phase8_official_llm_prompt.md)
verbatim, including its complete embedded facts and disclaimer. It requires
exactly the four requested sections: model hypotheses, vulgarisation, simulated
investment interpretation and critical review. It forbids unsupported statistics,
p-values, intervals, causal claims and economic stories, and requires the LLM
to state when a conclusion cannot be drawn.

For the later manual run, preserve the exact input and record in this document
the visible ChatGPT model label, run date/time with timezone, and any nondefault
settings that are exposed. Mark unavailable model/version/settings information
as unavailable; do not infer it. The current generation record is **pending**.
Keep the complete first official response, including errors or refusals,
unedited. Any later alternative run must be separately identified rather than
replacing the official response. Input reproducibility does not promise an
identical stochastic response or the same future hosted model version.

## Full LLM response

**Pending manual generation.**
[Response placeholder](../llm/responses/phase8_official_llm_response.md) contains
only the requested title and paste instruction. No response is fabricated in
Phase 8A. After manual generation, paste the complete, unedited response there.

## Team baseline interpretation

The existing files are treated as **team-reviewed baseline interpretations
produced during model development**:

- [phase2_interpretation.md](../llm/human_analysis/phase2_interpretation.md)
- [phase3a_arima_interpretation.md](../llm/human_analysis/phase3a_arima_interpretation.md)
- [phase3b_arima_validation_interpretation.md](../llm/human_analysis/phase3b_arima_validation_interpretation.md)
- [phase4_var_vecm_interpretation.md](../llm/human_analysis/phase4_var_vecm_interpretation.md)
- [phase5_garch_interpretation.md](../llm/human_analysis/phase5_garch_interpretation.md)
- [phase6_lstm_gru_interpretation.md](../llm/human_analysis/phase6_lstm_gru_interpretation.md)
- [phase7_final_evaluation_interpretation.md](../llm/human_analysis/phase7_final_evaluation_interpretation.md)

This is the classification used for the exercise, not an independently blinded
human control or a certification that no assistance was used. Independence
from AI assistance has not been demonstrated; this is **not an independent human analysis**.
The original files are preserved. Their phase-relative statements (for example,
"holdout not yet evaluated") describe their development stage, not the current
state. Historical phase reports may still describe their original interpretation
templates as unanswered; the current baseline files contain working text.
Numeric outputs take precedence over rounded prose in any later audit.

## Human/team vs LLM comparison

**Pending.** [Comparison template](../llm/human_analysis/phase8_human_vs_llm_comparison.md)
has only the requested title and twelve unanswered headings. The team fills it
only after preserving the full manual response, checking agreement, disagreement,
useful additions and relative weaknesses against source evidence. No preference
for either author is assumed in advance.

## Hallucination audit

**Pending.** [Audit CSV](../llm/human_analysis/phase8_hallucination_audit.csv)
contains only its header. After the response exists, assign a stable claim_id,
quote the relevant llm_claim, record whether supported_by_project is true,
false or uncertain, and supply a precise source path plus row/column or document
section. Use only these issue_type values:

- supported
- invented_number
- causal_overclaim
- pvalue_misinterpretation
- oversimplification
- unsupported_financial_claim
- other

Suggested severity values are none, low, medium and high; explain impact in
team_comment. These are audit conventions, not completed audit judgments.
Check numerical fidelity, raw/Holm distinctions, non-significance, Granger and
Cholesky causal language, stationarity/cointegration claims, price versus
volatility targets, the Phase 3B lock versus Phase 7 challenger, the GARCH
selection policy and simulated-investment caution. Include supported claims
as well as issues to avoid reporting only errors. No audit data row is created
before the manual response exists.

## Investment simulation and limitations

[Investment disclaimer](../llm/prompts/phase8_investment_disclaimer.md) is also
embedded in the official prompt. This is an academic, educational simulation,
not personalized financial advice. Historical results and a single holdout do
not establish profit, causal economics or future performance. Volatility does
not identify price direction. The price-model recommendation concerns measured
prediction errors, not an executable trading recommendation. No held-out
volatility performance was measured; GARCH has a separate risk target.

## Scientific honesty

No LLM response, comparison answer or audit finding is fabricated. The current
state is preparation, not a completed generative-AI evaluation. Negative neural
results, diagnostic warnings, language differences and policy-dependent locks
are retained. No holdout observation is reloaded for analysis, no model is
refitted and no final evaluation is recalculated in Phase 8A.

The required post-generation chronology statement is reserved for the later
manual-generation record:

> The LLM response was generated only after the statistical analyses and final holdout evaluation had been completed.

This quoted statement is **not yet a claim that generation has occurred**.
After the response is produced, record its actual generation metadata and
confirm this chronology. The existing team interpretations are not represented
as wholly independent human work.

## Phase boundary

Phase 8A stops after preparing and validating the package and making the local
commit. No push, LLM invocation, comparison completion, populated claim audit,
model tuning, holdout replay or earlier-phase edit is included. The holdout
remains consumed for final evaluation, not a new tuning dataset.

Read-only preparation checks (from the repository root):

```powershell
.venv/Scripts/python.exe -m pytest tests/test_llm_package.py -q
.venv/Scripts/python.exe -m ruff check tests/test_llm_package.py
```

The placeholder assertions deliberately validate the Phase 8A boundary. Once
the manual response and team assessments are legitimately added in a subsequent
phase, these preparation-state assertions must be explicitly revised for that
new boundary; do not weaken them to hide premature completion.
