"""Synthetic fixtures test integrity logic; they are not market-data results."""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "python" / "00_data_acquisition.py"
SPEC = importlib.util.spec_from_file_location("data_acquisition", SCRIPT)
acquisition = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acquisition)


@pytest.fixture
def sample():
    """Small artificial daily data; never written to raw or report directories."""
    return pd.DataFrame(
        [[10.0, 12.0, 9.0, 11.0, 11.0, 100], [11.0, 13.0, 10.0, 12.0, 12.0, 200]],
        columns=acquisition.EXPECTED_COLUMNS,
        index=pd.DatetimeIndex(["2018-01-03", "2018-01-02"], tz="America/New_York"),
    )


@pytest.mark.parametrize("ticker_level", [None, 0, 1])
def test_normalization_preserves_values_missing_rows_and_duplicates(
    sample, ticker_level
):
    sample.iloc[0, 0] = np.nan
    sample = pd.concat([sample, sample.iloc[[0]]])
    if ticker_level is not None:
        columns = [("NVDA", column) for column in sample.columns]
        if ticker_level == 1:
            columns = [(column, ticker) for ticker, column in columns]
        sample.columns = pd.MultiIndex.from_tuples(columns)
    result = acquisition.normalize_download(sample, "NVDA")
    assert len(result) == 3
    assert result.index.tz is None
    assert result.index.name == "Date"
    assert result.index.strftime("%Y-%m-%d").tolist() == [
        "2018-01-02",
        "2018-01-03",
        "2018-01-03",
    ]
    assert result["Open"].isna().sum() == 2
    assert result["Volume"].tolist() == [200, 100, 100]
    assert result.columns.tolist() == acquisition.EXPECTED_COLUMNS


@pytest.mark.parametrize(
    "problem", ["missing_column", "wrong_ticker", "bad_date", "numeric_index"]
)
def test_reject_invalid_structure(sample, problem):
    if problem == "missing_column":
        sample = sample.drop(columns="Adj Close")
    elif problem == "wrong_ticker":
        sample.columns = pd.MultiIndex.from_product([sample.columns, ["AMD"]])
    elif problem == "bad_date":
        sample.index = pd.Index(["2018-01-02", "bad date"])
    else:
        sample.index = pd.RangeIndex(2)
    with pytest.raises(acquisition.AcquisitionError, match="NVDA"):
        acquisition.normalize_download(sample, "NVDA")


def test_audit_counts_anomalies_without_modifying_data(sample):
    data = acquisition.normalize_download(sample, "NVDA")
    data.iloc[0] = [10, 8, 12, 11, 0, -1]
    data.iloc[1] = [np.nan, np.inf, 10, 12, 12, 0]
    data.index = pd.DatetimeIndex(["2018-01-02", "2018-01-02"], name="Date")
    original = data.copy(deep=True)
    audit = acquisition.audit_asset(data, "NVDA")
    for key in [
        "missing_total",
        "duplicate_dates",
        "infinite_values",
        "nonpositive_prices",
        "negative_volume",
        "zero_volume",
        "high_below_low",
        "invalid_high",
        "invalid_low",
        "incomplete_ohlc_rows",
    ]:
        assert audit[key] == 1, key
    assert audit["critical_validation_failures"] is True
    pd.testing.assert_frame_equal(data, original)


def test_calendar_comparison_uses_observed_dates_and_keeps_assets(sample):
    data = acquisition.normalize_download(sample, "NVDA")
    assets = {"NVDA": data, "AMD": data.iloc[[0]], "SOXX": data.iloc[[1]]}
    audit = acquisition.compare_calendars(assets).set_index("ticker")
    assert audit["union_dates"].tolist() == [2, 2, 2]
    assert audit["common_dates"].tolist() == [0, 0, 0]
    assert audit["missing_from_union"].tolist() == [0, 1, 1]
    assert audit["unique_to_asset"].tolist() == [0, 0, 0]
    assert [len(asset) for asset in assets.values()] == [2, 1, 1]


def test_download_retains_nan_rows_and_explicit_parameters(sample, monkeypatch):
    sample.iloc[0] = np.nan

    def fake_download(ticker, **kwargs):
        assert ticker == "NVDA"
        assert kwargs["start"] == "2018-01-01"
        assert kwargs["end"] == "2026-10-03"
        assert kwargs["keepna"] is True
        for flag in [
            "auto_adjust",
            "actions",
            "progress",
            "threads",
            "repair",
            "rounding",
        ]:
            assert kwargs[flag] is False
        return sample

    monkeypatch.setattr(acquisition.yf, "download", fake_download)
    result = acquisition.download_asset("NVDA")
    assert len(result) == 2
    assert result.isna().all(axis=1).sum() == 1


def test_empty_download_fails_explicitly(monkeypatch):
    monkeypatch.setattr(
        acquisition.yf, "download", lambda *args, **kwargs: pd.DataFrame()
    )
    with pytest.raises(acquisition.AcquisitionError, match="NVDA.*no observations"):
        acquisition.download_asset("NVDA")
