"""Offline synthetic fixtures exercise preparation without production files."""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "python" / "01_data_preparation.py"
SPEC = importlib.util.spec_from_file_location("data_preparation", SCRIPT)
preparation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preparation)


def asset(dates: list[str]) -> pd.DataFrame:
    """Build small artificial observations; never use Yahoo or production CSVs."""
    size = len(dates)
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(dates),
            "Open": [10.0] * size,
            "High": [12.0] * size,
            "Low": [9.0] * size,
            "Close": [11.0] * size,
            "Adj Close": [10.123456789012345] * size,
            "Volume": [100] * size,
        }
    )


@pytest.fixture
def assets():
    return {
        ticker: asset(["2020-01-02", "2020-01-03"]) for ticker in preparation.TICKERS
    }


def write_raw_manifest(tmp_path: Path) -> pd.DataFrame:
    records = []
    for ticker in preparation.TICKERS:
        data = asset(["2020-01-02", "2020-01-03"])
        path = tmp_path / f"{ticker}_raw.csv"
        data.to_csv(path, index=False, date_format="%Y-%m-%d")
        records.append(
            {
                "ticker": ticker,
                "file_name": path.name,
                "rows": len(data),
                "first_date": "2020-01-02",
                "last_date": "2020-01-03",
                "sha256": preparation.compute_sha256(path),
            }
        )
    return pd.DataFrame(records)


@pytest.mark.parametrize("ticker", ["NVDA", "AMD", "SOXX"])
def test_prefix_names_and_values_are_preserved(assets, ticker):
    original = assets[ticker].copy(deep=True)
    result = preparation.prefix_asset_columns(assets[ticker], ticker)
    assert result.columns.tolist() == [
        "Date",
        f"{ticker}_Open",
        f"{ticker}_High",
        f"{ticker}_Low",
        f"{ticker}_Close",
        f"{ticker}_Adj_Close",
        f"{ticker}_Volume",
    ]
    pd.testing.assert_frame_equal(assets[ticker], original)
    pd.testing.assert_frame_equal(result.set_axis(original.columns, axis=1), original)


def test_identical_calendars_keep_all_dates_and_have_deterministic_schema(assets):
    # Input mapping and raw-column order must not change the canonical schema.
    reordered = {
        ticker: assets[ticker].loc[:, list(reversed(preparation.RAW_COLUMNS))]
        for ticker in reversed(preparation.TICKERS)
    }
    data, audit = preparation.build_aligned_dataset(reordered)
    assert data.columns.tolist() == preparation.CANONICAL_COLUMNS
    assert data.shape == (2, 19)
    assert data["Date"].is_monotonic_increasing
    assert not data["Date"].duplicated().any()
    assert audit["common_dates"] == audit["union_dates"] == 2
    assert all(
        audit[f"{ticker.lower()}_dates_dropped"] == 0 for ticker in preparation.TICKERS
    )
    for ticker in preparation.TICKERS:
        expected = preparation.prefix_asset_columns(assets[ticker], ticker)
        pd.testing.assert_frame_equal(data[expected.columns], expected)


def test_different_calendars_use_only_intersection_and_measure_losses():
    assets = {
        "NVDA": asset(["2020-01-02", "2020-01-03", "2020-01-06"]),
        "AMD": asset(["2020-01-03", "2020-01-06", "2020-01-07"]),
        "SOXX": asset(["2020-01-03", "2020-01-06"]),
    }
    original = {ticker: data.copy(deep=True) for ticker, data in assets.items()}
    result, audit = preparation.build_aligned_dataset(assets)
    assert result["Date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2020-01-03",
        "2020-01-06",
    ]
    assert audit["union_dates"] == 4
    assert audit["common_dates"] == 2
    assert [
        audit[f"{ticker.lower()}_dates_dropped"] for ticker in preparation.TICKERS
    ] == [1, 1, 0]
    for ticker in preparation.TICKERS:
        pd.testing.assert_frame_equal(assets[ticker], original[ticker])


@pytest.mark.parametrize(
    "problem, message",
    [
        ("missing_column", "columns"),
        ("extra_column", "columns"),
        ("duplicate_dates", "duplicate dates"),
        ("unsorted", "chronologically sorted"),
        ("missing_value", "missing values"),
        ("string_prices", "real numeric"),
        ("invalid_date", "valid timezone-free datetimes"),
        ("empty", "zero observations"),
    ],
)
def test_invalid_raw_fails_without_repair(assets, problem, message):
    data = assets["NVDA"].copy()
    if problem == "missing_column":
        data = data.drop(columns="Adj Close")
    elif problem == "extra_column":
        data["unexpected"] = 1
    elif problem == "duplicate_dates":
        data.loc[1, "Date"] = data.loc[0, "Date"]
    elif problem == "unsorted":
        data = data.iloc[::-1]
    elif problem == "missing_value":
        data.loc[0, "Open"] = float("nan")
    elif problem == "string_prices":
        data["Open"] = ["invalid", "invalid"]
    elif problem == "invalid_date":
        data["Date"] = ["invalid", "invalid"]
    else:
        data = data.iloc[:0]
    with pytest.raises(preparation.PreparationError, match=message):
        preparation.validate_raw_asset(data, "NVDA")


def test_empty_intersection_is_critical():
    assets = {
        ticker: asset([f"2020-01-0{position + 2}"])
        for position, ticker in enumerate(preparation.TICKERS)
    }
    with pytest.raises(preparation.PreparationError, match="Empty intersection"):
        preparation.build_aligned_dataset(assets)


def test_missing_raw_error_is_actionable(tmp_path):
    with pytest.raises(
        preparation.PreparationError,
        match="Raw data missing. Run python/00_data_acquisition.py first.",
    ):
        preparation.load_raw_asset("NVDA", tmp_path)


def test_raw_hash_verification_detects_changed_bytes(tmp_path):
    manifest = write_raw_manifest(tmp_path)
    verified = preparation.verify_raw_integrity(manifest, tmp_path)
    assert verified == dict(zip(manifest["ticker"], manifest["sha256"], strict=True))
    path = tmp_path / "AMD_raw.csv"
    path.write_bytes(path.read_bytes() + b"\n")
    actual = preparation.compute_sha256(path)
    expected = manifest.loc[manifest["ticker"] == "AMD", "sha256"].iloc[0]
    with pytest.raises(preparation.PreparationError) as error:
        preparation.verify_raw_integrity(manifest, tmp_path)
    assert all(
        value in str(error.value)
        for value in ["AMD", expected, actual, "Rerun Phase 1"]
    )


def test_manifest_rejects_ambiguous_or_invalid_records(tmp_path):
    manifest = write_raw_manifest(tmp_path)
    path = tmp_path / "manifest.csv"
    manifest.to_csv(path, index=False)
    assert (
        preparation.load_phase1_manifest(path)["ticker"].tolist() == preparation.TICKERS
    )
    manifest.loc[1, "ticker"] = "NVDA"
    manifest.to_csv(path, index=False)
    with pytest.raises(preparation.PreparationError, match="exactly once"):
        preparation.load_phase1_manifest(path)


def test_read_csv_rejects_unparseable_date_and_metadata_mismatch(tmp_path):
    manifest = write_raw_manifest(tmp_path)
    data = preparation.load_raw_asset("NVDA", tmp_path)
    record = manifest.iloc[0].to_dict()
    preparation.validate_raw_asset(data, "NVDA", record)
    record["rows"] += 1
    with pytest.raises(preparation.PreparationError, match="rows differs"):
        preparation.validate_raw_asset(data, "NVDA", record)
    path = tmp_path / "NVDA_raw.csv"
    path.write_text(
        path.read_text().replace("2020-01-02", "invalid-date"), encoding="utf-8"
    )
    with pytest.raises(preparation.PreparationError, match="parse Date"):
        preparation.load_raw_asset("NVDA", tmp_path)


def test_final_audit_detects_ohlc_infinity_and_negative_volume(assets):
    data, _ = preparation.build_aligned_dataset(assets)
    data.loc[0, ["NVDA_High", "NVDA_Low", "NVDA_Volume"]] = [8, 12, -1]
    data.loc[1, "SOXX_Adj_Close"] = float("inf")
    original = data.copy(deep=True)
    audit = preparation.audit_aligned_dataset(data)
    assert audit["invalid_ohlc_total"] == audit["nvda_invalid_ohlc_rows"] == 1
    assert audit["negative_volume_total"] == 1
    assert audit["infinite_values"] == 1
    pd.testing.assert_frame_equal(data, original)
    with pytest.raises(
        preparation.PreparationError, match="Canonical validation failed"
    ):
        preparation.validate_aligned_dataset(audit)


def test_saved_csv_preserves_precision_and_is_byte_deterministic(assets, tmp_path):
    data, _ = preparation.build_aligned_dataset(assets)
    path = tmp_path / "market_aligned.csv"
    preparation.save_processed_dataset(data, path)
    first_hash = preparation.compute_sha256(path)
    preparation.save_processed_dataset(data, path)
    assert preparation.compute_sha256(path) == first_hash
    saved = pd.read_csv(path, float_precision="round_trip")
    saved["Date"] = pd.to_datetime(saved["Date"], format="%Y-%m-%d")
    pd.testing.assert_frame_equal(data, saved, check_exact=True)
    assert saved.columns.tolist() == preparation.CANONICAL_COLUMNS
    assert "Unnamed: 0" not in saved.columns
