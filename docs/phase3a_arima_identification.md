# Phase 3A — ARIMA Identification and Residual Diagnostics

## Objective

Identify, estimate and diagnose a univariate NVDA mean model using **TRAIN only**.
R (`forecast`) is the pedagogical reference; Python (`statsmodels`, `pmdarima`)
is the independent replication. All results below were computed locally.
The selected model is a **provisional selected mean model**: predictive
validation has not been performed.

Both languages read `data/processed/market_train.csv`: 1,980 observations,
2018-01-02 through 2025-11-14, in their original trading-session order.
There are 1,979 first differences. No rows are imputed, shuffled, winsorized or
globally dropped. No final holdout observations are read, even for diagnostics.

Input provenance is recorded in `outputs/tables/phase3_train_manifest.csv`:

- Phase 2 TRAIN SHA-256, verified by Python before analysis:
  `c3651f95959a49d8d64c791a8d48443dd520b978c3887b8793256dfff76c8f1c`.
- Independently computed R/Python MD5:
  `23b4e319310d569b6f2ebb52c98539e7` in both readers.
- Row counts, date bounds, sum of log-prices (5977.57240777717) and sum of
  differences (3.65282124420418) also agree to floating-point precision.

## Why NVDA?

NVDA is the project's previously defined main forecasting target (D002).
This phase concerns its univariate conditional mean. AMD and SOXX do not
enter model fitting or order selection here.

## Why log-price?

The final financial target remains NVDA Adjusted Close. The working variable
is `y_t = log(NVDA_Adj_Close_t)`. Its first difference is
`delta_y_t = y_t - y_(t-1) = NVDA_Log_Return_t / 100`.
Both scripts recompute these transformations from positive adjusted prices
and check them against the frozen Phase 2 derived columns.
No back-transformation or price forecast is produced in this phase.

## Why d=1?

The decision is based on complementary Phase 2 TRAIN diagnostics, rather than
automatic order selection:

| Series | ADF p-value | KPSS reported p-value | Combined interpretation |
| --- | ---: | ---: | --- |
| NVDA Log_Price | 0.461103 | 0.01, actual p smaller | Nonstationarity supported |
| NVDA Log_Return | 7.91143e-27 | 0.10, actual p larger | Stationarity supported |

ADF tests a unit-root null; KPSS tests a stationarity null. These results
support one difference of log-price, without proving that the series is
exactly I(1). The original deterministic terms are trend+constant for
log-price and constant for returns.

R `ndiffs()` provides auxiliary checks: KPSS level (forecast default), KPSS
trend, and ADF trend **all return 1**. Thus `final_d=1`, with no disagreement.
`phase3_d_justification_r.csv` records `phase2_conclusion`, `ndiffs_result`,
`final_d`, test specification and agreement; `phase3_d_phase2_evidence.csv`
retains the original statistical evidence, including censored KPSS warnings.
The auxiliary tests do not silently override the Phase 2 conclusion.
See the [forecast ndiffs reference](https://pkg.robjhyndman.com/forecast/reference/ndiffs.html).

## ACF/PACF identification

The inspected Phase 2 figures were the adjusted-price ACF/PACF, log-return
ACF/PACF and robust log-price STL. Phase 3 adds ACF/PACF of log-price itself
and of its first difference, using only TRAIN.

The log-price ACF decays slowly. The differenced series has a small negative
lag-1 correlation; later isolated spikes do not establish a clear cutoff or
a seasonal pattern. Selected values from `phase3_acf_pacf_numeric.csv`:

| Lag, trading sessions | ACF | PACF |
| ---: | ---: | ---: |
| 1 | -0.081476 | -0.081476 |
| 2 | 0.047813 | 0.041449 |
| 5 | 0.014469 | 0.014759 |
| 7 | 0.055862 | 0.051107 |
| 9 | 0.046479 | 0.035657 |
| 10 | -0.025300 | -0.013103 |
| 15 | -0.026976 | -0.020160 |
| 20 | 0.021551 | 0.026894 |

The approximate pointwise 95% reference bound is ±0.044059. It is not a
simultaneous confidence bound across all 20 inspected lags. Python PACF uses
Yule-Walker `ywm`; R's PACF implementation can differ numerically.
The weak low-lag pattern motivates parsimonious AR(1), MA(1) and ARMA(1,1)
alternatives. No extra manual candidates are added from isolated spikes.

## Manual candidates

Exactly five specifications are estimated independently in both languages.
The three AR/MA alternatives include drift, so comparison with the drift
random walk isolates mean dependence. All use `d=1`, `p,q <= 3`.

| Candidate | Drift | k, including variance | R AICc | Python AICc |
| --- | --- | ---: | ---: | ---: |
| ARIMA(0,1,0) | No | 1 | -7946.389747 | -7946.389661 |
| ARIMA(0,1,0) | Yes | 2 | -7950.787082 | -7950.786951 |
| ARIMA(1,1,0) | Yes | 3 | -7961.981485 | -7961.981419 |
| ARIMA(0,1,1) | Yes | 3 | -7960.957470 | -7960.951998 |
| ARIMA(1,1,1) | Yes | 4 | -7963.715534 | -7963.715481 |

All five fits converge in each language. Their CSV tables retain convergence,
parameter count, effective sample size, log-likelihood, AIC, AICc, BIC,
Ljung–Box p-values, warnings and any errors. R uses `forecast::Arima(method="ML")`;
Python uses the state-space likelihood in `statsmodels.ARIMA`, with 1,000
optimizer iterations permitted. `trend="t"` in statsmodels represents drift
in the integrated log-price model. For the manual fits,
`AICc = AIC + 2*k*(k+1)/(1979-k-1)`.
See the [statsmodels ARIMA specification](https://www.statsmodels.org/stable/generated/statsmodels.tsa.arima.model.ARIMA.html).

## auto.arima in R

The transparent exhaustive check is:

```r
forecast::auto.arima(
  y, d=1, seasonal=FALSE, stepwise=FALSE, approximation=FALSE,
  allowdrift=TRUE, max.p=3, max.q=3, max.order=6,
  ic="aicc", method="ML", trace=TRUE, optim.control=list(maxit=1000)
)
```

The explicit bounds align with Python; 16 nonseasonal orders and both drift
policies are considered. `phase3_auto_arima_trace_r.csv` preserves the trace,
including **Inf** criteria for both R ARIMA(3,1,3) attempts. These attempts
were rejected by the search and are not presented as successful fits.

R selects **ARIMA(2,1,2) with drift**, seasonal order `(0,0,0,0)`:
log-likelihood 3993.228998, AIC -7974.457997, AICc -7974.415400,
BIC -7940.915915; six parameters including variance. The estimation converges.
This extends the weak manual identification and is assessed through
parsimony and residual diagnostics rather than accepted solely for its AICc.
See the [forecast auto.arima reference](https://pkg.robjhyndman.com/forecast/reference/auto.arima.html).

## auto_arima in Python

`pmdarima.auto_arima` uses the identical TRAIN log-price vector, `d=1`,
`max_p=max_q=3`, `max_order=6`, `seasonal=False`, `stepwise=False`,
`information_criterion="aicc"`, `maxiter=1000`, and `out_of_sample_size=0`.
Two explicit searches compare `with_intercept=False` and `True`; this avoids
assuming that a non-stepwise intercept default exhausts both policies.
Search traces and captured warnings are saved, with no validation partition.

The converged automatic winner is **ARIMA(3,1,3) without drift**, seasonal
order `(0,0,0,0)`: AIC -7965.754846, AICc -7965.698051, BIC -7926.622418.
The best drift search result is ARIMA(0,1,3). These are automatic proposals,
not additions to the five manual candidates.

Of the 32 returned automatic fits, two no-drift attempts, ARIMA(1,1,0) and
ARIMA(0,1,1), report nonconvergence and are excluded from automatic selection.
Their rows are retained. The Python `warnings` column aggregates warnings
within each drift-policy search; the per-row `converged` field determines
the status of the individual fit, including the successful winner.

The reported pmdarima AICc uses its package sample size, 1,980;
`aicc_package_nobs` makes this explicit. The manual statsmodels/R calculation
uses 1,979 effective observations after differencing. This tiny correction
does not explain the substantial high-order likelihood differences.
An automatic order not already manual is independently refitted with
statsmodels before joining Python's provisional selection pool.
See the [pmdarima auto_arima reference](https://alkaline-ml.com/pmdarima/modules/generated/pmdarima.arima.auto_arima.html).

## SARIMA seasonality gate

**`sarima_justified = FALSE` in both languages. No SARIMA is estimated.**

Evidence in `phase3_seasonality_gate.csv` and the language-specific gates:

- Robust TRAIN STL, period=5: clipped seasonal strength is 0 in both
  recomputations. A plotted seasonal component alone is insufficient evidence.
- Return ACF at lags 5, 10, 15 and 20: 0.014469, -0.025300, -0.026976,
  0.021551. None exceeds the four-lag Bonferroni bound ±0.056146.
- Phase 2 TRAIN weekday return means: Monday 0.211997%, Tuesday 0.255431%,
  Wednesday 0.262920%, Thursday 0.286513%, Friday -0.095332%.
  They are descriptive. An auxiliary TRAIN weekday mean ANOVA has p=0.431880;
  heavy tails and unequal variance limit this test's interpretation.
- R `nsdiffs(ts(y, frequency=5), test="seas")` returns 0; an OCSB check also
  returns 0. These checks concern seasonal differencing, not every possible
  calendar effect. See the [forecast nsdiffs reference](https://pkg.robjhyndman.com/forecast/reference/nsdiffs.html).

The conservative gate requires joint evidence: seasonal strength >0.64,
at least three of four seasonal ACF values beyond the corrected reference,
weekday auxiliary p<0.05, and a positive R seasonal-differencing check.
No single element opens the gate. If strong evidence or cross-language gate
disagreement emerges on another input, scripts stop for documented seasonal
identification before estimation. **Five trading sessions are not five
calendar days**; exchange holidays break literal weekday alignment.

## Provisional model selection

The same deterministic rule is applied independently in each language:

1. Exclude nonconverged or nonfinite fits.
2. Prefer candidates with both Ljung–Box p-values at least 0.05.
3. Within two AICc units of the best eligible fit, prefer fewer parameters,
   then BIC, AICc and a stable model identifier.
4. If no model passes both residual tests, retain a clearly inadequate
   provisional candidate rather than claiming residual adequacy.

Both manual pools prefer ARIMA(1,1,1) with drift. The simpler AR(1) has a
better BIC but fails Ljung–Box at lag 10; MA(1) also fails. Both random walks
leave substantial residual autocorrelation. Identification therefore supports
testing a mixed low-order mean specification without claiming a sharp cutoff.

After including each local automatic proposal:

| Selection | Model | AIC | AICc | BIC |
| --- | --- | ---: | ---: | ---: |
| R reference, primary provisional model | ARIMA(2,1,2), drift | -7974.457997 | -7974.415400 | -7940.915915 |
| Python independent provisional model | ARIMA(1,1,1), drift | -7963.735745 | -7963.715481 | -7941.374357 |

R's ARIMA(2,1,2) improves AICc by about 10.70 over its manual ARMA(1,1)
and passes both residual correlation checks. BIC marginally favors the simpler
ARMA(1,1) among these two (-7941.374409 versus -7940.915915), so the evidence
does not unanimously favor the extra parameters. It remains provisional.

In Python, ARIMA(1,1,1) is 1.98257 AICc units above its automatic ARIMA(3,1,3)
proposal, passes both checks, and uses four parameters instead of seven.
The selection rule therefore retains the simpler model. This decision lies
close to the two-unit rule boundary and should be reviewed during later
TRAIN-only predictive validation. `phase3_arima_selection_comparison.csv`
preserves all manual and valid automatic fits and labels each independent
selection; the R row is marked primary in the shared diagnostic summary.

## Residual diagnostics

Formal tests use 1,979 raw innovations: the first initialization innovation
is removed consistently in both languages. Residuals are not standardized or
variance-filtered. R's `checkresiduals` teaching figure also shows its native
residual convention, including the initial innovation, explaining its tiny
Ljung–Box difference (lag-20 p about 0.7842 versus 0.784385 in the table).

The four requested unsuffixed residual figures show the **primary R
ARIMA(2,1,2)** model. Figures suffixed `_python` show the independent Python
ARIMA(1,1,1); the model identifier is included in every residual plot title.
The two identification figures and R's four-panel ACF/PACF and
`checkresiduals` figures complete the inventory of 12 PNGs.

### Ljung-Box

H0: no overall residual autocorrelation through the specified lag.
Degrees of freedom are `lag-(p+q)`; drift and variance are not subtracted.

| Fit | lag 10 statistic / df / p | lag 20 statistic / df / p |
| --- | --- | --- |
| R ARIMA(2,1,2), drift | 2.488158 / 6 / 0.869791 | 11.396361 / 16 / 0.784385 |
| Python ARIMA(1,1,1), drift | 14.597312 / 8 / 0.067465 | 25.252332 / 18 / 0.118122 |

Both diagnostics are compatible with absence of residual linear
autocorrelation at these horizons. Failure to reject is not proof of
independence. The summary field `white_noise_mean_supported` refers only to
these mean-correlation checks; it does not assert Gaussian iid white noise.

### Normality

H0: residuals are compatible with a normal distribution. Jarque–Bera gives
1704.152267 for the primary R fit and 1776.106839 for Python, each with df=2.
Both implementations report numerical p=0 from underflow, **not a literal
probability of zero**. The diagnostics are not compatible with normality;
the QQ-plots show substantial tail departures.

### ARCH-LM

H0: absence of ARCH effects at the specified lag order.
R uses `FinTS::ArchTest(demean=FALSE)`; Python uses `het_arch(ddof=0)` to
match the raw-innovation `n*R^2` LM convention. These degrees of freedom
settings are explicit; the autoregressive mean fit is not silently used to
change the ARCH-LM sample-size correction.

| Lag | R statistic | R p-value | Python statistic | Python p-value |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 64.386574 | 1.50217e-12 | 69.852262 | 1.09996e-13 |
| 10 | 73.468634 | 9.44313e-12 | 83.520038 | 1.02156e-13 |
| 20 | 89.104025 | 1.06283e-10 | 98.844094 | 2.02698e-12 |

The residual diagnostics support ARCH effects at all three horizons and are
not compatible with a constant conditional variance. Squared-residual ACF
plots reinforce this conclusion. These results are information for a future
volatility phase; **no GARCH is estimated here**.

R residual mean/std are -0.0000223294 / 0.0321768711; Python's are
0.0000071808 / 0.0322976033 (sample std). The shared diagnostic summary records
all p-values and the boolean conclusions separately for each model.
See the [statsmodels ARCH-LM reference](https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.het_arch.html).

## R vs Python comparison

The independent automatic orders differ: R `(2,1,2)` with drift, Python
`(3,1,3)` without drift. Independent provisional selections also differ:
R `(2,1,2)` with drift, Python `(1,1,1)` with drift. This divergence is retained
in the outputs and is not treated as an input-data discrepancy.

The matched manual ARIMA(1,1,1) specification demonstrates close estimation:

| Coefficient | R | Python |
| --- | ---: | ---: |
| AR(1) | -0.47041736 | -0.47198453 |
| MA(1) | 0.38851955 | 0.39015882 |
| Drift, log-price/session | 0.0018439071 | 0.0018381295 |

R's selected ARIMA(2,1,2) coefficients are AR1=-1.69986396,
AR2=-0.86857737, MA1=1.63746830, MA2=0.81072310,
drift=0.0018661929. Its AR and MA root moduli are respectively about 1.073
and 1.111, outside the unit circle; relatively close AR/MA behavior makes
optimizer sensitivity relevant. This is not evidence of weekly seasonality.

A reproducible supplementary check (`--compare-r`) fits this same R-selected
order in Python using two initializations:

| Python initialization, same (2,1,2)+drift | Log-likelihood | AICc |
| --- | ---: | ---: |
| Independent default start | 3985.905488 | -7959.768380 |
| Start from saved R coefficients | 3993.229479 | -7974.416362 |

The R-initialized Python result almost matches R's likelihood and diagnostics
(Ljung–Box p=0.869850 / 0.784482; ARCH p-values approximately
1.52742e-12 / 9.54435e-12 / 1.07450e-10). This supports initialization/local
optima as a concrete explanation for much of the divergence. It does not
prove that either fit is a global maximum. **This second fit depends on R;
it is a sensitivity analysis, not independent replication, and it never
changes the independent selection tables.** All three sensitivity tables
retain their initialization labels.

Other implementation differences include R's ML optimizer and initialization
versus statsmodels' state-space L-BFGS estimation, R's search rejection checks,
drift parameterization and AICc sample-size convention. In pmdarima/SARIMAX,
the differenced-equation intercept corresponds to `drift*(1-sum(AR))`;
statsmodels ARIMA's `x1` trend slope is comparable to R's drift. These are
not interchangeable coefficient names. Standard errors also differ because
the default covariance estimators differ. R reports a degrees-of-freedom
adjusted innovation variance; it should not be equated blindly with Python's
MLE `sigma2` parameter. These conventions are detailed in the
[statsmodels ARIMA/SARIMAX FAQ](https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_sarimax_faq.html)
and the [forecast implementation](https://github.com/robjhyndman/forecast/blob/master/R/arima.R).

Despite different independent orders, both selected fits support the same
qualitative residual conclusions: no detected linear autocorrelation at
lags 10/20, rejection of normality, and ARCH effects at lags 5/10/20.

## Limitations

- TRAIN diagnostics and information criteria are not evidence of predictive
  superiority. Neither independent model has been validated predictively.
- Higher-order likelihoods are sensitive to initialization; R rejects its
  two `(3,1,3)` attempts. No rejected attempt or divergence is hidden.
- R's extra parameters improve AICc and whiten mean residuals but do not
  improve BIC over the adequate manual ARMA(1,1). Python's two-unit decision
  is close to the threshold. Both are provisional choices for review.
- Non-normality and conditional heteroskedasticity limit Gaussian likelihood
  assumptions, conventional standard errors and future Gaussian intervals.
- Residual tests are asymptotic and conducted after model search; their
  non-rejections are limited diagnostic evidence, not proof of independence.
- STL is a two-sided TRAIN diagnostic, never a causal forecasting feature.
  R/Python STL smoother details and PACF estimators can differ.
- The installed statsmodels 0.15.0 emits an ARCH-LM result API FutureWarning;
  it is preserved in candidate/sensitivity warning columns. R emits the
  `quantmod` S3 registration notice. Neither prevents successful execution.
- Windows exported `C.UTF-8` initially caused locale warnings and a failed
  FinTS installation on the accented repository path. A valid Windows UTF-8
  locale resolved it. Both missing dependencies were explicitly installed
  with approval, never by the analysis scripts. FinTS resides in the ignored
  `.cache/R-library`; pmdarima is declared in `requirements.txt`.

## Phase boundary

Produced **12 PNG figures and 34 CSV tables**. No VAR, VECM, GARCH, LSTM, GRU
or Prophet files are changed. No final forecast, RMSE/MAE/MAPE, Diebold–Mariano
test, back-transformation or final holdout evaluation is computed.
The team's human interpretation file remains an unfilled template.

`phase3_holdout_guard.csv` has **14 PASS checks**, including fit, order
selection, residual diagnostics and seasonality in each language, explicit
read allowlists, frozen TRAIN integrity and byte-identical cross-language
input. The guard combines runtime input validation with a code audit.
Offline synthetic tests add a holdout-read trap and verify its modification
time/size remain unchanged; no real holdout content is used by these checks.

Reproduce from the repository root after activating `.venv`:

```powershell
python python/02_arima.py
python -m ruff check python/02_arima.py tests/test_arima.py
python -m pytest
$env:LC_ALL = 'English_United States.utf8'  # Windows shell exporting invalid C.UTF-8
Rscript r/02_arima.R
python python/02_arima.py --compare-r     # explicitly dependent sensitivity check
python python/02_arima.py --summarize     # refresh shared tables; no refitting
```

On Unix omit the Windows locale line. Without activation, use
`.\.venv\Scripts\python.exe` on Windows. Missing Python packages require the
explicit command `python -m pip install -r requirements.txt -r requirements-dev.txt`.
The R script prints package versions and stops with the exact installation
command if `forecast`, `tseries` or `FinTS` is missing; it installs nothing.

Validation completed successfully: Python pipeline exit 0, Ruff PASS,
**75 pytest tests passed** (20 Phase 3A tests; four ARCH API FutureWarnings),
R pipeline exit 0, and all 14 holdout guard checks PASS. Figures were visually
inspected for readable titles, axes and diagnostic content.

Recorded runtime: Python 3.12.3, numpy 2.5.3, pandas 3.0.6, scipy 1.18.1,
statsmodels 0.15.0, pmdarima 2.1.1, matplotlib 3.11.2; R 4.5.2,
forecast 9.0.2, tseries 0.10.63, FinTS 0.4.9.

Stop after Phase 3A diagnostics for team review. No later phase is started.
