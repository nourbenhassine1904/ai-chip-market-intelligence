# Phase 3B — TRAIN-Only ARIMA Rolling Validation

## Objective

Compare five fixed Phase 3A hypotheses and lock one specification for later
work. **This is TRAIN-only internal validation and not the final holdout evaluation.**
Phase 3A remains the historical in-sample identification and diagnostic phase;
its conclusions and files are unchanged.

## Why rolling-origin validation?

Each origin mimics a forecast made with information available at that date.
Expanding prefixes preserve temporal order and allow multiple validation dates;
there is no random split, shuffle or ordinary K-fold. Fixed orders avoid a
new auto.arima search. The full-TRAIN Phase 3A identification informed the
candidate list, so this is internal model selection, not a fully nested or
independent assessment of the entire identification process.

## Data and anti-leakage design

Only `data/processed/market_train.csv` supplies market observations: 1,980 rows,
2018-01-02 to 2025-11-14. Python verifies the frozen SHA-256; R verifies the
matching frozen MD5. Both verify dates, positive finite prices and chronology.
The closed reader rejects other market paths before opening them. Protocol,
candidates and language output files are metadata, not extra market inputs.
Targets are retrieved for scoring only after each fit; only a copied prefix
ending at its origin is passed to estimation. No full-TRAIN refit is performed.
`phase3b_holdout_guard.csv` combines measured assertions and labelled code
audits; all rows must PASS. Cross-language input/config hashes and origin
grids must agree before a lock can be written. No final test file is opened.

## Candidate models

| model | p | d | q | drift | k |
| --- | --- | --- | --- | --- | --- |
| Naive | 0 | 1 | 0 | False | 1 |
| RW_drift | 0 | 1 | 0 | True | 2 |
| ARIMA111_drift | 1 | 1 | 1 | True | 4 |
| ARIMA212_drift | 2 | 1 | 2 | True | 6 |
| ARIMA313_no_drift | 3 | 1 | 3 | False | 7 |

Naive uses the last observed price exactly. RW_drift uses the Gaussian ML
mean of log-price differences, the analytic ARIMA(0,1,0)+drift point forecast.
Both implementations use these identical baseline formulae. Complex models
use R forecast::Arima ML and Python statsmodels ARIMA state-space ML with
independent default initialization, maxiter=1000, with
no alternate-model fallback, no cross-language initialization and no silent replacement.

## Expanding-window protocol

The protocol and selection rule were written to files before any Phase 3B
result was computed: [protocol](phase3b_validation_protocol.csv) and
[candidates](phase3b_validation_candidates.csv). They are predeclared, not
tuned after observing results. Initial size: 1386
(70% of TRAIN). Step: 10 observed trading sessions.
Number of origins: **59**. First origin:
**2023-07-06** (zero-based index 1385); last origin:
**2025-10-27** (index 1965, prefix size 1966).
The prefix always starts at the first TRAIN row and adds ten sessions.
Ten-session spacing was chosen before execution to limit independent
high-order ML fits while covering the remaining TRAIN period regularly;
it is coarser than every-session or five-session evaluation. No opportunistic
origin reduction, terminal origin insertion or fold deletion is performed.
The full origin/target grids are exported for both languages.
The two protocol CSV files use Git-enforced LF endings so their recorded
fingerprints remain stable across Windows and Unix checkouts.

## Horizons

h=5 and h=10 observed sessions. Target index equals origin index+h; a ten-step
forecast is computed at each origin and only the exact fifth/tenth endpoints
are evaluated. All origins support both horizons. Last h=10 target:
2025-11-10. Remaining terminal TRAIN sessions outside this regular
grid are not extra folds. One origin generates two endpoint observations,
not ten observations for each horizon. The fixed spacing avoids overlapping
forecast intervals across adjacent origins, but does not establish
statistical independence of forecast errors.

## Back-transformation

All ARIMA point forecasts use `exp(log_price_forecast)`, without lognormal
bias correction. This is generally a conditional median under a lognormal
interpretation, not necessarily the conditional price expectation. The same
convention applies to every candidate and language. For naive, the exact
last price is retained to avoid floating-point exp/log round-trip error.

## Validation metrics

Main metrics on positive adjusted prices in USD: MSE=mean(error squared),
RMSE=sqrt(MSE), MAE=mean(abs(error)), MAPE=100*mean(abs(error)/actual).
Log-price MAE/RMSE are secondary. Endpoints have equal weight within a
model/horizon. Higher late-period price levels can dominate USD losses;
MAPE is reported as a complementary scale-sensitive diagnostic.
Unusable fits have blank forecasts and explicit fit-log rows. Metrics use
available converged origins; coverage and failures accompany every row.
Incomplete candidates cannot lock. Baseline gains use exactly the successful
origins of each candidate. Nonconvergence counts are per fit, not the sum
of duplicate h=5/h=10 rows.

## R results

| model | horizon | n_forecasts | MSE | RMSE | MAE | MAPE | log_MAE | log_RMSE | failed_fits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ARIMA111_drift | 5 | 59 | 61.5947 | 7.84823 | 5.9342 | 5.72118 | 0.056886 | 0.0711568 | 0 |
| ARIMA111_drift | 10 | 59 | 82.4701 | 9.08131 | 6.73085 | 6.82398 | 0.0683095 | 0.0886271 | 0 |
| ARIMA212_drift | 5 | 59 | 61.5712 | 7.84673 | 5.93824 | 5.72276 | 0.0569048 | 0.0711694 | 0 |
| ARIMA212_drift | 10 | 59 | 82.4394 | 9.07961 | 6.72939 | 6.82122 | 0.0682841 | 0.0886236 | 0 |
| ARIMA313_no_drift | 5 | 59 | 60.287 | 7.76447 | 5.88357 | 5.65658 | 0.056699 | 0.0708539 | 0 |
| ARIMA313_no_drift | 10 | 59 | 88.0866 | 9.38545 | 7.29488 | 7.18545 | 0.0729769 | 0.0918688 | 0 |
| Naive | 5 | 59 | 59.6576 | 7.72383 | 5.856 | 5.63916 | 0.0565647 | 0.0705796 | 0 |
| Naive | 10 | 59 | 87.7827 | 9.36924 | 7.25316 | 7.12552 | 0.0725397 | 0.0918771 | 0 |
| RW_drift | 5 | 59 | 61.0543 | 7.81373 | 5.91673 | 5.7 | 0.0566763 | 0.070801 | 0 |
| RW_drift | 10 | 59 | 82.9073 | 9.10534 | 6.76008 | 6.84717 | 0.0685372 | 0.0887582 | 0 |

R fit coverage, counting each fit only once across the two horizons:

| language | model | n_origins | n_forecasts | failed_fits |
| --- | --- | --- | --- | --- |
| R | ARIMA111_drift | 59 | 59 | 0 |
| R | ARIMA212_drift | 59 | 59 | 0 |
| R | ARIMA313_no_drift | 59 | 59 | 0 |
| R | Naive | 59 | 59 | 0 |
| R | RW_drift | 59 | 59 | 0 |

## Python results

| model | horizon | n_forecasts | MSE | RMSE | MAE | MAPE | log_MAE | log_RMSE | failed_fits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ARIMA111_drift | 5 | 53 | 61.4288 | 7.83765 | 6.03248 | 5.70412 | 0.0564619 | 0.0695538 | 6 |
| ARIMA111_drift | 10 | 53 | 77.0867 | 8.77991 | 6.49639 | 6.57334 | 0.065538 | 0.0855137 | 6 |
| ARIMA212_drift | 5 | 54 | 54.033 | 7.35071 | 5.43358 | 5.36556 | 0.0532768 | 0.0674882 | 5 |
| ARIMA212_drift | 10 | 54 | 75.1972 | 8.67163 | 6.61925 | 6.79309 | 0.0683687 | 0.0866051 | 5 |
| ARIMA313_no_drift | 5 | 59 | 59.7761 | 7.7315 | 5.82565 | 5.61624 | 0.0563317 | 0.0706974 | 0 |
| ARIMA313_no_drift | 10 | 59 | 86.8008 | 9.3167 | 7.21512 | 7.12328 | 0.0725001 | 0.0916674 | 0 |
| Naive | 5 | 59 | 59.6576 | 7.72383 | 5.856 | 5.63916 | 0.0565647 | 0.0705796 | 0 |
| Naive | 10 | 59 | 87.7827 | 9.36924 | 7.25316 | 7.12552 | 0.0725397 | 0.0918771 | 0 |
| RW_drift | 5 | 59 | 61.0543 | 7.81373 | 5.91673 | 5.7 | 0.0566763 | 0.070801 | 0 |
| RW_drift | 10 | 59 | 82.9073 | 9.10534 | 6.76008 | 6.84717 | 0.0685372 | 0.0887582 | 0 |

Python fit coverage:

| language | model | n_origins | n_forecasts | failed_fits |
| --- | --- | --- | --- | --- |
| Python | ARIMA111_drift | 59 | 53 | 6 |
| Python | ARIMA212_drift | 59 | 54 | 5 |
| Python | ARIMA313_no_drift | 59 | 59 | 0 |
| Python | Naive | 59 | 59 | 0 |
| Python | RW_drift | 59 | 59 | 0 |

All failed origins and warning messages are preserved in
`phase3b_fit_log_python.csv` and `phase3b_fit_log_r.csv`. No nonconverged
forecast contributes to a loss and no failed fit is silently replaced.

## R/Python comparison

| model | horizon | n_forecasts_R | n_forecasts_Python | n_paired_forecasts | RMSE_R | RMSE_Python | RMSE_relative_difference_pct | MAE_R | MAE_Python | MAE_relative_difference_pct | divergence_warning |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ARIMA111_drift | 5 | 59 | 53 | 53 | 7.84244 | 7.83765 | 0.061087 | 6.0353 | 6.03248 | 0.046818 | True |
| ARIMA111_drift | 10 | 59 | 53 | 53 | 8.78199 | 8.77991 | 0.023771 | 6.49642 | 6.49639 | 0.000343076 | True |
| ARIMA212_drift | 5 | 59 | 54 | 54 | 7.35827 | 7.35071 | 0.102685 | 5.43738 | 5.43358 | 0.0698695 | True |
| ARIMA212_drift | 10 | 59 | 54 | 54 | 8.66004 | 8.67163 | 0.133866 | 6.61311 | 6.61925 | 0.0929054 | True |
| ARIMA313_no_drift | 5 | 59 | 59 | 59 | 7.76447 | 7.7315 | 0.424625 | 5.88357 | 5.82565 | 0.984457 | False |
| ARIMA313_no_drift | 10 | 59 | 59 | 59 | 9.38545 | 9.3167 | 0.732525 | 7.29488 | 7.21512 | 1.09335 | False |
| Naive | 5 | 59 | 59 | 59 | 7.72383 | 7.72383 | 0 | 5.856 | 5.856 | 0 | False |
| Naive | 10 | 59 | 59 | 59 | 9.36924 | 9.36924 | 0 | 7.25316 | 7.25316 | 0 | False |
| RW_drift | 5 | 59 | 59 | 59 | 7.81373 | 7.81373 | 0 | 5.91673 | 5.91673 | 0 | False |
| RW_drift | 10 | 59 | 59 | 59 | 9.10534 | 9.10534 | 0 | 6.76008 | 6.76008 | 0 | False |

Comparison losses use the intersection of usable origins. Absolute and
relative differences (relative to R) are exported. A predeclared >5% RMSE
or MAE difference, differing coverage or absent pairs flags a warning.
Observed maximum paired RMSE difference is 0.7325% and maximum
paired MAE difference is 1.0933%. The warnings for (1,1,1) and
(2,1,2) concern unequal coverage, rather than a >5% paired-loss gap.
Python's apparently lower available-case losses must not be interpreted as
a language advantage: the missing origins change the evaluation sample.
Optimization/initialization and numerical likelihood conventions can explain
differences; no language is adjusted to force equality. Baselines share an
analytic definition. The fit logs preserve warnings and exceptions, including
nonconvergence, rather than replacing failed high-order models.

## Comparison with naive baseline

| language | model | horizon | n_forecasts | RMSE_improvement_vs_naive_pct | MAE_improvement_vs_naive_pct |
| --- | --- | --- | --- | --- | --- |
| Python | ARIMA111_drift | 5 | 53 | -2.26336 | -2.03994 |
| Python | ARIMA111_drift | 10 | 53 | 2.29864 | 7.43454 |
| Python | ARIMA212_drift | 5 | 54 | -1.9388 | -1.79078 |
| Python | ARIMA212_drift | 10 | 54 | 4.19065 | 7.42412 |
| Python | ARIMA313_no_drift | 5 | 59 | -0.099332 | 0.518273 |
| Python | ARIMA313_no_drift | 10 | 59 | 0.56081 | 0.524449 |
| Python | Naive | 5 | 59 | 0 | 0 |
| Python | Naive | 10 | 59 | 0 | 0 |
| Python | RW_drift | 5 | 59 | -1.16387 | -1.03701 |
| Python | RW_drift | 10 | 59 | 2.81662 | 6.79819 |
| R | ARIMA111_drift | 5 | 59 | -1.61056 | -1.33544 |
| R | ARIMA111_drift | 10 | 59 | 3.07319 | 7.2012 |
| R | ARIMA212_drift | 5 | 59 | -1.59122 | -1.40448 |
| R | ARIMA212_drift | 10 | 59 | 3.09125 | 7.22131 |
| R | ARIMA313_no_drift | 5 | 59 | -0.526191 | -0.470818 |
| R | ARIMA313_no_drift | 10 | 59 | -0.172983 | -0.575188 |
| R | Naive | 5 | 59 | 0 | 0 |
| R | Naive | 10 | 59 | 0 | 0 |
| R | RW_drift | 5 | 59 | -1.16387 | -1.03701 |
| R | RW_drift | 10 | 59 | 2.81662 | 6.79819 |

Positive values improve on naive; negative values are worse. These are
descriptive internal gains, not significance tests or final performance.
Rows with incomplete coverage must be interpreted alongside failed_fits.

Cases worse than naive on at least one of RMSE/MAE, using matched origins:

| language | model | horizon | RMSE_improvement_vs_naive_pct | MAE_improvement_vs_naive_pct |
| --- | --- | --- | --- | --- |
| Python | ARIMA111_drift | 5 | -2.26336 | -2.03994 |
| Python | ARIMA212_drift | 5 | -1.9388 | -1.79078 |
| Python | ARIMA313_no_drift | 5 | -0.099332 | 0.518273 |
| Python | RW_drift | 5 | -1.16387 | -1.03701 |
| R | ARIMA111_drift | 5 | -1.61056 | -1.33544 |
| R | ARIMA212_drift | 5 | -1.59122 | -1.40448 |
| R | ARIMA313_no_drift | 5 | -0.526191 | -0.470818 |
| R | ARIMA313_no_drift | 10 | -0.172983 | -0.575188 |
| R | RW_drift | 5 | -1.16387 | -1.03701 |

No challenger improves both main metrics at both horizons in both languages
by the predeclared threshold. In particular, gains at h=10 do not compensate
for worse h=5 losses under the common-horizon rule. There is no clear robust
advantage for a complex ARIMA over naive in this internal comparison.

## Locked ARIMA specification

**locked_arima_specification: Naive, order
(0,1,0), drift=False.**

No challenger satisfies complete convergence and >=1% RMSE AND MAE gain at BOTH horizons in BOTH languages; retain naive. Phase3A random-walk residual autocorrelation remains a limitation.

Rule frozen before results: require all origins usable in both languages,
then at least 1% improvement in BOTH price RMSE and MAE at BOTH horizons in
BOTH languages. Rank qualifying challengers by their worst ratio to naive
over metrics/horizons/languages. Within 1% of the best score, prefer evidence
of Phase 3A mean adequacy in at least one implementation, then fewer
parameters, score and model id. MAPE/log losses are secondary diagnostics.
If no challenger qualifies, lock naive and retain its Phase 3A mean-residual
warning; predictive parsimony does not retroactively validate its residuals.
Phase 3A adequacy is existing full-TRAIN evidence, not a new per-fold test.
Normality/ARCH limitations remain for all candidate interpretations.

Phase 3A note for the lock: Phase3A random walk fails Ljung-Box; benchmark fallback retains this warning.
Status: `locked_arima_specification_baseline_with_diagnostic_warning`. This locks a specification only; no model
is refitted on all TRAIN and it is not a best final model declaration.

## Limitations

59 origins and one predeclared schedule cannot establish robustness to all
origins, regimes or alternate schedules. Candidate identification used full
TRAIN, and validation is used for selection, so final generalization remains
unproven. The 1% thresholds are explicit practical conventions, not tests of
statistical significance. No final Diebold-Mariano test is run. Incomplete
coverage may bias available-case summaries; such candidates cannot lock.
Independent default initializations can yield local optima even when fits
converge. Phase 3A non-normality and conditional heteroskedasticity persist
as limitations; no volatility model is estimated. No bias-corrected price
mean or forecast interval is assessed. The team interpretation template is
intentionally unanswered.

## Phase boundary

Only internal TRAIN forecasts and losses are computed. No holdout observation,
holdout metric, final forecast, full-data refit, GARCH, VAR/VECM, Prophet or
neural model is used. Historical Phase 3A files are unchanged.

Reproduction from the repository root, using the project environment:

```powershell
python python/02b_arima_validation.py
Rscript r/02b_arima_validation.R
python python/02b_arima_validation.py --summarize
python -m ruff check python/02b_arima_validation.py tests/test_arima_validation.py
python -m pytest
```

The summarize command reads language outputs and regenerates common reports,
the lock and six figures without refitting. Language-specific manifests,
origins, forecasts, fit logs, metrics and guards remain auditable under
`outputs/tables/phase3b_*.csv`. Figures are in `outputs/figures/phase3b/`.

- [RMSE h=5](../outputs/figures/phase3b/phase3b_rmse_by_model_h5.png)
- [RMSE h=10](../outputs/figures/phase3b/phase3b_rmse_by_model_h10.png)
- [MAE h=5](../outputs/figures/phase3b/phase3b_mae_by_model_h5.png)
- [MAE h=10](../outputs/figures/phase3b/phase3b_mae_by_model_h10.png)
- [Endpoint errors h=5](../outputs/figures/phase3b/phase3b_forecast_errors_over_time_h5.png)
- [Endpoint errors h=10](../outputs/figures/phase3b/phase3b_forecast_errors_over_time_h10.png)

Stop after Phase 3B review; no subsequent phase is started automatically.
