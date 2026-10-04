"""
AI-Chip Market Intelligence
Phase 1.5 — Canonical Dataset Preparation

This script builds the canonical aligned multivariate dataset
from the validated raw Yahoo Finance files.

No feature engineering, statistical transformation or modeling
is performed in this phase.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
PHASE1_MANIFEST = OUTPUT_TABLES_DIR / "phase1_raw_manifest.csv"
TICKERS = ["NVDA", "AMD", "SOXX"]
MARKET_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
RAW_COLUMNS = ["Date", *MARKET_COLUMNS]
CANONICAL_COLUMNS = [
    "Date",
    *[
        f"{ticker}_{column.replace(' ', '_')}"
        for ticker in TICKERS
        for column in MARKET_COLUMNS
    ],
]
ALIGNMENT_METHOD = "inner_join_on_common_trading_dates"


class PreparationError(RuntimeError):
    """Integrity, schema, alignment or I/O failure requiring explicit review."""


def compute_sha256(path: Path) -> str:
    """Hash the bytes of a saved file without altering it."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise PreparationError(f"Cannot read/hash {path.name}: {exc}") from exc
    return digest.hexdigest()


def load_phase1_manifest(path: Path = PHASE1_MANIFEST) -> pd.DataFrame:
    """Require one unambiguous validated raw-file record per official ticker."""
    if not path.is_file():
        raise PreparationError(
            "Phase 1 manifest missing. Run python/00_data_acquisition.py first."
        )
    try:
        manifest = pd.read_csv(path)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        raise PreparationError(f"Cannot read Phase 1 manifest: {exc}") from exc
    required = ["ticker", "file_name", "rows", "first_date", "last_date", "sha256"]
    if not set(required).issubset(manifest.columns):
        raise PreparationError(f"Phase 1 manifest requires columns {required}.")
    if manifest[required].isna().any().any():
        raise PreparationError("Phase 1 manifest contains missing required values.")
    if len(manifest) != len(TICKERS) or set(manifest["ticker"]) != set(TICKERS):
        raise PreparationError(
            "Phase 1 manifest must contain NVDA, AMD and SOXX exactly once."
        )
    for record in manifest.to_dict("records"):
        ticker = record["ticker"]
        if record["file_name"] != f"{ticker}_raw.csv":
            raise PreparationError(
                f"{ticker}: unexpected raw file name in Phase 1 manifest."
            )
        if not re.fullmatch(r"[0-9a-f]{64}", str(record["sha256"])):
            raise PreparationError(f"{ticker}: invalid SHA-256 in Phase 1 manifest.")
        try:
            rows = float(record["rows"])
            dates = pd.to_datetime(
                [record["first_date"], record["last_date"]], format="%Y-%m-%d"
            )
            if rows <= 0 or not rows.is_integer() or dates[0] > dates[1]:
                raise ValueError("invalid row count or date bounds")
        except (TypeError, ValueError, OverflowError) as exc:
            raise PreparationError(
                f"{ticker}: invalid Phase 1 manifest metadata: {exc}"
            ) from exc
    return manifest.set_index("ticker", drop=False).loc[TICKERS].reset_index(drop=True)


def verify_raw_integrity(
    manifest: pd.DataFrame, raw_dir: Path = RAW_DATA_DIR
) -> dict[str, str]:
    """Stop on missing raw or a mismatch with the Phase 1 file fingerprints."""
    hashes = {}
    records = manifest.set_index("ticker")
    for ticker in TICKERS:
        path = raw_dir / f"{ticker}_raw.csv"
        if not path.is_file():
            raise PreparationError(
                "Raw data missing. Run python/00_data_acquisition.py first."
            )
        expected = records.loc[ticker, "sha256"]
        current = compute_sha256(path)
        if current != expected:
            raise PreparationError(
                f"{ticker}: raw SHA-256 mismatch. Expected: {expected}. Actual: {current}. "
                "Rerun Phase 1 (python/00_data_acquisition.py) and review its validation."
            )
        hashes[ticker] = current
    return hashes


def load_raw_asset(ticker: str, raw_dir: Path = RAW_DATA_DIR) -> pd.DataFrame:
    """Read a local CSV at round-trip float precision; never download or rewrite raw."""
    path = raw_dir / f"{ticker}_raw.csv"
    if not path.is_file():
        raise PreparationError(
            "Raw data missing. Run python/00_data_acquisition.py first."
        )
    try:
        data = pd.read_csv(path, dtype={"Date": "string"}, float_precision="round_trip")
        if "Date" not in data.columns:
            raise PreparationError(f"{ticker}: required Date column missing.")
        data["Date"] = pd.to_datetime(data["Date"], format="%Y-%m-%d", errors="raise")
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        raise PreparationError(
            f"{ticker}: cannot read raw CSV or parse Date: {exc}"
        ) from exc
    validate_raw_asset(data, ticker)
    return data.loc[:, RAW_COLUMNS]


def validate_raw_asset(
    data: pd.DataFrame, ticker: str, manifest_record: dict[str, object] | None = None
) -> None:
    """Reject invalid inputs explicitly; do not sort, remove or impute raw rows."""
    if data.empty:
        raise PreparationError(f"{ticker}: raw data has zero observations.")
    if len(data.columns) != len(RAW_COLUMNS) or set(data.columns) != set(RAW_COLUMNS):
        raise PreparationError(f"{ticker}: raw columns must be exactly {RAW_COLUMNS}.")
    if not pd.api.types.is_datetime64_dtype(data["Date"]):
        raise PreparationError(
            f"{ticker}: Date must contain valid timezone-free datetimes."
        )
    if data.isna().any().any():
        raise PreparationError(
            f"{ticker}: raw data contains missing values; review Phase 1."
        )
    if (data["Date"] != data["Date"].dt.normalize()).any():
        raise PreparationError(f"{ticker}: intraday timestamps in daily raw data.")
    if data["Date"].duplicated().any():
        raise PreparationError(f"{ticker}: duplicate dates; review Phase 1.")
    if not data["Date"].is_monotonic_increasing:
        raise PreparationError(f"{ticker}: raw dates are not chronologically sorted.")
    invalid_types = [
        column
        for column in MARKET_COLUMNS
        if not pd.api.types.is_numeric_dtype(data[column])
        or pd.api.types.is_bool_dtype(data[column])
        or pd.api.types.is_complex_dtype(data[column])
    ]
    if invalid_types:
        raise PreparationError(
            f"{ticker}: market columns must be real numeric: {invalid_types}."
        )
    if manifest_record is not None:
        actual = {
            "rows": len(data),
            "first_date": data["Date"].iloc[0].strftime("%Y-%m-%d"),
            "last_date": data["Date"].iloc[-1].strftime("%Y-%m-%d"),
        }
        for key, value in actual.items():
            if value != manifest_record[key]:
                raise PreparationError(
                    f"{ticker}: {key} differs from Phase 1 manifest."
                )


def prefix_asset_columns(data: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Retain Date and prefix each financial field, using Adj_Close in wide format."""
    validate_raw_asset(data, ticker)
    return data.loc[:, RAW_COLUMNS].rename(
        columns={
            column: f"{ticker}_{column.replace(' ', '_')}" for column in MARKET_COLUMNS
        }
    )


def build_aligned_dataset(
    assets: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Measure date losses before strict one-to-one inner joins in canonical order."""
    if set(assets) != set(TICKERS):
        raise PreparationError("Alignment requires exactly NVDA, AMD and SOXX.")
    for ticker in TICKERS:
        validate_raw_asset(assets[ticker], ticker)
    dates = {ticker: pd.DatetimeIndex(assets[ticker]["Date"]) for ticker in TICKERS}
    union_dates = dates[TICKERS[0]]
    common_dates = dates[TICKERS[0]]
    for ticker in TICKERS[1:]:
        union_dates = union_dates.union(dates[ticker])
        common_dates = common_dates.intersection(dates[ticker])
    alignment: dict[str, object] = {
        **{f"{ticker.lower()}_rows": len(assets[ticker]) for ticker in TICKERS},
        "union_dates": len(union_dates),
        "common_dates": len(common_dates),
    }
    for ticker in TICKERS:
        dropped = dates[ticker].difference(common_dates)
        alignment[f"{ticker.lower()}_dates_dropped"] = len(dropped)
        alignment[f"{ticker.lower()}_dropped_date_examples"] = json.dumps(
            dropped[:5].strftime("%Y-%m-%d").tolist()
        )
    if common_dates.empty:
        raise PreparationError(
            "Empty intersection: no trading dates common to all three assets."
        )
    aligned = prefix_asset_columns(assets[TICKERS[0]], TICKERS[0])
    for ticker in TICKERS[1:]:
        aligned = aligned.merge(
            prefix_asset_columns(assets[ticker], ticker),
            on="Date",
            how="inner",
            validate="one_to_one",
            sort=False,
        )
    aligned = (
        aligned.loc[:, CANONICAL_COLUMNS]
        .sort_values("Date", kind="stable")
        .reset_index(drop=True)
    )
    if not pd.DatetimeIndex(aligned["Date"]).equals(common_dates.sort_values()):
        raise PreparationError(
            "Alignment result differs from the measured date intersection."
        )
    return aligned, alignment


def audit_aligned_dataset(data: pd.DataFrame) -> dict[str, object]:
    """Count final structure and asset-session anomalies without changing any value."""
    if data.empty or data.columns.tolist() != CANONICAL_COLUMNS:
        raise PreparationError(
            "Canonical dataset is empty or its ordered schema is invalid."
        )
    missing = {column: int(data[column].isna().sum()) for column in data.columns}
    result: dict[str, object] = {
        "aligned_rows": len(data),
        "aligned_columns": len(data.columns),
        "first_date": data["Date"].min().strftime("%Y-%m-%d"),
        "last_date": data["Date"].max().strftime("%Y-%m-%d"),
        "missing_total": sum(missing.values()),
        "missing_by_column": json.dumps(missing),
        "duplicate_dates": int(data["Date"].duplicated().sum()),
        "chronological_order": bool(data["Date"].is_monotonic_increasing),
        "infinite_values": int(
            data[CANONICAL_COLUMNS[1:]].isin([float("inf"), -float("inf")]).sum().sum()
        ),
        "dates_retained": int(data["Date"].nunique()),
        "expected_columns_present": len(set(data.columns) & set(CANONICAL_COLUMNS)),
        "unexpected_columns": len(set(data.columns) - set(CANONICAL_COLUMNS)),
    }
    invalid_ohlc_total = negative_volume_total = nonpositive_prices_total = 0
    for ticker in TICKERS:
        high, low = data[f"{ticker}_High"], data[f"{ticker}_Low"]
        opening, close = data[f"{ticker}_Open"], data[f"{ticker}_Close"]
        invalid = (
            (high < low)
            | (high < opening)
            | (high < close)
            | (low > opening)
            | (low > close)
        )
        result[f"{ticker.lower()}_invalid_ohlc_rows"] = int(invalid.sum())
        invalid_ohlc_total += int(invalid.sum())
        negative_volume_total += int((data[f"{ticker}_Volume"] < 0).sum())
        prices = [
            f"{ticker}_{column.replace(' ', '_')}" for column in MARKET_COLUMNS[:-1]
        ]
        nonpositive_prices_total += int((data[prices] <= 0).sum().sum())
    result.update(
        {
            "invalid_ohlc_total": invalid_ohlc_total,
            "negative_volume_total": negative_volume_total,
            "nonpositive_prices_total": nonpositive_prices_total,
        }
    )
    return result


def validate_aligned_dataset(audit: dict[str, object]) -> None:
    """Refuse to publish a canonical dataset with critical integrity anomalies."""
    checks = [
        "missing_total",
        "duplicate_dates",
        "infinite_values",
        "unexpected_columns",
        "invalid_ohlc_total",
        "negative_volume_total",
        "nonpositive_prices_total",
    ]
    failures = [key for key in checks if audit[key]]
    if not audit["chronological_order"]:
        failures.append("chronological_order")
    if failures:
        raise PreparationError(
            f"Canonical validation failed: {', '.join(failures)}. No rows were repaired."
        )


def write_csv(data: pd.DataFrame, path: Path) -> None:
    """Write generated files deterministically, with full float representation."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(
            path,
            index=False,
            encoding="utf-8",
            date_format="%Y-%m-%d",
            lineterminator="\n",
        )
    except (OSError, ValueError) as exc:
        raise PreparationError(f"Cannot write {path.name}: {exc}") from exc


def save_processed_dataset(data: pd.DataFrame, path: Path) -> None:
    """Save only the ordered canonical schema and verify the actual CSV read back."""
    validate_aligned_dataset(audit_aligned_dataset(data))
    write_csv(data, path)
    try:
        saved = pd.read_csv(path, float_precision="round_trip")
        saved["Date"] = pd.to_datetime(saved["Date"], format="%Y-%m-%d", errors="raise")
        pd.testing.assert_frame_equal(
            data.reset_index(drop=True), saved, check_exact=True
        )
        validate_aligned_dataset(audit_aligned_dataset(saved))
    except (OSError, ValueError, AssertionError) as exc:
        raise PreparationError(
            f"Canonical CSV read-back verification failed: {exc}"
        ) from exc


def save_processed_manifest(path: Path, audit: dict[str, object]) -> str:
    """Record the saved dataset fingerprint and its exact Phase 1 source lineage."""
    sha256 = compute_sha256(path)
    phase1 = load_phase1_manifest()
    source_hashes = dict(zip(phase1["ticker"], phase1["sha256"], strict=True))
    row = {
        "dataset_name": "market_aligned",
        "file_name": path.name,
        "rows": audit["aligned_rows"],
        "columns": audit["aligned_columns"],
        "first_date": audit["first_date"],
        "last_date": audit["last_date"],
        "sha256": sha256,
        "source_assets": "|".join(TICKERS),
        "alignment_method": ALIGNMENT_METHOD,
        "source_raw_sha256": json.dumps(source_hashes),
        "phase1_manifest_sha256": compute_sha256(PHASE1_MANIFEST),
    }
    write_csv(
        pd.DataFrame([row]), OUTPUT_TABLES_DIR / "phase1_5_processed_manifest.csv"
    )
    return sha256


def save_alignment_audit(
    alignment: dict[str, object], audit: dict[str, object]
) -> None:
    """Save measured calendar losses and final validation counts as metric/value rows."""
    metrics = {**alignment, **audit}
    write_csv(
        pd.DataFrame(metrics.items(), columns=["metric", "value"]),
        OUTPUT_TABLES_DIR / "phase1_5_alignment_audit.csv",
    )


def print_section(title: str) -> None:
    """Keep terminal output readable for review."""
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}", flush=True)


def main() -> int:
    """Prepare validated local data only, stopping explicitly on any critical failure."""
    print_section("PHASE 1.5 - CANONICAL DATASET PREPARATION")
    hashes_verified = alignment_completed = canonical_validated = False
    critical_failures = False
    try:
        manifest = load_phase1_manifest()
        verify_raw_integrity(manifest)
        hashes_verified = True
        print_section("RAW INTEGRITY")
        for ticker in TICKERS:
            print(f"{ticker}: PASS")
        assets = {}
        for record in manifest.to_dict("records"):
            ticker = record["ticker"]
            assets[ticker] = load_raw_asset(ticker)
            validate_raw_asset(assets[ticker], ticker, record)
        aligned, alignment = build_aligned_dataset(assets)
        alignment_completed = True
        print_section("CALENDAR ALIGNMENT")
        for metric, value in alignment.items():
            print(f"{metric}: {value}")
        if any(alignment[f"{ticker.lower()}_dates_dropped"] for ticker in TICKERS):
            print(
                "WARNING: dates outside the intersection were excluded; see counts/examples above."
            )
        audit = audit_aligned_dataset(aligned)
        print_section("CANONICAL DATASET")
        for metric, value in audit.items():
            print(f"{metric}: {value}")
        validate_aligned_dataset(audit)
        # Verify source fingerprints again before writing the derived reference copy.
        verify_raw_integrity(manifest)
        path = PROCESSED_DATA_DIR / "market_aligned.csv"
        save_processed_dataset(aligned, path)
        sha256 = save_processed_manifest(path, audit)
        save_alignment_audit(alignment, audit)
        canonical_validated = True
        print(
            f"\nOutput: {path.relative_to(PROJECT_ROOT).as_posix()}\nSHA-256: {sha256}"
        )
    except (PreparationError, OSError, pd.errors.MergeError) as exc:
        critical_failures = True
        print(f"\nERROR: {exc}", file=sys.stderr, flush=True)
        print(
            "Existing generated files may belong to an earlier run; review their manifest."
        )
    print_section("PHASE 1.5 STATUS")
    for label, flag in [
        ("Raw hashes verified", hashes_verified),
        ("Alignment completed", alignment_completed),
        ("Canonical dataset validated", canonical_validated),
        ("Critical failures", critical_failures),
        ("Ready for Phase 2 review", canonical_validated and not critical_failures),
    ]:
        print(f"{label}: {'YES' if flag else 'NO'}")
    return 1 if critical_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
