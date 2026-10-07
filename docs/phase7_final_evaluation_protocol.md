# Phase 7 — Predeclared final holdout evaluation protocol

This protocol is written and committed before opening `market_test.csv` in
Phase 7. Split metadata below comes from the existing Phase 2 documentation;
no holdout values or new holdout diagnostics inform this protocol.
The machine-readable companion is `phase7_final_evaluation_protocol.json`.
SHA-256 fingerprints of both files will be calculated before the protocol
commit and verified against committed bytes before test access. The commit
contains these two files only, followed by a clean-working-tree check.

## Fixed panel and target

Exactly five adjusted-NVDA-price models: Naive (ARIMA(0,1,0), no drift),
ARIMA(2,1,2) with drift, VAR(9), LSTM C and GRU C. All originate from frozen
development phases. No extra model, feature, configuration or alternative
order is considered after test access. GARCH remains a conditional-volatility
risk analysis and is excluded from price RMSE rankings.

Official TRAIN: 1980 rows, 2018-01-02–2025-11-14. Documented TEST: 220 rows,
2025-11-17–2026-10-02; 34 matching columns. Historical SHA-256 values are
copied from Phase 2, not calculated by accessing TEST now. After opening,
verify hashes, schema, finite values, increasing unique dates, disjoint
chronology, documented endpoints and boundary return/rolling continuity.
Any mismatch stops execution without methodological adaptation.

Horizon is an observed trading-session count, not calendar days. Use daily
origins from concatenated index 1979 through N_total-11 inclusive, retaining
only complete ten-step forecasts. With documented sizes this is 211 origins.
h5 and h10 and all five models share exactly these origins. h10 reaches the
last TEST date; h5 ends five observations earlier. Other origins are not
added to improve coverage or results. A count other than 211 stops the run.

## Frozen models and information updates

All estimation, scaler fitting and cache verification/reconstruction occur
on official TRAIN, before loading TEST. During evaluation, parameters remain
fixed; only already observed information through the current origin is used.
No `fit`, optimizer, neural training, scaler fitting or hyperparameter change
is permitted after TEST access. Initial nonconvergence stops the pipeline;
no alternate optimizer or opportunistic initialization is tried.

- Naive forecasts the exact origin adjusted close at all horizons.
- ARIMA uses statsmodels ARIMA order (2,1,2), trend='t', default stationary/
  invertible constraints, native independent initialization and maxiter=1000,
  coherent with Phase 3A. Fit once on all TRAIN log-prices. At each successive
  origin append only newly observed log-price with refit=False; freeze all
  coefficients and the innovation variance. Produce ten log forecasts and
  nominal 95% log prediction intervals, then exponentiate without bias
  correction. Interval coverage is reported separately and never selects a
  model. [ARIMA append reference](https://www.statsmodels.org/stable/generated/statsmodels.tsa.arima.model.ARIMAResults.append.html).
- VAR uses the ordered three percentage log-return series, constant and lag
  9, fitted once on the 1979 valid TRAIN return vectors. At each origin use
  the last nine observed return vectors. Recursively forecast ten returns
  using fixed coefficients; add their cumulative sum divided by 100 to the
  origin log-price, then exponentiate.
- LSTM C and GRU C are Input(60,5) → recurrent(64) → Dropout(.20) → Dense(10),
  as locked in Phase 6. Their fixed refit epochs are 38/36, seed 42, CPU,
  TensorFlow 2.21.0, Adam .001, batch 32, no shuffle. Prefer original Phase 6
  cache only when its pre-access byte hashes match the JSON, provenance
  matches Phase 6 outputs, scaler statistics match TRAIN-only fitting,
  architecture counts/configuration match and all ten TRAIN-end log forecasts
  reproduce Phase 6 within 1e-6. If unavailable or invalid, reconstruct once
  using the locked TRAIN-only specification and epochs, before loading TEST.
  Record loaded_from_phase6_cache or reconstructed_from_locked_specification.
  Do not replace the original Phase 6 cache or outputs. For reconstruction,
  use the unchanged Phase 6 builders/batching/deterministic settings and save
  Phase 7 models separately. The fixed scalers use the same 1960 usable TRAIN
  observations, with separate X/y normalization. At an origin only its last
  60 available feature rows enter inference; dropout is off.

Neural features are exactly NVDA_Log_Price, NVDA_Log_Return,
NVDA_Rolling_Vol_20D, AMD_Log_Return and SOXX_Log_Return. Validate backward
returns and trailing 20-return volatility (sample std × sqrt(252)), using
TRAIN for boundary history. No centered window, future shift, GARCH sigma
or additional variable. Assert max(feature_source_date)<=origin, and pass
only an observed prefix to every forecast function. Forecasts assume the
origin session's NVDA/AMD/SOXX closes are all available.

## Prediction freeze and metrics

Generate every forecast before computing aggregate metrics. Materialize
`phase7_final_predictions.csv` with model, origin/target dates and indices,
horizon, forecast/actual price, forecast log-price, error=forecast−actual,
squared/absolute error, and ARIMA interval bounds. There are 2110 rows
(5×211×2). Archive SHA-256 after writing; then reload the exact CSV for all
metrics, DM and interval coverage, verifying the hash each time. No model is
modified after inspecting the prediction file. If an existing frozen file
exists, do not silently overwrite it with changed forecasts.

Per model/horizon compute MSE=mean(error²), RMSE=sqrt(MSE), MAE=mean(|error|),
MAPE=100*mean(|error|/actual), in adjusted USD (MSE in USD², MAPE in percent).
Require complete finite forecasts and identical origin/target/actual panels;
any failure stops comparison without deleting dates or models. Rank RMSE and
MAE ascending, with equal numerical values receiving equal minimum rank.

## Diebold–Mariano specification

Exactly ten two-sided squared-error tests: ARIMA, VAR, LSTM, GRU versus Naive,
and GRU versus LSTM, each at h5/h10. Define d_t=loss_challenger−loss_reference;
a negative mean favors the challenger. Let n=211, L=h−1 and centered u=d−mean(d).
Use gamma_k=sum(u_t*u_(t−k))/n, Bartlett weights w_k=1−k/(L+1), and
LRV=gamma_0+2*sum(w_k*gamma_k,k=1..L). No additional finite-sample HAC scaling.
Uncorrected DM=mean(d)/sqrt(LRV/n). Apply Harvey–Leybourne–Newbold:

```text
HLN_factor = sqrt((n + 1 - 2*h + h*(h-1)/n) / n)
DM_HLN = DM * HLN_factor
p_value = 2 * Student_t_survival(abs(DM_HLN), df=n-1)
```

Report LRV, lag, HLN factor and raw/adjusted statistics. Identical zero loss
differences give statistic 0, p=1 and an explicitly degenerate-observed-loss
status; this is not evidence of equivalence. Nonpositive LRV for nonzero
differences gives undefined inference, never fabricated significance.

Apply Holm to the four comparisons versus Naive separately at each horizon
(two families of four). Report raw p and Holm p; baseline decision_5pct uses
Holm. GRU versus LSTM uses its raw two-sided p and is labeled a separate
unadjusted comparison. alpha=.05. p>.05 means insufficient evidence, not
identical expected accuracy. HAC truncation, nonstationarity, single holdout,
heavy-tailed losses and nested-model DM calibration remain limitations.
See [forecast modified-DM documentation](https://search.r-project.org/CRAN/refmans/forecast/html/dm.test.html)
and [statsmodels HAC](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html).

## Final recommendation rule

Eligibility first requires all valid forecasts on the same panel. RMSE is
primary, MAE secondary, MAPE complementary. To recommend a challenger over
Naive, require RMSE and MAE no worse than Naive at BOTH horizons, at least 1%
improvement in the equal-weight mean of its two RMSE ratios, and a negative
mean squared-loss difference with Holm p<.05 at at least one horizon.
Undefined DM does not count as support. No statistically worse horizon is
allowed. If none qualifies, recommend Naive by parsimony.

Among eligible challengers minimize mean(RMSE_model/RMSE_naive) over h5/h10.
Scores within absolute .001 are practically tied; then minimize mean MAE
ratio with the same tolerance, then use the predeclared parsimony order
Naive, ARIMA, VAR, GRU, LSTM. No threshold changes after test access.
The output field is final_recommended_price_model.

Prior stability and diagnostic limitations are retained, not erased by a
holdout win: Naive's mean-correlation warning; ARIMA's optimization sensitivity
and ARCH; VAR's conditional-variance/distribution assumptions; neural networks'
poor internal benchmark scores and one-seed uncertainty. These accompany the
recommendation and inform conservative tie-breaking; they do not authorize
post-hoc exclusion, retuning or a new model grid.

## Cost, complexity and interpretability

Use recorded Phase 6 refit times for loaded neural models, plus actual Phase 7
load/inference measurements; reconstructed-model times are measured separately.
Measure initial ARIMA/VAR fitting and all forecast/update times in this run.
No invented duration or hardware-equivalence claim. Training_cost and
prediction_cost retain seconds and source labels rather than arbitrary bins.
Interpretability is preclassified: Naive=high (last observation), ARIMA=medium
(univariate linear dynamic coefficients), VAR=medium (multivariate linear
coefficients, predictive rather than causal), LSTM/GRU=low (nonlinear gated
weights). Complexity is none/univariate linear/multivariate linear/nonlinear
recurrent respectively. Counts distinguish mean coefficients from variance
parameters; no ranking of unlike parameter definitions is implied.

## Boundary and provenance

The holdout is authorized only for this final evaluation. Record protocol
commit and SHA-256, first-access event sequence/time, TRAIN/TEST/implementation
fingerprints, pre/post coefficient/weight/scaler hashes, frozen-prediction
fingerprint and all checks. This is application-level evidence, not a claim
of an operating-system audit of every historical process. The Phase 2 full
descriptive workflow previously processed the full dataset; protected means
not used for model development, rather than never historically downloaded.
Do not begin Prophet, LLM interpretation, another phase or modify the final
report. Human interpretation template stays unanswered. No push, PR or merge.
