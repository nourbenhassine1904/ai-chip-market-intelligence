# Data Dictionary

This document describes the raw daily observations for NVDA, AMD and SOXX.
Python/yfinance is the canonical acquisition pipeline. R will later consume
the same validated reference dataset.

## Raw variables

| Variable | Definition | Expected type | Unit / interpretation | Source |
| --- | --- | --- | --- | --- |
| Date | Trading observation date | DatetimeIndex; ISO date in CSV | Observed trading day, timezone removed without shifting dates | Yahoo Finance via yfinance |
| Open | Opening price | Real numeric | USD per share, as supplied | Yahoo Finance via yfinance |
| High | Highest price during the session | Real numeric | USD per share, as supplied | Yahoo Finance via yfinance |
| Low | Lowest price during the session | Real numeric | USD per share, as supplied | Yahoo Finance via yfinance |
| Close | Session closing price supplied by Yahoo | Real numeric | USD per share; Yahoo historical Close is split adjusted | Yahoo Finance via yfinance |
| Adj Close | Closing price adjusted for applicable corporate actions | Real numeric | USD per share, adjusted for splits and relevant distributions | Yahoo Finance via yfinance |
| Volume | Number of shares traded during the session | Integer-like numeric; float possible when missing | Shares for NVDA/AMD; ETF shares for SOXX, as supplied | Yahoo Finance via yfinance |

These fields are retained for each asset: **NVDA**, **AMD** and **SOXX**.
`Adjusted Close` is the descriptive name; `Adj Close` is the exact CSV column.
Prices are vendor historical values: `auto_adjust=False` prevents additional
yfinance OHLC adjustment and does not reverse Yahoo's existing adjustments.
See [Yahoo historical field definitions](https://finance.yahoo.com/quote/NVDA/history/).
Missing observations remain unchanged; no derived variables are calculated here.

## Canonical aligned dataset

`data/processed/market_aligned.csv` is the common local input for future
Python/R analyses. It contains `Date` and 18 financial columns in wide format,
ordered by NVDA, AMD, SOXX, then Open, High, Low, Close, Adj_Close, Volume.

Financial columns follow `<TICKER>_<VARIABLE>`:

- `TICKER` ∈ {`NVDA`, `AMD`, `SOXX`}.
- `VARIABLE` ∈ {`Open`, `High`, `Low`, `Close`, `Adj_Close`, `Volume`}.
- `Date` is an ISO trading-date column, shared by all three assets.

The definitions, numeric types, units and Yahoo/yfinance source in the raw
dictionary above also apply to the prefixed financial columns. Only the
column labels change: raw `Adj Close` becomes `<TICKER>_Adj_Close`.
An inner join retains only the intersection of observed trading dates;
date losses are measured explicitly in the alignment audit. Market values
are neither adjusted, rounded, imputed nor otherwise transformed.
The generated CSV is ignored by Git and identified by its SHA-256 manifest.

Both Close (the vendor's session closing price) and Adj_Close (adjusted for
applicable corporate actions) are retained. Adj_Close is the main
historical price variable for Phase 2 transformations (decision D009).
No returns are calculated during Phase 1.5.

## Phase 2 financial transformations

Each name below is prefixed by `<TICKER>_`, for NVDA, AMD and SOXX.
Let P_t be `<TICKER>_Adj_Close`, V_t be `<TICKER>_Volume`, and t−1 the
previous observed trading session, not the previous calendar day.

| Suffix | Exact definition | Unit | Structural NA |
| --- | --- | --- | --- |
| Log_Price | ln(P_t), natural logarithm | Log of adjusted USD price | None for positive validated prices |
| Log_Return | 100 × [ln(P_t) − ln(P_{t−1})] | Daily logarithmic return, percent | First row |
| Return_Pct | 100 × (P_t / P_{t−1} − 1) | Daily simple return, percent | First row |
| Volume_Change_Pct | 100 × (V_t / V_{t−1} − 1) | Daily volume change, percent | First row |
| Rolling_Vol_20D | 100 × sqrt(252) × sample_std(Log_Return_s / 100, s=t−19,…,t), ddof=1 | Annualized historical volatility, percent | First 20 rows, including undefined initial return |

Rolling volatility requires 20 valid returns and uses an uncentered trailing
window including the current session. It is a descriptive historical measure,
not an automatically accepted forecasting feature. Annualization assumes
252 sessions per year. Missing values are never filled; no global row drop.
Ratio calculations do not forward-fill missing values; a zero denominator is
undefined and yields NA. The validated canonical dataset has positive volumes.

`market_features.csv` retains all 19 original columns and adds 15 numeric
columns, for 34 columns and all canonical dates. `market_train.csv` and
`market_test.csv` contain this same schema, split at floor(0.90 × N) canonical
rows before NA exclusion. The first test return uses the last training price;
that is past information. All three generated CSVs remain local and ignored.
SHA-256, shape and source lineage are recorded in the Phase 2 feature manifest.

Descriptive variance and standard deviation use ddof=1. Skewness and excess
kurtosis use pandas' unbiased sample estimators; normal excess kurtosis is 0.
Diagnostic tables use `scope=train`; full descriptive statistics are explicitly
labeled `scope=full_descriptive` and cannot guide model selection.
