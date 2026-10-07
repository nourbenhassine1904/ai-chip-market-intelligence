# Phase 5 — Conditional Volatility and GARCH

## Objective

Model NVDA's conditional innovation variance using TRAIN alone, with independent
R and Python implementations. The workflow is mean filtering, prerequisite
diagnostics, symmetric GARCH(1,1) Normal/Student-t fitting, standardized-residual
diagnostics, distribution comparison and a ten-session TRAIN-end variance forecast.
The shared **locked_garch_specification is GARCH(1,1) Normal**. Student-t is a
strong competing fit, but the predeclared cross-language tail criterion does
not pass in R. The higher-order gate is FALSE; no higher-order model is fitted.

**GARCH forecasts volatility/risk, not the direction of the asset price.**

## Why volatility modeling?

Phase 2 supported stationary NVDA percentage log-returns and documented
volatility clustering, squared-return dependence and TRAIN excess kurtosis
**4.698018**. Phase 3A found residual non-normality and highly significant
ARCH-LM results despite acceptable mean-correlation diagnostics. A variance
model therefore addresses a different property from a price forecast model.
No GARCH is fitted to price levels or log-price levels.

The [motivation table](../outputs/tables/phase5_arch_motivation.csv) preserves
actual historical model identifiers, statistics, p-values and source paths.
It links the existing Phase 2 TRAIN squared-return ACF figure and distinguishes
qualitative clustering from a formal test. Phase 5 recomputes only its own
TRAIN squared-return ACF and verifies the historical kurtosis; historical
Phase 2/3A outputs are not regenerated or edited.

## Link with Phase 3A ARCH-LM

Historical evidence is read from `phase3_arima_residual_diagnostics_r.csv` and
`phase3_arima_residual_diagnostics_python.csv`, rather than copied from rounded
human prose. These are **different selected mean models**:

| Historical model | ARCH-LM p, lag 5 | lag 10 | lag 20 | Jarque–Bera statistic |
| --- | ---: | ---: | ---: | ---: |
| R ARIMA(2,1,2), drift | 1.50216868e-12 | 9.44313238e-12 | 1.06283446e-10 | 1704.152267 |
| Python ARIMA(1,1,1), drift | 1.09996401e-13 | 1.02155759e-13 | 2.02697858e-12 | 1776.106839 |

Both Jarque–Bera p-values numerically underflow to zero; this is not literally
zero probability. These results justify studying volatility, but they are not
substituted for the new common-filter prerequisite diagnostics below.

## Data and returns

The only observation input is `data/processed/market_train.csv`, with **1980
rows from 2018-01-02 through 2025-11-14**. The volatility variable is
`NVDA_Log_Return`, in daily percentage points:
`r_t = 100 * (log(P_t) - log(P_(t-1)))`, using adjusted prices.
Only the initial structural missing return is excluded, leaving **1979
returns/innovations, 2018-01-03 through 2025-11-14**. No imputation, scaling to
unit variance, winsorization or subsequent burn is applied.

Both readers verify columns, strictly increasing unique dates, finite positive
adjusted prices and the backward transformations. They reject any other market
path before opening it, including a redirect of the authorized TRAIN path.
Python verifies frozen SHA-256 and MD5; base R independently verifies MD5 and
records the SHA reference without claiming a SHA calculation.

SHA-256: `c3651f95959a49d8d64c791a8d48443dd520b978c3887b8793256dfff76c8f1c`.
MD5: `23b4e319310d569b6f2ebb52c98539e7`.
The [manifest](../outputs/tables/phase5_train_manifest.csv), language manifests,
protocol and implementation fingerprints record provenance. The summarizer
rejects missing, empty or stale language tables. Observation access and reads
of historical statistical summaries are separate operations.

## Mean equation / filtering

Both languages fit the same ARMA(1,1) with an unconditional mean:

```text
r_t - mu = phi * (r_(t-1) - mu) + epsilon_t + theta * epsilon_(t-1)
recursion intercept c = (1 - phi) * mu
```

The return mean mu corresponds to 100 times the drift of an ARIMA(1,1,1)
on log-price. Python uses `ARIMA(order=(1,0,1), trend="c")`; R uses
`stats::arima(order=c(1,0,1), include.mean=TRUE, method="ML")`.
The constant is a mean in the centered ARMA equation, not the raw recursion
intercept; see the [R mean convention](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/arima.html)
and [statsmodels ARIMA specification](https://www.statsmodels.org/stable/generated/statsmodels.tsa.arima.model.ARIMA.html).

| Quantity | R | Python |
| --- | ---: | ---: |
| mu, daily percent | 0.184247 | 0.184272 |
| phi | -0.471646 | -0.471310 |
| theta | 0.389794 | 0.389467 |
| recursion intercept | 0.271146 | 0.271121 |
| Ljung–Box p, lag 10 | 0.067472 | 0.067451 |
| Ljung–Box p, lag 20 | 0.118128 | 0.118106 |

Both fits converge and pass the 5% mean checks, although lag 10 is near the
threshold. Ljung–Box uses `fitdf=2`, giving df=8/18. The rule fixed before
fitting stops before GARCH for nonconvergence or any mean p<0.01, and flags
intermediate 0.01–0.05 evidence. That stop was not triggered here. All dated
innovations are exported with their corresponding returns and no additional
initial-row deletion. Native Kalman initialization and optimizer differences
remain: maximum absolute R/Python innovation difference is **0.026470 pp**.

Phase 3B locked ARIMA(0,1,0) without drift as a **price-prediction baseline**.
That lock remains unchanged. Phase 5 uses the diagnostically acceptable common
ARMA filter to isolate innovations for variance modeling; it does not replace
the Phase 3B predictive lock. The ARMA order was already fitted comparably in
Phase 3A and is not reselected here. This is a two-stage procedure: the mean
parameters are frozen before variance fitting, not jointly estimated by GARCH.

## ARCH-LM before GARCH

R uses `FinTS::ArchTest(demean=FALSE)`; Python uses `het_arch(ddof=0)` on the
same-length raw innovation samples. This is the auxiliary squared-innovation
regression LM convention, documented by [FinTS](https://search.r-project.org/CRAN/refmans/FinTS/html/ArchTest.html).
Python explicitly requests the named result API to avoid a new deprecation
warning in this phase. The test df is the lag; mean-parameter uncertainty is
not subtracted from its sample-size correction.

| Lag | R statistic | R p-value | Python statistic | Python p-value |
| --- | ---: | ---: | ---: | ---: |
| 5 | 69.858288 | 1.096793e-13 | 69.862195 | 1.094742e-13 |
| 10 | 83.521791 | 1.020746e-13 | 83.523550 | 1.019932e-13 |
| 20 | 98.846659 | 2.024842e-12 | 98.848117 | 2.023629e-12 |

The predeclared gate requires at least two rejections at 5% in each language;
all three reject. GARCH fitting is therefore permitted. Insufficient evidence
would stop the pipeline before constructing a variance model. The shared
[pre-GARCH table](../outputs/tables/phase5_arch_lm_pre_garch.csv) keeps all six rows.

## GARCH(1,1) equation

```text
epsilon_t = sigma_t * z_t,  E(z_t)=0, Var(z_t)=1
sigma_t^2 = omega + alpha1 * epsilon_(t-1)^2 + beta1 * sigma_(t-1)^2
```

The input is the first-stage innovations, in percentage points. Omega and
conditional variance have squared-percentage-point units; sigma has daily
percent units. The variance model has zero mean, since the ARMA mean has
already been removed. The common order, zero-mean setting, power=2, absence of
asymmetry, distribution, solver, initialization, warnings, convergence and
parameter counts are recorded in the language model tables.

## Normal specification

Python uses `arch_model(mean="Zero", vol="GARCH", p=1, o=0, q=1, power=2,
dist="normal", rescale=False)` with SLSQP and robust covariance. Native
backcasting uses up to the first 75 innovations with decay 0.94.
R uses `rugarch::ugarchspec(model="sGARCH", garchOrder=c(1,1),
armaOrder=c(0,0), include.mean=FALSE, distribution.model="norm")`, passed to
`ugarchfit(solver="solnp", out.sample=0, scale=0, stationarity=1,
rec.init="all")`. Both fits converge with positive stationary parameters.

## Student-t specification

The only distribution change is Python `dist="t"` and R
`distribution.model="std"`. These use standardized Student-t innovations with
unit variance, requiring nu>2. QQ theoretical quantiles are
`t_ppf(p, nu) * sqrt((nu-2)/nu)`, not unscaled ordinary t quantiles.
No normality requirement is applied to Student-t standardized residuals.
The existing tail and Jarque–Bera evidence motivates this comparison before
seeing fit results. See [arch volatility models](https://arch.readthedocs.io/en/latest/univariate/univariate_volatility_modeling.html)
and the [rugarch fitting/distribution reference](https://alexiosg.r-universe.dev/rugarch/doc/manual.html).

## Model comparison

The [numeric protocol](phase5_protocol.csv) and [selection rule](phase5_selection_rule.md)
were written before Phase 5 fitting. Each language independently estimates
both distributions on 1979 observations. No R estimates initialize Python fits.
R's native IC is per observation; the comparison additionally calculates
**total AIC = -2L+2k and BIC = -2L+k*log(n)**, matching Python's scale.
Here k=3 for Normal and k=4 for Student-t. The frozen first-stage mean
parameters are common to both distributions and excluded from these
conditional second-stage IC; these are not joint ARMA-GARCH likelihood IC.

| Language / distribution | loglik | Total AIC | Total BIC | Tail-quantile RMSE |
| --- | ---: | ---: | ---: | ---: |
| R Normal | -5009.969993 | 10025.939986 | 10042.711027 | 0.151076 |
| R Student-t | -4928.209767 | 9864.419535 | 9886.780922 | 0.155118 |
| Python Normal | -5009.936582 | 10025.873165 | 10042.644206 | 0.149534 |
| Python Student-t | -4928.096952 | 9864.193904 | 9886.555291 | 0.139315 |

Selection first requires convergence, finite quantities, omega>0,
nonnegative alpha/beta and a stationary variance. Residual mean and variance
adequacy precede IC. Among adequate baselines, switching from Normal to
Student-t requires **both** languages to show AIC and BIC gains >=10,
better tail-quantile RMSE and no more diagnostic rejections. The tail score
uses empirical/theoretical z quantiles at .01/.02/.05/.95/.98/.99. It is a
unitless in-sample distribution diagnostic, not a volatility forecast RMSE or
a price forecast score. Each quantile difference is exported for audit.

Student-t gains about 161.5–161.7 AIC and 155.9–156.1 BIC units in both
languages, and both distributions pass the serial/ARCH criteria. However,
the six-quantile score improves only in Python. The independent rule proposals
are therefore **Normal in R and Student-t in Python**. The predeclared
cross-language rule conservatively locks **GARCH(1,1) Normal**. The
[selection checks](../outputs/tables/phase5_distribution_selection_checks.csv)
show the failed condition explicitly; no result or threshold is changed to
force Student-t or to hide the disagreement.

This lock concerns a variance specification. It does **not** validate Gaussian
tails: full QQ plots retain substantial extremes, while Student-t visually
represents more of the tail shape and has much better overall likelihood.
The narrow quantile metric, its sensitivity to initialization and the choice
to require agreement are material limitations of this conservative lock.
Student-t remains a credible alternative. Neither is labeled best final model.

## Omega, alpha and beta

| Language / distribution | omega | alpha1 | beta1 | Student-t nu |
| --- | ---: | ---: | ---: | ---: |
| R Normal | 0.441744 | 0.112580 | 0.851597 | — |
| Python Normal | 0.437129 | 0.111580 | 0.852923 | — |
| R Student-t | 0.306615 | 0.095030 | 0.879255 | 5.755317 |
| Python Student-t | 0.302954 | 0.094033 | 0.880479 | 5.763517 |

Omega is the positive variance intercept. Alpha measures the response to the
previous squared innovation; beta carries previous conditional variance.
These statistical responses do not identify a particular economic news cause.
All four estimates satisfy the positivity and stationarity checks.

## Persistence

For GARCH(1,1), persistence is alpha1+beta1. For 0<persistence<1, the implied
unconditional innovation variance is omega/(1-persistence), and the variance
shock half-life is log(0.5)/log(persistence), in trading sessions.
No finite long-run variance or half-life is reported for persistence>=1.
The scalar AR(1) half-life formula is not reused for higher-order models.

| Language / distribution | Persistence | Unconditional variance, pp² | Half-life, sessions |
| --- | ---: | ---: | ---: |
| R Normal | 0.964177 | 12.331218 | 19.000403 |
| Python Normal | 0.964503 | 12.314664 | 19.178477 |
| R Student-t | 0.974285 | 11.923695 | 26.607156 |
| Python Student-t | 0.974512 | 11.885977 | 26.846639 |

Persistence is high but below 1 for all fits. These are point-estimate
properties under a constant-parameter model, not guarantees of finite-sample
stability, regime invariance or confidence intervals for a long-run variance.

## Standardized residual diagnostics

For each fitted model, `z_t = epsilon_t/sigma_t`. Both implementations export
Ljung–Box tests on z and z² at 10/20 and ARCH-LM on z at 5/10/20. Ljung–Box
uses fitdf=2 for the mean ARMA order and, separately, for the squared-series
GARCH order; these reference chi-square calibrations are approximate after
two-stage estimation. ARCH-LM uses ddof=0/demean=FALSE. Raw p-values are always
retained; Holm adjusts the five variance tests within each model/language.
Mean adequacy uses both raw z Ljung–Box p>=.05; variance adequacy requires all
five Holm p>=.05. The gate does not interpret non-rejection as proof of iid data.

| Model | z LB p10/p20 | z² LB p10/p20 | ARCH-LM p5/p10/p20 |
| --- | --- | --- | --- |
| R Normal | .220408 / .419153 | .904343 / .994389 | .891175 / .966311 / .998017 |
| Python Normal | .222665 / .424654 | .905154 / .994405 | .894106 / .967342 / .998105 |
| R Student-t | .222534 / .433217 | .936740 / .995449 | .943188 / .981251 / .998456 |
| Python Student-t | .225528 / .440192 | .937729 / .995475 | .944801 / .982036 / .998544 |

All raw tests already fail to reject at 5%; Holm variance p-values equal 1
here. Thus there is no detected remaining serial or ARCH dependence at the
tested horizons. ACFs extend to 40 sessions with pointwise bands. Normal QQ
plots use unit Normal quantiles; Student-t QQ plots use its fitted unit-variance
t distribution. No Student-t fit is rejected merely for being non-Normal.
Extreme tail departures remain visible for both distributions.

## Higher-order gate

The [gate](../outputs/tables/phase5_higher_order_gate.csv) is evaluated on the
selected valid GARCH(1,1), not on whichever model yields a desired escalation:
`garch11_arch_remaining=FALSE`,
`squared_residual_dependence_remaining=FALSE`,
**higher_order_justified=FALSE**. No GARCH(2,1), (1,2) or (2,2) is fitted.
The code permits only the first two extensions behind an explicit shared
positive gate and requires improved adequacy plus IC before retaining one.
Mean correlation alone cannot open the variance-order gate.

**asymmetric GARCH extensions were not estimated because they are optional
and require an explicit leverage/asymmetry justification.**
No GJR, EGARCH, DCC or broad model grid is run. Asymmetry could be studied in
a separately justified future analysis; it is not estimated in this phase.

## Conditional volatility

The [conditional-volatility table](../outputs/tables/phase5_conditional_volatility.csv)
contains all 1980 TRAIN dates per language, the original NVDA return, Normal
sigma, Student-t sigma and locked sigma. The first date has no defined return
or sigma and is explicitly retained as structural NA. The remaining 1979 dates
have finite positive sigmas. Locked sigma equals the Normal path here.
The columns are daily percentages; they are not annualized volatility.

The locked sigma ranges from about **1.934% to 9.134% in R** and **1.934% to
9.106% in Python**, with the maximum on **2020-03-17**. Persistent clusters
are visible across TRAIN. The models' paths are close on average; maximum
cross-language differences are larger at initialization. Every historical
sigma uses parameters estimated on full TRAIN, and R's initialization uses
full-TRAIN innovation moments. These are fitted retrospective paths, not
real-time features that could be fed to an earlier forecasting origin without
refitting on its past. No claim of prefix-invariant full-sample estimates is made.

Seven final figures, rendered from the independently exported language results:

- [NVDA returns](../outputs/figures/phase5/phase5_nvda_returns.png)
- [Squared-return ACF](../outputs/figures/phase5/phase5_squared_returns_acf.png)
- [Conditional volatility](../outputs/figures/phase5/phase5_conditional_volatility.png)
- [Standardized residuals](../outputs/figures/phase5/phase5_standardized_residuals.png)
- [Standardized-residual ACF](../outputs/figures/phase5/phase5_standardized_residual_acf.png)
- [Squared-standardized-residual ACF](../outputs/figures/phase5/phase5_squared_standardized_residual_acf.png)
- [Distribution-specific QQ plots](../outputs/figures/phase5/phase5_standardized_residual_qq.png)

## TRAIN-end volatility forecast

Each fitted baseline produces ten analytical innovation-variance forecasts
from **2025-11-14**, the last TRAIN observation. Horizon is an integer count of
future trading sessions; no future dates, observations or realized volatility
are loaded. The recursion uses observed past squared innovations/variances
and replaces future squared innovations by their conditional expectations.
Python checks all ten native forecasts against an independent recursion;
R checks its next-step forecast against the endpoint formula.

| Language / model | h=10 variance, pp² | Daily sigma, % | sqrt(252)-scaled sigma, % |
| --- | ---: | ---: | ---: |
| R Normal, locked | 10.055229 | 3.170998 | 50.338033 |
| Python Normal, locked | 10.038995 | 3.168437 | 50.297382 |
| R Student-t, alternative | 9.501458 | 3.082443 | 48.932272 |
| Python Student-t, alternative | 9.477227 | 3.078510 | 48.869839 |

The [forecast table](../outputs/tables/phase5_volatility_forecast_train_end.csv)
contains h=1–10 for both baseline distributions and languages, with origin,
units and lock flags. `forecast_sigma = sqrt(forecast_variance)`.
The annualized column merely scales a daily sigma by sqrt(252); it is not an
estimated annual-horizon volatility forecast. These forecasts concern epsilon,
not the multi-step return forecast-error variance after propagation through
the ARMA mean. They contain no price-direction prediction and no interval or
parameter-uncertainty coverage claim. No future realization or loss is computed.
See the distinction between residual and process variance in
[arch forecasting](https://arch.readthedocs.io/en/latest/univariate/forecasting.html).

## R vs Python

The [summary](../outputs/tables/phase5_r_python_summary.csv) includes both
models in both languages, their mean parameters, variance coefficients,
persistence, IC, diagnostic rejection counts, native distribution proposals,
shared lock and h=10 forecasts. Matched dates and original return values agree.
All four fits converge and pass the same residual diagnostics. Coefficients
and forecasts are close, but not artificially equated.

Independent native variance initializations differ (Python weighted first-75
backcast versus R full-sample second moment), as do optimizers and small
mean-fit details. These are plausible sources of the observed differences,
not a demonstrated unique decomposition of their causes. Normal sigma paths
differ by about **0.004419 pp on average**, maximum **0.468828 pp**; Student-t
paths differ by **0.005282 pp on average**, maximum **0.479657 pp**.
The locked h=10 sigma differs by only **0.002561 pp**. The disagreement of the
tail score changes the native rule proposal and is explicitly retained.

Runtime versions: Python 3.12.3, arch 8.0.0, statsmodels 0.15.0, numpy 2.5.3,
pandas 3.0.6, scipy 1.18.1; R 4.5.2, rugarch 1.5.6, FinTS 0.4.9.
`arch>=8,<9` is declared in requirements.txt and was installed explicitly into
the project environment. Neither analysis script installs packages. If an R
package is missing, the script stops with an explicit install.packages command.
R uses seed 2026 and a deterministic solnp fit; no random-start grid is used.

## Limitations

The stationary symmetric model may miss regime changes and asymmetric effects.
Gaussian tail adequacy is not established by passing serial/ARCH tests; Student-t
also leaves extremes. A narrow six-quantile diagnostic and a conservative
cross-language condition produce the Normal lock despite a large likelihood
advantage for Student-t. The lock is sensitive to that predeclared policy and
should not be read as evidence that Normal is the true innovation distribution.
No selection threshold is changed after viewing results.

Two-stage fitting ignores first-stage mean-parameter uncertainty in variance
inference and forecasts. Conventional Ljung–Box/ARCH reference distributions
after estimation are approximate, and 5% non-rejection does not prove independence
or constant distribution across regimes. Tail scores and all IC are in-sample;
there is no held-out volatility score. Long-run variance, half-life and h=10
sigma are point estimates without parameter-uncertainty intervals. Full-TRAIN
historical sigmas cannot be used retrospectively as leak-free rolling features.
No volatility RMSE is compared with a price RMSE.

## Phase boundary

The **final holdout remains untouched**. The shared
[holdout guard](../outputs/tables/phase5_holdout_guard.csv) contains **26 PASS
rows**, 13 per language. It distinguishes runtime input/dates/transformation
checks from source-scope assertions about TRAIN arrays and absence of final
evaluation. It is not an operating-system audit of all file operations.
A failed check stops execution. Offline tests additionally trap forbidden
observation reads and verify that a failed mean/ARCH gate prevents GARCH fitting.

The phase produces **36 CSV tables and seven PNG figures**, including language
artifacts, shared comparisons and provenance, rather than 36 fitted models.
There are only four actual variance fits: Normal/Student-t in R/Python.
The 13-question human interpretation template is intentionally unanswered.
Historical Phases 1–4 files/results remain unchanged. No holdout realization,
final RMSE/MAE/MAPE, final Diebold–Mariano, LSTM, GRU, Prophet, DCC, GJR or
EGARCH is used. Only a local commit is made; no push, PR, merge or other phase.

Reproduce from the repository root with the project environment:

```powershell
python python/04_garch.py
Rscript r/04_garch.R
python python/04_garch.py --summarize
python -m ruff check python/04_garch.py tests/test_garch.py
python -m pytest
```

On Windows, set `$env:LC_ALL = 'English_United States.utf8'` before Rscript if
the shell exports an unsupported locale. Missing R packages require explicit
installation in RStudio, for example `install.packages(c("rugarch", "FinTS"))`;
scripts do not install them. No `--higher` command belongs in this closed-gate
reproduction. A separately supported positive gate would require both language
`--higher` runs followed by another `--summarize`, with a maximum of two extensions.

Validation: Python PASS, R PASS, Ruff PASS, **140 pytest tests passed**, including
26 Phase 5 tests. Four existing Phase 3A FutureWarnings remain; Phase 5 has no
fit warnings or automatic package installations. Final technical checks and
the local commit stop at the Phase 5 boundary.
