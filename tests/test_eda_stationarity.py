"""Offline synthetic fixtures; no market files, Internet or precise random p-values."""

import importlib.util
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from statsmodels.tools.sm_exceptions import InterpolationWarning

SCRIPT = Path(__file__).resolve().parents[1] / "python/01_data_eda.py"
SPEC = importlib.util.spec_from_file_location("eda_stationarity", SCRIPT)
eda = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(eda)


@pytest.fixture
def canonical():
    rng = np.random.default_rng(42)
    size = 120
    data = pd.DataFrame({"Date": pd.bdate_range("2020-01-02", periods=size)})
    for ticker in eda.TICKERS:
        price = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.015, size)))
        for field in eda.FIELDS:
            data[f"{ticker}_{field}"] = (
                rng.integers(100, 1000, size) if field == "Volume" else price.copy()
            )
    return data


def test_log_price_and_return_units_and_structural_na():
    prices = pd.Series([10.0, 11.0, 9.0])
    np.testing.assert_allclose(eda.log_price(prices), np.log([10, 11, 9]))
    result = eda.log_return(prices)
    assert np.isnan(result.iloc[0])
    np.testing.assert_allclose(
        result.iloc[1:], [100 * np.log(1.1), 100 * np.log(9 / 11)]
    )
    with pytest.raises(eda.EDAError, match="positive"):
        eda.log_price(pd.Series([10.0, 0.0]))


@pytest.mark.parametrize(
    "values,expected",
    [([100.0, 110.0, 99.0], [10.0, -10.0]), ([100.0, 200.0, 50.0], [100.0, -75.0])],
)
def test_percentage_return_and_volume_change(values, expected):
    result = eda.percentage_change(pd.Series(values))
    assert pd.isna(result.iloc[0])
    np.testing.assert_allclose(result.iloc[1:], expected)


def test_missing_values_and_zero_denominator_are_never_filled():
    result = eda.percentage_change(pd.Series([10.0, np.nan, 20.0, 0.0, 5.0]))
    assert result.isna().tolist() == [True, True, True, False, True]
    assert result.iloc[3] == -100


def test_rolling_volatility_sample_std_annualized_and_trailing():
    returns = pd.Series([np.nan, 1.0, -1.0, 3.0, 2.0])
    result = eda.rolling_volatility(returns, window=3)
    assert result.iloc[:3].isna().all()
    expected = np.std([0.01, -0.01, 0.03], ddof=1) * np.sqrt(252) * 100
    assert result.iloc[3] == pytest.approx(expected)
    returns.iloc[4] = 999
    assert eda.rolling_volatility(returns, 3).iloc[3] == result.iloc[3]


def test_features_preserve_original_values_rows_and_initial_na(canonical):
    original = canonical.copy(deep=True)
    result = eda.financial_features(canonical)
    pd.testing.assert_frame_equal(canonical, original)
    pd.testing.assert_frame_equal(result[canonical.columns], original)
    assert result.columns.tolist() == eda.CANONICAL_COLUMNS + [
        f"{t}_{d}" for t in eda.TICKERS for d in eda.DERIVED
    ]
    for ticker in eda.TICKERS:
        assert result[f"{ticker}_Log_Price"].isna().sum() == 0
        assert result[f"{ticker}_Log_Return"].isna().sum() == 1
        assert result[f"{ticker}_Rolling_Vol_20D"].isna().sum() == 20
        np.testing.assert_allclose(
            result[f"{ticker}_Volume_Change_Pct"].iloc[1:],
            100
            * (
                original[f"{ticker}_Volume"].to_numpy()[1:]
                / original[f"{ticker}_Volume"].to_numpy()[:-1]
                - 1
            ),
        )


@pytest.mark.parametrize("size", [10, 11, 21])
def test_split_uses_canonical_dates_floor_and_has_no_overlap(size):
    data = pd.DataFrame(
        {
            "Date": pd.bdate_range("2020-01-02", periods=size),
            "return": [np.nan] + list(range(size - 1)),
        }
    )
    train, test, meta = eda.chronological_split(data)
    assert len(train) == int(np.floor(0.9 * size))
    assert len(test) == size - len(train)
    assert train.Date.max() < test.Date.min()
    assert not train.Date.isin(test.Date).any()
    assert pd.isna(train["return"].iloc[0])
    pd.testing.assert_frame_equal(pd.concat([train, test]), data)
    assert meta.split_method.iloc[0] == "chronological_90_10_holdout"


@pytest.mark.parametrize("problem", ["unsorted", "duplicate", "missing", "one_row"])
def test_split_rejects_invalid_chronology(problem):
    data = pd.DataFrame({"Date": pd.bdate_range("2020-01-02", periods=10)})
    if problem == "unsorted":
        data = data.iloc[::-1]
    elif problem == "duplicate":
        data.loc[1, "Date"] = data.loc[0, "Date"]
    elif problem == "missing":
        data.loc[0, "Date"] = pd.NaT
    else:
        data = data.iloc[:1]
    with pytest.raises(eda.EDAError):
        eda.chronological_split(data)


@pytest.mark.parametrize("test_name", ["adf_test", "kpss_test"])
@pytest.mark.parametrize("regression", ["c", "ct"])
def test_stationarity_functions_schema_and_decisions(canonical, test_name, regression):
    result = getattr(eda, test_name)(
        canonical.NVDA_Adj_Close, "NVDA", "Adj_Close", regression
    )
    assert set(result) == set(eda.TEST_COLUMNS)
    assert result["scope"] == "train"
    assert result["regression"] == regression
    assert 0 <= result["p_value"] <= 1
    assert result["nobs"] <= len(canonical)
    assert {"1%", "5%", "10%"}.issubset(json.loads(result["critical_values"]))
    if test_name == "adf_test":
        expected = "reject_H0" if result["p_value"] < 0.05 else "fail_to_reject_H0"
    else:
        expected = (
            "reject_stationarity"
            if result["p_value"] < 0.05
            else "fail_to_reject_stationarity"
        )
    assert result["decision_5pct"] == expected


@pytest.mark.parametrize(
    "direction,p,bound",
    [
        ("smaller", 0.01, "actual_p_smaller_than_reported"),
        ("greater", 0.1, "actual_p_greater_than_reported"),
    ],
)
def test_kpss_boundary_warnings_are_recorded(
    canonical, monkeypatch, direction, p, bound
):
    def fake_kpss(*args, **kwargs):
        warnings.warn(
            f"The actual p-value is {direction} than the p-value returned.",
            InterpolationWarning,
        )
        return 0.2, p, 2, {"1%": 0.7, "5%": 0.4, "10%": 0.3}

    monkeypatch.setattr(eda, "kpss", fake_kpss)
    result = eda.kpss_test(canonical.NVDA_Adj_Close, "NVDA", "Adj_Close", "ct")
    assert direction in result["warnings"]
    assert result["p_value_bound"] == bound


def test_iqr_bounds_and_extremes_retained():
    s = pd.Series([np.nan, -2.0, -1.0, 0.0, 1.0, 2.0, 100.0])
    original = s.copy()
    row, mask = eda.iqr_outliers(s, "NVDA")
    assert row["Q1"] == -0.75
    assert row["Q3"] == 1.75
    assert row["lower_bound"] == -4.5
    assert row["upper_bound"] == 5.5
    assert row["outlier_count"] == 1
    assert row["outlier_pct"] == pytest.approx(100 / 6)
    assert mask.iloc[-1]
    pd.testing.assert_series_equal(s, original)


def test_rolling_correlations_use_full_past_windows():
    returns = pd.DataFrame(
        {
            "NVDA": [1.0, 2.0, 3.0, 4.0, 5.0],
            "AMD": [2.0, 4.0, 6.0, 8.0, 10.0],
            "SOXX": [-1.0, -2.0, -3.0, -4.0, -5.0],
        }
    )
    result = eda.rolling_correlations(returns, window=3)
    assert result.iloc[:2].isna().all().all()
    np.testing.assert_allclose(result.iloc[2:], [[1, -1, -1]] * 3, atol=1e-12)
    changed = returns.copy()
    changed.iloc[-1] = 100
    pd.testing.assert_frame_equal(
        result.iloc[:-1], eda.rolling_correlations(changed, 3).iloc[:-1]
    )


def test_tables_schemas_scopes_and_holdout_independence(canonical):
    full = eda.financial_features(canonical)
    train, test, split = eda.chronological_split(full)
    tables = eda.build_tables(train, full)
    assert tables["phase2_descriptive_stats"].columns.tolist() == eda.STAT_COLUMNS
    assert tables["phase2_stationarity_tests"].columns.tolist() == eda.TEST_COLUMNS
    assert len(tables["phase2_stationarity_tests"]) == 18
    assert len(tables["phase2_stationarity_summary"]) == 9
    assert set(tables["phase2_stationarity_summary"].mechanical_summary) <= {
        "stationary_supported",
        "nonstationary_supported",
        "mixed_evidence",
    }
    assert tables["phase2_return_correlation_train"].columns.tolist() == [
        "ticker",
        *eda.TICKERS,
    ]
    assert {"pair", "mean", "median", "min", "max", "std"} <= set(
        tables["phase2_rolling_correlation_summary"].columns
    )
    assert {
        "ticker",
        "lower_bound",
        "upper_bound",
        "outlier_count",
        "outlier_pct",
    } <= set(tables["phase2_outlier_summary"].columns)
    assert {"weekday", "ticker", "mean", "median", "std", "count"} <= set(
        tables["phase2_weekday_returns"].columns
    )
    assert len(tables["phase2_extreme_returns"]) == 30
    assert tables["phase2_extreme_returns"].Date.max() <= train.Date.max()
    for name, table in tables.items():
        if "scope" in table and name != "phase2_descriptive_stats":
            assert set(table.scope) == {"train"}
    changed = canonical.copy()
    changed.loc[test.index, eda.CANONICAL_COLUMNS[1:]] *= 10
    changed_full = eda.financial_features(changed)
    changed_tables = eda.build_tables(changed_full.iloc[: len(train)], changed_full)
    for name, table in tables.items():
        if name == "phase2_descriptive_stats":
            pd.testing.assert_frame_equal(
                table.loc[table.scope == "train"],
                changed_tables[name].loc[changed_tables[name].scope == "train"],
            )
        else:
            pd.testing.assert_frame_equal(table, changed_tables[name])
    checks = eda.leakage_checks(canonical, full, train, test)
    assert checks.columns.tolist() == ["check", "status", "details"]
    assert set(checks.status) == {"PASS"}
    assert split.total_rows.iloc[0] == len(canonical)
    assert test.NVDA_Log_Return.iloc[0] == pytest.approx(
        100 * np.log(test.NVDA_Adj_Close.iloc[0] / train.NVDA_Adj_Close.iloc[-1])
    )


def write_synthetic_input(canonical, tmp_path):
    path = tmp_path / "market_aligned.csv"
    manifest = tmp_path / "manifest.csv"
    eda.save_csv(canonical, path)
    eda.save_csv(
        pd.DataFrame(
            [
                {
                    "file_name": path.name,
                    "rows": len(canonical),
                    "columns": len(canonical.columns),
                    "first_date": canonical.Date.iloc[0],
                    "last_date": canonical.Date.iloc[-1],
                    "sha256": eda.sha256(path),
                }
            ]
        ),
        manifest,
    )
    return path, manifest


def test_canonical_manifest_hash_guard(canonical, tmp_path):
    path, manifest = write_synthetic_input(canonical, tmp_path)
    loaded, digest = eda.load_canonical(path, manifest)
    pd.testing.assert_frame_equal(canonical, loaded)
    assert digest == eda.sha256(path)
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(eda.EDAError, match="SHA-256 mismatch"):
        eda.load_canonical(path, manifest)


def test_offline_pipeline_output_schemas(canonical, tmp_path, monkeypatch):
    processed = tmp_path / "data/processed"
    processed.mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    path, manifest = write_synthetic_input(canonical, processed)
    table_dir = tmp_path / "outputs/tables"
    table_dir.mkdir(parents=True)
    manifest.rename(table_dir / "phase1_5_processed_manifest.csv")
    source_bytes = path.read_bytes()
    monkeypatch.setattr(eda, "ROOT", tmp_path)
    monkeypatch.setattr(eda, "generate_figures", lambda *args: [])
    assert eda.main() == 0
    assert path.read_bytes() == source_bytes
    feature = pd.read_csv(processed / "market_features.csv")
    assert feature.shape == (len(canonical), 34)
    feature_manifest = pd.read_csv(table_dir / "phase2_feature_manifest.csv")
    assert {
        "file_name",
        "rows",
        "columns",
        "first_date",
        "last_date",
        "sha256",
        "derived_variable_count",
        "notes",
    } <= set(feature_manifest.columns)
    assert feature_manifest.sha256.iloc[0] == eda.sha256(
        processed / "market_features.csv"
    )
    assert feature_manifest.derived_variable_count.iloc[0] == 15
    assert len(list(table_dir.glob("phase2_*.csv"))) == 12
    assert (tmp_path / "docs/phase2_eda_stationarity.md").exists()
