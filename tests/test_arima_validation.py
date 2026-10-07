"""Offline synthetic Phase 3B tests; never read real market observations."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "python/02b_arima_validation.py"
SPEC = importlib.util.spec_from_file_location("arima_validation", SCRIPT)
validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validation)


@pytest.fixture
def fixture():
    dates = pd.bdate_range("2020-01-01", periods=70)
    frame = pd.DataFrame(
        {"Date": dates.strftime("%Y-%m-%d"), "NVDA_Adj_Close": 20 + np.arange(70) / 10}
    )
    protocol = SimpleNamespace(
        expected_rows=70,
        first_date=frame.Date.iloc[0],
        last_date=frame.Date.iloc[-1],
        initial_size=40,
        origin_step=5,
        horizon_1=5,
        horizon_2=10,
        maxiter=100,
        clear_improvement_pct=1,
        near_score_pct=1,
    )
    candidates = pd.DataFrame(
        [
            {
                "model": "Naive",
                "p": 0,
                "d": 1,
                "q": 0,
                "drift": False,
                "k": 1,
                "phase3a_mean_adequate": False,
                "phase3a_note": "warning",
            }
        ]
    )
    return frame, protocol, candidates


def test_chronological_expanding_origins(fixture):
    frame, protocol, _ = fixture
    dates = pd.to_datetime(frame.Date)
    origins = validation.make_origins(
        dates, protocol.initial_size, protocol.origin_step, [5, 10]
    )
    assert list(origins.origin_index.unique()) == [39, 44, 49, 54, 59]
    assert origins.origin_index.is_monotonic_increasing
    assert (origins.train_size == origins.origin_index + 1).all()


@pytest.mark.parametrize("h", [5, 10])
def test_exact_target_alignment_and_naive(fixture, h):
    frame, protocol, candidates = fixture
    _, predictions, _ = validation.rolling_validate(frame, protocol, candidates)
    rows = predictions.loc[predictions.horizon == h]
    assert (rows.target_index == rows.origin_index + h).all()
    np.testing.assert_allclose(
        rows.actual_price, frame.NVDA_Adj_Close.iloc[rows.target_index]
    )
    np.testing.assert_allclose(
        rows.forecast_price, frame.NVDA_Adj_Close.iloc[rows.origin_index]
    )
    assert list(rows.target_date) == list(frame.Date.iloc[rows.target_index])


def test_no_future_information_and_future_perturbation(fixture):
    frame, protocol, candidates = fixture
    seen = []

    def spy(history, spec, h, maxiter):
        seen.append(history.copy())
        np.testing.assert_array_equal(
            history, np.log(frame.NVDA_Adj_Close.iloc[: len(history)])
        )
        return validation.fit_forecast(history, spec, h, maxiter)

    _, first, _ = validation.rolling_validate(frame, protocol, candidates, spy)
    assert [len(x) for x in seen] == [40, 45, 50, 55, 60]
    changed = frame.copy()
    changed.loc[40:, "NVDA_Adj_Close"] *= 2
    _, second, _ = validation.rolling_validate(changed, protocol, candidates)
    np.testing.assert_array_equal(
        first.loc[first.origin_index == 39, "forecast_price"],
        second.loc[second.origin_index == 39, "forecast_price"],
    )
    assert not np.array_equal(
        first.loc[first.origin_index == 39, "actual_price"],
        second.loc[second.origin_index == 39, "actual_price"],
    )


def test_log_back_transformation_and_drift():
    history = np.log([10.0, 11.0, 13.0])
    spec = SimpleNamespace(model="RW_drift")
    log_prediction, converged, _, _ = validation.fit_forecast(history, spec, 10)
    expected = history[-1] + np.arange(1, 11) * np.mean(np.diff(history))
    np.testing.assert_allclose(validation.to_price(log_prediction), np.exp(expected))
    assert converged
    with pytest.raises((FloatingPointError, ValueError)):
        validation.to_price([np.inf])


def test_metric_correctness():
    actual = np.array([10.0, 20.0])
    prediction = np.array([12.0, 16.0])
    metrics = validation.metric_values(
        actual, prediction, np.log(actual), np.log(prediction)
    )
    assert metrics["MSE"] == 10
    assert metrics["RMSE"] == np.sqrt(10)
    assert metrics["MAE"] == 3
    assert metrics["MAPE"] == 20
    np.testing.assert_allclose(
        metrics["log_MAE"], np.mean(np.abs(np.log(prediction / actual)))
    )
    with pytest.raises(ValueError):
        validation.metric_values([0], [1], [0], [0])
    with pytest.raises(ValueError):
        validation.metric_values([1, 2], [1], [0, 0], [0, 0])


def test_fixed_order_statsmodels_forecast_on_synthetic_data():
    rng = np.random.default_rng(314)
    history = 3 + np.cumsum(rng.normal(0.001, 0.02, 180))
    spec = SimpleNamespace(model="ARIMA111_drift", p=1, d=1, q=1, drift=True)
    prediction, converged, method, _ = validation.fit_forecast(history, spec, 10)
    assert prediction.shape == (10,)
    assert np.isfinite(prediction).all()
    assert isinstance(converged, bool)
    assert "statsmodels" in method


def test_reader_rejects_test_file_before_open(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No file should be opened")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(pd, "read_csv", forbidden)
    for path in [
        "data/processed/market_test.csv",
        "data/processed/market_features.csv",
        "../market_train.csv",
    ]:
        with pytest.raises(ValueError, match="Unauthorized"):
            validation.read_observations(tmp_path, path, [])


def test_rolling_has_no_dataset_access(fixture, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Rolling loop must not open dataset files")

    monkeypatch.setattr(pd, "read_csv", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    validation.rolling_validate(*fixture)


def test_guard_and_determinism(fixture):
    frame, protocol, candidates = fixture
    origins, predictions, fits = validation.rolling_validate(
        frame, protocol, candidates
    )
    guards = validation.guard_table(
        frame, origins, predictions, fits, [validation.TRAIN]
    )
    assert guards.status.eq("PASS").all()
    _, repeat, _ = validation.rolling_validate(frame, protocol, candidates)
    pd.testing.assert_frame_equal(predictions, repeat)
    fits.loc[0, "fit_last_index"] += 1
    assert "FAIL" in set(
        validation.guard_table(
            frame, origins, predictions, fits, [validation.TRAIN]
        ).status
    )


def test_failure_is_retained_not_replaced(fixture):
    def failed(history, spec, h, maxiter):
        return np.repeat(history[-1], h), False, "synthetic nonconvergence", "warning"

    _, predictions, fits = validation.rolling_validate(*fixture, forecaster=failed)
    assert not fits.usable.any()
    assert predictions.forecast_price.isna().all()
    metrics = validation.metrics_table(predictions)
    assert metrics.n_forecasts.eq(0).all()
    assert metrics.failed_fits.eq(5).all()


def test_same_real_origin_metadata_across_languages():
    root = SCRIPT.parents[1]
    files = [
        root / f"outputs/tables/phase3b_origins_{lang}.csv" for lang in ["python", "r"]
    ]
    if not all(x.exists() for x in files):
        pytest.skip("Run both languages to create origin metadata; no market reads")
    p, r = [pd.read_csv(x) for x in files]
    pd.testing.assert_frame_equal(p, r, check_dtype=False)


def test_exported_language_metrics_match_individual_model_forecasts():
    root = SCRIPT.parents[1]
    for lang in ["python", "r"]:
        paths = [
            root / f"outputs/tables/phase3b_{kind}_{lang}.csv"
            for kind in ["forecasts", "validation_metrics"]
        ]
        if not all(p.exists() for p in paths):
            pytest.skip("Language outputs pending; no market observations read")
        forecasts, reported = [pd.read_csv(p) for p in paths]
        calculated = validation.metrics_table(forecasts).sort_values(
            ["model", "horizon"]
        )
        reported = reported.sort_values(["model", "horizon"])
        for column in [
            "n_origins",
            "n_forecasts",
            "failed_fits",
            "MSE",
            "RMSE",
            "MAE",
            "MAPE",
            "log_MAE",
            "log_RMSE",
        ]:
            np.testing.assert_allclose(
                reported[column], calculated[column], rtol=1e-12, atol=1e-12
            )


def test_lock_requires_both_horizons_languages_and_convergence(fixture):
    _, protocol, candidates = fixture
    challenger = candidates.iloc[0].copy()
    challenger["model"] = "ARIMA111_drift"
    challenger["k"] = 4
    challenger["phase3a_mean_adequate"] = True
    candidates = pd.concat([candidates, pd.DataFrame([challenger])], ignore_index=True)
    metrics = pd.DataFrame(
        [
            {
                "model": "ARIMA111_drift",
                "language": lang,
                "horizon": h,
                "RMSE": 9.0,
                "MAE": 8.0,
                "failed_fits": 0,
            }
            for lang in ["R", "Python"]
            for h in [5, 10]
        ]
    )
    baseline = metrics.copy()
    baseline["RMSE_improvement_vs_naive_pct"] = 10.0
    baseline["MAE_improvement_vs_naive_pct"] = 10.0
    assert (
        validation.lock_model(metrics, baseline, candidates, protocol).iloc[0].model
        == "ARIMA111_drift"
    )
    baseline.loc[0, "MAE_improvement_vs_naive_pct"] = -0.1
    assert (
        validation.lock_model(metrics, baseline, candidates, protocol).iloc[0].model
        == "Naive"
    )
    baseline["MAE_improvement_vs_naive_pct"] = 10.0
    metrics.loc[0, "failed_fits"] = 1
    assert (
        validation.lock_model(metrics, baseline, candidates, protocol).iloc[0].model
        == "Naive"
    )
