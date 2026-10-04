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
applicable corporate actions) are retained. Adj_Close is the envisaged main
historical price variable; its use for each model will be reviewed in Phase 2.
No returns are calculated during Phase 1.5.

## Derived variables — future phases

The following variables are planned:

- `log_price`
- `log_return`
- `return_pct`
- `volume_change`
- `realized_volatility`

The exact definition, handling of missing observations and calculation choices
for each derived variable will be fixed and documented before use.
