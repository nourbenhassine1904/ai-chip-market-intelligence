# Phase 2 — EDA, Financial Transformations and Stationarity

## Objective

Create financial transformations, freeze a chronological final holdout and produce exploratory diagnostics. No forecasting model is estimated. This document records calculations; the team's human interpretation remains pending in `llm/human_analysis/phase2_interpretation.md`.

## Input dataset

`data/processed/market_aligned.csv`: 2200 observations and 19 original columns. SHA-256 verified against Phase 1.5 **before analysis**: `e4f69e14cb46c797c6eb383c0f60ecc8b5d6a918ccd248288696f08557473b04`. Original values and row order are preserved; the feature dataset has 34 columns.

| file_name | rows | columns | first_date | last_date | sha256 | derived_variable_count | source_sha256 | train_sha256 | test_sha256 | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| market_features.csv | 2200 | 34 | 2018-01-02 | 2026-10-02 | d64fe085b919bf20c4bf0fc372235cb4f42a2b45d6815883573ec0746aeff00a | 15 | e4f69e14cb46c797c6eb383c0f60ecc8b5d6a918ccd248288696f08557473b04 | c3651f95959a49d8d64c791a8d48443dd520b978c3887b8793256dfff76c8f1c | 124ebdff5b37de4459fcd9738e8d8ad968b3f945b66b647310f741640fa55fe4 | Canonical values retained; structural NA preserved; trailing windows; no model fit |

## Chronological split

Split computed first from canonical dates: `floor(0.90*N)` train, remaining rows test. No structural NA is removed before splitting. The first test return uses the last training price, a legitimate past observation. Holdout values are used only in explicitly descriptive full-period charts/statistics.

| total_rows | train_rows | test_rows | train_ratio | test_ratio | train_start | train_end | test_start | test_end | split_method |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2200 | 1980 | 220 | 0.9 | 0.1 | 2018-01-02 | 2025-11-14 | 2025-11-17 | 2026-10-02 | chronological_90_10_holdout |

## Financial transformations

For each asset, P is Adjusted Close and V is volume. `Log_Price = ln(P_t)`; `Log_Return = 100*(ln(P_t)-ln(P_{t-1}))`; `Return_Pct = 100*(P_t/P_{t-1}-1)`; `Volume_Change_Pct = 100*(V_t/V_{t-1}-1)`. `Rolling_Vol_20D = 100*sqrt(252)*sample_std(Log_Return/100 over sessions t-19..t)` with ddof=1 and 20 valid observations. Windows include the current observation and use no future value. Log-return, percentage return and volume change each have one initial NA; volatility has 20 initial NAs because the first return is undefined. No imputation or global deletion occurs. Historical volatility is descriptive, not automatically a forecasting feature.

| ticker | Log_Price | Log_Return | Return_Pct | Volume_Change_Pct | Rolling_Vol_20D |
| --- | --- | --- | --- | --- | --- |
| NVDA | 0 | 1 | 1 | 1 | 20 |
| AMD | 0 | 1 | 1 | 1 | 20 |
| SOXX | 0 | 1 | 1 | 1 | 20 |

## Price dynamics

Adjusted-price and Base 100 figures cover the full descriptive period and mark the final holdout. Base 100 uses only the first observed price, not fitted normalization. Trading volumes are shown in millions of shares. Model conclusions must use TRAIN diagnostics.

## Return dynamics

Daily log-return and squared-return plots are descriptive full-period charts with the test boundary. Squared returns visualize variance concentration only. Histograms, boxplots, normal QQ-plots and historical volatility are saved; distribution diagnostics use TRAIN. No normality or ARCH test is performed.

## Descriptive statistics

Sample variance/std use ddof=1. Skewness is pandas' unbiased sample skewness; kurtosis is unbiased **excess** kurtosis (normal reference 0). Full-period rows are labeled `full_descriptive` in the CSV and must not guide model selection. Counts exclude only each series' own NA.

| ticker | series | scope | count | mean | median | variance | standard_deviation | minimum | Q1 | Q3 | maximum | skewness | kurtosis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NVDA | Adj_Close | train | 1980 | 42.1823 | 16.9938 | 2656.34 | 51.5397 | 3.14321 | 6.37697 | 47.9781 | 206.545 | 1.45512 | 0.802925 |
| NVDA | Log_Return | train | 1979 | 0.184579 | 0.283475 | 10.5209 | 3.2436 | -20.7711 | -1.52095 | 1.97056 | 21.8088 | -0.192489 | 4.69802 |
| AMD | Adj_Close | train | 1980 | 87.7311 | 86.99 | 2634.86 | 51.3309 | 9.53 | 41.255 | 118.78 | 264.33 | 0.423479 | -0.17253 |
| AMD | Log_Return | train | 1979 | 0.157279 | 0.0593746 | 11.9084 | 3.45086 | -16.7772 | -1.68381 | 2.03534 | 21.3663 | 0.250518 | 3.57136 |
| SOXX | Adj_Close | train | 1980 | 133.9 | 133.152 | 4022.1 | 63.42 | 45.085 | 72.0472 | 172.086 | 308.608 | 0.436253 | -0.75648 |
| SOXX | Log_Return | train | 1979 | 0.0849012 | 0.125843 | 4.92462 | 2.21915 | -16.5202 | -1.05681 | 1.34088 | 17.0347 | -0.208953 | 5.12609 |

## Correlation structure

Pearson correlations of contemporaneous TRAIN log-returns; correlation does not establish causality.

| ticker | NVDA | AMD | SOXX |
| --- | --- | --- | --- |
| NVDA | 1 | 0.684939 | 0.819116 |
| AMD | 0.684939 | 1 | 0.744839 |
| SOXX | 0.819116 | 0.744839 | 1 |

## Rolling correlations

TRAIN only; trailing 60 observed trading-session windows, minimum 60 valid paired returns, no centered windows. Summary std uses ddof=1. Descriptive analysis only; no DCC-GARCH.

| pair | scope | mean | median | min | max | std |
| --- | --- | --- | --- | --- | --- | --- |
| NVDA/AMD | train | 0.669317 | 0.659535 | 0.153628 | 0.93615 | 0.158178 |
| NVDA/SOXX | train | 0.795832 | 0.8002 | 0.50562 | 0.956457 | 0.10034 |
| AMD/SOXX | train | 0.73839 | 0.733277 | 0.348225 | 0.943442 | 0.126886 |

## Weekday exploration

TRAIN log-returns grouped by actual calendar weekday. Mean/median/std/count are descriptive; no inferential evidence of a weekly effect is claimed. Missing holiday sessions make period=5 different from literal weekday alignment.

| ticker | scope | weekday_number | weekday | mean | median | std | count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NVDA | train | 0 | Monday | 0.211997 | 0.530291 | 3.54531 | 370 |
| NVDA | train | 1 | Tuesday | 0.255431 | 0.233594 | 3.02522 | 407 |
| NVDA | train | 2 | Wednesday | 0.26292 | 0.290134 | 3.08638 | 404 |
| NVDA | train | 3 | Thursday | 0.286513 | 0.337901 | 3.48692 | 400 |
| NVDA | train | 4 | Friday | -0.095332 | -0.0987383 | 3.0637 | 398 |
| AMD | train | 0 | Monday | 0.495498 | 0.406082 | 3.41909 | 370 |
| AMD | train | 1 | Tuesday | 0.163906 | 0 | 3.08294 | 407 |
| AMD | train | 2 | Wednesday | 0.154434 | 0.0552281 | 3.73276 | 404 |
| AMD | train | 3 | Thursday | 0.0246209 | -0.0809885 | 3.81687 | 400 |
| AMD | train | 4 | Friday | -0.0277121 | 0.0378362 | 3.1308 | 398 |
| SOXX | train | 0 | Monday | 0.188658 | 0.333695 | 2.24853 | 370 |
| SOXX | train | 1 | Tuesday | 0.10444 | 0.0772833 | 2.03898 | 407 |
| SOXX | train | 2 | Wednesday | 0.133112 | 0.197838 | 2.29762 | 404 |
| SOXX | train | 3 | Thursday | 0.0549744 | 0.120306 | 2.42114 | 400 |
| SOXX | train | 4 | Friday | -0.0503967 | -0.0565098 | 2.07434 | 398 |

## Extreme observations

IQR bounds fitted only on TRAIN: Q1−1.5*(Q3−Q1), Q3+1.5*(Q3−Q1). Percentages divide by valid TRAIN returns. All observations retained; no winsorization or automatic correction. Top ten absolute TRAIN returns per asset are exported separately.

| ticker | scope | Q1 | Q3 | IQR | lower_bound | upper_bound | outlier_count | outlier_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NVDA | train | -1.52095 | 1.97056 | 3.4915 | -6.7582 | 7.20781 | 74 | 3.73926 |
| AMD | train | -1.68381 | 2.03534 | 3.71915 | -7.26254 | 7.61407 | 89 | 4.49722 |
| SOXX | train | -1.05681 | 1.34088 | 2.39769 | -4.65335 | 4.93742 | 74 | 3.73926 |

| ticker | scope | rank_abs | Date | log_return_pct | absolute_log_return_pct | iqr_outlier |
| --- | --- | --- | --- | --- | --- | --- |
| NVDA | train | 1 | 2023-05-25 | 21.8088 | 21.8088 | True |
| NVDA | train | 2 | 2018-11-16 | -20.7711 | 20.7711 | True |
| NVDA | train | 3 | 2020-03-16 | -20.3979 | 20.3979 | True |
| NVDA | train | 4 | 2025-01-27 | -18.5946 | 18.5946 | True |
| NVDA | train | 5 | 2025-04-09 | 17.1621 | 17.1621 | True |
| NVDA | train | 6 | 2020-03-24 | 15.834 | 15.834 | True |
| NVDA | train | 7 | 2024-02-22 | 15.187 | 15.187 | True |
| NVDA | train | 8 | 2019-01-28 | -14.8784 | 14.8784 | True |
| NVDA | train | 9 | 2022-11-10 | 13.3912 | 13.3912 | True |
| NVDA | train | 10 | 2023-02-23 | 13.1216 | 13.1216 | True |
| AMD | train | 1 | 2025-04-09 | 21.3663 | 21.3663 | True |
| AMD | train | 2 | 2025-10-06 | 21.2754 | 21.2754 | True |
| AMD | train | 3 | 2019-01-30 | 18.1889 | 18.1889 | True |
| AMD | train | 4 | 2018-10-25 | -16.7772 | 16.7772 | True |
| AMD | train | 5 | 2020-03-12 | -15.828 | 15.828 | True |
| AMD | train | 6 | 2020-07-24 | 15.2735 | 15.2735 | True |
| AMD | train | 7 | 2019-08-08 | 15.0179 | 15.0179 | True |
| AMD | train | 8 | 2022-10-07 | -14.9299 | 14.9299 | True |
| AMD | train | 9 | 2018-07-26 | 13.3921 | 13.3921 | True |
| AMD | train | 10 | 2022-11-10 | 13.3385 | 13.3385 | True |
| SOXX | train | 1 | 2025-04-09 | 17.0347 | 17.0347 | True |
| SOXX | train | 2 | 2020-03-16 | -16.5202 | 16.5202 | True |
| SOXX | train | 3 | 2020-03-12 | -11.6131 | 11.6131 | True |
| SOXX | train | 4 | 2025-04-03 | -10.637 | 10.637 | True |
| SOXX | train | 5 | 2020-03-24 | 10.2701 | 10.2701 | True |
| SOXX | train | 6 | 2020-03-13 | 10.1907 | 10.1907 | True |
| SOXX | train | 7 | 2022-11-10 | 9.84682 | 9.84682 | True |
| SOXX | train | 8 | 2020-04-06 | 9.71265 | 9.71265 | True |
| SOXX | train | 9 | 2020-03-09 | -8.92777 | 8.92777 | True |
| SOXX | train | 10 | 2020-03-18 | -8.5737 | 8.5737 | True |

## ACF/PACF

TRAIN only: Adjusted Close and Log Return, 40 lags; PACF uses `ywm`. Squared-return ACF also uses 40 lags. Pointwise 95% intervals are not simultaneous significance bands. No p/q selection and no ARCH-LM. Log-returns represent the first difference of log-price, not the raw dollar-price difference.

## STL decomposition

TRAIN log-price, `period=5`, `robust=True`. Five trading sessions are an exploratory weekly-cycle hypothesis, not evidence of exploitable seasonality. STL smoothers are two-sided within TRAIN; components are diagnostics, never causal forecasting features. No SARIMA decision follows.

## ADF

H0: a unit root. Pre-specified constant+linear trend (`ct`) for prices/log-prices and constant (`c`) for returns. Trend accommodates possible deterministic trends without test observations or selecting terms from p-values. `autolag='AIC'`; p<0.05 mechanically rejects H0.

| ticker | series | test_statistic | p_value | used_lag | nobs | regression | decision_5pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NVDA | Adj_Close | -0.334247 | 0.988692 | 26 | 1953 | ct | fail_to_reject_H0 |
| NVDA | Log_Price | -2.25121 | 0.461103 | 9 | 1970 | ct | fail_to_reject_H0 |
| NVDA | Log_Return | -14.421 | 7.91143e-27 | 8 | 1970 | c | reject_H0 |
| AMD | Adj_Close | -2.20418 | 0.487496 | 25 | 1954 | ct | fail_to_reject_H0 |
| AMD | Log_Price | -2.33116 | 0.416796 | 3 | 1976 | ct | fail_to_reject_H0 |
| AMD | Log_Return | -26.7347 | 0 | 2 | 1976 | c | reject_H0 |
| SOXX | Adj_Close | -2.25341 | 0.459873 | 4 | 1975 | ct | fail_to_reject_H0 |
| SOXX | Log_Price | -2.60601 | 0.277134 | 9 | 1970 | ct | fail_to_reject_H0 |
| SOXX | Log_Return | -15.1151 | 7.59993e-28 | 8 | 1970 | c | reject_H0 |

## KPSS

H0: stationarity around the specified constant/trend. Deterministic terms match ADF; `nlags='auto'`. p<0.05 mechanically rejects stationarity. Boundary p-values are censored, not exact: warnings are captured in the CSV and displayed during execution.

| ticker | series | test_statistic | p_value | lags | regression | decision_5pct | p_value_bound |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NVDA | Adj_Close | 1.42459 | 0.01 | 27 | ct | reject_stationarity | actual_p_smaller_than_reported |
| NVDA | Log_Price | 0.621809 | 0.01 | 27 | ct | reject_stationarity | actual_p_smaller_than_reported |
| NVDA | Log_Return | 0.165973 | 0.1 | 4 | c | fail_to_reject_stationarity | actual_p_greater_than_reported |
| AMD | Adj_Close | 0.201928 | 0.0152772 | 27 | ct | reject_stationarity | none |
| AMD | Log_Price | 1.10162 | 0.01 | 27 | ct | reject_stationarity | actual_p_smaller_than_reported |
| AMD | Log_Return | 0.119577 | 0.1 | 5 | c | fail_to_reject_stationarity | actual_p_greater_than_reported |
| SOXX | Adj_Close | 0.324906 | 0.01 | 27 | ct | reject_stationarity | actual_p_smaller_than_reported |
| SOXX | Log_Price | 0.498083 | 0.01 | 27 | ct | reject_stationarity | actual_p_smaller_than_reported |
| SOXX | Log_Return | 0.0379992 | 0.1 | 7 | c | fail_to_reject_stationarity | actual_p_greater_than_reported |

Captured warnings:

- 9 diagnostic(s): adfuller currently returns a plain tuple whose length depends on the store and autolag arguments. In release 0.16 or after July 2027, whichever is later, the default behavior will switch to always returning an ADFullerResult. Set result_object=True to switch now, or result_object=False to keep the current behavior and silence this warning.

- 5 diagnostic(s): The test statistic is outside of the range of p-values available in the look-up table. The actual p-value is smaller than the p-value returned.

- 9 diagnostic(s): kpss currently returns a plain tuple whose length and layout depends on the store argument (and which silently drops `lags` when store=True). In release 0.16 or after July 2027, whichever is later, the default behavior will switch to always returning a KPSSResult. Set result_object=True to switch now, or result_object=False to keep the current behavior and silence this warning.

- 3 diagnostic(s): The test statistic is outside of the range of p-values available in the look-up table. The actual p-value is greater than the p-value returned.

## Mechanical stationarity summary

`stationary_supported`: ADF rejects and KPSS does not reject stationarity. `nonstationary_supported`: ADF does not reject and KPSS rejects stationarity. Otherwise `mixed_evidence`. Non-rejection is not proof. No automatic ARIMA/VAR/VECM choice.

| ticker | series | scope | ADF_decision | KPSS_decision | mechanical_summary |
| --- | --- | --- | --- | --- | --- |
| NVDA | Adj_Close | train | fail_to_reject_H0 | reject_stationarity | nonstationary_supported |
| NVDA | Log_Price | train | fail_to_reject_H0 | reject_stationarity | nonstationary_supported |
| NVDA | Log_Return | train | reject_H0 | fail_to_reject_stationarity | stationary_supported |
| AMD | Adj_Close | train | fail_to_reject_H0 | reject_stationarity | nonstationary_supported |
| AMD | Log_Price | train | fail_to_reject_H0 | reject_stationarity | nonstationary_supported |
| AMD | Log_Return | train | reject_H0 | fail_to_reject_stationarity | stationary_supported |
| SOXX | Adj_Close | train | fail_to_reject_H0 | reject_stationarity | nonstationary_supported |
| SOXX | Log_Price | train | fail_to_reject_H0 | reject_stationarity | nonstationary_supported |
| SOXX | Log_Return | train | reject_H0 | fail_to_reject_stationarity | stationary_supported |

## Limitations

Vendor revisions, nonuniform trading calendars, structural breaks and finite test power can affect diagnostics. Trend specification matters. Multiple pointwise diagnostics lack multiplicity correction. Weekday differences and STL cycles are not established effects. Extremes are retained. The final holdout remains reserved for later evaluation. Future scalers, lag choices and neural-network windows must be designed using TRAIN, with rolling validation inside TRAIN where appropriate.

Anti-leakage checks combine measured assertions and labeled code-scope audits:

| check | status | details |
| --- | --- | --- |
| chronological_split | PASS | max(train.Date) < min(test.Date) |
| no_date_overlap | PASS | Disjoint observed dates |
| canonical_row_split | PASS | floor(0.90*N) before any NA exclusion |
| all_rows_and_original_values_preserved | PASS | Original 19 columns preserved exactly; no global drop |
| training_features_independent_of_holdout | PASS | Train features equal recomputation on canonical train alone |
| no_future_features | PASS | Changing later observations leaves every earlier feature unchanged |
| backward_rolling_windows | PASS | Uncentered rolling(20/60), min_periods=window; shift(1)/diff() only |
| adf_kpss_train_only | PASS | Code audit: stationarity_tables(train); full/test never passed to test functions |
| acf_pacf_train_only | PASS | Code audit: generate_figures ACF/PACF loops read train only |
| stl_train_only | PASS | Code audit: STL(train log-price, period=5, robust=True) |
| iqr_thresholds_train_only | PASS | Code audit: build_tables fits IQR bounds from train log-returns only |
| no_full_data_fitted_normalization | PASS | Code audit: no scaler; descriptive Base 100 uses first observed price only |

Runtime versions:

| package | version |
| --- | --- |
| python | 3.12.3 |
| numpy | 2.5.3 |
| pandas | 3.0.6 |
| matplotlib | 3.11.2 |
| scipy | 1.18.1 |
| statsmodels | 0.15.0 |

## Phase boundary

24 final PNG figures and 12 CSV tables produced. Feature/train/test datasets remain local and ignored by Git. No ARIMA, SARIMA, VAR, Granger, Johansen, VECM, ARCH, GARCH, LSTM, GRU, forecasting or Diebold–Mariano computation. Stop for review before Phase 3. The team must complete the human template before requesting LLM interpretation.

Reproduce in the project environment:

```bash
python python/01_data_eda.py
python -m ruff check python/01_data_eda.py tests/test_eda_stationarity.py
python -m pytest
```

Figure inventory:

- [`adjusted_close.png`](../outputs/figures/phase2/adjusted_close.png)
- [`trading_volumes.png`](../outputs/figures/phase2/trading_volumes.png)
- [`log_returns.png`](../outputs/figures/phase2/log_returns.png)
- [`squared_log_returns.png`](../outputs/figures/phase2/squared_log_returns.png)
- [`rolling_volatility_20d.png`](../outputs/figures/phase2/rolling_volatility_20d.png)
- [`normalized_prices_base100.png`](../outputs/figures/phase2/normalized_prices_base100.png)
- [`return_histograms_train.png`](../outputs/figures/phase2/return_histograms_train.png)
- [`return_boxplots_train.png`](../outputs/figures/phase2/return_boxplots_train.png)
- [`return_qqplots_train.png`](../outputs/figures/phase2/return_qqplots_train.png)
- [`return_correlation_train.png`](../outputs/figures/phase2/return_correlation_train.png)
- [`rolling_correlations_60d.png`](../outputs/figures/phase2/rolling_correlations_60d.png)
- [`weekday_returns_train.png`](../outputs/figures/phase2/weekday_returns_train.png)
- [`nvda_adj_close_acf_pacf_train.png`](../outputs/figures/phase2/nvda_adj_close_acf_pacf_train.png)
- [`nvda_log_return_acf_pacf_train.png`](../outputs/figures/phase2/nvda_log_return_acf_pacf_train.png)
- [`nvda_squared_returns_acf_train.png`](../outputs/figures/phase2/nvda_squared_returns_acf_train.png)
- [`nvda_log_price_stl_train.png`](../outputs/figures/phase2/nvda_log_price_stl_train.png)
- [`amd_adj_close_acf_pacf_train.png`](../outputs/figures/phase2/amd_adj_close_acf_pacf_train.png)
- [`amd_log_return_acf_pacf_train.png`](../outputs/figures/phase2/amd_log_return_acf_pacf_train.png)
- [`amd_squared_returns_acf_train.png`](../outputs/figures/phase2/amd_squared_returns_acf_train.png)
- [`amd_log_price_stl_train.png`](../outputs/figures/phase2/amd_log_price_stl_train.png)
- [`soxx_adj_close_acf_pacf_train.png`](../outputs/figures/phase2/soxx_adj_close_acf_pacf_train.png)
- [`soxx_log_return_acf_pacf_train.png`](../outputs/figures/phase2/soxx_log_return_acf_pacf_train.png)
- [`soxx_squared_returns_acf_train.png`](../outputs/figures/phase2/soxx_squared_returns_acf_train.png)
- [`soxx_log_price_stl_train.png`](../outputs/figures/phase2/soxx_log_price_stl_train.png)
