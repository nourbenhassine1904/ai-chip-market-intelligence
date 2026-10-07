# Phase 7 — Final Holdout Evaluation

## Predeclared protocol

The final recommended price model is **Naive**, under the rule committed
before opening the holdout. ARIMA has the smallest h10 RMSE, but its small
gain does not satisfy the predeclared practical/statistical requirements.
Both recurrent networks have higher RMSE and MAE than Naive at both horizons.

The holdout was opened only after all model-development phases were
completed and the final evaluation protocol was committed.

Branch: `feature/final-evaluation`, from the completed Phase 6 state with
`v0.9.0-phase6` present. The protocol-only local commit is
`1e5ad76c6834f4e24fee825c894261597c94c917`, subject
`docs: predeclare final holdout evaluation protocol`, committed at
2026-10-07 20:19:24 UTC. Its working tree was verified clean before
implementation began. Neither protocol file changed afterward.

| Artifact | SHA-256 |
|---|---|
| [Protocol JSON](phase7_final_evaluation_protocol.json) | `c0d6eb9a7496041dc6cad76ced1607f9e2c47bb53f69e15d7de1e4dfdbac60de` |
| [Protocol Markdown](phase7_final_evaluation_protocol.md) | `bd3c481ff986bb0e98a4a31c5a1b3899d645eeb86576635e890bd152571469f7` |
| [Executed forecast source, archived in runtime evidence](../outputs/tables/phase7_runtime_audit.json) | `e3ab3fc5ad7a12ae2067a471a0a964c1fe84eea61e1ff7925c59c90ae2f4f93e` |
| [Final runner, including portable replay](../python/06_evaluation.py) | `8c9dfe8026997c6483b055910b247c1cb6be8c04e1bfbfae4a7e1844b0bb2f4f` |
| [Frozen predictions](../outputs/tables/phase7_final_predictions.csv) | `c49642b267f443b32649703341e3b83a045df75dc911e496e0d14d22b8ccee50` |

The committed rule requires complete matching forecasts, RMSE and MAE no
worse than Naive at both horizons, at least 1% improvement in the mean of
the two RMSE ratios, and a Holm-significant reduction in squared loss at
at least one horizon. No statistically worse horizon is allowed. Eligible
models are ordered by mean RMSE ratio, then mean MAE ratio within .001
ties, then the predeclared parsimony order. Otherwise recommend Naive.
MAPE is complementary. Prior diagnostics, interpretability and cost remain
context; they never authorize a new grid or post-hoc exclusion.

## Final holdout

TRAIN has 1980 rows, 2018-01-02–2025-11-14. TEST has exactly **220 rows and
34 columns**, 2025-11-17–2026-10-02. Both match the documented structure and
historical fingerprints. Dates are increasing and unique, splits do not
overlap, and combined backward returns/trailing volatility validate across
the split boundary. No methodological adaptation was necessary.

| Input | SHA-256 |
|---|---|
| Official TRAIN | `c3651f95959a49d8d64c791a8d48443dd520b978c3887b8793256dfff76c8f1c` |
| Official TEST | `124ebdff5b37de4459fcd9738e8d8ad968b3f945b66b647310f741640fa55fe4` |

First Phase 7 TEST access: **2026-10-07 20:37:49.449261 UTC**, after the
protocol commit, clean gate and TRAIN model freeze. All 2110 forecasts were
written and SHA-frozen at 20:38:41.057782 UTC; metrics began at
20:38:41.397092 UTC. The [manifest](../outputs/tables/phase7_holdout_manifest.csv),
[ordered access log](../outputs/tables/phase7_access_events.csv) and
[prediction freeze](../outputs/tables/phase7_prediction_freeze.csv) preserve
this application-level evidence. This is not an operating-system audit of
every historical process: Phase 2 previously processed the full descriptive
dataset. The protection concerns model development and this final opening.

## Frozen-model policy

All classical estimation and neural cache verification occurred on official
TRAIN before TEST access. No coefficient, innovation variance, network
weight, scaler or hyperparameter changed during the holdout. Numeric
coefficient/weight/scaler hashes were compared before and after forecasting;
ARIMA additionally checks coefficient equality after every append.

Only observed information through the current origin is allowed. Every
predictor receives an observed prefix. Neural input uses its last 60 rows;
VAR uses its last nine observed return vectors; ARIMA updates filtered state
with `append(..., refit=False)`. Cached features are verified against backward
price differences and trailing 20-return sample volatility × sqrt(252).
Every prediction records `max_feature_source_date <= origin_date`.

The [holdout audit](../outputs/tables/phase7_holdout_evaluation_audit.csv)
contains **16 PASS checks**. Source-scope checks distinguish allowed state
updates from prohibited model estimation. No test-performance-driven change
was made to the protocol, forecast logic, specifications or panel.

## Common rolling origins

There are **211 daily origins**, concatenated indices 1979–2189 inclusive,
from 2025-11-14 to 2026-09-18. Both horizons and all five models use exactly
this panel. No model loses dates or receives a different target/actual series.
Horizons count observed sessions, not calendar days.

| Origin | h5 target | h10 target |
|---|---|---|
| First: 2025-11-14 | 2025-11-21 | 2025-12-01 |
| Last: 2026-09-18 | 2026-09-25 | 2026-10-02 |

See [evaluation origins](../outputs/tables/phase7_evaluation_origins.csv).
Each of the ten model/horizon groups contains 211 forecasts: 2110 rows total.

## Models compared

Exactly Naive, ARIMA(2,1,2) with drift, VAR(9), LSTM C and GRU C. All predict
adjusted NVDA price in USD. Classical log forecasts and inverse-scaled neural
log forecasts are exponentiated without a lognormal bias correction, as
predeclared. They are not claimed to be conditional mean price estimators.
No new order, architecture, feature, optimizer or epoch choice was evaluated.

## Naive

The Phase 3B random walk is ARIMA(0,1,0) without drift. Implementation uses
the exact last observed adjusted close for both horizons, with no estimated
parameter. It has the lowest h5 RMSE and the lowest MAE and MAPE at both
horizons. This result does not establish that its innovations are white noise;
the prior mean-correlation diagnostic warning remains applicable.

## ARIMA

Fit once on the 1980 TRAIN NVDA log-prices, order (2,1,2), `trend='t'`,
stationarity/invertibility enforced, native initialization, maxiter=1000.
The fit converged without captured estimation warnings. Six fitted
parameters include innovation variance. Frozen parameter SHA-256:
`6c7fa8b5e7a7471d98057e3a780764e524a4071428ed5c7c5652cc5710cb661e`.
All appended observations are already realized at the current origin.
[statsmodels documents the no-refit append operation](https://www.statsmodels.org/stable/generated/statsmodels.tsa.arima.model.ARIMAResults.append.html).

ARIMA is marginally worse than Naive at h5 and improves h10 RMSE by about
0.40%, but has worse MAE at both horizons. Its mean normalized RMSE gain is
only 0.1514%, below the 1% threshold, and Holm DM p-values are 1 at both
horizons. Phase 3A optimization sensitivity, nonnormality and ARCH evidence
are retained as limitations, despite this run's convergence.

## VAR price reconstruction

Fit one constant VAR(9) on 1979 valid TRAIN return vectors ordered NVDA,
AMD, SOXX. The fitted system is stable; 84 mean coefficients are frozen.
The six distinct covariance components are separate from this count.
Parameter SHA-256:
`01c27c23dc00c26453c05da933cde1fe68b8894ef089e52183240fb65762fc43`.

At each origin, forecast ten percentage log returns from the last nine
observed vectors. Reconstruct
`log_price(t+k) = log_price(t) + sum(NVDA_forecast_returns[1:k])/100`,
then exponentiate. The `/100` is essential and tested. This is a recursive
return forecast, not a refitted price regression. VAR has slightly higher
RMSE/MAE than Naive at both horizons; DM does not demonstrate a difference.
Multivariate dynamics remain informative without establishing a final price
accuracy gain or a causal relationship. Phase 4 distributional/variance
assumption limitations remain.

## LSTM

LSTM C uses lookback=60, five fixed features, 64 units, dropout=.20 and ten
direct outputs. It has **18570 trainable parameters**, 38 locked refit epochs,
seed=42. Mode: **loaded_from_phase6_cache**. The original file hash,
Phase 6 provenance, TRAIN scaler statistics, architecture and all ten
TRAIN-end forecasts matched before TEST access; no reconstruction was needed.
Initial weight SHA-256:
`ea7182fb463738881339e2f2010a6f5a998f778dafe26b825520937a5a146e46`;
the post-evaluation comparison passed.

LSTM loses to Naive on RMSE/MAE at both horizons. Its squared-loss disadvantage
is significant after Holm at h5, but not demonstrated at h10 at 5%.
The latter does not prove equal accuracy. Its h10 RMSE is lower than its own
h5 RMSE; the direct outputs are learned separately, so increasing error
with horizon is not a mathematical requirement.

## GRU

GRU C has the same input/output specification, **14282 trainable parameters**,
36 locked refit epochs and seed=42. Mode: **loaded_from_phase6_cache**, with
the same complete pre-access verification. Initial weight SHA-256:
`63830a2b12f74a8fb30ee79b761f04e1344a619afac49e9add9387cffdff1dc5`;
the post-evaluation comparison passed.

Both neural scalers use exactly the 1960 usable TRAIN rows after the 20-row
feature warm-up; saved Phase 6 statistics are loaded after comparison with
TRAIN-only estimates. There is no scaler fitting on TEST. Inference disables
dropout and weights remain unchanged.

GRU loses to Naive at both horizons, with Holm-significant squared-loss
disadvantages at both. GRU beats LSTM at h5 in the separate raw DM comparison;
LSTM has lower observed loss at h10, without a significant difference at 5%.
Neither network improves on the benchmark, consistent with Phase 6 internal
validation warnings. One seed, finite sample and distribution shift limit
broader architectural conclusions.

## Final price metrics

MSE is adjusted USD²; RMSE and MAE are adjusted USD; MAPE is percent.
Error is forecast minus actual. Every row below uses the same 211 origins.
All metrics reload the byte-verified frozen prediction CSV.

| Model | h | MSE | RMSE | MAE | MAPE % | RMSE rank | MAE rank |
|---|---:|---:|---:|---:|---:|---:|---:|
| Naive | 5 | 93.810205 | 9.685567 | 7.687824 | 3.847370 | 1 | 1 |
| ARIMA(2,1,2) | 5 | 93.995452 | 9.695125 | 7.702535 | 3.880257 | 2 | 2 |
| VAR(9) | 5 | 95.344002 | 9.764425 | 7.844553 | 3.947441 | 3 | 3 |
| LSTM C | 5 | 274.923575 | 16.580819 | 13.398414 | 6.583835 | 5 | 5 |
| GRU C | 5 | 187.607669 | 13.696995 | 10.765880 | 5.311274 | 4 | 4 |
| Naive | 10 | 131.922930 | 11.485771 | 9.074526 | 4.490089 | 2 | 1 |
| ARIMA(2,1,2) | 10 | 130.865552 | 11.439648 | 9.403591 | 4.709423 | 1 | 3 |
| VAR(9) | 10 | 132.359775 | 11.504772 | 9.252920 | 4.633611 | 3 | 2 |
| LSTM C | 10 | 181.648260 | 13.477695 | 9.911475 | 4.909849 | 4 | 4 |
| GRU C | 10 | 215.000788 | 14.662905 | 11.172323 | 5.464275 | 5 | 5 |

RMSE order h5: **Naive → ARIMA → VAR → GRU → LSTM**.
RMSE order h10: **ARIMA → Naive → VAR → LSTM → GRU**.
MAE complements RMSE's greater sensitivity to large errors; MAPE expresses
relative errors at the observed price level. See [complete metrics](../outputs/tables/phase7_final_metrics.csv).

## Diebold-Mariano

Two-sided squared-error DM uses `d = loss_A - loss_B`. Negative mean loss
difference favors A. Center `u=d-mean(d)`, set `L=h-1` (4/9), and compute
`gamma[k]=sum(u[t]*u[t-k])/n` with denominator n=211. The Bartlett/Newey–West
long-run variance is `gamma[0]+2*sum((1-k/(L+1))*gamma[k], k=1..L)`.
No further finite-sample HAC scaling is applied.

```text
DM = mean(d) / sqrt(LRV / n)
HLN = sqrt((n + 1 - 2*h + h*(h-1)/n) / n)
DM_HLN = DM * HLN
p = 2 * t_survival(abs(DM_HLN), df=n-1)
```

HLN factors are .9786701169300297 and .9549733632779646; df=210.
This agrees with the Bartlett/HLN formulas in the
[official forecast DM implementation](https://raw.githubusercontent.com/robjhyndman/forecast/master/R/DM2.R).
The frozen protocol does not use its optional fallback to a shorter lag:
nonpositive variance would yield undefined inference. Identical observed
losses get statistic=0, p=1 and an explicit degenerate status. All ten actual
tests here have defined positive long-run variances.

| A versus B | h | Mean loss A−B, USD² | DM_HLN | Raw p | Holm p | Decision at 5% |
|---|---:|---:|---:|---:|---:|---|
| ARIMA vs Naive | 5 | .185247 | .043141 | .965630 | 1 | Not rejected |
| VAR vs Naive | 5 | 1.533797 | .294678 | .768531 | 1 | Not rejected |
| LSTM vs Naive | 5 | 181.113370 | 4.482168 | .0000121421 | .0000485686 | Reject; Naive lower loss |
| GRU vs Naive | 5 | 93.797464 | 3.796617 | .0001919622 | .0005758866 | Reject; Naive lower loss |
| GRU vs LSTM | 5 | −87.315906 | −4.603907 | .0000071766 | — | Reject; GRU lower loss |
| ARIMA vs Naive | 10 | −1.057377 | −.080255 | .936111 | 1 | Not rejected |
| VAR vs Naive | 10 | .436845 | .032619 | .974010 | 1 | Not rejected |
| LSTM vs Naive | 10 | 49.725330 | 1.790989 | .074735 | .224206 | Not rejected |
| GRU vs Naive | 10 | 83.077858 | 3.273679 | .001241379 | .004965515 | Reject; Naive lower loss |
| GRU vs LSTM | 10 | 33.352529 | 1.675476 | .095329 | — | Not rejected |

Holm has two separate families, four comparisons versus Naive per horizon.
The baseline decision uses Holm p, while GRU-vs-LSTM is a separately labeled
raw comparison. All tests remain two-sided. **p>.05 is insufficient evidence
of different expected accuracy, not evidence of equivalence.** Complete LRV,
raw DM, correction factors and decisions are in the [DM table](../outputs/tables/phase7_diebold_mariano.csv).

## ARIMA interval coverage

| Horizon | Forecasts | Empirical 95pct_coverage | Mean width, adjusted USD |
|---|---:|---:|---:|
| 5 | 211 | 100% | 54.202430 |
| 10 | 211 | 100% | 77.390142 |

The nominal 95% log-price prediction bounds were exponentiated. Coverage is
the inclusive fraction with lower≤actual≤upper; the CSV stores proportions
1.0. Full coverage with these broad intervals is consistent with conservative
intervals on this sample; it does not establish calibration or future 95%
coverage. Overlapping errors and retained variance/distribution assumptions
matter. Coverage does not enter selection, and no direct interval comparison
is made with the uncalibrated neural outputs. See [coverage table](../outputs/tables/phase7_arima_interval_coverage.csv).

## Performance vs complexity

Interpretability categories and complexity definitions were committed before
TEST access. All times are actual recorded seconds; these are not controlled
hardware-equivalent benchmarks. Neural training times are Phase 6 full-TRAIN
refits, excluding configuration search. Phase 7 cache loading took .358799s
for LSTM and .158844s for GRU, excluding framework startup.

| Model | Training seconds | Prediction seconds, 211 origins | Parameters | Interpretability |
|---|---:|---:|---:|---|
| Naive | 0 (no estimation) | .031911 | 0 | High |
| ARIMA | .413224 (Phase 7) | 2.616274 | 6 including variance | Medium |
| VAR | .007049 (Phase 7) | .137148 | 84 mean coefficients | Medium |
| LSTM | 66.368045 (Phase 6) | 20.378052 | 18570 trainable weights | Low |
| GRU | 74.530217 (Phase 6) | 27.993916 | 14282 trainable weights | Low |

Prediction times include ten-step forecasts and ARIMA state updates, but
exclude disk output, plotting and metric calculation. Parameter definitions
differ; VAR additionally estimates six unique covariance components. Naive
is the exact observed level; ARIMA has linear univariate coefficients; VAR
has multivariate predictive coefficients; neural gates have many nonlinear
weights. Extra complexity produces no qualifying improvement here. See
[tradeoffs](../outputs/tables/phase7_model_tradeoffs.csv) and
[fit/load provenance](../outputs/tables/phase7_model_fit_log.csv).

## Final recommended price model

`final_recommended_price_model = Naive`

No challenger satisfies every predeclared requirement. ARIMA's mean RMSE
ratio is .998485622, its mean MAE ratio is 1.019087994, and neither Holm DM
comparison supports improvement. VAR's mean RMSE ratio is 1.004898085,
LSTM's 1.442667730 and GRU's 1.345390183. Both neural models have higher
RMSE/MAE at both horizons. Naive therefore wins by the predeclared fallback
and parsimony rule, without claiming universal superiority.

See [recommendation](../outputs/tables/phase7_final_model_recommendation.csv)
and [all eligibility checks](../outputs/tables/phase7_recommendation_checks.csv).
The h10 RMSE winner is not automatically the final recommended model.

## Why GARCH is evaluated separately

GARCH is not ranked against price-forecast models because it forecasts a
different statistical target.

Phase 5 concerns conditional variance/volatility and risk. Its volatility
RMSE cannot be compared with adjusted-price RMSE. GARCH appears only in the
[target scope note](../outputs/tables/phase7_target_scope_note.csv), never in
the five-model price metrics, rankings or DM tests. No new GARCH fit is run.

## Limitations

- One 220-row holdout, two horizons and 211 overlapping origins provide a
  limited regime sample, not 211 independent errors per horizon.
- Fixed-lag HAC/HLN is an approximation under dependent, potentially
  nonstationary/heavy-tailed financial losses; nested-model comparisons also
  have calibration limitations. Holm covers the declared four baseline tests
  per horizon, not every possible study-wide comparison.
- Development phases, original data quality and adjusted-price conventions
  remain relevant. Forecasts assume all three origin-session closes are
  available; this is a close-to-future-close evaluation, not an executable
  trading backtest, profit claim or transaction-cost analysis.
- Frozen parameters can become stale. No adaptive retraining comparison is
  attempted. Neural conclusions concern these two locked models and one seed,
  not all deep-learning methods.
- Exponentiated log forecasts have no bias correction; neural models provide
  no calibrated interval. Broad ARIMA intervals do not remove ARCH warnings.
- CPU timing depends on framework, process warm-up and machine load. No missing
  historical search durations are invented.

## Scientific honesty

All five required models and all 211 origins are retained, including negative
neural results. No holdout-driven retuning, feature change, model exclusion,
optimizer fallback or recommendation-threshold change occurred. Prior
diagnostic warnings remain visible. The protocol and prediction fingerprints
are unchanged; aggregate tables and DM come exclusively from frozen forecasts.
The holdout is now consumed for final evaluation and must not become a new
development set.

Validation completed:

```text
.venv/Scripts/python.exe python/06_evaluation.py
.venv/Scripts/python.exe -m ruff check python/06_evaluation.py tests/test_evaluation.py
.venv/Scripts/python.exe -m pytest
.venv/Scripts/python.exe python/06_evaluation.py --summarize
```

Ruff passes. **208 pytest tests pass**, including 39 Phase 7 tests; four
pre-existing Phase 3A statsmodels `acorr_lm` FutureWarnings remain. The run
also reports TensorFlow oneDNN round-off information and native-Windows GPU
unavailability; CPU was predeclared. No initial ARIMA fit warning was captured.
The full `--summarize` replay reproduces **all 17 CSV tables and eight PNGs
byte-for-byte**, without opening TEST or loading/fitting models. The tracked
[runtime evidence JSON](../outputs/tables/phase7_runtime_audit.json) preserves
the original clean protocol gate, event sequence, measured freeze checks and
executed forecast source. A post-freeze portability correction lets the runner
replay this evidence without the ignored local cache; it changes no prediction,
metric formula or recommendation rule. An AST comparison test verifies that
all forecast/preparation/metric/DM/recommendation functions match the archived
executed source. Original `implementation_sha256` values are retained; derived
tables additionally identify `summary_implementation_sha256`. A scoped
`.gitattributes` rule preserves Phase 7 CSV LF bytes across Windows checkouts.
The final replay also preserves the evidence JSON byte-for-byte. Tests
trap ignored-cache dependencies and observation reads/fits in the summary
path, independently verify the
Bartlett covariance with a quadratic form, check HLN/sign/Holm, and reject
tampered forecast bytes, future features and mismatched panels. Running the
default pipeline again refuses to overwrite the immutable prediction file.

All eight PNG figures were visually inspected. Curves are plotted by target
date; two panels separate classical models and recurrent networks, each
retaining Naive. Produced figures:

- [RMSE h5](../outputs/figures/phase7/phase7_rmse_comparison_h5.png)
- [RMSE h10](../outputs/figures/phase7/phase7_rmse_comparison_h10.png)
- [MAE h5](../outputs/figures/phase7/phase7_mae_comparison_h5.png)
- [MAE h10](../outputs/figures/phase7/phase7_mae_comparison_h10.png)
- [Actual vs forecasts h5](../outputs/figures/phase7/phase7_actual_vs_forecasts_h5.png)
- [Actual vs forecasts h10](../outputs/figures/phase7/phase7_actual_vs_forecasts_h10.png)
- [Absolute errors h5](../outputs/figures/phase7/phase7_absolute_errors_over_time_h5.png)
- [Absolute errors h10](../outputs/figures/phase7/phase7_absolute_errors_over_time_h10.png)

Seventeen `phase7_*.csv` tables: holdout_manifest, evaluation_origins,
model_fit_log, scaler_audit, runtime_versions, final_predictions,
prediction_freeze, prediction_costs, access_events, final_metrics,
diebold_mariano, arima_interval_coverage, final_model_recommendation,
recommendation_checks, model_tradeoffs, target_scope_note,
holdout_evaluation_audit; plus the runtime evidence JSON. [Runtime versions](../outputs/tables/phase7_runtime_versions.csv)
and [scaler audit](../outputs/tables/phase7_scaler_audit.csv) provide additional
provenance. Phase 7 runtime caches are ignored by Git. The
[12-question human template](../llm/human_analysis/phase7_final_evaluation_interpretation.md)
has no answers. No Prophet, LLM analysis, final report edit or push is included.
