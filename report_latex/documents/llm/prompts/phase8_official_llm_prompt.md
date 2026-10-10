# Phase 8 — Official LLM Analysis Prompt

You are interpreting a completed academic time-series project on NVDA, AMD
and SOXX. Statistical modeling and the final holdout evaluation were completed
before this interpretive exercise. Use only the supplied facts. You have no
repository access; source paths below are provenance labels, not instructions
to retrieve files. Do not browse, run code, re-estimate models or compute new
tests. Do not infer missing results from a model's reputation.

Write the response in French, keeping the four section headings below exactly
in English. Return EXACTLY four sections, A through D, in the given order, with
no introduction, conclusion, appendix or extra top-level section. Explanations,
source references and limitations belong within these four sections.
Distinguish recorded findings from proposed modeling hypotheses. Where useful,
attribute a numerical claim to its supplied source path and name its scope
(TRAIN identification, internal validation or final holdout). Numeric tables
are rounded to six significant digits; NA means no value supplied/applicable,
never zero. Do not add precision or manufacture uncertainty intervals.

Do not invent statistics, p-values, confidence intervals, causal claims,
model results or economic explanations not supported by the supplied facts.

If a requested conclusion is not supported by the supplied information,
state that it cannot be concluded.

The existing interpretations are classified for this exercise as
"team-reviewed baseline interpretations produced during model development".
Their independence from AI assistance has not been demonstrated. They are not
an independently blinded human control. You are not being supplied their full
text and must not claim to have compared your response with it. The team will
perform the comparison and claim audit later. Do not fill them yourself.
Do not write a retrospective claim that you proposed a model before its outcome
was known: every modeling hypothesis below is an interpretation of completed
results, not an independent prospective model-selection experiment.

Use these exact output headings and satisfy each section's instructions:

## A. MODEL HYPOTHESES FROM STATISTICAL RESULTS

From the stationarity, correlation, tails and residual diagnostics, propose
reasonable modeling hypotheses. Explain why differenced log-price ARIMA,
return VAR, innovation-variance GARCH and nonlinear LSTM/GRU windows can be
relevant, then relate those hypotheses to the recorded outcomes. Distinguish
identification from internal selection and final evaluation. Respect the FALSE
SARIMA and VECM gates; do not invent missing model estimates, tests or p-values.
Preserve the R/Python ARIMA differences, the Phase 3B Naive lock versus the
Phase 7 ARIMA challenger, and the policy-dependent GARCH Normal lock despite
Student-t's information-criterion advantage.

## B. VULGARISATION

Explain the project to a nontechnical audience. Cover stationarity and what
ADF/KPSS can and cannot establish; the random walk/last-price benchmark;
conditional Granger predictability versus economic causality; cointegration
and its specification-dependent unsupported result; GARCH and volatility
clustering; and why these neural networks can lose to Naive. Possible
mechanisms such as estimation noise, limited samples and extrapolation should
be labeled plausible limitations, not experimentally established causes.
Explain RMSE/MAE and distinguish internal validation from the final holdout.

## C. SIMULATED INVESTMENT INTERPRETATION

Offer a SIMULATED, educational interpretation for a hypothetical investor,
consistent with the disclaimer supplied below. Do not give personalized
financial advice, buy/sell instructions, target returns, allocation percentages
or unsupported profitability claims. Explain separately what price-prediction
results and conditional-volatility results say. State the limits of historical
evidence, elevated uncertainty, a single holdout and the absence of an executed
trading/cost evaluation. The project establishes no strong economic causality.
Neither a Naive point forecast nor GARCH sigma establishes price direction or
future profit. Include the disclaimer's substance within this section.

## D. CRITICAL REVIEW

Identify well-supported findings within this project and fragile or
specification-dependent conclusions. Discuss overinterpretation risks:
correlation/Granger/Cholesky are not economic causality; Johansen rank zero is
not proof of no long-run relation; non-rejected diagnostics do not prove iid
innovations; p > 0.05 is not evidence of equal model accuracy; the reported
Jarque-Bera zero p-values reflect numerical underflow, not literal zero
probabilities. Use raw versus Holm DM values correctly, preserving
the separate GRU/LSTM raw comparison. Explain why Naive was recommended even
though ARIMA has the smallest h10 RMSE, and why increased complexity did not
qualify for replacement. Retain the Naive residual warning and discuss the
limited neural grid/seed, overlapping errors, Gaussian tails, GARCH selection
policy, lack of held-out volatility scoring and broad ARIMA intervals.
Do not invent a causal narrative or unreported tests. Separate project-specific
recommendation from universal claims about finance or deep learning.

The following complete fact block is the sole empirical input.

<!-- BEGIN PROJECT FACTS -->
# Phase 8 — Verified Project Facts

## Scope and data

This is a factual extract of completed project outputs, not an LLM response.
NVDA is the adjusted-price forecasting target; AMD and SOXX supply multivariate
context. Prices are adjusted USD; daily log-returns are percentage points.
The aligned dataset covers 2018-01-02 through 2026-10-02. TRAIN and TEST are
chronological, without shuffling. The initial missing return is structural.
Source: `docs/phase2_eda_stationarity.md` (Input dataset, Chronological split,
Financial transformations).

<!-- table: split -->
Source: `outputs/tables/phase2_split_metadata.csv`.

| total_rows | train_rows | test_rows | train_ratio | test_ratio | train_start | train_end | test_start | test_end |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2200 | 1980 | 220 | 0.9 | 0.1 | 2018-01-02 | 2025-11-14 | 2025-11-17 | 2026-10-02 |
<!-- endtable: split -->

## Phase 2 — TRAIN stationarity, dependence and tails

For all assets, ADF does not reject a unit root in adjusted prices/log-prices,
while KPSS rejects stationarity. For log-returns, ADF rejects a unit root and
KPSS does not reject stationarity. Deterministic terms are constant plus trend
for levels and constant for returns. This supports differencing log-prices;
non-rejection is not proof of either null. KPSS boundary values are censored,
not exact probabilities. The reported AMD return ADF zero is a numerical
output, not a claim of literally zero probability.
Source: `docs/phase2_eda_stationarity.md` (ADF, KPSS, Mechanical stationarity summary).

<!-- table: stationarity -->
Source: `outputs/tables/phase2_stationarity_tests.csv`.

| ticker | series | test | p_value | regression | decision_5pct | p_value_bound |
| --- | --- | --- | --- | --- | --- | --- |
| NVDA | Adj_Close | ADF | 0.988692 | ct | fail_to_reject_H0 | none |
| NVDA | Adj_Close | KPSS | 0.01 | ct | reject_stationarity | actual_p_smaller_than_reported |
| NVDA | Log_Price | ADF | 0.461103 | ct | fail_to_reject_H0 | none |
| NVDA | Log_Price | KPSS | 0.01 | ct | reject_stationarity | actual_p_smaller_than_reported |
| NVDA | Log_Return | ADF | 7.91143e-27 | c | reject_H0 | none |
| NVDA | Log_Return | KPSS | 0.1 | c | fail_to_reject_stationarity | actual_p_greater_than_reported |
| AMD | Adj_Close | ADF | 0.487496 | ct | fail_to_reject_H0 | none |
| AMD | Adj_Close | KPSS | 0.0152772 | ct | reject_stationarity | none |
| AMD | Log_Price | ADF | 0.416796 | ct | fail_to_reject_H0 | none |
| AMD | Log_Price | KPSS | 0.01 | ct | reject_stationarity | actual_p_smaller_than_reported |
| AMD | Log_Return | ADF | 0 | c | reject_H0 | none |
| AMD | Log_Return | KPSS | 0.1 | c | fail_to_reject_stationarity | actual_p_greater_than_reported |
| SOXX | Adj_Close | ADF | 0.459873 | ct | fail_to_reject_H0 | none |
| SOXX | Adj_Close | KPSS | 0.01 | ct | reject_stationarity | actual_p_smaller_than_reported |
| SOXX | Log_Price | ADF | 0.277134 | ct | fail_to_reject_H0 | none |
| SOXX | Log_Price | KPSS | 0.01 | ct | reject_stationarity | actual_p_smaller_than_reported |
| SOXX | Log_Return | ADF | 7.59993e-28 | c | reject_H0 | none |
| SOXX | Log_Return | KPSS | 0.1 | c | fail_to_reject_stationarity | actual_p_greater_than_reported |
<!-- endtable: stationarity -->

Contemporaneous TRAIN Pearson return correlations are positive; the strongest
pair is NVDA/SOXX. Correlation is not economic causality.
Source: `docs/phase2_eda_stationarity.md` (Correlation structure).

<!-- table: correlation -->
Source: `outputs/tables/phase2_return_correlation_train.csv`.

| ticker | NVDA | AMD | SOXX |
| --- | --- | --- | --- |
| NVDA | 1 | 0.684939 | 0.819116 |
| AMD | 0.684939 | 1 | 0.744839 |
| SOXX | 0.819116 | 0.744839 | 1 |
<!-- endtable: correlation -->

The kurtosis column below is **excess** kurtosis (Normal reference zero).
Positive values and QQ-tail departures document thick empirical tails;
kurtosis is not the same quantity as overall volatility.
Source: `docs/phase2_eda_stationarity.md` (Descriptive statistics, Return dynamics).

<!-- table: tails -->
Source: `outputs/tables/phase2_descriptive_stats.csv`.

| ticker | count | standard_deviation | kurtosis |
| --- | --- | --- | --- |
| NVDA | 1979 | 3.2436 | 4.69802 |
| AMD | 1979 | 3.45086 | 3.57136 |
| SOXX | 1979 | 2.21915 | 5.12609 |
<!-- endtable: tails -->

Return/squared-return and historical-volatility plots show volatility clustering;
squared-return ACF supplies descriptive dependence evidence. Phase 2 did not
perform a formal ARCH-LM or normality test.
Sources: `docs/phase2_eda_stationarity.md` (Return dynamics, ACF/PACF),
`outputs/figures/phase2/nvda_squared_returns_acf_train.png`,
`docs/phase5_garch.md` (Why volatility modeling?).

## Phase 3A — Identification and residual diagnostics

On NVDA log-price, d=1 is supported by the TRAIN ADF/KPSS evidence and all
three R ndiffs checks. The SARIMA gate is FALSE in both languages; no SARIMA
was estimated. R auto.arima proposes and provisionally selects ARIMA(2,1,2)
with drift. Python auto_arima proposes ARIMA(3,1,3) without drift, but the
parsimony/diagnostic rule provisionally selects ARIMA(1,1,1) with drift.
These are identification results, not predictive winners. A sensitivity fit
initialized from R almost matches its likelihood, but is not independent
replication and does not prove a global optimum.
Source: `docs/phase3a_arima_identification.md` (Why d=1?, SARIMA seasonality gate,
Provisional model selection, R vs Python comparison).

Both selected fits have non-rejected Ljung-Box checks at lags 10/20, rejected
normality and rejected ARCH-LM checks at lags 5/10/20. Jarque-Bera numerical
p=0 is underflow, not literal zero probability. Non-rejected mean-correlation
tests do not establish iid Gaussian residuals or constant conditional variance.
Source: `docs/phase3a_arima_identification.md` (Residual diagnostics).

<!-- table: arima_r -->
Source: `outputs/tables/phase3_arima_residual_diagnostics_r.csv`.

| model | test | lag | statistic | p_value | df |
| --- | --- | --- | --- | --- | --- |
| ARIMA(2,1,2)_drift | Ljung-Box | 10 | 2.48816 | 0.869791 | 6 |
| ARIMA(2,1,2)_drift | Ljung-Box | 20 | 11.3964 | 0.784385 | 16 |
| ARIMA(2,1,2)_drift | Jarque-Bera | 0 | 1704.15 | 0 | 2 |
| ARIMA(2,1,2)_drift | ARCH-LM | 5 | 64.3866 | 1.50217e-12 | 5 |
| ARIMA(2,1,2)_drift | ARCH-LM | 10 | 73.4686 | 9.44313e-12 | 10 |
| ARIMA(2,1,2)_drift | ARCH-LM | 20 | 89.104 | 1.06283e-10 | 20 |
<!-- endtable: arima_r -->

<!-- table: arima_python -->
Source: `outputs/tables/phase3_arima_residual_diagnostics_python.csv`.

| model | test | lag | statistic | p_value | df |
| --- | --- | --- | --- | --- | --- |
| ARIMA(1,1,1)_drift | Ljung-Box | 10 | 14.5973 | 0.0674649 | 8 |
| ARIMA(1,1,1)_drift | Ljung-Box | 20 | 25.2523 | 0.118122 | 18 |
| ARIMA(1,1,1)_drift | Jarque-Bera | 0 | 1776.11 | 0 | 2 |
| ARIMA(1,1,1)_drift | ARCH-LM | 5 | 69.8523 | 1.09996e-13 | 5 |
| ARIMA(1,1,1)_drift | ARCH-LM | 10 | 83.52 | 1.02156e-13 | 10 |
| ARIMA(1,1,1)_drift | ARCH-LM | 20 | 98.8441 | 2.02698e-12 | 20 |
<!-- endtable: arima_python -->

## Phase 3B — Internal rolling-origin validation and lock

Expanding TRAIN-only validation starts with 1386 rows, advances by 10 observed
sessions and uses 59 origins, 2023-07-06 through 2025-10-27, at endpoints h5/h10.
Candidates came from full-TRAIN identification, so this is internal selection,
not a nested independent evaluation. Prices use exp(log forecast) without
lognormal bias correction. Incomplete fits are excluded from scoring and
cannot lock; available-case rows are not directly comparable to complete
panels without matching origins.
Source: `docs/phase3b_arima_validation.md` (Expanding-window protocol, Back-transformation,
Validation metrics, R/Python comparison).

<!-- table: validation -->
Source: `outputs/tables/phase3b_arima_validation_metrics.csv`.

| language | model | horizon | n_forecasts | failed_fits | RMSE | MAE | MAPE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Python | ARIMA111_drift | 5 | 53 | 6 | 7.83765 | 6.03248 | 5.70412 |
| Python | ARIMA111_drift | 10 | 53 | 6 | 8.77991 | 6.49639 | 6.57334 |
| Python | ARIMA212_drift | 5 | 54 | 5 | 7.35071 | 5.43358 | 5.36556 |
| Python | ARIMA212_drift | 10 | 54 | 5 | 8.67163 | 6.61925 | 6.79309 |
| Python | ARIMA313_no_drift | 5 | 59 | 0 | 7.7315 | 5.82565 | 5.61624 |
| Python | ARIMA313_no_drift | 10 | 59 | 0 | 9.3167 | 7.21512 | 7.12328 |
| Python | Naive | 5 | 59 | 0 | 7.72383 | 5.856 | 5.63916 |
| Python | Naive | 10 | 59 | 0 | 9.36924 | 7.25316 | 7.12552 |
| Python | RW_drift | 5 | 59 | 0 | 7.81373 | 5.91673 | 5.7 |
| Python | RW_drift | 10 | 59 | 0 | 9.10534 | 6.76008 | 6.84717 |
| R | ARIMA111_drift | 5 | 59 | 0 | 7.84823 | 5.9342 | 5.72118 |
| R | ARIMA111_drift | 10 | 59 | 0 | 9.08131 | 6.73085 | 6.82398 |
| R | ARIMA212_drift | 5 | 59 | 0 | 7.84673 | 5.93824 | 5.72276 |
| R | ARIMA212_drift | 10 | 59 | 0 | 9.07961 | 6.72939 | 6.82122 |
| R | ARIMA313_no_drift | 5 | 59 | 0 | 7.76447 | 5.88357 | 5.65658 |
| R | ARIMA313_no_drift | 10 | 59 | 0 | 9.38545 | 7.29488 | 7.18545 |
| R | Naive | 5 | 59 | 0 | 7.72383 | 5.856 | 5.63916 |
| R | Naive | 10 | 59 | 0 | 9.36924 | 7.25316 | 7.12552 |
| R | RW_drift | 5 | 59 | 0 | 7.81373 | 5.91673 | 5.7 |
| R | RW_drift | 10 | 59 | 0 | 9.10534 | 6.76008 | 6.84717 |
<!-- endtable: validation -->

The predeclared lock requires complete convergence and at least 1% RMSE AND
MAE improvement at BOTH horizons in BOTH languages. No challenger qualifies.
The locked specification is Naive, ARIMA(0,1,0), without drift. The prior
random-walk Ljung-Box failure remains a diagnostic warning.
Source: `docs/phase3b_arima_validation.md` (Locked ARIMA specification).

<!-- table: arima_lock -->
Source: `outputs/tables/phase3b_locked_arima_model.csv`.

| model | order | drift | status |
| --- | --- | --- | --- |
| Naive | (0,1,0) | False | locked_arima_specification_baseline_with_diagnostic_warning |
<!-- endtable: arima_lock -->

## Phase 4 — VAR, Granger, Johansen and FEVD

The return system is ordered NVDA, AMD, SOXX. Both languages' information
criteria propose lag 1, but serial diagnostics select stable VAR(9).
Its companion eigenvalues lie inside the unit circle; Python inverse-root
conventions must not be confused with companion roots. Portmanteau
non-rejection does not prove white innovations; residual normality is rejected.
Source: `docs/phase4_var_vecm.md` (VAR lag selection, VAR stability, Residual diagnostics).

<!-- table: var -->
Source: `outputs/tables/phase4_r_python_summary.csv`.

| language | aic_proposed_lag | bic_proposed_lag | selected_lag | stable | max_companion_modulus | serial_p20 | serial_p30 | johansen_rank | vecm_justified |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R | 1 | 1 | 9 | True | 0.840223 | 0.0587904 | 0.1568 | 0 | False |
| Python | 1 | 1 | 9 | True | 0.840223 | 0.0587904 | 0.1568 | 0 | False |
<!-- endtable: var -->

Six directed equation-wise conditional Wald Granger tests use Holm adjustment.
SOXX -> NVDA and SOXX -> AMD are supported; the other directions are not.
These are conditional predictive precedence results, not structural economic
causality. Conventional variance assumptions and lag selection limit inference.
Source: `docs/phase4_var_vecm.md` (Granger causality).

<!-- table: granger -->
Source: `outputs/tables/phase4_granger_causality_comparison.csv`.

| cause | effect | p_value_r | p_value_holm_r | p_value_python | p_value_holm_python | decision_agrees |
| --- | --- | --- | --- | --- | --- | --- |
| NVDA | AMD | 0.464045 | 1 | 0.464045 | 1 | True |
| NVDA | SOXX | 0.464486 | 1 | 0.464486 | 1 | True |
| AMD | NVDA | 0.231963 | 0.927853 | 0.231963 | 0.927853 | True |
| AMD | SOXX | 0.737034 | 1 | 0.737034 | 1 | True |
| SOXX | NVDA | 6.57077e-05 | 0.000394246 | 6.57077e-05 | 0.000394246 | True |
| SOXX | AMD | 0.00916676 | 0.0458338 | 0.00916676 | 0.0458338 | True |
<!-- endtable: granger -->

Johansen tests log-price levels with K=3 level lags and 2 lagged differences.
Both native procedures select rank=0; nearby K=2/4 checks also select rank=0.
R/Python critical tables differ and are preserved. The VECM gate is FALSE;
no VECM, alpha or beta was estimated. Rank zero is lack of supported
cointegration under tested specifications, not proof that no long-run relation
exists. The short-run lag specification and deterministic terms are limitations.
Source: `docs/phase4_var_vecm.md` (Johansen cointegration, VECM decision).

<!-- table: johansen -->
Source: `outputs/tables/phase4_johansen_rank_comparison.csv`.

| level_lags | null_rank_at_most | trace_statistic_r | critical_5pct_r | trace_statistic_python | critical_5pct_python | selected_rank_r | selected_rank_python |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 0 | 21.5701 | 31.52 | 21.5701 | 29.7961 | 0 | 0 |
| 3 | 1 | 9.8573 | 17.95 | 9.8573 | 15.4943 | 0 | 0 |
| 3 | 2 | 0.00167671 | 8.18 | 0.00167671 | 3.8415 | 0 | 0 |
<!-- endtable: johansen -->

The main NVDA FEVD at h20 below uses R shares; independent Python shares agree
to numerical precision. The recursive Cholesky order is NVDA, AMD, SOXX.
These shares describe model forecast-error variance of returns, not realized
holdout price errors or structural causal effects. Ordering affects the
allocation; Granger significance does not imply a large FEVD share.
Source: `docs/phase4_var_vecm.md` (IRF, FEVD).

<!-- table: fevd -->
Source: `outputs/tables/phase4_var_fevd.csv`.

| response | shock | horizon | variance_share_pct | order |
| --- | --- | --- | --- | --- |
| NVDA | NVDA | 20 | 97.5168 | NVDA;AMD;SOXX |
| NVDA | AMD | 20 | 0.591106 | NVDA;AMD;SOXX |
| NVDA | SOXX | 20 | 1.8921 | NVDA;AMD;SOXX |
<!-- endtable: fevd -->

## Phase 5 — Conditional innovation volatility

Both languages use a common ARMA(1,1) return-mean filter, frozen before the
second-stage GARCH(1,1) fit. This does not replace the Phase 3B price lock.
Normal and standardized Student-t models converge. The variance coefficients
alpha1 and beta1 measure recent squared-innovation response and variance
memory; persistence=alpha1+beta1 is high but below 1 for every fit.
AIC/BIC are total conditional second-stage criteria, not joint ARMA-GARCH
criteria; tail_quantile_rmse is an in-sample distribution diagnostic, not a
price or held-out volatility score.
Source: `docs/phase5_garch.md` (Mean equation / filtering, Model comparison, Persistence).

<!-- table: garch -->
Source: `outputs/tables/phase5_garch_model_comparison.csv`.

| language | distribution | alpha1 | beta1 | persistence | shape_df_if_applicable | AIC | BIC | tail_quantile_rmse |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R | Normal | 0.11258 | 0.851597 | 0.964177 | NA | 10025.9 | 10042.7 | 0.151076 |
| R | Student-t | 0.0950298 | 0.879255 | 0.974285 | 5.75532 | 9864.42 | 9886.78 | 0.155118 |
| Python | Normal | 0.11158 | 0.852923 | 0.964503 | NA | 10025.9 | 10042.6 | 0.149534 |
| Python | Student-t | 0.0940332 | 0.880479 | 0.974512 | 5.76352 | 9864.19 | 9886.56 | 0.139315 |
<!-- endtable: garch -->

ARCH-LM rejected before GARCH. Afterwards, none of the tested standardized
residual ARCH-LM checks rejects; the squared-residual Ljung-Box checks also
do not reject. This is no detected remaining ARCH at tested horizons,
not proof that all ARCH or dependence has disappeared.
Source: `docs/phase5_garch.md` (ARCH-LM before GARCH, Standardized residual diagnostics).

<!-- table: post_arch -->
Source: `outputs/tables/phase5_garch_standardized_residual_diagnostics.csv`.

| language | model | lag | p_value | p_value_holm_variance | reject_for_gate |
| --- | --- | --- | --- | --- | --- |
| R | GARCH(1,1)_Normal | 5 | 0.891175 | 1 | False |
| R | GARCH(1,1)_Normal | 10 | 0.966311 | 1 | False |
| R | GARCH(1,1)_Normal | 20 | 0.998017 | 1 | False |
| R | GARCH(1,1)_Student-t | 5 | 0.943188 | 1 | False |
| R | GARCH(1,1)_Student-t | 10 | 0.981251 | 1 | False |
| R | GARCH(1,1)_Student-t | 20 | 0.998456 | 1 | False |
| Python | GARCH(1,1)_Normal | 5 | 0.894106 | 1 | False |
| Python | GARCH(1,1)_Normal | 10 | 0.967342 | 1 | False |
| Python | GARCH(1,1)_Normal | 20 | 0.998105 | 1 | False |
| Python | GARCH(1,1)_Student-t | 5 | 0.944801 | 1 | False |
| Python | GARCH(1,1)_Student-t | 10 | 0.982036 | 1 | False |
| Python | GARCH(1,1)_Student-t | 20 | 0.998544 | 1 | False |
<!-- endtable: post_arch -->

The shared locked model is **GARCH(1,1) Normal**. Student-t has better AIC/BIC,
but its tail-quantile score improves only in Python; the predeclared rule
requires improvement in both languages. The lock does not validate Normal
tails. Student-t remains a credible alternative. The higher-order gate is
FALSE and no higher-order or asymmetric GARCH was estimated.
Sources: `docs/phase5_garch.md` (Model comparison, Higher-order gate),
`outputs/tables/phase5_higher_order_gate.csv`.

<!-- table: garch_lock -->
Source: `outputs/tables/phase5_locked_garch_model.csv`.

| locked_garch_specification | distribution | selection_reason |
| --- | --- | --- |
| GARCH(1,1)_Normal | Normal | Adequate parsimonious Normal; Student-t superiority rule not satisfied |
<!-- endtable: garch_lock -->

The TRAIN-end forecast originates on 2025-11-14. At h10, variance is in squared
percentage points and sigma is daily percent **at that horizon**. These are
innovation-variance forecasts, not cumulative ten-session risk, return
forecast-error variance, price-direction predictions or guarantees. The
annualized column in the original output merely scales daily sigma by sqrt(252).
Held-out volatility forecasting performance was **not measured**.
Source: `docs/phase5_garch.md` (TRAIN-end volatility forecast, Limitations).

<!-- table: volatility -->
Source: `outputs/tables/phase5_volatility_forecast_train_end.csv`.

| language | model | origin_date | horizon | forecast_variance | forecast_sigma | locked |
| --- | --- | --- | --- | --- | --- | --- |
| R | GARCH(1,1)_Normal | 2025-11-14 | 10 | 10.0552 | 3.171 | True |
| R | GARCH(1,1)_Student-t | 2025-11-14 | 10 | 9.50146 | 3.08244 | False |
| Python | GARCH(1,1)_Normal | 2025-11-14 | 10 | 10.039 | 3.16844 | True |
| Python | GARCH(1,1)_Student-t | 2025-11-14 | 10 | 9.47723 | 3.07851 | False |
<!-- endtable: volatility -->

## Phase 6 — LSTM C and GRU C

Both locked configurations are C. Inputs are exactly NVDA_Log_Price,
NVDA_Log_Return, NVDA_Rolling_Vol_20D, AMD_Log_Return, SOXX_Log_Return.
Networks emit ten future log-price levels directly. Fold-specific scalers and
inner early stopping use only the corresponding TRAIN prefix. Three temporal
folds supply 187 origins each, hence 561 matched forecasts per model/horizon.
The first 20 feature-warmup rows are excluded. Configuration selection uses
the six equally weighted fold/horizon RMSE ratios; it is not the pooled ratio.
Sources: `docs/phase6_lstm_gru.md` (Feature set, Temporal validation folds,
Scaling and leakage prevention, Locked LSTM configuration, Locked GRU configuration).

<!-- table: lstm -->
Source: `outputs/tables/phase6_locked_lstm.csv`.

| model | configuration | lookback | units | dropout | trainable_parameters | average_RMSE_ratio | seed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LSTM | C | 60 | 64 | 0.2 | 18570 | 2.31918 | 42 |
<!-- endtable: lstm -->

<!-- table: gru -->
Source: `outputs/tables/phase6_locked_gru.csv`.

| model | configuration | lookback | units | dropout | trainable_parameters | average_RMSE_ratio | seed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GRU | C | 60 | 64 | 0.2 | 14282 | 1.65178 | 42 |
<!-- endtable: gru -->

Both C networks have worse pooled RMSE/MAE than Naive at both horizons.
GRU C performs better than LSTM C internally; that is not a universal
architectural superiority claim or a final holdout ranking.
Source: `docs/phase6_lstm_gru.md` (Comparison with naive benchmark, LSTM vs GRU).

<!-- table: neural_validation -->
Source: `outputs/tables/phase6_validation_metrics_summary.csv`.

| model | configuration | horizon | n_forecasts | RMSE | MAE | MAPE |
| --- | --- | --- | --- | --- | --- | --- |
| GRU | C | 5 | 561 | 10.516 | 8.124 | 7.82209 |
| GRU | C | 10 | 561 | 13.2687 | 10.4651 | 9.93107 |
| LSTM | C | 5 | 561 | 15.2526 | 11.7969 | 11.8774 |
| LSTM | C | 10 | 561 | 15.0709 | 11.397 | 11.2121 |
| Naive | baseline | 5 | 561 | 7.37231 | 5.58442 | 5.17255 |
| Naive | baseline | 10 | 561 | 10.0516 | 7.75769 | 7.276 |
<!-- endtable: neural_validation -->

The recorded CPU fitting work includes 18 main fits and two full-TRAIN refits;
total fitting time is 1208.461 seconds (20.14 minutes), excluding preprocessing,
scoring, figures, tests and documentation. Hardware load affects timings;
fewer GRU parameters did not produce shorter measured fitting time here.
Sources: `docs/phase6_lstm_gru.md` (Computational cost),
`outputs/tables/phase6_training_runs.csv`,
`outputs/tables/phase6_full_train_refits.csv`.

<!-- table: neural_cost -->
Source: `outputs/tables/phase6_model_complexity.csv`.

| model | configuration | total_training_seconds | median_best_epoch |
| --- | --- | --- | --- |
| GRU | C | 230.711 | 36 |
| LSTM | C | 160.501 | 38 |
<!-- endtable: neural_cost -->

<!-- table: refits -->
Source: `outputs/tables/phase6_full_train_refits.csv`.

| model | configuration | train_rows | refit_epochs | training_seconds |
| --- | --- | --- | --- | --- |
| LSTM | C | 1960 | 38 | 66.368 |
| GRU | C | 1960 | 36 | 74.5302 |
<!-- endtable: refits -->

One seed, a limited configuration grid, overlapping windows, nonstationary
log-price extrapolation and possible regime shifts limit conclusions.
These are documented limitations, not established economic causes of errors.
Source: `docs/phase6_lstm_gru.md` (Limitations).

## Phase 7 — Frozen final holdout evaluation

The final evaluation uses 211 common daily origins, 2025-11-14 through
2026-09-18, and exactly matched h5/h10 targets for all models. Forecast origins
include the last TRAIN date. All coefficients, neural weights and scalers
remain frozen; observed history/ARIMA filtered states may update without
refitting. The holdout is now consumed for final evaluation. Its protection
concerned model development: Phase 2 had previously processed full-period
descriptive data, so it was not literally never read historically.
Source: `docs/phase7_final_evaluation.md` (Final holdout, Frozen-model policy,
Common rolling origins, Scientific honesty).

<!-- table: holdout -->
Source: `outputs/tables/phase7_holdout_manifest.csv`.

| train_rows | test_rows | test_first_date | test_last_date | common_origins | first_test_access_utc |
| --- | --- | --- | --- | --- | --- |
| 1980 | 220 | 2025-11-17 | 2026-10-02 | 211 | 2026-10-07T20:37:49.449261+00:00 |
<!-- endtable: holdout -->

The five final price models are Naive, ARIMA(2,1,2) with drift, VAR(9), LSTM C
and GRU C. ARIMA(2,1,2) is the Phase 3A pedagogical challenger explicitly
included by the precommitted Phase 7 protocol; it is **not** the Phase 3B
locked specification, which remains Naive. The neural models were loaded
from verified Phase 6 caches. Exponentiated log forecasts have no lognormal
bias correction and need not be conditional mean price estimators.
Sources: `docs/phase7_final_evaluation_protocol.md` (Fixed panel and target),
`docs/phase7_final_evaluation.md` (Models compared, ARIMA, LSTM, GRU).

MSE is adjusted USD squared, RMSE/MAE adjusted USD and MAPE percent.
Every metric row uses the same number of origins. These frozen output
metrics are distinct from the internal Phase 3B/6 validation panels.
Source: `docs/phase7_final_evaluation.md` (Final price metrics).

<!-- table: final_metrics -->
Source: `outputs/tables/phase7_final_metrics.csv`.

| model | horizon | n_forecasts | MSE | RMSE | MAE | MAPE | rank_RMSE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ARIMA(2,1,2) | 5 | 211 | 93.9955 | 9.69513 | 7.70253 | 3.88026 | 2 |
| ARIMA(2,1,2) | 10 | 211 | 130.866 | 11.4396 | 9.40359 | 4.70942 | 1 |
| GRU C | 5 | 211 | 187.608 | 13.697 | 10.7659 | 5.31127 | 4 |
| GRU C | 10 | 211 | 215.001 | 14.6629 | 11.1723 | 5.46427 | 5 |
| LSTM C | 5 | 211 | 274.924 | 16.5808 | 13.3984 | 6.58384 | 5 |
| LSTM C | 10 | 211 | 181.648 | 13.4777 | 9.91148 | 4.90985 | 4 |
| Naive | 5 | 211 | 93.8102 | 9.68557 | 7.68782 | 3.84737 | 1 |
| Naive | 10 | 211 | 131.923 | 11.4858 | 9.07453 | 4.49009 | 2 |
| VAR(9) | 5 | 211 | 95.344 | 9.76443 | 7.84455 | 3.94744 | 3 |
| VAR(9) | 10 | 211 | 132.36 | 11.5048 | 9.25292 | 4.63361 | 3 |
<!-- endtable: final_metrics -->

DM compares two-sided squared losses, d=loss_A-loss_B; a negative mean favors A.
It uses Bartlett/Newey-West HAC lag h-1, Harvey-Leybourne-Newbold correction
and a t reference with 210 degrees of freedom. Holm adjusts four comparisons
versus Naive separately per horizon; GRU-versus-LSTM is a separate raw test.
An NA Holm cell means not applicable, not zero or missing raw inference.
ARIMA and VAR show no demonstrated difference against Naive. Naive's lower
loss is Holm-significant against both networks at h5 and GRU at h10;
LSTM-vs-Naive at h10 is not significant. **p > 0.05 is not proof of equality.**
Overlapping errors, HAC assumptions, heavy tails and nested-model comparisons
limit inference.
Source: `docs/phase7_final_evaluation.md` (Diebold-Mariano, Limitations).

<!-- table: dm -->
Source: `outputs/tables/phase7_diebold_mariano.csv`.

| model_a | model_b | horizon | mean_loss_diff | dm_statistic | p_value | p_value_holm_if_applicable | hac_lag | decision_5pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ARIMA(2,1,2) | Naive | 5 | 0.185247 | 0.0431408 | 0.96563 | 1 | 4 | not_rejected |
| VAR(9) | Naive | 5 | 1.5338 | 0.294678 | 0.768531 | 1 | 4 | not_rejected |
| LSTM C | Naive | 5 | 181.113 | 4.48217 | 1.21421e-05 | 4.85686e-05 | 4 | reject_equal_accuracy |
| GRU C | Naive | 5 | 93.7975 | 3.79662 | 0.000191962 | 0.000575887 | 4 | reject_equal_accuracy |
| GRU C | LSTM C | 5 | -87.3159 | -4.60391 | 7.17661e-06 | NA | 4 | reject_equal_accuracy |
| ARIMA(2,1,2) | Naive | 10 | -1.05738 | -0.0802552 | 0.936111 | 1 | 9 | not_rejected |
| VAR(9) | Naive | 10 | 0.436845 | 0.0326186 | 0.97401 | 1 | 9 | not_rejected |
| LSTM C | Naive | 10 | 49.7253 | 1.79099 | 0.0747353 | 0.224206 | 9 | not_rejected |
| GRU C | Naive | 10 | 83.0779 | 3.27368 | 0.00124138 | 0.00496551 | 9 | reject_equal_accuracy |
| GRU C | LSTM C | 10 | 33.3525 | 1.67548 | 0.0953293 | NA | 9 | not_rejected |
<!-- endtable: dm -->

ARIMA interval coverage is stored as a proportion, not percent. Full empirical
coverage with broad intervals does not establish calibration or future coverage.
Source: `docs/phase7_final_evaluation.md` (ARIMA interval coverage).

<!-- table: intervals -->
Source: `outputs/tables/phase7_arima_interval_coverage.csv`.

| horizon | 95pct_coverage | mean_interval_width | nominal_coverage |
| --- | --- | --- | --- |
| 5 | 1 | 54.2024 | 0.95 |
| 10 | 1 | 77.3901 | 0.95 |
<!-- endtable: intervals -->

The final recommended **price** model is **Naive / Random Walk**. It has the
lowest h5 RMSE and lowest MAE/MAPE at both horizons. ARIMA has the smallest
h10 RMSE, but its small gain, higher MAE and absent Holm DM support fail the
predeclared recommendation rule. That rule requires no worse RMSE/MAE at
both horizons, at least 1% improvement in mean RMSE ratio, Holm-supported
improvement at at least one horizon and no statistically worse horizon.
No challenger qualifies; Naive is retained by fallback and parsimony.
This does not prove universal optimality or a true random-walk data process.
Source: `docs/phase7_final_evaluation.md` (Predeclared protocol, Final recommended price model).

<!-- table: recommendation -->
Source: `outputs/tables/phase7_final_model_recommendation.csv`.

| final_recommended_price_model | rule | reason |
| --- | --- | --- |
| Naive | predeclared RMSE/MAE both horizons, >=1% mean gain, Holm DM support; otherwise naive | No challenger satisfies every predeclared requirement; retain parsimonious naive |
<!-- endtable: recommendation -->

**GARCH is excluded from the price ranking and DM price comparisons** because
its target is conditional innovation variance/volatility, a different quantity.
There is no evaluated volatility RMSE to report or compare with price RMSE.
Sources: `outputs/tables/phase7_target_scope_note.csv`,
`docs/phase5_garch.md` (Limitations),
`docs/phase7_final_evaluation.md` (Why GARCH is evaluated separately).

This is a single historical holdout evaluation of prediction errors, not a
trading backtest or a demonstration of profit after costs. It establishes no
strong economic causality, event-specific explanation or future-performance
guarantee. Source: `docs/phase7_final_evaluation.md` (Limitations).
<!-- END PROJECT FACTS -->

The following disclaimer governs section C; it does not create a fifth output
section.

# Investment Simulation Disclaimer

This is an academic exercise. Any investment interpretation or recommendation
is simulated and educational; it is not personalized financial advice.
The analysis uses historical results from a fixed sample, with high uncertainty
about future outcomes and changing market regimes. Volatility is the magnitude
of uncertainty, not the direction of the price. A volatility forecast does not
establish an expected gain or loss. Forecast accuracy does not establish a
profitable trading strategy, and the project has not evaluated trading costs
or investor-specific objectives. No future performance is guaranteed.
