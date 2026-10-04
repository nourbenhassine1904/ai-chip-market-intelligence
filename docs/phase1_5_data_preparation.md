# Phase 1.5 — Canonical Dataset Preparation

## Objective

Build one validated, aligned reference dataset shared by the four team
members and future Python/R analyses. This is structural preparation only;
Phase 2 has not started.

## Inputs

- `data/raw/NVDA_raw.csv`
- `data/raw/AMD_raw.csv`
- `data/raw/SOXX_raw.csv`
- `outputs/tables/phase1_raw_manifest.csv`

The raw files were acquired and audited during Phase 1. Preparation reads
them locally; it never downloads data or rewrites a raw file. If a raw file
is missing, execution stops with:
`Raw data missing. Run python/00_data_acquisition.py first.`

## Raw integrity verification

Recompute each raw file's SHA-256 and compare it with the Phase 1 manifest
before loading any market observations. A mismatch reports the ticker,
expected hash, actual hash and recommendation to rerun and review Phase 1.
The manifest must contain exactly one valid record for each official ticker
and the expected file names. After reading, row counts and first/last dates
are also checked against that manifest. The source hashes are verified again
before saving the canonical dataset. Raw values and file bytes stay unchanged.

## Alignment strategy

Use an **inner join on common trading dates**, with one-to-one validation
on `Date`. Before joining, compute the observed union and intersection and
the number of dates excluded for each asset. The audit records these counts
and up to five excluded-date examples per asset. Date losses are explicitly
reported as a warning; they are allowed if the intersection is nonempty.
An empty intersection is a critical failure.

No weekend or holiday rows are synthesized. There is no imputation.
Final rows are sorted by ascending Date and columns follow a fixed order,
independent of input mapping or raw column order.

## Canonical schema

The CSV contains exactly these 19 columns; Date is a real column and no
pandas index is exported:

```text
Date
NVDA_Open
NVDA_High
NVDA_Low
NVDA_Close
NVDA_Adj_Close
NVDA_Volume
AMD_Open
AMD_High
AMD_Low
AMD_Close
AMD_Adj_Close
AMD_Volume
SOXX_Open
SOXX_High
SOXX_Low
SOXX_Close
SOXX_Adj_Close
SOXX_Volume
```

Close is the vendor's session closing price; Yahoo historical Close already
reflects split adjustments, as documented in Phase 1. Adj Close is the
closing price adjusted for applicable corporate actions and distributions.
Both fields are retained. Adj_Close is the envisaged principal price variable
for historical analysis; the choice will be confirmed for each use in Phase 2.
No returns are calculated and no model-specific price choice is imposed here.

## Why a canonical dataset?

A shared reference gives all members and both languages the same market
observations and trading dates. One reproducible preparation pipeline prevents
divergent preprocessing and makes downstream inputs identifiable by SHA-256.

## Integrity checks

Raw validation requires nonempty data, exactly the seven raw fields, valid
timezone-free daily dates, chronological order, unique dates, no missing
values and real numeric market fields. Unsorted dates, missing columns,
unexpected columns, NA and duplicate dates cause explicit errors; no row is
silently repaired or discarded.

The aligned audit records shape, date bounds, total/per-column NA, duplicate
dates, chronology, infinite cells, retained dates, expected/unexpected columns
and excluded dates per asset. It checks High >= Low/Open/Close,
Low <= Open/Close, nonnegative volumes and strictly positive price cells.
OHLC counts are measured once per anomalous asset-session; the total sums
these asset-session counts, so multiple assets on one date can contribute.
NA, duplicates, infinite cells, OHLC contradictions, negative volumes,
nonpositive prices or invalid schema/order prevent successful publication.

CSV loading uses `float_precision="round_trip"`; writing does not specify a
rounding precision. Immediately after saving, the CSV is read back and
compared exactly with the in-memory dataset, including values, column order
and dtypes. Its integrity audit is repeated. Fixed column/row order, ISO dates
and LF line endings make identical raw inputs produce identical output bytes.

Errors return exit code 1 with an actionable message. Existing generated
files may belong to a previous successful run and must be checked against
their manifest rather than assumed to describe the failed execution.

## Output

`data/processed/market_aligned.csv` is generated locally and ignored by Git.
The reproducible script and these small provenance reports are committed:

- `outputs/tables/phase1_5_processed_manifest.csv`: dataset name, file name,
  shape, dates, SHA-256, source assets, alignment method, raw source hashes
  and Phase 1 manifest fingerprint.
- `outputs/tables/phase1_5_alignment_audit.csv`: measured metrics and values.

From the root with the project environment active:

```bash
python python/01_data_preparation.py
python -m ruff check python/01_data_preparation.py tests/test_data_preparation.py
python -m pytest
```

Tests use synthetic temporary fixtures and require neither Internet nor
production raw files. They cover naming, common-date alignment and measured
losses, sorting/schema determinism, preservation of raw values, input failures,
hash mismatches, anomaly detection, CSV precision and byte determinism.

## Actual execution results

The script completed successfully twice with exit code 0, using the same local raw files. All three raw SHA-256 hashes matched the Phase 1 manifest before and after preparation. No raw file was rewritten or downloaded.

| ticker | rows | sha256_verified |
| --- | --- | --- |
| NVDA | 2200 | True |
| AMD | 2200 | True |
| SOXX | 2200 | True |

Measured alignment and final dataset checks copied from the generated audit:

| metric | value |
| --- | --- |
| nvda_rows | 2200 |
| amd_rows | 2200 |
| soxx_rows | 2200 |
| union_dates | 2200 |
| common_dates | 2200 |
| nvda_dates_dropped | 0 |
| nvda_dropped_date_examples | [] |
| amd_dates_dropped | 0 |
| amd_dropped_date_examples | [] |
| soxx_dates_dropped | 0 |
| soxx_dropped_date_examples | [] |
| aligned_rows | 2200 |
| aligned_columns | 19 |
| first_date | 2018-01-02 |
| last_date | 2026-10-02 |
| missing_total | 0 |
| duplicate_dates | 0 |
| chronological_order | True |
| infinite_values | 0 |
| dates_retained | 2200 |
| expected_columns_present | 19 |
| unexpected_columns | 0 |
| nvda_invalid_ohlc_rows | 0 |
| amd_invalid_ohlc_rows | 0 |
| soxx_invalid_ohlc_rows | 0 |
| invalid_ohlc_total | 0 |
| negative_volume_total | 0 |
| nonpositive_prices_total | 0 |

Missing values by column, copied from the generated audit:

```json
{"Date": 0, "NVDA_Open": 0, "NVDA_High": 0, "NVDA_Low": 0, "NVDA_Close": 0, "NVDA_Adj_Close": 0, "NVDA_Volume": 0, "AMD_Open": 0, "AMD_High": 0, "AMD_Low": 0, "AMD_Close": 0, "AMD_Adj_Close": 0, "AMD_Volume": 0, "SOXX_Open": 0, "SOXX_High": 0, "SOXX_Low": 0, "SOXX_Close": 0, "SOXX_Adj_Close": 0, "SOXX_Volume": 0}
```

Canonical file SHA-256: `e4f69e14cb46c797c6eb383c0f60ecc8b5d6a918ccd248288696f08557473b04`.

The SHA-256 was identical across both preparation executions. Disk read-back independently confirmed the shape, date bounds, schema, chronological order, NA, duplicates and exact financial values against the common-date subset of the raw files. All values and dtypes were preserved without rounding.

Ruff: `All checks passed!`

Full pytest suite: `31 passed` (11 acquisition tests and 20 preparation tests).

`git check-ignore -v data/processed/market_aligned.csv` confirmed the existing `data/processed/*` rule. The raw CSVs, environment and test/lint caches are also ignored.

No calendar date was excluded in this execution, and no OHLC contradiction, negative volume, nonpositive price, infinite cell, missing value or duplicate date was detected by the implemented checks.

## Phase boundary

No feature engineering or statistical modeling was performed
during Phase 1.5.

No log-prices, returns, rolling features, statistical tests, splits, scalers
or forecasts were calculated. The next step is a review of this canonical
dataset before Phase 2 begins.
