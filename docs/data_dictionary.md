# Data Dictionary

This document describes the fields planned for the raw daily observations
for NVDA, AMD and SOXX. No market data has been downloaded in Phase 0.

## Planned raw variables

| Variable | Description |
| --- | --- |
| Date | Trading observation date |
| Open | Opening price |
| High | Highest price during the session |
| Low | Lowest price during the session |
| Close | Closing price |
| Adjusted Close | Closing price adjusted for applicable corporate actions |
| Volume | Number of shares traded during the session |

These raw fields are planned for each asset: **NVDA**, **AMD** and **SOXX**.

## Derived variables — to be implemented during Phase 1/2

The following variables are planned:

- `log_price`
- `log_return`
- `return_pct`
- `volume_change`
- `realized_volatility`

The exact definition, handling of missing observations and calculation choices
for each derived variable will be fixed and documented before use.
