# Phase 6 — LSTM and GRU Temporal Deep Learning

## Objective

Develop mandatory LSTM and GRU architectures for direct ten-session NVDA
log-price forecasting and compare them with the locked random-walk benchmark.
This phase performs TRAIN-only temporal model development.
The final holdout remains untouched.

The [frozen protocol](phase6_protocol.json) and
[predeclared rule](phase6_selection_rule.md) were written before fitting any
network. They limit the search to 18 main fits and two final TRAIN refits.
No results from Phases 1–5 are recalculated or modified.

## Why LSTM and GRU?

Both recurrent architectures can learn nonlinear relationships across a
historical multivariate window. LSTM uses an additional cell state and gates;
GRU is a smaller gated alternative here. Their inclusion is mandatory, not
evidence that deep learning will outperform a random walk. Complexity and
small financial samples make a matched naive comparison essential.
See the official [LSTM](https://keras.io/api/layers/recurrent_layers/lstm/)
and [GRU](https://keras.io/api/layers/recurrent_layers/gru/) layer references.

## Target

`NVDA_Log_Price = ln(NVDA_Adj_Close)`. Each network emits the ten future
log-price levels directly. `exp(forecast_log_price)` returns an adjusted USD
point forecast without lognormal bias correction. It is not automatically
the conditional mean price. USD MSE/RMSE/MAE and percentage MAPE are primary;
log RMSE/MAE are secondary. No volatility metric is mixed with price metrics.

## Feature set

Only `data/processed/market_train.csv` supplies observations. Its SHA-256 is
`c3651f95959a49d8d64c791a8d48443dd520b978c3887b8793256dfff76c8f1c`.
All five requested names match the real columns:

| Feature | Purpose and unit |
| --- | --- |
| NVDA_Log_Price | Recent level of target, natural log of adjusted USD |
| NVDA_Log_Return | Recent NVDA dynamics, daily percentage log-return |
| NVDA_Rolling_Vol_20D | Recent trailing volatility state, annualized percent |
| AMD_Log_Return | Competitor return information, daily percent |
| SOXX_Log_Return | Sector return information, daily percent |

Phase 4 found incremental predictive information from past SOXX returns in
the NVDA VAR equation (Holm p≈0.000394). This motivates sector context, not
economic causality or a guarantee of nonlinear-model gains.
Phase 5's full-TRAIN fitted GARCH sigmas are deliberately not added as features:
they would require origin-specific refitting to be available historically.

There are 1980 initial rows, 2018-01-02 through 2025-11-14. Exactly 20 leading
rows are removed, leaving **1960 usable rows, 2018-01-31 through 2025-11-14**.
No interior NA, imputation, outlier deletion or additional variable is allowed.
The script checks all three assets' log-prices/backward returns and independently
recomputes NVDA trailing 20-return sample volatility, including sqrt(252).
This feature is available after the origin session's close; forecasts assume
contemporaneous AMD/SOXX closing information is then available too.

## Sliding windows

For origin index t and lookback L, X includes t-L+1 through t, with five columns.
The target vector contains t+1 through t+10. Runtime assertions prohibit future
input features and targets outside the permitted block. Inputs have shape
`[sequences, lookback, 5]`; targets have shape `[sequences, 10]`.

Validation advances origins daily. Historical windows may include past
observations from the current validation block, since they are known by the
new origin; weights and scalers remain fixed before that block. This is a
rolling-origin evaluation, not a single ten-step forecast for the entire block.

## Why direct multi-output forecasting?

A Dense(10) output predicts all future levels in one pass. h5 and h10 are
positions 5 and 10 of the same vector, without recursive substitution of a
predicted price into the next input. Training MSE equally weights all ten
standardized log-price outputs. This does not impose temporal consistency or
estimate a predictive interval.

## Scaling and leakage prevention

Separate StandardScaler X/y objects are fitted on the fold TRAIN prefix only.
The y scaler has one scalar mean/std shared by all ten target positions.
Each original daily observation counts once in scaler fitting, rather than
being duplicated through overlapping windows. No full-TRAIN scaling occurs
before internal validation. Every architecture/configuration uses the same
fold scaler statistics. Float64 preprocessing precedes float32 neural inputs.
See [StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html).

Early stopping uses the last 10% of fold TRAIN, not its external validation
block. Thus future external labels cannot select the weights used at an earlier
external origin. Optimization targets end before floor(.9*TRAIN rows); stopping
targets lie wholly in the remaining TRAIN tail. Nine target windows straddling
this inner boundary are purged. The fold scalers include this tail because it
belongs to TRAIN; its loss is a stopping device, not an independent test score.
There are no extra fold refits. The validation metrics below use only the
external blocks, which never enter `model.fit` or its callbacks.

## Temporal validation folds

For N=1960, boundaries are floor(.7N)=1372, floor(.8N)=1568,
floor(.9N)=1764, and N. Ends in code are exclusive. Each validation block
contains 196 observed sessions. No random split, ordinary K-fold or shuffle.

| Fold | Fold TRAIN dates | Rows | External validation dates | Rows |
| --- | --- | ---: | --- | ---: |
| 1 | 2018-01-31–2023-07-14 | 1372 | 2023-07-17–2024-04-24 | 196 |
| 2 | 2018-01-31–2024-04-24 | 1568 | 2024-04-25–2025-02-05 | 196 |
| 3 | 2018-01-31–2025-02-05 | 1764 | 2025-02-06–2025-11-14 | 196 |

| Fold | Optimization rows | Optimization sequences A / B,C | Inner-stop sequences | External origins h5 / h10 |
| --- | ---: | ---: | ---: | ---: |
| 1 | 1234 | 1205 / 1165 | 129 | 187 / 187 |
| 2 | 1411 | 1382 / 1342 | 148 | 187 / 187 |
| 3 | 1587 | 1558 / 1518 | 168 | 187 / 187 |

Only complete ten-target vectors are scored. Origins run from block_start-1
to block_end-11 inclusive. h10 targets reach the last block date; h5 targets
stop five observations earlier. All six network candidates and naive use the
same 187 origins per fold/horizon, or **561 forecasts per model/horizon**.
This choice is fixed before scores and keeps h5/h10 panels directly aligned.

## Hyperparameters

| Configuration | Lookback | Units | Dropout |
| --- | ---: | ---: | ---: |
| A | 20 | 32 | 0.10 |
| B | 60 | 32 | 0.10 |
| C | 60 | 64 | 0.20 |

Both architectures use output_horizon=10, Adam learning_rate=.001, MSE,
batch_size=32, max_epochs=100, patience=10, restore_best_weights=True,
shuffle=False, seed=42. No further candidates are tried after seeing scores.

## LSTM architecture

Input `[lookback,5]` → LSTM(units) → Dropout(dropout) → Dense(10).
Default tanh/sigmoid gates; one recurrent layer, no stateful recurrence.
Trainable parameters: 5194 for A/B, 18570 for C.

## GRU architecture

Input `[lookback,5]` → GRU(units) → Dropout(dropout) → Dense(10).
Default reset_after=True and tanh/sigmoid gates; otherwise the same design.
Trainable parameters: 4074 for A/B, 14282 for C. Counts are checked against
Keras at runtime; fewer parameters do not imply better forecasting accuracy.

## Training and early stopping

Python 3.12.3, TensorFlow 2.21.0, CPU, seed 42. Python random, NumPy and
TensorFlow seeds are reset before each independent model. Deterministic
operations are requested; intra/inter-op thread counts are fixed at 4/1.
Ordered tf.data batches use a one-thread private pool and no shuffle.
Native-Windows GPU/oneDNN informational messages are not fit failures.
No CUDA, WSL, PyTorch migration or dependency installation occurs.
`tensorflow==2.21.0` is declared in requirements.txt.

Keras early stopping monitors inner val_loss, restores its minimum-loss
weights and stops after ten non-improving epochs, or at the 100-epoch cap.
Best epochs are one-based. All histories and elapsed training times are
exported. Timing includes model construction/compilation and fit, excluding
forecast scoring. A technical failure is recorded and stops execution;
no configuration is silently replaced. References:
[EarlyStopping](https://keras.io/api/callbacks/early_stopping/),
[training API](https://keras.io/api/models/model_training_apis/),
[determinism](https://www.tensorflow.org/api_docs/python/tf/config/experimental/enable_op_determinism).
Reproducibility is scoped to the software/hardware stack, not promised
bit-for-bit across platforms or TensorFlow versions.

## Loss curves

The displayed curves use the locked configuration C in Fold 3 for each
architecture. Both runs train for 48 epochs and restore epoch **38**. Inner
validation loss stops improving while optimization continues; this is a
warning of possible overfitting to the optimization segment, not evidence
from the outer validation labels. Dropout is active for training loss but
inactive for validation loss, so their numerical gap alone is not a calibrated
overfitting test. Early stopping limits this behavior without changing the
predeclared grid or monitoring the external scoring block.

At epoch 38 versus epoch 48, LSTM inner loss rises from .005469 to .005704
while training loss falls from .016831 to .011133; GRU inner loss rises from
.005791 to .006683 while training loss falls from .012752 to .010447. These
small late changes are less visible than the initial spikes on the full loss
scale; the archived numeric histories preserve them.

Best epochs (one-based) and total epochs run are fully retained:

| Architecture / config | Best epochs, folds 1/2/3 | Epochs run, folds 1/2/3 | Median best |
| --- | --- | --- | ---: |
| LSTM A | 50 / 84 / 58 | 60 / 94 / 68 | 58 |
| LSTM B | 29 / 71 / 75 | 39 / 81 / 85 | 71 |
| LSTM C | 16 / 45 / 38 | 26 / 55 / 48 | 38 |
| GRU A | 34 / 95 / 69 | 44 / 100 / 79 | 69 |
| GRU B | 32 / 71 / 51 | 42 / 81 / 61 | 51 |
| GRU C | 21 / 36 / 38 | 31 / 46 / 48 | 36 |

Seventeen runs stop before the cap. GRU A Fold 2 reaches 100 epochs and
restores epoch 95; this is a recorded cap, not a failed fit or an excuse to
change patience/max_epochs. No technical training failure occurred.

## Validation metrics

The [fold table](../outputs/tables/phase6_validation_metrics_by_fold.csv)
has 42 rows: seven candidates including naive × three folds × two horizons.
The [summary](../outputs/tables/phase6_validation_metrics_summary.csv)
has 14 rows and pools the 561 forecast errors per candidate/horizon.
Pooled RMSE is sqrt(mean squared errors), not the mean of fold RMSEs.

| Model / config | Horizon | MSE, USD² | RMSE, USD | MAE, USD | MAPE, % | Log RMSE | Log MAE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Naive | 5 | 54.350957 | 7.372310 | 5.584424 | 5.172548 | .065418 | .052217 |
| Naive | 10 | 101.033836 | 10.051559 | 7.757694 | 7.275997 | .093101 | .074096 |
| LSTM A | 5 | 412.806820 | 20.317648 | 16.573134 | 14.803792 | .217703 | .168466 |
| LSTM A | 10 | 338.184536 | 18.389794 | 14.609821 | 13.786946 | .217023 | .157030 |
| LSTM B | 5 | 632.704558 | 25.153619 | 21.143396 | 20.574593 | .306926 | .245157 |
| LSTM B | 10 | 478.839995 | 21.882413 | 17.884439 | 17.824917 | .282025 | .210660 |
| LSTM C | 5 | 232.640827 | 15.252568 | 11.796895 | 11.877425 | .195740 | .134535 |
| LSTM C | 10 | 227.132465 | 15.070915 | 11.397046 | 11.212128 | .182390 | .125411 |
| GRU A | 5 | 157.528824 | 12.551049 | 9.504835 | 9.836119 | .151820 | .108217 |
| GRU A | 10 | 214.343352 | 14.640470 | 11.729596 | 11.642922 | .164232 | .124026 |
| GRU B | 5 | 257.997718 | 16.062307 | 13.143729 | 13.083517 | .185193 | .145954 |
| GRU B | 10 | 216.101893 | 14.700405 | 11.655360 | 12.015573 | .178381 | .132621 |
| GRU C | 5 | 110.586258 | 10.516000 | 8.123999 | 7.822086 | .107494 | .081784 |
| GRU C | 10 | 176.059620 | 13.268746 | 10.465105 | 9.931074 | .135825 | .105402 |

Primary scores use six equally weighted fold/horizon ratios, not pooled USD
metrics, and select C separately for each architecture:

| Architecture / config | Mean RMSE ratio | Mean MAE ratio | Successful folds |
| --- | ---: | ---: | ---: |
| LSTM A | 2.815826 | 2.731314 | 3 |
| LSTM B | 3.390592 | 3.526673 | 3 |
| LSTM C | 2.319180 | 2.205964 | 3 |
| GRU A | 2.007837 | 1.939758 | 3 |
| GRU B | 2.269081 | 2.283454 | 3 |
| GRU C | 1.651779 | 1.586649 | 3 |

## Comparison with naive benchmark

The locked Phase 3B ARIMA(0,1,0) without drift gives the origin's latest NVDA
adjusted price at every horizon. It is recomputed analytically on the current
matched origins. Historical Phase 3B metrics use a different panel and are
not copied into this comparison. Improvement is 100*(naive-model)/naive;
negative values are reported without suppression.

For both locked architectures, **the network did not outperform the naive
benchmark on TRAIN-only temporal validation**. All six candidates have worse
pooled RMSE and MAE than naive at both horizons; no negative result is hidden.

| Locked candidate | h5 RMSE improvement, % | h10 RMSE improvement, % | h5 MAE improvement, % | h10 MAE improvement, % |
| --- | ---: | ---: | ---: | ---: |
| LSTM C | -106.889939 | -49.936092 | -111.246391 | -46.912809 |
| GRU C | -42.641857 | -32.006847 | -45.476038 | -34.899694 |

The [full comparison](../outputs/tables/phase6_vs_naive.csv) retains all
configurations and both horizons. A ratio above one means degradation.

## Locked LSTM configuration

Selection requires all three successful folds and no leakage. The primary
score is the equally weighted mean of RMSE_model/RMSE_naive over 3 folds ×
h5/h10. Absolute score differences ≤.001 are practically tied; use mean
MAE ratio, fewer parameters, shorter lookback, then label. This numeric
tolerance is predeclared. No champion final project model is selected.

`locked_lstm_configuration=C`: lookback=60, units=64, dropout=.20,
18570 parameters, mean RMSE ratio=2.319180, mean MAE ratio=2.205964.
C has the lowest primary score; no practical tie or tie-breaker is needed.

## Locked GRU configuration

The identical rule applies independently to GRU. Mandatory architectures
remain included even if they fail to outperform naive.

`locked_gru_configuration=C`: lookback=60, units=64, dropout=.20,
14282 parameters, mean RMSE ratio=1.651779, mean MAE ratio=1.586649.
C has the lowest primary score; no practical tie or tie-breaker is needed.

## LSTM vs GRU

GRU C has a lower mean RMSE/MAE ratio and lower pooled h5/h10 RMSE/MAE
than LSTM C on this internal validation. It uses 14282 versus 18570 parameters
but takes more measured CPU training time in this run. Fewer parameters do
not guarantee shorter wall time: recurrent kernels, operations and host load
also matter. Both models remain required and both trail naive. This is an
internal comparison, not a declaration of the project's final champion.

## Full-TRAIN refit

After locking, each architecture is trained once on every usable TRAIN
window with new scalers fitted on the 1960 TRAIN rows. The epoch count is the
integer median of its three best fold epochs. No early stopping or validation
data is used at refit. Models and full-TRAIN scaler statistics are saved locally
under ignored `.cache/phase6`; fitted weights are not committed as raw artifacts.

Both refits pass: LSTM C uses **38 fixed epochs**, GRU C **36 fixed epochs**.
Each uses **1891 complete training windows**, lookback 60, ten targets, and
X/y scalers fitted on exactly 1960 observations. Neither refit has validation
data or an early-stopping callback.

Both saved `.keras` refits were reloaded with their saved scaler statistics.
Direct inference reproduces all ten exported endpoint log-prices exactly in
this environment (maximum absolute difference 0 for each model).

## TRAIN-end forecasts

Origin is **2025-11-14**, the last official TRAIN observation. There are 30
forecast rows, ten per locked architecture and naive, each labeled
`TRAIN_endpoint_forecast_no_holdout_evaluation`. No future dates are invented
and no realized holdout price is loaded. Complete log-price outputs are in the
[forecast table](../outputs/tables/phase6_train_end_forecasts.csv).

| Horizon, sessions | LSTM C, adjusted USD | GRU C, adjusted USD | Naive, adjusted USD |
| --- | ---: | ---: | ---: |
| 1 | 182.104524 | 181.407672 | 189.715469 |
| 2 | 184.287924 | 181.610950 | 189.715469 |
| 3 | 187.142590 | 181.578674 | 189.715469 |
| 4 | 188.571201 | 182.673636 | 189.715469 |
| 5 | 184.176082 | 184.284148 | 189.715469 |
| 6 | 181.032534 | 184.619115 | 189.715469 |
| 7 | 183.393289 | 184.195373 | 189.715469 |
| 8 | 184.110040 | 181.297395 | 189.715469 |
| 9 | 189.025897 | 182.382267 | 189.715469 |
| 10 | 194.630131 | 184.814714 | 189.715469 |

These are model outputs, not evidence that their future price direction or
accuracy is correct. Independent output heads may produce a nonmonotonic
forecast path. There is no final metric, future error or prediction interval.

## Computational cost

The 18 main CPU fits take **1067.562 seconds (17.79 minutes)** in total.
Full-TRAIN refits take **66.368 seconds for LSTM C** and **74.530 seconds for
GRU C**, or **140.898 seconds** combined. Total measured fitting time is
**1208.461 seconds (20.14 minutes)**, excluding preprocessing, scoring,
figures, tests and documentation. Background verification and host load can
affect these wall-clock measurements; they are not hardware benchmarks.

| Architecture / config | Parameters | Mean seconds / fold | Total seconds / three folds | Median best epoch |
| --- | ---: | ---: | ---: | ---: |
| LSTM A | 5194 | 39.942318 | 119.826954 | 58 |
| LSTM B | 5194 | 57.535789 | 172.607367 | 71 |
| LSTM C | 18570 | 53.500217 | 160.500652 | 38 |
| GRU A | 4074 | 45.544144 | 136.632433 | 69 |
| GRU B | 4074 | 82.428069 | 247.284208 | 51 |
| GRU C | 14282 | 76.903610 | 230.710830 | 36 |

The longest individual fit is GRU B Fold 2, **115.315 seconds**. Slow fits
do not trigger a changed grid or opportunistic epoch reduction. The
[complexity table](../outputs/tables/phase6_model_complexity.csv) records all
six candidates; timing is measured, not inferred from parameter counts.

## Limitations

Nonstationary log-price levels and large changes in price scale can make
out-of-range extrapolation difficult for gated networks. Scalers transform
unseen levels without clipping. The small sample, overlapping windows,
single seed, regime changes and equal ten-output log-MSE can limit generality.
Pooled USD scores emphasize expensive-price periods; the main selection score
instead weights fold/horizon ratios equally. No confidence intervals or DM
test are produced; overlapping forecast errors are not independent.

Inner stopping reduces the observations used for gradient updates within
each fold. Full-TRAIN refits use all windows for median selected epochs and
are different fits, without a new validation score. Configuration selection
uses all three outer development blocks, so reported internal scores are not
an unbiased final evaluation of the chosen configuration. The final holdout
is required later to establish generalization. No predictive-interval,
economic profitability or trading-cost claim follows from these results.

## Phase boundary

This phase performs TRAIN-only temporal model development.
The final holdout remains untouched.

The guard distinguishes runtime assertions from labeled code-scope audits;
it is not an operating-system audit of every file access. Unit tests use
synthetic data and trap forbidden observation reads before opening files.
Historical Phases 1–5 remain unchanged; the human interpretation template
contains only unanswered headings. No Prophet, hybrid, final evaluation,
final DM, push, PR, merge or next phase is run.

Technical validation: **Python pipeline PASS**, **Ruff PASS**, **169 pytest
tests passed**, including 29 Phase 6 cases. The guard has **17 PASS rows**.
All seven final figures were visually inspected. There are 19 CSV outputs,
18 successful main runs and two successful refits. The 257 historical files
checked outside the three authorized shared/script edits remain unchanged.

Four existing Phase 3A statsmodels FutureWarnings remain in pytest.
TensorFlow emits informational oneDNN/native-Windows GPU messages and an
upstream deprecated `tf.reset_default_graph` alias warning during Keras
session clearing. None is a fit failure; no training produces nonfinite
losses or forecasts. Runtime Keras is 3.15.1; NumPy 2.5.3 and pandas 3.0.6.

Reproduce from the repository root using the project environment:

```powershell
.\.venv\Scripts\python.exe python/05_lstm_gru.py
.\.venv\Scripts\python.exe -m ruff check python/05_lstm_gru.py tests/test_lstm_gru.py
.\.venv\Scripts\python.exe -m pytest
```

Each pipeline run performs the same 18 main fits and two refits; no silent
package installation or automatic grid expansion occurs.

Figure inventory (seven PNGs):

- [LSTM Fold 3 loss](../outputs/figures/phase6/phase6_lstm_loss_curve.png)
- [GRU Fold 3 loss](../outputs/figures/phase6/phase6_gru_loss_curve.png)
- [Validation RMSE h5](../outputs/figures/phase6/phase6_validation_rmse_h5.png)
- [Validation RMSE h10](../outputs/figures/phase6/phase6_validation_rmse_h10.png)
- [LSTM versus GRU score](../outputs/figures/phase6/phase6_lstm_vs_gru_validation.png)
- [Matched fold predictions h5](../outputs/figures/phase6/phase6_fold_predictions_h5.png)
- [Matched fold predictions h10](../outputs/figures/phase6/phase6_fold_predictions_h10.png)

Table inventory (all names prefixed `outputs/tables/phase6_`, suffix `.csv`):

```text
runtime_versions                 train_manifest
temporal_folds                   scaler_audit
training_runs                    loss_history
validation_predictions           validation_metrics_by_fold
validation_metrics_summary       validation_ratios_by_fold
configuration_scores             vs_naive
locked_lstm                      locked_gru
lstm_gru_comparison              model_complexity
full_train_refits                train_end_forecasts
holdout_guard
```

Tables retain scope, seed, TRAIN SHA-256, protocol SHA-256, predeclared-rule
SHA-256 and implementation SHA-256. The protocol JSON and source/rule files
have Git-enforced LF line endings for stable fingerprints. Full histories
cover every candidate/fold, not only the two displayed locked loss curves.
