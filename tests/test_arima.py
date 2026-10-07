"""Offline synthetic checks for Phase 3A; no network or market-data fixtures."""

import hashlib
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "python/02_arima.py"
SPEC = importlib.util.spec_from_file_location("arima_phase3a", SCRIPT)
arima = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(arima)


@pytest.fixture
def synthetic():
    rng = np.random.default_rng(2026)
    innovations = rng.normal(0.001, 0.02, 250)
    return np.exp(3 + np.cumsum(innovations))


@pytest.fixture
def frozen_root(tmp_path, synthetic):
    tables = tmp_path / "outputs/tables"
    tables.mkdir(parents=True)
    processed = tmp_path / "data/processed"
    processed.mkdir(parents=True)
    dates = pd.bdate_range("2020-01-02", periods=len(synthetic))
    y = np.log(synthetic)
    frame = pd.DataFrame(
        {
            "Date": dates,
            "NVDA_Adj_Close": synthetic,
            "NVDA_Log_Price": y,
            "NVDA_Log_Return": np.r_[np.nan, 100 * np.diff(y)],
        }
    )
    frame.to_csv(processed / "market_train.csv", index=False)
    pd.DataFrame(
        [
            {
                "train_rows": len(frame),
                "train_start": str(dates[0].date()),
                "train_end": str(dates[-1].date()),
            }
        ]
    ).to_csv(tables / "phase2_split_metadata.csv", index=False)
    pd.DataFrame(
        [
            {
                "train_sha256": hashlib.sha256(
                    (processed / "market_train.csv").read_bytes()
                ).hexdigest(),
            }
        ]
    ).to_csv(tables / "phase2_feature_manifest.csv", index=False)
    pd.DataFrame(
        {
            "ticker": ["NVDA", "NVDA"],
            "scope": ["train", "train"],
            "series": ["Log_Price", "Log_Return"],
            "mechanical_summary": ["nonstationary_supported", "stationary_supported"],
        }
    ).to_csv(tables / "phase2_stationarity_summary.csv", index=False)
    pd.DataFrame(
        {
            "ticker": ["NVDA"],
            "scope": ["train"],
            "series": ["Log_Price"],
        }
    ).to_csv(tables / "phase2_stationarity_tests.csv", index=False)
    pd.DataFrame({"status": ["PASS"]}).to_csv(
        tables / "phase2_leakage_check.csv", index=False
    )
    pd.DataFrame(
        {
            "ticker": ["NVDA"] * 5,
            "scope": ["train"] * 5,
            "weekday": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "mean": [0.1] * 5,
        }
    ).to_csv(tables / "phase2_weekday_returns.csv", index=False)
    return tmp_path


def test_log_transform_and_difference_units():
    prices = [10, 11, 9]
    y = arima.log_transform(prices)
    np.testing.assert_allclose(y, np.log(prices))
    np.testing.assert_allclose(arima.difference(y), [np.log(1.1), np.log(9 / 11)])
    assert len(arima.difference(y)) == len(prices) - 1


@pytest.mark.parametrize("bad", [[1, 0], [1, -1], [np.nan], [np.inf]])
def test_log_rejects_invalid_prices(bad):
    with pytest.raises(ValueError, match="positive"):
        arima.log_transform(bad)


def test_five_reasoned_candidates_have_frozen_d_and_drift_policy():
    assert arima.candidate_orders() == [
        (0, 1, 0, False),
        (0, 1, 0, True),
        (1, 1, 0, True),
        (0, 1, 1, True),
        (1, 1, 1, True),
    ]
    assert all(p <= 3 and q <= 3 and d == 1 for p, d, q, _ in arima.candidate_orders())


def test_aicc_formula_and_undefined_small_sample():
    assert arima.aicc(100, 50, 3) == pytest.approx(100 + 24 / 46)
    assert np.isinf(arima.aicc(100, 4, 3))


def test_load_train_checks_integrity_and_transformation(frozen_root, synthetic):
    data, dates, y, delta, audit, _ = arima.load_train(frozen_root)
    np.testing.assert_allclose(np.exp(y), synthetic)
    assert len(data) == len(dates) == len(y) == len(delta) + 1
    assert all(path in arima.INPUTS for path in audit)
    with (frozen_root / arima.TRAIN).open("a", encoding="utf-8") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match="SHA-256"):
        arima.load_train(frozen_root)


def test_disallowed_input_is_rejected_before_io(tmp_path, monkeypatch):
    def unexpected_read(*args, **kwargs):
        pytest.fail("Rejected input reached the CSV reader")

    monkeypatch.setattr(arima.pd, "read_csv", unexpected_read)
    with pytest.raises(ValueError, match="Unauthorized"):
        arima.read_input(tmp_path, "data/processed/market_test.csv", [])
    with pytest.raises(ValueError, match="Unauthorized"):
        arima.read_input(tmp_path, "data/processed/market_aligned.csv", [])


def test_residual_tests_structure_df_and_arch_output(synthetic):
    r = np.diff(np.log(synthetic))
    result = arima.residual_diagnostics(r, 1, 1, "synthetic")
    assert (
        result.test.tolist()
        == ["Ljung-Box", "Ljung-Box", "Jarque-Bera"] + ["ARCH-LM"] * 3
    )
    assert result.lag.tolist() == [10, 20, 0, 5, 10, 20]
    assert result.df.tolist() == [8, 18, 2, 5, 10, 20]
    assert result.nobs.eq(len(r)).all()
    assert result.scope.eq("train").all()
    assert result.p_value.between(0, 1).all()
    assert np.isfinite(result.statistic).all()
    assert result.reject_5pct.equals(result.p_value < 0.05)
    assert result.loc[result.test == "ARCH-LM", "model_df"].eq(0).all()


def test_real_synthetic_fit_reports_variance_parameter_and_diagnostics(synthetic):
    row, fit = arima.fit_candidate(np.log(synthetic), (0, 1, 0, True))
    assert fit is not None
    assert row["converged"]
    assert row["k"] == 2
    assert row["n_eff"] == len(synthetic) - 1
    assert np.isfinite(row["AICc"])
    assert 0 <= row["ljung_box_10"] <= 1


def selection_table():
    return pd.DataFrame(
        [
            {
                "model": "complex",
                "converged": True,
                "k": 7,
                "AICc": 100,
                "BIC": 130,
                "ljung_box_10": 0.2,
                "ljung_box_20": 0.2,
            },
            {
                "model": "simple",
                "converged": True,
                "k": 4,
                "AICc": 101.8,
                "BIC": 110,
                "ljung_box_10": 0.2,
                "ljung_box_20": 0.2,
            },
            {
                "model": "autocorrelated",
                "converged": True,
                "k": 1,
                "AICc": 90,
                "BIC": 95,
                "ljung_box_10": 0.001,
                "ljung_box_20": 0.001,
            },
            {
                "model": "failed",
                "converged": False,
                "k": 1,
                "AICc": 80,
                "BIC": 85,
                "ljung_box_10": 0.2,
                "ljung_box_20": 0.2,
            },
        ]
    )


def test_selection_is_deterministic_and_not_minimum_aic_only():
    table = selection_table()
    assert arima.select_candidate(table).model == "simple"
    assert arima.select_candidate(table.iloc[::-1]).model == "simple"
    with pytest.raises(RuntimeError, match="No converged"):
        arima.select_candidate(table.loc[~table.converged])


def test_selection_does_not_claim_whiteness_if_every_candidate_fails():
    table = selection_table().iloc[:2].copy()
    table[["ljung_box_10", "ljung_box_20"]] = 0.001
    result = arima.select_candidate(table)
    assert result.model == "simple"
    assert result.ljung_box_10 < 0.05


def test_fit_failure_is_recorded(synthetic, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("synthetic optimization failure")

    monkeypatch.setattr(arima, "ARIMA", fail)
    row, fit = arima.fit_candidate(np.log(synthetic), (1, 1, 1, True))
    assert fit is None
    assert not row["converged"]
    assert "synthetic optimization failure" in row["error"]


def test_automatic_search_explicitly_compares_drift_and_never_uses_validation(
    synthetic, monkeypatch
):
    calls = []
    y = np.log(synthetic)

    def fake_auto(values, **kwargs):
        np.testing.assert_array_equal(values, y)
        calls.append(kwargs)
        fit = arima.ARIMA(
            values, order=(0, 1, 0), trend="t" if kwargs["with_intercept"] else "n"
        ).fit()
        return [
            SimpleNamespace(
                arima_res_=fit,
                order=(0, 1, 0),
                seasonal_order=(0, 0, 0, 0),
                aic=lambda: fit.aic,
                aicc=lambda: fit.aicc,
                bic=lambda: fit.bic,
            )
        ]

    monkeypatch.setitem(sys.modules, "pmdarima", SimpleNamespace(auto_arima=fake_auto))
    table = arima.automatic_search(y)
    assert len(calls) == 2
    assert [c["with_intercept"] for c in calls] == [False, True]
    for call in calls:
        assert call["d"] == 1 and call["max_p"] == call["max_q"] == 3
        assert call["seasonal"] is call["stepwise"] is False
        assert call["out_of_sample_size"] == 0
    assert table.selected_by_auto.sum() == 1


def test_end_to_end_train_only_with_holdout_access_trap(frozen_root, monkeypatch):
    holdout = frozen_root / "data/processed/market_test.csv"
    holdout.write_text("FORBIDDEN HOLDOUT SENTINEL", encoding="utf-8")
    before = holdout.stat()
    original_read_csv = pd.read_csv
    original_read_bytes = Path.read_bytes
    reads = []

    def guarded_csv(path, *args, **kwargs):
        path = Path(path)
        assert path.name != holdout.name
        reads.append(path)
        return original_read_csv(path, *args, **kwargs)

    def guarded_bytes(path):
        assert path.name != holdout.name
        return original_read_bytes(path)

    monkeypatch.setattr(pd, "read_csv", guarded_csv)
    monkeypatch.setattr(Path, "read_bytes", guarded_bytes)
    monkeypatch.setattr(
        arima,
        "automatic_search",
        lambda y: pd.DataFrame(
            [
                {
                    "selected_by_auto": True,
                    "model": "ARIMA(0,1,0)_drift",
                    "p": 0,
                    "q": 0,
                    "drift": True,
                    "converged": True,
                }
            ]
        ),
    )
    monkeypatch.setattr(arima, "generate_figures", lambda *args: None)
    arima.main(frozen_root)
    assert holdout.stat().st_mtime_ns == before.st_mtime_ns
    assert holdout.stat().st_size == before.st_size
    assert {p.name for p in reads if p.parent.name == "processed"} == {
        "market_train.csv"
    }
    diagnostic = original_read_csv(
        frozen_root / "outputs/tables/phase3_arima_diagnostic_summary.csv"
    )
    assert diagnostic.qualification.iloc[0] == "provisional selected mean model"
    guard = original_read_csv(frozen_root / "outputs/tables/phase3_holdout_guard.csv")
    assert not guard.status.eq("FAIL").any()


def test_both_scripts_have_no_holdout_reference_or_other_market_input():
    r_script = SCRIPT.parents[1] / "r/02_arima.R"
    for source in (
        SCRIPT.read_text(encoding="utf-8"),
        r_script.read_text(encoding="utf-8"),
    ):
        assert "market_test.csv" not in source
        assert "market_aligned.csv" not in source
        assert "market_features.csv" not in source


def test_summary_rejects_different_train_bytes_across_languages(tmp_path):
    directory = tmp_path / "outputs/tables"
    directory.mkdir(parents=True)
    for lang, digest in [("r", "aaa"), ("python", "bbb")]:
        pd.DataFrame(
            [
                {
                    "md5": digest,
                    "rows": 100,
                    "first_date": "2020-01-02",
                    "last_date": "2020-05-20",
                }
            ]
        ).to_csv(directory / f"phase3_train_manifest_{lang}.csv", index=False)
    with pytest.raises(RuntimeError, match="identical TRAIN"):
        arima.summarize(tmp_path)
    guard = pd.read_csv(directory / "phase3_holdout_guard.csv")
    assert guard.status.eq("FAIL").all()


def test_summary_rejects_seasonality_disagreement(tmp_path):
    directory = tmp_path / "outputs/tables"
    directory.mkdir(parents=True)
    for lang, decision in [("r", True), ("python", False)]:
        pd.DataFrame(
            [
                {
                    "evidence": "sarima_justified",
                    "result": decision,
                    "interpretation": "synthetic",
                }
            ]
        ).to_csv(directory / f"phase3_seasonality_gate_{lang}.csv", index=False)
    with pytest.raises(RuntimeError, match="gates disagree"):
        arima.summarize(tmp_path)


def test_initialization_sensitivity_preserves_independent_selection(
    frozen_root, synthetic
):
    directory = frozen_root / "outputs/tables"
    pd.DataFrame(
        [
            {
                "md5": hashlib.md5(
                    (frozen_root / arima.TRAIN).read_bytes()
                ).hexdigest(),
            }
        ]
    ).to_csv(directory / "phase3_train_manifest_r.csv", index=False)
    model = "ARIMA(0,1,0)_drift"
    pd.DataFrame(
        [
            {
                "model": model,
                "p": 0,
                "d": 1,
                "q": 0,
                "drift": True,
                "selected_candidate": True,
            }
        ]
    ).to_csv(directory / "phase3_arima_selection_pool_r.csv", index=False)
    delta = np.diff(np.log(synthetic))
    pd.DataFrame(
        {
            "model": [model, model],
            "term": ["drift", "sigma2"],
            "estimate": [delta.mean(), delta.var()],
        }
    ).to_csv(directory / "phase3_arima_coefficients_r.csv", index=False)
    independent = directory / "phase3_arima_selection_pool_python.csv"
    independent.write_text("INDEPENDENT SELECTION SENTINEL", encoding="utf-8")
    arima.compare_r_optimizer(frozen_root)
    assert independent.read_text(encoding="utf-8") == "INDEPENDENT SELECTION SENTINEL"
    table = pd.read_csv(directory / "phase3_optimizer_sensitivity_python.csv")
    assert table.source.tolist() == [
        "independent_default_start",
        "R_initialized_sensitivity",
    ]
    assert table.model.eq(model).all()
