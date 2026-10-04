# Phase 1 — Data Acquisition & Audit

## Objective

Obtain and validate the market data before any transformation or modeling.
Python is the canonical acquisition mechanism; R will later use the same
validated dataset. This phase stops at acquisition and structural auditing.

## Assets

- NVDA — NVIDIA; future principal forecasting target.
- AMD — Advanced Micro Devices.
- SOXX — iShares Semiconductor ETF.

## Source

Yahoo Finance via yfinance. Each ticker is downloaded separately with
`yf.download()`, `interval="1d"`, `auto_adjust=False`, `actions=False`,
`progress=False`, `threads=False`, `keepna=True`, `repair=False` and
`rounding=False`. The explicit `keepna=True` preserves NaN rows that Yahoo
returns. See the [yfinance download reference](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html).

## Period

2018-01-01 to 2026-10-02, inclusive as requested. Because yfinance's `end`
is exclusive, the actual request uses `start="2018-01-01"` and
`end="2026-10-03"`. The first observed trading day may follow the requested
start. The audit separately reports whether the last requested date was returned;
absent endpoint coverage is a warning, not evidence of complete acquisition.

## Frequency

Daily trading observations. Weekends and holidays are not synthesized.

## Raw variables

`Date`, `Open`, `High`, `Low`, `Close`, `Adj Close`, `Volume`.
Date is the named index and is written explicitly to CSV.
See [the data dictionary](data_dictionary.md) for types and units.

## Why both Close and Adjusted Close?

Close is the session closing price supplied by Yahoo; historical Close already
reflects Yahoo's split adjustments. Adjusted Close additionally reflects
relevant distributions, supporting historical comparisons. Both vendor fields
are retained without further price adjustment by this pipeline.
See [Yahoo historical field definitions](https://finance.yahoo.com/quote/NVDA/history/).

## Integrity checks

The pipeline validates nonempty data, required unique columns, real numeric
types, parseable daily dates and the requested date bounds. It handles either
flat columns or a single-ticker two-level MultiIndex. Timezone removal keeps
the local trading date; stable sorting preserves duplicate rows.

Each asset audit records row count, first/last dates, column count/names/types,
total and per-column missing values, duplicate dates, chronological order,
infinite cells, nonpositive price cells, negative/zero volume rows and OHLC
anomalies. `high_below_low` counts rows with High < Low; `invalid_high` counts
rows with High < Open or Close; `invalid_low` counts rows with Low > Open or
Close. Together they check all High/Low bounds. Counts can overlap and should
not be added as a count of distinct anomalous rows. `incomplete_ohlc_rows`
reports rows for which complete OHLC validation is impossible due to NA.
Pairwise comparisons detect available contradictions without imputing NA.

Duplicates, infinite values, nonpositive prices, negative volume or OHLC
contradictions flag critical integrity failures: raw files and completed
reports are retained, but the process exits with code 1. Missing values and
zero volume are reported as review warnings. A download/schema/write failure
stops the pipeline explicitly with code 1 and an actionable error; partial
files may remain. Previous reports must not be interpreted as the failed run.

## Calendar checks

Compare distinct observed trading dates using the union and intersection of
NVDA, AMD and SOXX calendars. For each asset, count dates absent relative to
the union, dates present but outside the three-way intersection, and dates
unique to that asset; record up to five examples of each. No comparison with
all calendar days, synchronization, or destructive join is performed.
Identical calendars alone cannot detect a date absent from all three assets.

## Important scientific rule

No market value is transformed, removed, imputed or manually edited before
reviewing detected anomalies. No returns, exploratory statistics, stationarity
tests, model, split or forecast is produced in Phase 1.

## Execution and reproducibility

From the repository root, with the project environment active:

```bash
python python/00_data_acquisition.py
python -m ruff check python/00_data_acquisition.py
```

Local ignored raw files: `data/raw/{NVDA,AMD,SOXX}_raw.csv`.
The ignored `.cache/yfinance/` stores only yfinance's operational cache.
Generated tracked reports:

- `outputs/tables/phase1_asset_audit.csv`
- `outputs/tables/phase1_calendar_audit.csv`
- `outputs/tables/phase1_raw_manifest.csv`

The manifest records SHA-256 of saved CSV bytes, row counts and dates, request
bounds, acquisition timestamp in UTC and Python/yfinance/pandas/numpy versions.
Rerunning downloads the vendor's then-current historical copy; the vendor may
revise past values. Compare hashes to identify the exact local copy used.
The actual run results below describe the documented manifest, not future runs.

## Actual run results

Acquisition started (UTC): `2026-10-04T10:45:18.606758+00:00`.

The actual download completed with exit code 0. The initial sandbox attempt failed to connect to Yahoo Finance (curl error 7); the authorized execution outside the sandbox succeeded. The following values are generated from the saved program reports, whose SHA-256 hashes and audits were verified against the raw CSVs read back from disk.

| Check | NVDA | AMD | SOXX |
| --- | --- | --- | --- |
| rows | 2200 | 2200 | 2200 |
| first_date | 2018-01-02 | 2018-01-02 | 2018-01-02 |
| last_date | 2026-10-02 | 2026-10-02 | 2026-10-02 |
| column_count | 6 | 6 | 6 |
| missing_total | 0 | 0 | 0 |
| duplicate_dates | 0 | 0 | 0 |
| chronological_order | True | True | True |
| infinite_values | 0 | 0 | 0 |
| nonpositive_prices | 0 | 0 | 0 |
| negative_volume | 0 | 0 | 0 |
| zero_volume | 0 | 0 | 0 |
| high_below_low | 0 | 0 | 0 |
| invalid_high | 0 | 0 | 0 |
| invalid_low | 0 | 0 | 0 |
| incomplete_ohlc_rows | 0 | 0 | 0 |
| last_requested_date_present | True | True | True |
| critical_validation_failures | False | False | False |

Columns, types and per-column missing counts copied from the asset audit:

- **NVDA**: columns `["Open", "High", "Low", "Close", "Adj Close", "Volume"]`; types `{"Open": "float64", "High": "float64", "Low": "float64", "Close": "float64", "Adj Close": "float64", "Volume": "int64"}`; missing counts `{"Open": 0, "High": 0, "Low": 0, "Close": 0, "Adj Close": 0, "Volume": 0}`.

- **AMD**: columns `["Open", "High", "Low", "Close", "Adj Close", "Volume"]`; types `{"Open": "float64", "High": "float64", "Low": "float64", "Close": "float64", "Adj Close": "float64", "Volume": "int64"}`; missing counts `{"Open": 0, "High": 0, "Low": 0, "Close": 0, "Adj Close": 0, "Volume": 0}`.

- **SOXX**: columns `["Open", "High", "Low", "Close", "Adj Close", "Volume"]`; types `{"Open": "float64", "High": "float64", "Low": "float64", "Close": "float64", "Adj Close": "float64", "Volume": "int64"}`; missing counts `{"Open": 0, "High": 0, "Low": 0, "Close": 0, "Adj Close": 0, "Volume": 0}`.

Calendar comparison:

| ticker | observed_dates | union_dates | common_dates | missing_from_union | non_common_dates | unique_to_asset | identical_calendars | missing_date_examples | non_common_date_examples | unique_date_examples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NVDA | 2200 | 2200 | 2200 | 0 | 0 | 0 | True | [] | [] | [] |
| AMD | 2200 | 2200 | 2200 | 0 | 0 | 0 | True | [] | [] | [] |
| SOXX | 2200 | 2200 | 2200 | 0 | 0 | 0 | True | [] | [] | [] |

Raw-file manifest (the full CSV also records requested bounds and package versions):

| ticker | file_name | rows | first_date | last_date | sha256 |
| --- | --- | --- | --- | --- | --- |
| NVDA | NVDA_raw.csv | 2200 | 2018-01-02 | 2026-10-02 | ce0be7475afb30081b9127580e87fe98a4de60c3d3ea73583b7a1455354fcdd5 |
| AMD | AMD_raw.csv | 2200 | 2018-01-02 | 2026-10-02 | fcd5544f0ab3c134223fff66432ca980d903540b1d3ffe62371ac950f6bf8b97 |
| SOXX | SOXX_raw.csv | 2200 | 2018-01-02 | 2026-10-02 | 7d4317ae33e89f8dc021037a4b7002964f17a43ef1a388218029dd63090e463e |

Execution environment:

| ticker | python_version | yfinance_version | pandas_version | numpy_version |
| --- | --- | --- | --- | --- |
| NVDA | 3.12.3 | 1.7.0 | 3.0.6 | 2.5.3 |
| AMD | 3.12.3 | 1.7.0 | 3.0.6 | 2.5.3 |
| SOXX | 3.12.3 | 1.7.0 | 3.0.6 | 2.5.3 |

The completed acquisition reported:

```text
Raw files created (all three this run): YES
Audit completed: YES
Critical validation failures: NO
```

No anomaly was detected by the implemented integrity checks. Calendars were compared without synchronization; no Phase 2 calculation was performed.
