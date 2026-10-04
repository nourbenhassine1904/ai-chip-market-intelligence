"""Acquire and audit daily Yahoo Finance data; no Phase 2 transformations."""

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
TICKERS = ["NVDA", "AMD", "SOXX"]
START_DATE = "2018-01-01"
LAST_REQUESTED_DATE = "2026-10-02"
END_DATE = "2026-10-03"  # yfinance's end is exclusive.
EXPECTED_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
PRICE_COLUMNS = EXPECTED_COLUMNS[:-1]
CRITICAL_CHECKS = [
    "duplicate_dates",
    "infinite_values",
    "nonpositive_prices",
    "negative_volume",
    "high_below_low",
    "invalid_high",
    "invalid_low",
]


class AcquisitionError(RuntimeError):
    """A download, structural validation or filesystem operation failed."""


def validate_schema(data: pd.DataFrame, ticker: str) -> None:
    """Reject unusable structures without deleting or imputing observations."""
    if data.empty:
        raise AcquisitionError(f"{ticker}: Yahoo Finance returned zero observations.")
    if data.columns.has_duplicates:
        raise AcquisitionError(f"{ticker}: duplicate column names in download.")
    missing = [column for column in EXPECTED_COLUMNS if column not in data.columns]
    if missing:
        raise AcquisitionError(f"{ticker}: required columns missing: {missing}.")
    invalid = [
        column
        for column in EXPECTED_COLUMNS
        if not pd.api.types.is_numeric_dtype(data[column])
        or pd.api.types.is_bool_dtype(data[column])
        or pd.api.types.is_complex_dtype(data[column])
    ]
    if invalid:
        raise AcquisitionError(f"{ticker}: non-real-numeric columns: {invalid}.")
    if not isinstance(data.index, pd.DatetimeIndex) or data.index.hasnans:
        raise AcquisitionError(f"{ticker}: invalid trading-date index.")
    if (data.index != data.index.normalize()).any():
        raise AcquisitionError(f"{ticker}: intraday timestamps in daily download.")
    if (
        (data.index < pd.Timestamp(START_DATE)) | (data.index >= pd.Timestamp(END_DATE))
    ).any():
        raise AcquisitionError(f"{ticker}: dates outside the requested period.")


def normalize_download(data: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Normalize labels and chronology, preserving every row and market value."""
    data = data.copy()
    if isinstance(data.columns, pd.MultiIndex):
        if data.columns.nlevels != 2:
            raise AcquisitionError(f"{ticker}: unsupported column MultiIndex.")
        ticker_levels = [
            level
            for level in range(2)
            if set(data.columns.get_level_values(level)) == {ticker}
        ]
        if len(ticker_levels) != 1:
            raise AcquisitionError(f"{ticker}: ambiguous/mismatched ticker columns.")
        data.columns = data.columns.droplevel(ticker_levels[0])
    # Numeric/RangeIndex labels are not valid dates, even if pandas can cast them.
    if pd.api.types.is_numeric_dtype(data.index.dtype):
        raise AcquisitionError(f"{ticker}: numeric index instead of trading dates.")
    try:
        dates = pd.DatetimeIndex(pd.to_datetime(data.index, errors="raise"))
        if dates.tz is not None:
            dates = dates.tz_localize(None)  # Keep the local trading date.
        data.index = dates.rename("Date")
    except (TypeError, ValueError, OverflowError) as exc:
        raise AcquisitionError(f"{ticker}: cannot parse trading dates: {exc}") from exc
    validate_schema(data, ticker)
    return data.loc[:, EXPECTED_COLUMNS].sort_index(kind="stable")


def download_asset(ticker: str) -> pd.DataFrame:
    """Request one ticker explicitly, retaining both price fields and NaN rows."""
    try:
        data = yf.download(
            ticker,
            start=START_DATE,
            end=END_DATE,
            interval="1d",
            auto_adjust=False,
            actions=False,
            progress=False,
            threads=False,
            keepna=True,
            repair=False,
            rounding=False,
            timeout=30,
        )
    except Exception as exc:
        raise AcquisitionError(
            f"{ticker}: Yahoo Finance download failed: {exc}"
        ) from exc
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise AcquisitionError(
            f"{ticker}: Yahoo Finance returned no observations; check connectivity, "
            "service availability and the ticker. See yfinance's error above."
        )
    return normalize_download(data, ticker)


def audit_asset(data: pd.DataFrame, ticker: str) -> dict[str, object]:
    """Count anomalies; comparisons involving missing fields are not imputations."""
    missing = {column: int(data[column].isna().sum()) for column in data.columns}
    # Pairwise comparisons avoid silently ignoring a missing OHLC component.
    invalid_high = (data["High"] < data["Open"]) | (data["High"] < data["Close"])
    invalid_low = (data["Low"] > data["Open"]) | (data["Low"] > data["Close"])
    result: dict[str, object] = {
        "ticker": ticker,
        "rows": len(data),
        "first_date": data.index.min().strftime("%Y-%m-%d"),
        "last_date": data.index.max().strftime("%Y-%m-%d"),
        "column_count": len(data.columns),
        "column_names": json.dumps(data.columns.tolist()),
        "column_types": json.dumps(
            {column: str(data[column].dtype) for column in data}
        ),
        "missing_total": sum(missing.values()),
        "missing_by_column": json.dumps(missing),
        "duplicate_dates": int(data.index.duplicated().sum()),
        "chronological_order": bool(data.index.is_monotonic_increasing),
        "infinite_values": int(np.isinf(data.to_numpy()).sum()),
        "nonpositive_prices": int((data[PRICE_COLUMNS] <= 0).to_numpy().sum()),
        "negative_volume": int((data["Volume"] < 0).sum()),
        "zero_volume": int((data["Volume"] == 0).sum()),
        "high_below_low": int((data["High"] < data["Low"]).sum()),
        "invalid_high": int(invalid_high.sum()),
        "invalid_low": int(invalid_low.sum()),
        "incomplete_ohlc_rows": int(
            data[["Open", "High", "Low", "Close"]].isna().any(axis=1).sum()
        ),
        "last_requested_date_present": bool(
            pd.Timestamp(LAST_REQUESTED_DATE) in data.index
        ),
    }
    result["critical_validation_failures"] = (
        any(result[key] for key in CRITICAL_CHECKS) or not result["chronological_order"]
    )
    return result


def compare_calendars(assets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compare observed date sets only; do not join or synchronize market data."""
    calendars = {
        ticker: data.index.unique().sort_values() for ticker, data in assets.items()
    }
    union_dates = pd.DatetimeIndex([])
    common_dates = next(iter(calendars.values()))
    for dates in calendars.values():
        union_dates = union_dates.union(dates)
        common_dates = common_dates.intersection(dates)
    rows = []
    for ticker, dates in calendars.items():
        missing = union_dates.difference(dates)
        non_common = dates.difference(common_dates)
        others_union = pd.DatetimeIndex([])
        for other_ticker, other_dates in calendars.items():
            if other_ticker != ticker:
                others_union = others_union.union(other_dates)
        unique = dates.difference(others_union)
        rows.append(
            {
                "ticker": ticker,
                "observed_dates": len(dates),
                "union_dates": len(union_dates),
                "common_dates": len(common_dates),
                "missing_from_union": len(missing),
                "non_common_dates": len(non_common),
                "unique_to_asset": len(unique),
                "identical_calendars": len(union_dates) == len(common_dates),
                "missing_date_examples": json.dumps(
                    missing[:5].strftime("%Y-%m-%d").tolist()
                ),
                "non_common_date_examples": json.dumps(
                    non_common[:5].strftime("%Y-%m-%d").tolist()
                ),
                "unique_date_examples": json.dumps(
                    unique[:5].strftime("%Y-%m-%d").tolist()
                ),
            }
        )
    return pd.DataFrame(rows)


def write_csv(data: pd.DataFrame, path: Path, *, include_index: bool = False) -> None:
    """Write raw observations or generated reports with actionable I/O errors."""
    try:
        data.to_csv(path, index=include_index, encoding="utf-8", date_format="%Y-%m-%d")
    except (OSError, ValueError) as exc:
        raise AcquisitionError(
            f"Cannot write {path.relative_to(PROJECT_ROOT)}: {exc}"
        ) from exc


def compute_file_sha256(path: Path) -> str:
    """Hash the actual saved file bytes, rather than an in-memory representation."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise AcquisitionError(f"Cannot hash {path.name}: {exc}") from exc
    return digest.hexdigest()


def print_section(title: str) -> None:
    """Separate acquisition, calendar and final status output."""
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}", flush=True)


def print_asset_audit(audit: dict[str, object]) -> None:
    """Display every measured check and warn about incomplete requested coverage."""
    print(f"\nAsset: {audit['ticker']}")
    for key, value in audit.items():
        if key != "ticker":
            print(f"{key.replace('_', ' ').capitalize()}: {value}")
    if audit["missing_total"] or audit["zero_volume"]:
        print("WARNING: missing values / zero volume retained; review before Phase 2.")
    if not audit["last_requested_date_present"]:
        print(f"WARNING: requested last date {LAST_REQUESTED_DATE} was not returned.")
    print(flush=True)


def main() -> int:
    """Run acquisition and audit only; fail visibly and keep anomalies in raw."""
    print_section("PHASE 1 - DATA ACQUISITION & AUDIT")
    print(
        f"Requested: {START_DATE} to {LAST_REQUESTED_DATE} (end={END_DATE}, exclusive)"
    )
    assets: dict[str, pd.DataFrame] = {}
    audits: list[dict[str, object]] = []
    manifest: list[dict[str, object]] = []
    raw_files_created = False
    audit_completed = False
    critical_failures = False
    run_utc = datetime.now(timezone.utc).isoformat()
    try:
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_TABLES_DIR.mkdir(parents=True, exist_ok=True)
        # Keep yfinance's generated timezone/cookie cache inside the ignored workspace.
        yf.set_tz_cache_location(str(PROJECT_ROOT / ".cache" / "yfinance"))
        for ticker in TICKERS:
            print(f"\nDownloading {ticker}...", flush=True)
            data = download_asset(ticker)
            path = RAW_DATA_DIR / f"{ticker}_raw.csv"
            write_csv(data, path, include_index=True)
            assets[ticker] = data
            audit = audit_asset(data, ticker)
            audits.append(audit)
            print_asset_audit(audit)
            manifest.append(
                {
                    "ticker": ticker,
                    "file_name": path.name,
                    "rows": audit["rows"],
                    "first_date": audit["first_date"],
                    "last_date": audit["last_date"],
                    "sha256": compute_file_sha256(path),
                    "downloaded_at_utc": run_utc,
                    "requested_start": START_DATE,
                    "requested_end_exclusive": END_DATE,
                    "python_version": platform.python_version(),
                    "yfinance_version": yf.__version__,
                    "pandas_version": pd.__version__,
                    "numpy_version": np.__version__,
                }
            )
        raw_files_created = True
        calendars = compare_calendars(assets)
        write_csv(pd.DataFrame(manifest), OUTPUT_TABLES_DIR / "phase1_raw_manifest.csv")
        write_csv(pd.DataFrame(audits), OUTPUT_TABLES_DIR / "phase1_asset_audit.csv")
        write_csv(calendars, OUTPUT_TABLES_DIR / "phase1_calendar_audit.csv")
        audit_completed = True
        critical_failures = any(
            audit["critical_validation_failures"] for audit in audits
        )
        print_section("CALENDAR COMPARISON")
        print(calendars.to_string(index=False))
        if critical_failures:
            print(
                "ERROR: critical integrity anomalies detected; retained in raw for review."
            )
    except (AcquisitionError, OSError) as exc:
        critical_failures = True
        print(f"\nERROR: {exc}", file=sys.stderr, flush=True)
        print(
            "Partial files may remain. Existing reports are valid only for their manifest."
        )
    print_section("PHASE 1 STATUS")
    for label, flag in [
        ("Raw files created (all three this run)", raw_files_created),
        ("Audit completed", audit_completed),
        ("Critical validation failures", critical_failures),
    ]:
        print(f"{label}: {'YES' if flag else 'NO'}")
    return 1 if critical_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
