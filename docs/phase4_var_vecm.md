# Phase 4 — VAR, Granger, Cointegration and Conditional VECM

## Objective

Study the dynamic interdependence of NVDA, AMD and SOXX using TRAIN alone.
Python and R independently estimate the same return VAR and test cointegration
in log-prices. Both retain VAR(9), both select Johansen rank 0, and no VECM is
estimated. These are within-TRAIN statistical findings, not final forecasting
performance or economic identification. correlation is not causality.

## Data and variables

The sole observation input is `data/processed/market_train.csv`: **1980 rows,
2018-01-02 through 2025-11-14**. Asset order is NVDA, AMD, SOXX throughout.
VAR uses `NVDA_Log_Return`, `AMD_Log_Return`, `SOXX_Log_Return`, in percent.
Only the structural first return row is excluded, leaving **1979 rows**;
there is no imputation or global deletion. Johansen uses all 1980 observations
of `NVDA_Log_Price`, `AMD_Log_Price`, `SOXX_Log_Price`.

Both scripts check required columns, unique increasing dates, positive adjusted
prices, log-price = log(adjusted price) and return = 100 times the backward
first difference. The closed observation reader rejects every path except TRAIN
before opening it and rejects redirected paths. No holdout observation is read,
including for descriptive plots. The final date is checked against the frozen
protocol rather than inspecting any other market dataset.

Frozen TRAIN SHA-256:
`c3651f95959a49d8d64c791a8d48443dd520b978c3887b8793256dfff76c8f1c`.
Measured MD5 in both languages: `23b4e319310d569b6f2ebb52c98539e7`.
Python verifies both digests; base R independently verifies MD5 and records
the SHA-256 **reference**, leaving its SHA verification field empty. The shared
[manifest](../outputs/tables/phase4_train_manifest.csv) records this distinction,
rows, dates, columns and the observation-read audit. Every language table records
TRAIN MD5, protocol MD5, implementation MD5, language and analysis scope. The
summarizer rejects stale implementations or mismatched provenance.

## Why returns for VAR?

[Phase 2](phase2_eda_stationarity.md) supported nonstationary log-prices and
stationary log-returns for all three assets using complementary ADF/KPSS evidence.
This phase reuses that evidence without rerunning Phase 2. The VAR models the
stationary return vector with an unrestricted intercept; no standard stationary
VAR is fitted directly to the log-price levels.

## VAR lag selection

The [protocol](phase4_protocol.csv) fixes lags 1–10, diagnostics at 20 and 30,
the 5% threshold and a two-unit total-BIC tie tolerance. The decision rule was
specified before computing Phase 4 results:

1. Require estimable finite coefficients and companion roots strictly inside
   the unit circle.
2. Require adjusted multivariate Portmanteau p-values >= 0.05 at **both 20 and
   30 sessions**. These horizons exceed every lag in the grid.
3. Within two **total** BIC units of the lowest BIC among eligible models,
   prefer the smallest lag, then BIC, HQIC and AIC. Total-BIC differences are
   `common_nobs * (BIC - best_BIC)`; the per-observation BIC tolerance is not 2.
4. If no stable candidate passes serial diagnostics, retain a provisional
   stable fit by the same IC/parsimony rule and withhold IRF/FEVD. This fallback
   was not needed here. The grid is not expanded to obtain a preferred result.

IC values use the **same 1969 response rows** at all orders. R uses
`vars::VARselect(type="const", lag.max=10)`; Python fits each order to an
appropriately trimmed predictor history so that responses start at lag 10.
After selection, estimation and diagnostics use every available TRAIN response
at that order. This follows the common-sample design documented by
[VARselect](https://search.r-project.org/CRAN/refmans/vars/html/VARselect.html).

| Finding | R | Python |
| --- | ---: | ---: |
| AIC proposal | 1 | 1 |
| BIC proposal | 1 | 1 |
| HQIC proposal | 1 | 1 |
| FPE proposal | 1 | 1 |
| Selected lag | **9** | **9** |
| VAR(1) serial p at 20 | 0.000210344 | 0.000210344 |
| VAR(1) serial p at 30 | 0.00137798 | 0.00137798 |
| VAR(8) serial p at 20 | 0.0357346 | 0.0357346 |
| VAR(9) serial p at 20 | 0.0587904 | 0.0587904 |
| VAR(9) serial p at 30 | 0.156800 | 0.156800 |

AIC and BIC do **not** disagree in this run. Their lag-1 proposal is superseded
by residual diagnostics: only orders 9 and 10 pass both serial checks. Order 9
has lower BIC and fewer parameters. Lag 9 is an adequacy-driven choice, not a
claim of superior out-of-sample forecasts. Selection on diagnostics makes
subsequent p-values exploratory and conditional on the chosen model.

Full values and eligibility flags are in the language lag-selection CSVs and
[comparison](../outputs/tables/phase4_var_lag_selection_comparison.csv).

## VAR estimation

Python uses `statsmodels.tsa.api.VAR(...).fit(9, trend="c")`; R uses
`vars::VAR(..., p=9, type="const")`. Each equation has an intercept and 27 lagged
regressors, with **1970 estimation responses**, 28 coefficients per equation,
84 mean coefficients in the system and 1942 residual degrees of freedom per
equation. Return units are percentage points per observed trading session.
Coefficients, standard errors and dated residuals are exported separately by
language. R uses only `vars` and `urca`; it installs nothing and stops with an
explicit `install.packages(...)` command if either is unavailable.

## VAR stability

All 27 companion eigenvalue moduli are below 1; the maximum is **0.840222610**
in both languages. R's `vars::roots` returns companion eigenvalues. Python's
`VARResults.roots` uses inverse characteristic roots, whose moduli must exceed
1. Python explicitly constructs the companion matrix to avoid confusing these
conventions. [Stability output](../outputs/tables/phase4_var_stability.csv)
contains real/imaginary components, companion moduli and reciprocal moduli.

## Residual diagnostics

The adjusted multivariate Portmanteau statistic uses residual covariance
matrices and the finite-sample adjustment, with degrees of freedom
`3^2 * (h - p)` for this unrestricted VAR. Its implementation is documented in
[vars serial.test](https://search.r-project.org/CRAN/refmans/vars/html/serial.html).

| Horizon | Adjusted statistic | df | p-value | Decision at 5% |
| --- | ---: | ---: | ---: | --- |
| 5 | — | — | — | Not applicable: h <= p |
| 10 | 10.796512 | 9 | 0.289915 | Fail to reject serial-null |
| 20 | 121.930652 | 99 | 0.058790 | Fail to reject serial-null |
| 30 | 208.567877 | 189 | 0.156800 | Fail to reject serial-null |

R/Python statistics agree numerically. Non-rejection is not proof of white
innovations, and the 20-session result is close to the decision threshold.
The multivariate Jarque–Bera statistic is **7513.503375**, df = 6, in both
languages. The numerical p-value underflows to 0; report it as **p < 1e-300**,
not an exactly zero probability. Normality is strongly rejected. Normality is
not an absolute validity gate for mean dynamics, but conventional Wald inference
and IRF bands retain distributional and variance-assumption limitations.

Residual time plots and equation ACFs show all three equations. ACF bands are
pointwise, not simultaneous, and do not replace the multivariate serial test.
Historical Phase 3A evidence of conditional heteroskedasticity is a limitation;
no new volatility model or ARCH/GARCH phase is run here.

## Granger causality

Granger causality is predictive precedence, not structural causality.
Each test restricts all nine lags of one predictor in **one target equation**,
conditional on all three variables' lagged histories. Python uses equation
Wald chi-square tests. R constructs the same Wald statistic from the target
equation coefficients and covariance matrix. `vars::causality(cause=X)` would
pool restrictions across the other equations and is therefore not used as a
substitute for these six directed tests. Each chi-square test has df = 9.

| Predictor → target | Wald statistic | Raw p | Holm p, six tests | Raw/Holm 5% |
| --- | ---: | ---: | ---: | --- |
| NVDA → AMD | 8.714396 | 0.464045 | 1.000000 | Not supported |
| NVDA → SOXX | 8.709752 | 0.464486 | 1.000000 | Not supported |
| AMD → NVDA | 11.679885 | 0.231963 | 0.927853 | Not supported |
| AMD → SOXX | 6.028780 | 0.737034 | 1.000000 | Not supported |
| SOXX → NVDA | 34.758922 | 0.000065708 | 0.000394246 | Supported |
| SOXX → AMD | 21.910572 | 0.00916676 | 0.0458338 | Supported |

R and Python agree on all six decisions and statistics to numerical precision.
Thus SOXX's past returns contain incremental predictive information for NVDA
and AMD in this fitted system. AMD → NVDA is not statistically supported.
Failure to reject does not establish absence of predictability. These are
conventional homoskedastic Wald tests, conditional on the selected lag; Holm
addresses six-test multiplicity but not lag selection, breaks or volatility.

## Why log-prices for cointegration?

Cointegration concerns stationary combinations of individually nonstationary
levels. Differencing first would remove the potential long-run relation being
tested. Johansen therefore receives the three log adjusted prices, not returns.
Phase 2's I(1) evidence motivates this specification without proving it for every
subperiod or deterministic assumption.

## Johansen cointegration

The primary specification fixes **K = 3 level lags**, hence **k_ar_diff = 2**,
before observing Johansen results. This is a modest short-run baseline distinct
from the subsequent return-VAR selection; it does not claim to inherit VAR(9)'s
serial adequacy. Predeclared nearby sensitivities K = 2 and 4 are also exported.
Neither the lag nor deterministic term is searched to obtain a positive rank.
The shorter Johansen lag structure and its limited sensitivity range remain
important limitations; larger-lag or alternate-deterministic analyses could
change rank evidence. The reported rank is conditional on these specifications.

R uses `urca::ca.jo(type="trace", ecdet="none", K=3, spec="transitory")`:
there is no intercept inside beta, and an unrestricted constant enters the
differenced equations. It allows drift in levels without an explicit linear
trend regressor in the short-run system. `spec="transitory"` puts lagged levels
at t−1; the long-run parameterization has the same cointegration eigenvalues.
[urca documentation](https://search.r-project.org/CRAN/refmans/urca/html/ca.jo.html)
distinguishes K in levels and the placement of deterministic terms.

Python uses `coint_johansen(det_order=0, k_ar_diff=2)`:
the implementation demeans levels and lagged differences before residualization.
Its level residualization uses the long-run lag representation. The matched
effective sample is **1977** observations and the trace statistics agree with R
within 1e-10. The [statsmodels API](https://www.statsmodels.org/stable/generated/statsmodels.tsa.vector_ar.vecm.coint_johansen.html)
defines `k_ar_diff` as the number of lagged differences, not level lags.

The native critical tables are **not interchangeable**. R reports its
Osterwald–Lenum table for `ecdet="none"`; Python reports its native
`c_sjt(3-r, 0)` table. Keeping both tables avoids asserting that the API term
"constant" automatically implies identical tabulated critical distributions.
No critical values are overwritten to force rank agreement.

| Null rank | R trace | Python trace | R 5% critical | Python 5% critical | Both decisions |
| --- | ---: | ---: | ---: | ---: | --- |
| r = 0 | 21.570119 | 21.570119 | 31.52 | 29.7961 | Fail to reject |
| r <= 1 | 9.857303 | 9.857303 | 17.95 | 15.4943 | Fail to reject |
| r <= 2 | 0.001677 | 0.001677 | 8.18 | 3.8415 | Fail to reject |

Rank is selected **sequentially**, stopping at the first non-rejection, rather
than counting all individually rejected hypotheses. Main rank: **R = 0,
Python = 0, shared rank = 0**. Sensitivities K=2 and K=4 also return rank 0
in both languages. The tables additionally contain 10% and 1% critical values.
This is a lack of supported cointegration in the tested specifications, not
proof that no long-run relation exists.

Python's installed eigensolver returns complex dtype with **zero imaginary
component** for these calculations, generating a statsmodels `ComplexWarning`
during assignment to real trace arrays. The warning is captured in the output,
eigenvalue bounds and imaginary components are checked, and agreement with R
independently confirms the real trace statistics. No substantive imaginary
component is silently accepted.

## VECM decision

VECM is estimated only if cointegration is supported.
The shared gate requires both native procedures to agree on rank 1 or 2;
disagreement withholds estimation pending specification review. Rank 3 requires
reconsidering the I(1) model, not fitting a standard reduced-rank VECM.

Here **cointegration_rank = 0; vecm_justified = FALSE**:
**no cointegration supported; VECM not justified**.
Only the [decision](../outputs/tables/phase4_vecm_decision.csv) is created.
There are no alpha, beta, VECM diagnostics or fabricated VECM figures.

The conditional code remains available behind `--vecm`, which checks the shared
decision before construction. If justified in a different authorized analysis,
Python's `VECM(..., k_ar_diff=2, coint_rank=r, deterministic="co")` and R's
`cajorls(ca.jo(..., ecdet="none"), r=r)` place the constant outside beta.
Beta represents normalized candidate long-run equilibrium relations; alpha
represents directions and speeds of adjustment. Neither has a numerical result
or economic interpretation in this rank-zero run. Native VECM diagnostics would
retain their exported degrees of freedom rather than forcing p-values to match.

## IRF

The selected VAR passes the stability and predeclared serial adequacy gates,
so nine orthogonalized impulse responses are computed through **20 sessions**.
These gates establish adequacy under the checked mean-dynamics criteria, not
proof of a fully correct model. Identification is recursive Cholesky, in the
fixed order **NVDA, AMD, SOXX**, with a one-standard-deviation orthogonalized
innovation. Responses are percentage points of daily log-return, not price
levels or cumulative returns. Ordering affects the contemporaneous allocation;
AMD/SOXX → NVDA responses at horizon 0 are zero by construction.

In the estimated VAR, an AMD innovation is associated with a next-session NVDA
response of **−0.06351 pp**, Python pointwise 95% interval
**[−0.20656, 0.07955]**. A SOXX innovation is associated with **−0.26486 pp**,
interval **[−0.40738, −0.12233]**. Responses then oscillate and decay;
at session 20 they are approximately −0.00345 and −0.00735 pp respectively,
with both intervals including zero. These are model responses to identified
innovations, not claims of economic causation. Individual interval exclusions
do not constitute simultaneous significance across shocks and horizons.

The figure shows Python asymptotic normal 95% pointwise bands. R independently
exports point responses and percentile residual-bootstrap bands (500 draws,
seed 2026). Point estimates agree within 6e-15; intervals need not agree because
their methods differ. Neither method is designed here to be robust to changing
conditional volatility; no coverage guarantee is claimed.

## FEVD

Twenty-session FEVD is computed from the same identified stable return VAR.
Rows below are response equations; columns are innovation components, in
percent. Each response/horizon sums to 100 in both implementations.

| Response at h=20 | NVDA innovation | AMD innovation | SOXX innovation |
| --- | ---: | ---: | ---: |
| NVDA | 97.516794 | 0.591106 | 1.892100 |
| AMD | 45.962985 | 52.807569 | 1.229445 |
| SOXX | 65.574576 | 6.724582 | 27.700842 |

For NVDA, most forecast-error variance is allocated to the first recursive
innovation. This is an ordering-dependent decomposition of model uncertainty,
not structural causality or an evaluated forecast error on future observations.
The large allocation of NVDA innovations to the other equations partly reflects
NVDA's first position in the recursive ordering and correlated contemporaneous
returns. R/Python shares agree within 2e-13 percentage points.

## R vs Python comparison

The [shared summary](../outputs/tables/phase4_r_python_summary.csv) reports all
IC proposals, selected lag, stability, main serial p-values, normality,
Granger conclusions, Johansen ranks, VECM and IRF/FEVD gates. Independent fits
agree on every primary decision. Maximum common-sample IC differences are below
2e-14 for AIC/BIC/HQIC and 2e-12 for FPE; Granger statistic differences are below
2e-13. Johansen trace differences are below 4e-11. Native critical values and
IRF interval methods differ explicitly as described above; they are not forced
to match.

Runtime: Python 3.12.3, numpy 2.5.3, pandas 3.0.6, scipy 1.18.1,
statsmodels 0.15.0; R 4.5.2, vars 1.6.1, urca 1.3.4. Version tables are exported.
R's bootstrap uses an explicit seed; Python's asymptotic IRF calculation is
deterministic. Reproduction requires these environments and the frozen local
TRAIN file, which remains ignored by Git.

There are **40 CSV tables** under `outputs/tables/phase4_*.csv` and **six PNGs**.
The table count includes separate language artifacts and shared comparisons,
not 40 distinct models. Six combined diagnostic/provenance/decision tables,
three comparison tables, two combined dynamics tables and language tables keep
both implementations auditable; the human interpretation template remains blank.

The six figures, all rendered by Python from TRAIN, are:

- [Multivariate returns](../outputs/figures/phase4/phase4_returns_multivariate.png)
- [VAR residuals](../outputs/figures/phase4/phase4_var_residuals.png)
- [Residual ACF](../outputs/figures/phase4/phase4_var_residual_acf.png)
- [IRF with pointwise intervals](../outputs/figures/phase4/phase4_var_irf.png)
- [FEVD](../outputs/figures/phase4/phase4_var_fevd.png)
- [Log-prices for cointegration](../outputs/figures/phase4/phase4_cointegration_log_prices.png)

## Limitations

Residual non-normality, conditional heteroskedasticity, possible breaks and
omitted market variables limit conventional inference. The 20-session serial
p-value is borderline and diagnostics were also used for lag selection; do not
interpret subsequent p-values as confirmatory post-selection inference.
Stationarity evidence from Phase 2 does not rule out regime changes.
Johansen deterministic terms, finite-sample power, native critical tables and
the deliberately short K=3 baseline matter; rank 0 is specification-dependent.
Nearby K=2/4 checks do not establish adequacy of all short-run specifications.
Cholesky ordering and SOXX's sector exposure limit interpretation of identified
innovations. Bootstrap/asymptotic bands are pointwise and do not correct for
all selection, multiplicity or volatility effects. There is no final predictive
ranking or economic causal identification.

## Phase boundary

The **final holdout remains untouched**.
The shared [holdout guard](../outputs/tables/phase4_holdout_guard.csv) contains
**24 PASS rows**, 12 per language. It distinguishes measured runtime checks
(input audit, chronology, digest, transformations) from source-scope assertions
(model stages receive TRAIN arrays and no final evaluation exists). It is not
an operating-system audit of every file access. A failed guard stops execution.
Offline tests additionally trap unauthorized observation reads before opening.

Historical Phase 1–3B outputs, scripts and documentation are preserved.
No ARIMA revalidation, final RMSE/MAE/MAPE, final Diebold–Mariano, GARCH,
Prophet, LSTM or GRU is run. No holdout forecast is generated. Human analysis
questions are left unanswered. Only a local commit is authorized; no push,
pull request, merge or subsequent phase is performed.

Reproduce from repository root with the project Python environment and R:

```powershell
python python/03_var_vecm.py
Rscript r/03_var_vecm.R
python python/03_var_vecm.py --summarize
python -m ruff check python/03_var_vecm.py tests/test_var_vecm.py
python -m pytest
```

For Windows R, use a valid locale such as
`$env:LC_ALL = 'English_United States.utf8'` before launching Rscript.
The `--vecm` option is deliberately omitted from this rank-zero reproduction.
If a future authorized run supports a shared positive reduced rank, both
language `--vecm` runs and another `--summarize` are required to create shared
alpha/beta/diagnostic tables.

Technical validation for this run: Python pipeline PASS; R pipeline PASS;
Ruff PASS; full pytest **114 passed**, including 25 Phase 4 tests, with four
existing Phase 3A `FutureWarning` messages. Numerical Johansen warnings are
captured separately in the language output as explained above.
