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

## Derived variables — future phases

The following variables are planned:

- `log_price`
- `log_return`
- `return_pct`
- `volume_change`
- `realized_volatility`

The exact definition, handling of missing observations and calculation choices
for each derived variable will be fixed and documented before use.
