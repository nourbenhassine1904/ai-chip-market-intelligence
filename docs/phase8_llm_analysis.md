# Phase 8 — Generative AI / LLM Analysis

## Objective

**Phase 8A preparation and Phase 8B documentary comparison/audit are complete.**
Phase 8A froze a self-contained prompt and empty assessment templates. The
complete official response was subsequently recorded in the separate local
commit `67d60efba09c05ec571cd6907014e08ada9a2cd6`,
"docs: add official LLM response". Phase 8B audits that exact artifact against
the supplied project facts and development baselines. It changes no statistical
analysis, result, model or official response.

## Why use an LLM?

The exercise evaluates retrospective interpretation, explanation and critical
review of completed results, including a cautious educational investment
simulation. It is not prospective model selection: the LLM already received
the outcomes. Correctly restating those outcomes is useful, but does not
constitute a new statistical finding or demonstrate independent forecasting
ability.

## Inputs supplied to the LLM

[Verified project facts](../llm/prompts/phase8_project_facts.md) cover data and
chronology, TRAIN stationarity/correlations/tails, ARIMA identification and
internal validation, VAR/Granger/Johansen/FEVD, GARCH, neural validation and
costs, final holdout price metrics, Diebold-Mariano and the Naive recommendation.
Every numerical table cites its CSV; documentary statements cite internal
sections. Scope and units are explicit.

The [unchanged source manifest](../llm/prompts/phase8_source_manifest.json)
records the Phase 7 base commit/tag, normalized-text source fingerprints,
selected columns, filters and expected counts. Tables retain CSV row order
and use six significant digits; NA is an empty source value, not zero. Manifest
hashes normalize CRLF to LF and are distinct from historical raw-byte hashes.
Tests reconstruct the existing summary tables and check that the complete facts
and disclaimer remain embedded in the official prompt. No model is run.

The prompt is self-contained; repository paths are provenance labels, and no
repository access or external browsing is supplied. Full baseline texts are
reserved for this subsequent comparison. The audit uses only existing facts,
CSV summaries, protocols and baseline interpretations; it performs no new
statistical estimation or holdout evaluation.

## Official prompt

[phase8_official_llm_prompt.md](../llm/prompts/phase8_official_llm_prompt.md)
remains unchanged. It requests exactly A, B, C and D: model hypotheses,
vulgarisation, simulated investment interpretation and critical review.
It forbids invented statistics, p-values, intervals, causal/economic claims
and requires unsupported conclusions to be identified as such.

The recorded response is the official artifact supplied for this audit.
The precise ChatGPT model label/version, generation timestamp and exposed
settings were not recorded in the repository or supplied with the response;
they are **unavailable**, not inferred. The response commit records storage,
not the exact generation time or model identity. Input reproducibility does
not promise an identical stochastic output or future hosted model version.

## Full LLM response

The complete [official response](../llm/responses/phase8_official_llm_response.md)
is stored only in llm/responses/. It contains the four requested A/B/C/D
sections, following the storage title, and is preserved without corrections,
reformatting or deletion of the editorial suffix in section C.

Frozen response commit: `67d60efba09c05ec571cd6907014e08ada9a2cd6`.
Raw UTF-8 SHA-256:
`eecb0de3e0dd8e152e93db70ff71f9dad87024b7b2f3e1bee1ede05225f6f3b4`.
The Phase 8B tests compare the working bytes to this digest and the committed
blob. The full response is not duplicated in this document.

## Team baseline interpretation

The reference documents are **team-reviewed baseline interpretations produced during model development**:

- [phase2_interpretation.md](../llm/human_analysis/phase2_interpretation.md)
- [phase3a_arima_interpretation.md](../llm/human_analysis/phase3a_arima_interpretation.md)
- [phase3b_arima_validation_interpretation.md](../llm/human_analysis/phase3b_arima_validation_interpretation.md)
- [phase4_var_vecm_interpretation.md](../llm/human_analysis/phase4_var_vecm_interpretation.md)
- [phase5_garch_interpretation.md](../llm/human_analysis/phase5_garch_interpretation.md)
- [phase6_lstm_gru_interpretation.md](../llm/human_analysis/phase6_lstm_gru_interpretation.md)
- [phase7_final_evaluation_interpretation.md](../llm/human_analysis/phase7_final_evaluation_interpretation.md)

They are **not an independent human analysis** or a blinded control. Their
independence from AI assistance has not been demonstrated. This classification
does not certify a separate human-only review. All baseline files are preserved.
Statements about a future holdout describe their historical development stage,
not the current completed evaluation. Existing CSV/protocol evidence takes
precedence over rounded prose or rhetorical simplifications.

## Human/team vs LLM comparison

The completed [comparison](../llm/human_analysis/phase8_human_vs_llm_comparison.md)
retains all twelve original headings. It documents agreement, real differences
of caution/detail, every material reported number, Granger, non-significance,
stationarity/cointegration, price/volatility, the Naive decision, simulated
investment caution, useful synthesis and areas where baselines are more detailed.

No material factual disagreement is found. The LLM is more precise than the
final Phase 5 baseline wording about ARCH effects disappearing: it says no ARCH
was detected at the tested lags, without a universal absence claim. Baselines
provide more detail on temporal folds/scalers, incomplete fit coverage, costs,
Johansen specifications and evaluation mechanics. These differences are tied
to baseline sections and original documentation in the comparison.

## Hallucination audit

The completed [audit CSV](../llm/human_analysis/phase8_hallucination_audit.csv)
contains 35 grouped material claims: A=11, B=8, C=6, D=10. Each row records a
verbatim response excerpt, support status, precise source references, issue
type, severity and an explanatory comment. Repeated ideas are grouped; counts
are not independent observations or an estimate of general LLM reliability.

| issue_type | Number of claims |
| --- | --- |
| supported | 35 |
| invented_number | 0 |
| causal_overclaim | 0 |
| pvalue_misinterpretation | 0 |
| oversimplification | 0 |
| unsupported_financial_claim | 0 |
| other | 0 |

**No numerical hallucination was detected in the material reported values checked.**
All 35 claims are supported, with severity none. Reasonable rounding is accepted.
Raw versus Holm DM, the ARIMA h10 RMSE advantage, post-GARCH non-rejection,
Johansen rank zero, GARCH sigma units and interval coverage/widths were checked.
No causal overclaim, p-value misuse or unsupported financial claim is retained.

The response is good overall, with specific limitations. Its local citations
sometimes group a correct number under an imprecise source: correlation in
A05/D02 belongs to the Phase 2 correlation CSV, and persistence in A08 belongs
to the GARCH comparison CSV, not the cited diagnostic table. The audit gives
the correct source; these are traceability defects, not invented numbers.
The isolated phase8_investment_disclaimer suffix in C is editorial. The
20-day feature and ARCH/clustering explanations are acceptable contextual
simplifications, not material erroneous oversimplifications. Costs, inferential
calibration and the Phase 3B lock versus Phase 7 challenger could be explained
more fully. See comparison sections 2, 5, 6, 8, 9 and 11.

The categorical audit evaluates factual claims. Editorial defects, incomplete
citations and omissions are explicitly described in comments/comparison rather
than mislabeled as false material claims. No anomaly is invented to populate
an issue category. This is a documentary audit prepared in the repository;
a second independent human review is not attested.

## Investment simulation and limitations

The unchanged [disclaimer](../llm/prompts/phase8_investment_disclaimer.md) remains
embedded in the prompt. Response C respects its academic, simulated scope:
no personalized financial advice, buy/sell instruction, portfolio allocation,
promised return or guaranteed performance. It distinguishes price prediction
from conditional-volatility risk and acknowledges historical uncertainty,
a single holdout, unassessed costs and no executed trading backtest.

The phrase about no robust directional signal means none is validated by the
supplied price-loss evaluation; it is not a negative result from an unreported
directional-accuracy test. No directional hit-rate is invented. Sigma near
3.17% is daily innovation volatility at h10, not a signed return, expected
profit or cumulative ten-session risk. GARCH has no held-out volatility score
and remains excluded from price-model ranking.

## Scientific honesty

The LLM received the project results **after modeling and final holdout
evaluation**. Its model proposals are retrospective. The baseline interpretations
are team-reviewed development documents, not an independent blinded human
control. The comparison assesses interpretation quality, not a pure experimental
human-versus-AI competition. Model/version and generation metadata unavailable
in the project are not fabricated, and no independent reviewer is invented.

> The LLM response was generated only after the statistical analyses and final holdout evaluation had been completed.

This chronology is the recorded project sequence; the precise generation time
is unavailable. The response was committed separately before Phase 8B and
remains byte-identical. Negative neural results, diagnostic warnings,
language differences and policy-dependent locks are retained.
No holdout is reloaded for analysis, no model is refitted, and no original
statistic, forecast, metric or final evaluation is recalculated in Phase 8B.
No new external LLM call is made.

## Phase boundary

Phase 8B stops after the comparison, claim audit, documentation, appropriate
tests and local commit. The official response, prompt/facts/disclaimer,
source manifest and every Phase 1–7 tracked file remain unchanged.
No push, PR, merge, Prophet or final-report work is performed. The consumed
holdout does not become a new tuning dataset.

Validation from the repository root:

```powershell
.venv/Scripts/python.exe -m ruff check tests/test_llm_package.py
.venv/Scripts/python.exe -m pytest tests/test_llm_package.py
.venv/Scripts/python.exe -m pytest
```

Validation completed: **Ruff PASS**, **128 targeted tests passed**, and the full
suite **336 passed**. The four existing Phase 3A statsmodels acorr_lm
FutureWarnings remain; no Phase 8B warning was reported.

Phase 8B tests replace the deliberately obsolete Phase 8A placeholder assertions
with checks for the frozen complete response, four sections, filled comparison,
valid sourced audit rows, counts consistent with the documentation, preserved
source summaries/disclaimer and no earlier-phase changes. Numeric checks read
existing source cells and verify the response's reported rounding only; they
are not statistical recalculation. Existing synthetic unit tests remain separate
from execution of historical analysis pipelines.
