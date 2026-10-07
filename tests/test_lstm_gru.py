"""Offline Phase 6 preparation tests; no network training or holdout reads."""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "python/05_lstm_gru.py"
SPEC = importlib.util.spec_from_file_location("recurrent_phase", SCRIPT)
phase = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(phase)


@pytest.fixture
def synthetic():
    rng = np.random.default_rng(42)
    n = 400
    frame = pd.DataFrame(
        {"Date": pd.bdate_range("2020-01-02", periods=n).strftime("%Y-%m-%d")}
    )
    for asset in ["NVDA", "AMD", "SOXX"]:
        level = 3 + np.cumsum(rng.normal(0.001, 0.02, n))
        frame[f"{asset}_Adj_Close"] = np.exp(level)
        frame[f"{asset}_Log_Price"] = level
        frame[f"{asset}_Log_Return"] = np.r_[np.nan, 100 * np.diff(level)]
    frame["NVDA_Rolling_Vol_20D"] = frame.NVDA_Log_Return.rolling(20).std(
        ddof=1
    ) * np.sqrt(252)
    p = phase.protocol()
    p.update(
        expected_rows=n,
        expected_first_date=frame.Date.iloc[0],
        expected_last_date=frame.Date.iloc[-1],
        expected_usable_rows=n - 20,
        expected_usable_first_date=frame.Date.iloc[20],
    )
    return frame, p


def test_expected_features_and_usable_dates(synthetic):
    frame, p = synthetic
    usable = phase.prepare_frame(frame, p)
    assert len(usable) == 380 and usable.Date.iloc[0] == frame.Date.iloc[20]
    assert usable.Date.iloc[-1] == frame.Date.iloc[-1]
    assert phase.FEATURES == (
        "NVDA_Log_Price",
        "NVDA_Log_Return",
        "NVDA_Rolling_Vol_20D",
        "AMD_Log_Return",
        "SOXX_Log_Return",
    )


@pytest.mark.parametrize(
    "fault",
    ["missing", "order", "duplicate", "interior_na", "future_return", "centered_vol"],
)
def test_invalid_data_rejected(synthetic, fault):
    frame, p = synthetic
    if fault == "missing":
        frame = frame.drop(columns=["SOXX_Log_Return"])
    elif fault == "order":
        frame = frame.iloc[::-1]
    elif fault == "duplicate":
        frame.loc[10, "Date"] = frame.loc[9, "Date"]
    elif fault == "interior_na":
        frame.loc[50, "AMD_Log_Return"] = np.nan
    elif fault == "future_return":
        frame.NVDA_Log_Return = frame.NVDA_Log_Return.shift(-1)
    else:
        frame.NVDA_Rolling_Vol_20D = frame.NVDA_Log_Return.rolling(
            20, center=True
        ).std() * np.sqrt(252)
    with pytest.raises(ValueError):
        phase.prepare_frame(frame, p)


@pytest.mark.parametrize("n", [1960, 381, 1001])
def test_exact_70_10_10_10_chronological_folds(n):
    folds = phase.expanding_folds(n)
    assert folds == [
        (1, 7 * n // 10, 8 * n // 10),
        (2, 8 * n // 10, 9 * n // 10),
        (3, 9 * n // 10, n),
    ]
    assert len(folds) == 3 and folds[-1][2] == n
    for _, start, end in folds:
        assert 0 < start < end <= n


def test_scalers_exclude_validation_features_and_targets(synthetic):
    frame, p = synthetic
    usable = phase.prepare_frame(frame, p)
    x, y = usable[list(phase.FEATURES)].to_numpy(), usable[phase.TARGET].to_numpy()
    end = 266
    sx, sy = phase.fit_scalers(x, y, end)
    altered_x, altered_y = x.copy(), y.copy()
    altered_x[end:] += 1e6
    altered_y[end:] -= 1e6
    ax, ay = phase.fit_scalers(altered_x, altered_y, end)
    np.testing.assert_array_equal(sx.mean_, ax.mean_)
    np.testing.assert_array_equal(sx.scale_, ax.scale_)
    np.testing.assert_array_equal(sy.mean_, ay.mean_)
    np.testing.assert_array_equal(sy.scale_, ay.scale_)
    np.testing.assert_allclose(sx.mean_, x[:end].mean(axis=0))
    assert sx.n_samples_seen_ == sy.n_samples_seen_ == end


@pytest.mark.parametrize("lookback", [20, 60])
def test_window_shapes_h5_h10_and_past_only(lookback):
    x = np.repeat(np.arange(400)[:, None], 5, axis=1)
    y = np.arange(400)
    origins = phase.window_origins(lookback, 280, 320)
    wx, wy = phase.make_windows(x, y, origins, lookback, 280, 320)
    assert wx.shape == (31, lookback, 5) and wy.shape == (31, 10)
    np.testing.assert_array_equal(wx[:, -1, 0], origins)
    np.testing.assert_array_equal(wx[:, 0, 0], origins - lookback + 1)
    np.testing.assert_array_equal(wy[:, 4], origins + 5)
    np.testing.assert_array_equal(wy[:, 9], origins + 10)
    assert wy.min() == 280 and wy.max() == 319
    assert (wx[:, :, 0] <= origins[:, None]).all()


def test_future_features_cannot_change_an_earlier_input():
    x = np.arange(2000).reshape(400, 5).astype(float)
    y = np.arange(400)
    a, _ = phase.make_windows(x, y, [280], 60, 281, 300)
    x[281:] += 1e6
    b, _ = phase.make_windows(x, y, [280], 60, 281, 300)
    np.testing.assert_array_equal(a, b)


def test_inner_stopping_and_optimization_targets_are_separate(synthetic):
    frame, p = synthetic
    frame = phase.prepare_frame(frame, p)
    for _, end, val_end in phase.expanding_folds(len(frame)):
        arrays, origins, _, _, cut = phase.fold_preparation(
            frame, p["configurations"]["B"], end, val_end, p
        )
        assert origins["optimization"][-1] + 10 < cut
        assert origins["stopping"][0] + 1 == cut
        assert origins["stopping"][-1] + 10 == end - 1
        assert origins["validation"][0] == end - 1
        assert origins["validation"][-1] + 10 == val_end - 1
        assert len(arrays["validation"][0]) == val_end - end - 9


@pytest.mark.parametrize(
    "origins,start,end", [([279], 280, 289), ([278], 280, 320), ([10], 11, 40)]
)
def test_invalid_windows_rejected(origins, start, end):
    with pytest.raises(ValueError, match="causality"):
        phase.make_windows(np.ones((400, 5)), np.ones(400), origins, 20, start, end)


def test_naive_and_inverse_scaling_price_transform(synthetic):
    frame, p = synthetic
    frame = phase.prepare_frame(frame, p)
    x, y = frame[list(phase.FEATURES)].to_numpy(), frame[phase.TARGET].to_numpy()
    _, sy = phase.fit_scalers(x, y, 266)
    original = y[280:300].reshape(2, 10)
    scaled = sy.transform(original.reshape(-1, 1)).reshape(2, 10)
    restored = phase.inverse_targets(scaled, sy)
    np.testing.assert_allclose(restored, original, atol=1e-14)
    np.testing.assert_allclose(
        phase.price_from_log(restored),
        frame.NVDA_Adj_Close.iloc[280:300].to_numpy().reshape(2, 10),
    )
    naive = phase.naive_forecast(y, np.array([265, 266]))
    assert naive.shape == (2, 10)
    np.testing.assert_array_equal(naive, np.repeat(y[[265, 266], None], 10, axis=1))


def test_metrics_match_manual_price_and_log_errors():
    actual, predicted = np.array([10.0, 20.0]), np.array([12.0, 16.0])
    m = phase.metrics(np.log(actual), np.log(predicted))
    assert m["MSE"] == pytest.approx(10)
    assert m["RMSE"] == pytest.approx(np.sqrt(10))
    assert m["MAE"] == pytest.approx(3)
    assert m["MAPE"] == pytest.approx(20)
    assert m["log_MAE"] == pytest.approx(np.abs(np.log(predicted / actual)).mean())
    assert m["log_RMSE"] == pytest.approx(
        np.sqrt(np.mean(np.log(predicted / actual) ** 2))
    )


@pytest.mark.parametrize(
    "relative",
    [
        "data/processed/market_test.csv",
        "data/processed/market_features.csv",
        "../market_train.csv",
    ],
)
def test_holdout_access_forbidden_before_open(tmp_path, monkeypatch, relative):
    def forbidden(*args, **kwargs):
        pytest.fail("Unauthorized observation access")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    with pytest.raises(ValueError, match="Unauthorized"):
        phase.read_observations(tmp_path, relative)


def test_seed_and_fixed_protocol_metadata():
    assert phase.seed_metadata() == phase.seed_metadata(42)
    assert phase.seed_metadata()["seed"] == 42
    p = phase.protocol()
    assert p["framework_version"] == "2.21.0"
    assert p["max_epochs"] == 100 and p["early_stopping_patience"] == 10
    assert p["batch_size"] == 32 and p["learning_rate"] == 0.001
    assert p["configurations"] == {
        "A": {"lookback": 20, "units": 32, "dropout": 0.1},
        "B": {"lookback": 60, "units": 32, "dropout": 0.1},
        "C": {"lookback": 60, "units": 64, "dropout": 0.2},
    }


def test_selection_ratios_tie_breakers_and_failed_folds():
    scores = pd.DataFrame(
        {
            "model": ["LSTM"] * 3,
            "configuration": ["A", "B", "C"],
            "average_RMSE_ratio": [2.0, 1.5, 1.8],
            "average_MAE_ratio": [2.0, 1.6, 1.7],
            "successful_folds": [3] * 3,
            "scored_cells": [6] * 3,
            "trainable_parameters": [5194, 5194, 18570],
            "lookback": [20, 60, 60],
        }
    )
    assert phase.choose_configuration(scores, "LSTM")["configuration"] == "B"
    scores.average_RMSE_ratio = [1.5, 1.5005, 1.5009]
    scores.average_MAE_ratio = [1.6, 1.6002, 1.6001]
    assert phase.choose_configuration(scores, "LSTM")["configuration"] == "A"
    scores.loc[0, "successful_folds"] = 2
    with pytest.raises(ValueError, match="train successfully"):
        phase.choose_configuration(scores, "LSTM")


def test_parameter_counts_and_nonfinite_transform():
    assert phase.parameter_count("LSTM", 32) == 5194
    assert phase.parameter_count("GRU", 32) == 4074
    assert phase.parameter_count("LSTM", 64) == 18570
    assert phase.parameter_count("GRU", 64) == 14282
    with pytest.raises(ValueError):
        phase.price_from_log([np.nan])
    with pytest.raises(FloatingPointError):
        phase.price_from_log([1000])


def test_equal_fold_ratio_score_pooled_metrics_and_negative_improvements():
    p = phase.protocol()
    predictions, training = [], []
    for fold in [1, 2, 3]:
        for model in ["Naive", "LSTM", "GRU"]:
            configs = ["baseline"] if model == "Naive" else ["A", "B", "C"]
            for config in configs:
                multiplier = {"baseline": 1, "A": 2, "B": 1, "C": 0.5}[config]
                if model != "Naive":
                    training.append(
                        {
                            "model": model,
                            "configuration": config,
                            "fold": fold,
                            "trainable_parameters": phase.parameter_count(
                                model, p["configurations"][config]["units"]
                            ),
                            "best_epoch": 10 * fold,
                            "training_seconds": fold,
                            "status": "PASS",
                        }
                    )
                for h in [5, 10]:
                    actual = 100 * fold
                    predicted = actual + fold * (h / 5) * multiplier
                    predictions.append(
                        {
                            "model": model,
                            "configuration": config,
                            "fold": fold,
                            "horizon": h,
                            "actual_log_price": np.log(actual),
                            "forecast_log_price": np.log(predicted),
                        }
                    )
    by_fold, summary, ratios, scores, vs_naive = phase.aggregate_results(
        pd.DataFrame(predictions), pd.DataFrame(training), p
    )
    assert len(by_fold) == 42 and len(ratios) == 36 and len(scores) == 6
    for row in scores.itertuples():
        assert row.average_RMSE_ratio == pytest.approx(
            {"A": 2, "B": 1, "C": 0.5}[row.configuration]
        )
        assert row.median_best_epoch == 20 and row.successful_folds == 3
    naive_h5 = summary.loc[summary.model.eq("Naive") & summary.horizon.eq(5)].iloc[0]
    assert naive_h5.RMSE == pytest.approx(np.sqrt(14 / 3))
    assert vs_naive.loc[
        vs_naive.configuration.eq("A"), "RMSE_improvement_pct"
    ].to_numpy() == pytest.approx(-100)
    assert vs_naive.loc[
        vs_naive.configuration.eq("C"), "MAE_improvement_pct"
    ].to_numpy() == pytest.approx(50)


def test_set_seed_controls_python_and_numpy_without_loading_tensorflow():
    import random
    from types import SimpleNamespace

    calls = []
    fake = SimpleNamespace(
        keras=SimpleNamespace(utils=SimpleNamespace(set_random_seed=calls.append))
    )
    phase.set_seed(fake, 42)
    first = (random.random(), np.random.random())
    phase.set_seed(fake, 42)
    assert first == (random.random(), np.random.random())
    assert calls == [42, 42]


def test_published_outputs_provenance_coverage_and_endpoint():
    root = SCRIPT.parents[1]
    p = phase.protocol()
    meta = phase.provenance(p)
    paths = list((root / "outputs/tables").glob("phase6_*.csv"))
    assert len(paths) >= 18
    for path in paths:
        table = pd.read_csv(path)
        assert not table.empty
        for key in [
            "seed",
            "train_sha256",
            "protocol_sha256",
            "selection_rule_sha256",
            "implementation_sha256",
        ]:
            assert table[key].eq(meta[key]).all(), (
                f"Stale provenance: {path.name}/{key}"
            )
    training = pd.read_csv(root / "outputs/tables/phase6_training_runs.csv")
    assert len(training) == 18 and training.status.eq("PASS").all()
    assert training.groupby(["model", "configuration"]).size().eq(3).all()
    guard = pd.read_csv(root / "outputs/tables/phase6_holdout_guard.csv")
    assert len(guard) >= 15 and guard.status.eq("PASS").all()
    forecasts = pd.read_csv(root / "outputs/tables/phase6_train_end_forecasts.csv")
    assert forecasts.origin_date.eq("2025-11-14").all()
    assert forecasts.scope.eq(phase.ENDPOINT_SCOPE).all()
    assert len(forecasts) == 30
    for _, group in forecasts.groupby("model"):
        assert group.horizon.tolist() == list(range(1, 11))
    np.testing.assert_allclose(
        np.exp(forecasts.forecast_log_price), forecasts.forecast_price
    )
    predictions = pd.read_csv(root / "outputs/tables/phase6_validation_predictions.csv")
    assert predictions.target_date.le("2025-11-14").all()
    for _, group in predictions.groupby(["model", "configuration", "fold", "horizon"]):
        assert len(group) == 187 and group.origin_date.is_monotonic_increasing
        assert group.target_date.gt(group.origin_date).all()
    refits = pd.read_csv(root / "outputs/tables/phase6_full_train_refits.csv")
    for row in refits.itertuples():
        source = training.loc[
            training.model.eq(row.model) & training.configuration.eq(row.configuration)
        ]
        assert row.refit_epochs == source.best_epoch.median()
        assert row.train_rows == row.X_n_fit == row.y_n_fit == 1960
        assert not row.early_stopping
