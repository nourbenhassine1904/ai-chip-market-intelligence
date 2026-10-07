"""Phase 6: TRAIN-only LSTM/GRU, 18 main fits and two full-TRAIN refits.

No package installation, holdout observation access or final evaluation.
Preparation functions are independent of TensorFlow for lightweight tests.
"""

import hashlib
import io
import json
import os
import platform
import random
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "1")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

TRAIN = "data/processed/market_train.csv"
PROTOCOL = "docs/phase6_protocol.json"
RULE = "docs/phase6_selection_rule.md"
FEATURES = (
    "NVDA_Log_Price",
    "NVDA_Log_Return",
    "NVDA_Rolling_Vol_20D",
    "AMD_Log_Return",
    "SOXX_Log_Return",
)
TARGET = "NVDA_Log_Price"
SCOPE = "TRAIN_only_internal_temporal_validation"
ENDPOINT_SCOPE = "TRAIN_endpoint_forecast_no_holdout_evaluation"


def protocol(root=ROOT):
    p = json.loads((root / PROTOCOL).read_text(encoding="utf8"))
    if (
        tuple(p["features"]) != FEATURES
        or p["target"] != TARGET
        or p["output_horizon"] != 10
        or p["shuffle"]
        or p["fold_cut_tenths"] != [7, 8, 9, 10]
    ):
        raise ValueError("Unsupported Phase 6 protocol")
    return p


def read_observations(root=ROOT, relative=TRAIN, audit=None):
    if relative != TRAIN:
        raise ValueError(f"Unauthorized observation input: {relative}")
    path = root / relative
    if path.resolve() != root.resolve() / TRAIN:
        raise ValueError("Redirected TRAIN path")
    raw = path.read_bytes()
    if audit is not None:
        audit.append(relative)
    return pd.read_csv(io.BytesIO(raw), float_precision="round_trip"), raw


def prepare_frame(frame, p):
    required = {"Date", *FEATURES, "NVDA_Adj_Close"}
    required.update(
        f"{a}_{s}" for a in ["AMD", "SOXX"] for s in ["Log_Price", "Adj_Close"]
    )
    if not required.issubset(frame.columns):
        raise ValueError("Missing required feature/price columns")
    dates = pd.to_datetime(frame.Date, format="%Y-%m-%d", errors="raise")
    if (
        len(frame) != p["expected_rows"]
        or not dates.is_monotonic_increasing
        or not dates.is_unique
        or dates.isna().any()
        or str(dates.iloc[0].date()) != p["expected_first_date"]
        or str(dates.iloc[-1].date()) != p["expected_last_date"]
    ):
        raise ValueError("Invalid frozen TRAIN chronology")
    for asset in ["NVDA", "AMD", "SOXX"]:
        price = frame[f"{asset}_Adj_Close"].to_numpy(float)
        level = frame[f"{asset}_Log_Price"].to_numpy(float)
        returns = frame[f"{asset}_Log_Return"].to_numpy(float)
        if (
            not np.isfinite(price).all()
            or np.any(price <= 0)
            or not np.isfinite(level).all()
            or not np.isnan(returns[0])
            or not np.isfinite(returns[1:]).all()
            or not np.allclose(level, np.log(price), atol=1e-12, rtol=0)
            or not np.allclose(returns[1:], 100 * np.diff(level), atol=1e-10, rtol=0)
        ):
            raise ValueError("Invalid backward log-price/return transformation")
    rolling = frame.NVDA_Log_Return.rolling(20, min_periods=20).std(ddof=1) * np.sqrt(
        252
    )
    if not np.allclose(
        rolling, frame.NVDA_Rolling_Vol_20D, equal_nan=True, atol=1e-8, rtol=1e-10
    ):
        raise ValueError("Volatility is not trailing 20-session annualized volatility")
    good = np.isfinite(frame[list(FEATURES)].to_numpy(float)).all(axis=1)
    positions = np.flatnonzero(good)
    if not len(positions) or not good[positions[0] :].all():
        raise ValueError("Only leading structural missing features may be removed")
    usable = frame.iloc[positions[0] :].copy().reset_index(drop=True)
    if (
        len(usable) != p["expected_usable_rows"]
        or usable.Date.iloc[0] != p["expected_usable_first_date"]
    ):
        raise ValueError("Unexpected usable TRAIN range")
    return usable


def expanding_folds(n):
    boundaries = [n * k // 10 for k in [7, 8, 9]] + [n]
    if n < 100 or len(set(boundaries)) != 4:
        raise ValueError("Insufficient temporal observations")
    return [(i + 1, boundaries[i], boundaries[i + 1]) for i in range(3)]


def fit_scalers(features, target, train_end):
    if not 0 < train_end <= len(features) or len(target) != len(features):
        raise ValueError("Invalid scaler TRAIN endpoint")
    sx = StandardScaler().fit(np.ascontiguousarray(features[:train_end], dtype=float))
    sy = StandardScaler().fit(
        np.asarray(target[:train_end], dtype=float).reshape(-1, 1)
    )
    return sx, sy


def window_origins(lookback, target_start, target_end, horizon=10):
    """All target indices are inside [target_start, target_end); X ends at t."""
    if horizon != 10 or lookback < 1 or target_start < 0 or target_end <= target_start:
        raise ValueError("Invalid window bounds/horizon")
    return np.arange(
        max(lookback - 1, target_start - 1), target_end - horizon, dtype=int
    )


def make_windows(features, target, origins, lookback, target_start, target_end):
    origins = np.asarray(origins, dtype=int)
    if (
        not len(origins)
        or len(features) != len(target)
        or np.any(np.diff(origins) <= 0)
        or origins.min() - lookback + 1 < 0
        or origins.min() + 1 < target_start
        or origins.max() + 10 >= target_end
        or target_end > len(target)
    ):
        raise ValueError("Window alignment/causality violation")
    xi = origins[:, None] + np.arange(-lookback + 1, 1)
    yi = origins[:, None] + np.arange(1, 11)
    assert (xi.max(axis=1) == origins).all()
    assert (yi.min(axis=1) > origins).all()
    return np.asarray(features)[xi].astype("float32"), np.asarray(target)[yi].astype(
        "float32"
    )


def inverse_targets(values, scaler):
    values = np.asarray(values, dtype=float)
    result = scaler.inverse_transform(values.reshape(-1, 1)).reshape(values.shape)
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite inverse target")
    return result


def price_from_log(values):
    with np.errstate(over="raise", invalid="raise"):
        prices = np.exp(np.asarray(values, dtype=float))
    if not np.isfinite(prices).all() or np.any(prices <= 0):
        raise ValueError("Invalid price back-transform")
    return prices


def naive_forecast(log_prices, origins):
    return np.repeat(np.asarray(log_prices)[origins, None], 10, axis=1)


def metrics(actual_log, predicted_log):
    actual_log, predicted_log = (
        np.asarray(actual_log, dtype=float),
        np.asarray(predicted_log, dtype=float),
    )
    if actual_log.shape != predicted_log.shape or actual_log.size == 0:
        raise ValueError("Metric alignment failure")
    actual, predicted = price_from_log(actual_log), price_from_log(predicted_log)
    error, log_error = predicted - actual, predicted_log - actual_log
    return {
        "n_forecasts": actual.size,
        "MSE": np.mean(error**2),
        "RMSE": np.sqrt(np.mean(error**2)),
        "MAE": np.mean(np.abs(error)),
        "MAPE": 100 * np.mean(np.abs(error) / actual),
        "log_RMSE": np.sqrt(np.mean(log_error**2)),
        "log_MAE": np.mean(np.abs(log_error)),
    }


def parameter_count(architecture, units, features=5):
    recurrent = (
        4 * units * (features + units + 1)
        if architecture == "LSTM"
        else 3 * units * (features + units + 2)
    )
    if architecture not in ["LSTM", "GRU"]:
        raise ValueError("Unknown architecture")
    return recurrent + (units + 1) * 10


def seed_metadata(seed=42):
    return {
        "seed": seed,
        "shuffle": False,
        "split": "expanding_70_10_10_10",
        "target_horizon": 10,
        "requested_device": "CPU",
    }


def load_tensorflow(p):
    try:
        import tensorflow as tf
    except ImportError as exc:
        raise RuntimeError(
            "STOP: explicitly install tensorflow==2.21.0 in .venv"
        ) from exc
    if tf.__version__ != p["framework_version"]:
        raise RuntimeError(f"Expected TensorFlow 2.21.0, got {tf.__version__}")
    tf.config.set_visible_devices([], "GPU")
    tf.config.threading.set_intra_op_parallelism_threads(p["intra_op_threads"])
    tf.config.threading.set_inter_op_parallelism_threads(p["inter_op_threads"])
    tf.config.experimental.enable_op_determinism()
    return tf


def set_seed(tf, seed):
    random.seed(seed)
    np.random.seed(seed)
    tf.keras.utils.set_random_seed(seed)


def build_model(tf, architecture, config, p):
    layer = {"LSTM": tf.keras.layers.LSTM, "GRU": tf.keras.layers.GRU}[architecture]
    model = tf.keras.Sequential(
        [
            tf.keras.Input(shape=(config["lookback"], len(FEATURES))),
            layer(config["units"]),
            tf.keras.layers.Dropout(config["dropout"]),
            tf.keras.layers.Dense(10),
        ]
    )
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=p["learning_rate"]),
        loss="mse",
        jit_compile=False,
    )
    assert model.count_params() == parameter_count(architecture, config["units"])
    return model


def dataset(tf, x, y, p):
    ds = tf.data.Dataset.from_tensor_slices((x, y)).batch(p["batch_size"])
    options = tf.data.Options()
    options.experimental_deterministic = True
    options.threading.private_threadpool_size = 1
    options.threading.max_intra_op_parallelism = 1
    return ds.with_options(options)


def predict_logs(model, x, sy, batch_size=32):
    # Direct inference avoids implicit Dataset.predict threadpools and preserves order.
    scaled = np.concatenate(
        [
            model(x[i : i + batch_size], training=False).numpy()
            for i in range(0, len(x), batch_size)
        ]
    )
    return inverse_targets(scaled, sy)


def provenance(p, root=ROOT):
    return {
        "scope": SCOPE,
        **seed_metadata(p["seed"]),
        "train_sha256": p["train_sha256"],
        "protocol_sha256": hashlib.sha256((root / PROTOCOL).read_bytes()).hexdigest(),
        "selection_rule_sha256": hashlib.sha256((root / RULE).read_bytes()).hexdigest(),
        "implementation_sha256": hashlib.sha256(
            (root / "python/05_lstm_gru.py").read_bytes()
        ).hexdigest(),
    }


def save_table(rows, name, meta, root=ROOT):
    table = pd.DataFrame(rows)
    for key, value in meta.items():
        if key not in table:
            table[key] = value
    folder = root / "outputs/tables"
    folder.mkdir(parents=True, exist_ok=True)
    table.to_csv(folder / f"phase6_{name}.csv", index=False, lineterminator="\n")
    return table


def fold_preparation(frame, config, train_end, val_end, p):
    features, target = frame[list(FEATURES)].to_numpy(), frame[TARGET].to_numpy()
    sx, sy = fit_scalers(features, target, train_end)
    x, y = sx.transform(features), sy.transform(target[:, None]).ravel()
    cut = int(np.floor(train_end * p["early_stopping_train_fraction"]))
    arrays, origins = {}, {}
    for name, start, end in [
        ("optimization", 0, cut),
        ("stopping", cut, train_end),
        ("validation", train_end, val_end),
    ]:
        origin = window_origins(config["lookback"], start, end)
        arrays[name] = make_windows(x, y, origin, config["lookback"], start, end)
        origins[name] = origin
    assert origins["optimization"][-1] + 10 < cut
    assert origins["stopping"][-1] + 10 < train_end
    assert origins["validation"][0] >= train_end - 1
    assert sx.n_samples_seen_ == sy.n_samples_seen_ == train_end
    return arrays, origins, sx, sy, cut


def prediction_rows(frame, actual, predicted, origins, model, config, fold):
    rows = []
    for h in [5, 10]:
        for j, origin in enumerate(origins):
            rows.append(
                {
                    "model": model,
                    "configuration": config,
                    "fold": fold,
                    "origin_index": origin,
                    "origin_date": frame.Date.iloc[origin],
                    "horizon": h,
                    "target_date": frame.Date.iloc[origin + h],
                    "actual_log_price": actual[j, h - 1],
                    "forecast_log_price": predicted[j, h - 1],
                    "actual_price": float(price_from_log(actual[j, h - 1])),
                    "forecast_price": float(price_from_log(predicted[j, h - 1])),
                }
            )
    return rows


def aggregate_results(predictions, training, p):
    fold_metrics, summary = [], []
    keys = ["model", "configuration", "horizon"]
    for labels, group in predictions.groupby(keys + ["fold"], sort=True):
        row = dict(zip(keys + ["fold"], labels, strict=True))
        row.update(metrics(group.actual_log_price, group.forecast_log_price))
        fold_metrics.append(row)
    by_fold = pd.DataFrame(fold_metrics)
    for labels, group in predictions.groupby(keys, sort=True):
        row = dict(zip(keys, labels, strict=True))
        row.update(metrics(group.actual_log_price, group.forecast_log_price))
        row["aggregation"] = "pooled forecast errors; no independence claim"
        summary.append(row)
    summary = pd.DataFrame(summary)
    naive = by_fold.loc[by_fold.model.eq("Naive"), ["fold", "horizon", "RMSE", "MAE"]]
    ratios = by_fold.loc[~by_fold.model.eq("Naive")].merge(
        naive, on=["fold", "horizon"], suffixes=("", "_naive"), validate="many_to_one"
    )
    if (
        len(ratios) != 36
        or ratios.RMSE_naive.le(0).any()
        or ratios.MAE_naive.le(0).any()
    ):
        raise ValueError("Missing matched positive naive scores")
    ratios["RMSE_ratio"], ratios["MAE_ratio"] = (
        ratios.RMSE / ratios.RMSE_naive,
        ratios.MAE / ratios.MAE_naive,
    )
    scores = ratios.groupby(["model", "configuration"], as_index=False).agg(
        average_RMSE_ratio=("RMSE_ratio", "mean"),
        average_MAE_ratio=("MAE_ratio", "mean"),
        scored_cells=("RMSE_ratio", "size"),
    )
    train_summary = training.groupby(["model", "configuration"], as_index=False).agg(
        trainable_parameters=("trainable_parameters", "first"),
        median_best_epoch=("best_epoch", "median"),
        mean_training_seconds=("training_seconds", "mean"),
        total_training_seconds=("training_seconds", "sum"),
        successful_folds=("status", lambda s: (s == "PASS").sum()),
    )
    scores = scores.merge(
        train_summary, on=["model", "configuration"], validate="one_to_one"
    )
    for name in ["lookback", "units", "dropout"]:
        scores[name] = scores.configuration.map(
            lambda c, field=name: p["configurations"][c][field]
        )
    vs_naive = summary.loc[~summary.model.eq("Naive")].merge(
        summary.loc[summary.model.eq("Naive"), ["horizon", "RMSE", "MAE"]],
        on="horizon",
        suffixes=("_model", "_naive"),
        validate="many_to_one",
    )
    for metric in ["RMSE", "MAE"]:
        vs_naive[f"{metric}_improvement_pct"] = 100 * (
            1 - vs_naive[f"{metric}_model"] / vs_naive[f"{metric}_naive"]
        )
    return by_fold, summary, ratios, scores, vs_naive


def choose_configuration(scores, architecture, tolerance=0.001):
    candidates = scores.loc[
        scores.model.eq(architecture)
        & scores.successful_folds.eq(3)
        & scores.scored_cells.eq(6)
    ].copy()
    if (
        len(candidates) != 3
        or not np.isfinite(candidates[["average_RMSE_ratio", "average_MAE_ratio"]])
        .all()
        .all()
    ):
        raise ValueError("All three fixed configurations must train successfully")
    candidates = candidates.loc[
        candidates.average_RMSE_ratio <= candidates.average_RMSE_ratio.min() + tolerance
    ]
    candidates = candidates.loc[
        candidates.average_MAE_ratio <= candidates.average_MAE_ratio.min() + tolerance
    ]
    return (
        candidates.sort_values(["trainable_parameters", "lookback", "configuration"])
        .iloc[0]
        .to_dict()
    )


def create_figures(predictions, summary, training, history, locked, meta):
    folder = ROOT / "outputs/figures/phase6"
    folder.mkdir(parents=True, exist_ok=True)

    def finish(fig, filename):
        fig.tight_layout()
        fig.savefig(
            folder / filename, dpi=150, metadata={"Description": json.dumps(meta)}
        )
        plt.close(fig)

    for architecture in ["LSTM", "GRU"]:
        config = locked[architecture]["configuration"]
        data = history.loc[
            history.model.eq(architecture)
            & history.configuration.eq(config)
            & history.fold.eq(3)
        ]
        best = int(
            training.loc[
                training.model.eq(architecture)
                & training.configuration.eq(config)
                & training.fold.eq(3),
                "best_epoch",
            ].iloc[0]
        )
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.plot(data.epoch, data.loss, label="Training loss")
        ax.plot(data.epoch, data.val_loss, label="Validation loss (inner TRAIN tail)")
        ax.axvline(best, color="black", linestyle="--", label=f"Restored epoch {best}")
        ax.set(
            xlabel="Epoch",
            ylabel="MSE of standardized log-prices",
            title=f"{architecture} {config} — Fold 3; outer validation excluded from stopping",
        )
        ax.legend()
        finish(fig, f"phase6_{architecture.lower()}_loss_curve.png")
    for h in [5, 10]:
        data = summary.loc[summary.horizon.eq(h)].sort_values(
            ["model", "configuration"]
        )
        fig, ax = plt.subplots(figsize=(10, 4.5))
        labels = [f"{r.model} {r.configuration}" for r in data.itertuples()]
        ax.bar(
            labels,
            data.RMSE,
            color=[
                "gray"
                if r.model == "Naive"
                else "steelblue"
                if r.model == "LSTM"
                else "darkorange"
                for r in data.itertuples()
            ],
        )
        ax.set(
            ylabel="Pooled internal RMSE (adjusted USD)",
            title=f"TRAIN-only temporal validation — horizon {h}",
        )
        finish(fig, f"phase6_validation_rmse_h{h}.png")
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        for fold, ax in enumerate(axes, 1):
            data = predictions.loc[
                predictions.horizon.eq(h) & predictions.fold.eq(fold)
            ]
            base = data.loc[data.model.eq("Naive")]
            ax.plot(
                pd.to_datetime(base.target_date),
                base.actual_price,
                color="black",
                label="Actual (inside official TRAIN)",
            )
            ax.plot(
                pd.to_datetime(base.target_date),
                base.forecast_price,
                color="gray",
                alpha=0.8,
                label="Naive",
            )
            for architecture, color in [("LSTM", "steelblue"), ("GRU", "darkorange")]:
                chosen = data.loc[
                    data.model.eq(architecture)
                    & data.configuration.eq(locked[architecture]["configuration"])
                ]
                ax.plot(
                    pd.to_datetime(chosen.target_date),
                    chosen.forecast_price,
                    color=color,
                    label=f"{architecture} {locked[architecture]['configuration']}",
                )
            ax.set(
                title=f"Fold {fold} — h={h}; rolling origins, weights fixed before block",
                ylabel="Adjusted USD",
            )
            ax.legend(fontsize=8, loc="upper left")
        finish(fig, f"phase6_fold_predictions_h{h}.png")
    fig, ax = plt.subplots(figsize=(9, 4.5))
    names = ["LSTM", "GRU"]
    ax.bar(
        names,
        [locked[a]["average_RMSE_ratio"] for a in names],
        color=["steelblue", "darkorange"],
    )
    ax.axhline(1, color="black", linestyle="--", label="Naive ratio = 1")
    ax.set(
        ylabel="Mean fold/horizon RMSE ratio to naive",
        title="Locked configurations — internal selection score",
    )
    ax.legend()
    finish(fig, "phase6_lstm_vs_gru_validation.png")


def holdout_guard(
    audit, folds, frame, fold_rows, scalers, predictions, endpoint, refits
):
    """Measured checks plus labeled source-scope checks; not an OS file-access audit."""
    matched = True
    for fold, start, end in folds:
        for h in [5, 10]:
            panel = predictions.loc[
                predictions.fold.eq(fold) & predictions.horizon.eq(h)
            ]
            baseline = panel.loc[panel.model.eq("Naive")].sort_values("origin_index")
            expected = np.arange(start - 1, end - 10)
            matched &= np.array_equal(baseline.origin_index.to_numpy(), expected)
            for _, group in panel.groupby(["model", "configuration"]):
                group = group.sort_values("origin_index")
                matched &= np.array_equal(group.origin_index.to_numpy(), expected)
                matched &= np.array_equal(
                    group.target_date.to_numpy(), baseline.target_date.to_numpy()
                )
                matched &= np.array_equal(
                    group.actual_log_price.to_numpy(),
                    baseline.actual_log_price.to_numpy(),
                )
    checks = [
        ("market_train.csv only", audit == [TRAIN], "runtime observation-reader audit"),
        (
            "market_test.csv not read",
            audit == [TRAIN],
            "runtime closed observation-reader audit",
        ),
        (
            "no holdout dates used",
            frame.Date.max() == "2025-11-14",
            "runtime TRAIN endpoint",
        ),
        (
            "scaler fit TRAIN-fold only",
            all(r["X_n_fit"] == r["train_rows"] for r in scalers),
            "runtime sample counts; prefix-only fit",
        ),
        (
            "target scaler fit TRAIN-fold only",
            all(r["y_n_fit"] == r["train_rows"] for r in scalers),
            "runtime target-scaler sample counts",
        ),
        (
            "chronological folds",
            folds == expanding_folds(len(frame)),
            "runtime fixed expanding boundaries",
        ),
        (
            "no shuffle",
            True,
            "source audit: ordered Dataset, shuffle=False; no shuffle call",
        ),
        (
            "no ordinary K-fold",
            True,
            "source audit: explicit chronological index slices",
        ),
        (
            "windows use past only",
            all(r["max_input_offset"] == 0 for r in fold_rows),
            "runtime window index assertions",
        ),
        (
            "targets after origin only",
            all(r["min_target_offset"] == 1 for r in fold_rows),
            "runtime window index assertions",
        ),
        (
            "validation targets remain inside fold",
            all(
                r["validation_last_target_index"] < r["validation_end_exclusive"]
                for r in fold_rows
            ),
            "runtime ten-target endpoint checks",
        ),
        (
            "early stopping excludes outer validation",
            all(r["inner_last_target_index"] < r["train_rows"] for r in fold_rows),
            "runtime inner bounds; outer labels not passed to fit",
        ),
        (
            "matched origins across models",
            matched,
            "runtime identical origin indices, target dates and actual values across models",
        ),
        (
            "final refit TRAIN only",
            len(refits) == 2 and all(r["train_rows"] == len(frame) for r in refits),
            "runtime TRAIN refit counts; no validation_data",
        ),
        (
            "train-end forecast does not read realized holdout",
            len(endpoint) == 30
            and all(r["origin_date"] == frame.Date.iloc[-1] for r in endpoint),
            "runtime origin; no future realized columns",
        ),
        ("no final test metrics", True, "source audit: internal prediction panel only"),
        ("no final DM test", True, "source audit: no DM implementation or call"),
    ]
    return [
        {
            "check": name,
            "status": "PASS" if bool(passed) else "FAIL",
            "evidence": evidence,
        }
        for name, passed, evidence in checks
    ]


def run():
    p = protocol()
    tf = load_tensorflow(p)
    audit = []
    raw_frame, raw = read_observations(audit=audit)
    if hashlib.sha256(raw).hexdigest() != p["train_sha256"]:
        raise ValueError("Frozen TRAIN SHA256 mismatch")
    frame = prepare_frame(raw_frame, p)
    meta = provenance(p)
    baseline = pd.read_csv(ROOT / "outputs/tables/phase3b_locked_arima_model.csv").iloc[
        0
    ]
    if baseline["order"] != "(0,1,0)" or bool(baseline.drift):
        raise ValueError("Historical locked naive specification changed")
    runtime = [
        {"package": n, "version": v}
        for n, v in [
            ("python", platform.python_version()),
            ("tensorflow", tf.__version__),
            ("keras", tf.keras.__version__),
            ("numpy", np.__version__),
            ("pandas", pd.__version__),
        ]
    ]
    runtime.append(
        {"package": "device", "version": str(tf.config.get_visible_devices())}
    )
    save_table(runtime, "runtime_versions", meta)
    save_table(
        [
            {
                "initial_rows": len(raw_frame),
                "dropped_leading_rows": len(raw_frame) - len(frame),
                "usable_rows": len(frame),
                "usable_first_date": frame.Date.iloc[0],
                "usable_last_date": frame.Date.iloc[-1],
                "features": "|".join(FEATURES),
                "target": TARGET,
                "rolling_vol_unit": "annualized percent; trailing ddof=1",
            }
        ],
        "train_manifest",
        meta,
    )
    folds = expanding_folds(len(frame))
    predictions, training, histories, fold_rows, scaler_rows = [], [], [], [], []
    cache = ROOT / ".cache/phase6"
    cache.mkdir(parents=True, exist_ok=True)
    for fold, train_end, val_end in folds:
        for label, config in p["configurations"].items():
            arrays, origins, sx, sy, cut = fold_preparation(
                frame, config, train_end, val_end, p
            )
            vo = origins["validation"]
            actual = frame[TARGET].to_numpy()[vo[:, None] + np.arange(1, 11)]
            if label == "A":
                predictions.extend(
                    prediction_rows(
                        frame,
                        actual,
                        naive_forecast(frame[TARGET], vo),
                        vo,
                        "Naive",
                        "baseline",
                        fold,
                    )
                )
                scaler_rows.append(
                    {
                        "fold": fold,
                        "train_rows": train_end,
                        "X_n_fit": int(sx.n_samples_seen_),
                        "y_n_fit": int(sy.n_samples_seen_),
                        "fit_first_date": frame.Date.iloc[0],
                        "fit_last_date": frame.Date.iloc[train_end - 1],
                        "X_mean": json.dumps(sx.mean_.tolist()),
                        "X_scale": json.dumps(sx.scale_.tolist()),
                        "y_mean": float(sy.mean_[0]),
                        "y_scale": float(sy.scale_[0]),
                    }
                )
            fold_rows.append(
                {
                    "fold": fold,
                    "configuration": label,
                    "lookback": config["lookback"],
                    "train_rows": train_end,
                    "train_first_date": frame.Date.iloc[0],
                    "train_last_date": frame.Date.iloc[train_end - 1],
                    "optimization_rows": cut,
                    "optimization_last_date": frame.Date.iloc[cut - 1],
                    "inner_stopping_first_date": frame.Date.iloc[cut],
                    "inner_stopping_last_date": frame.Date.iloc[train_end - 1],
                    "validation_rows": val_end - train_end,
                    "validation_first_date": frame.Date.iloc[train_end],
                    "validation_last_date": frame.Date.iloc[val_end - 1],
                    "optimization_sequences": len(origins["optimization"]),
                    "inner_stopping_sequences": len(origins["stopping"]),
                    "all_train_possible_sequences": train_end - config["lookback"] - 9,
                    "purged_inner_boundary_sequences": 9,
                    "validation_sequences": len(vo),
                    "h5_forecasts": len(vo),
                    "h10_forecasts": len(vo),
                    "first_validation_origin_date": frame.Date.iloc[vo[0]],
                    "last_validation_origin_date": frame.Date.iloc[vo[-1]],
                    "validation_last_target_index": int(vo[-1] + 10),
                    "validation_end_exclusive": val_end,
                    "max_input_offset": 0,
                    "min_target_offset": 1,
                    "inner_last_target_index": int(origins["stopping"][-1] + 10),
                }
            )
            for architecture in p["architectures"]:
                tf.keras.backend.clear_session()
                set_seed(tf, p["seed"])
                row = {
                    "model": architecture,
                    "configuration": label,
                    "fold": fold,
                    **config,
                    "seed": p["seed"],
                    "trainable_parameters": parameter_count(
                        architecture, config["units"]
                    ),
                }
                started = time.perf_counter()
                try:
                    model = build_model(tf, architecture, config, p)
                    stopping = tf.keras.callbacks.EarlyStopping(
                        monitor="val_loss",
                        patience=p["early_stopping_patience"],
                        restore_best_weights=True,
                    )
                    print(
                        f"START {architecture} {label} fold {fold}; optimization={len(origins['optimization'])}; stopping={len(origins['stopping'])}",
                        flush=True,
                    )
                    history = model.fit(
                        dataset(tf, *arrays["optimization"], p),
                        validation_data=dataset(tf, *arrays["stopping"], p),
                        epochs=p["max_epochs"],
                        shuffle=False,
                        verbose=0,
                        callbacks=[stopping, tf.keras.callbacks.TerminateOnNaN()],
                    ).history
                    if (
                        not np.isfinite(history["loss"]).all()
                        or not np.isfinite(history["val_loss"]).all()
                    ):
                        raise ValueError("Nonfinite training loss")
                    duration = time.perf_counter() - started
                    best_epoch = int(np.argmin(history["val_loss"]) + 1)
                    predicted = predict_logs(model, arrays["validation"][0], sy)
                    predictions.extend(
                        prediction_rows(
                            frame, actual, predicted, vo, architecture, label, fold
                        )
                    )
                    row.update(
                        status="PASS",
                        best_epoch=best_epoch,
                        epochs_run=len(history["loss"]),
                        training_seconds=duration,
                        best_inner_loss=min(history["val_loss"]),
                        stopped_early=len(history["loss"]) < p["max_epochs"],
                        error="",
                    )
                    histories.extend(
                        {
                            "model": architecture,
                            "configuration": label,
                            "fold": fold,
                            "epoch": e + 1,
                            "loss": loss,
                            "val_loss": history["val_loss"][e],
                            "validation_scope": "inner TRAIN tail; outer scores excluded",
                        }
                        for e, loss in enumerate(history["loss"])
                    )
                    print(
                        f"PASS {architecture} {label} fold {fold}: best={best_epoch}, epochs={row['epochs_run']}, seconds={duration:.2f}",
                        flush=True,
                    )
                except Exception as exc:
                    row.update(
                        status="FAIL",
                        training_seconds=time.perf_counter() - started,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    training.append(row)
                    save_table(training, "training_runs", meta)
                    save_table(histories, "loss_history", meta)
                    (cache / "technical_failure.txt").write_text(
                        traceback.format_exc(), encoding="utf8"
                    )
                    raise
                training.append(row)
                save_table(training, "training_runs", meta)
                save_table(histories, "loss_history", meta)
    assert len(training) == 18
    predictions = save_table(predictions, "validation_predictions", meta)
    training, history = pd.DataFrame(training), pd.DataFrame(histories)
    save_table(fold_rows, "temporal_folds", meta)
    save_table(scaler_rows, "scaler_audit", meta)
    by_fold, summary, ratios, scores, vs_naive = aggregate_results(
        predictions, training, p
    )
    for name, table in [
        ("validation_metrics_by_fold", by_fold),
        ("validation_metrics_summary", summary),
        ("validation_ratios_by_fold", ratios),
        ("configuration_scores", scores),
        ("vs_naive", vs_naive),
    ]:
        save_table(table, name, meta)
    locked, comparison = {}, []
    for architecture in p["architectures"]:
        row = choose_configuration(scores, architecture, p["score_tolerance"])
        row[f"locked_{architecture.lower()}_configuration"] = row["configuration"]
        row["status"] = f"locked_{architecture.lower()}_configuration"
        row["selection_rule"] = "mean six matched RMSE ratios; predeclared tie-breakers"
        locked[architecture] = row
        save_table([row], f"locked_{architecture.lower()}", meta)
        compare = row.copy()
        for h in [5, 10]:
            v = vs_naive.loc[
                vs_naive.model.eq(architecture)
                & vs_naive.configuration.eq(row["configuration"])
                & vs_naive.horizon.eq(h)
            ].iloc[0]
            compare[f"h{h}_RMSE"], compare[f"h{h}_MAE"] = v.RMSE_model, v.MAE_model
            compare[f"h{h}_RMSE_improvement_pct"] = v.RMSE_improvement_pct
        comparison.append(compare)
    save_table(comparison, "lstm_gru_comparison", meta)
    complexity = scores.copy()
    complexity["framework"], complexity["device"] = (
        f"TensorFlow {tf.__version__} / Keras",
        "CPU",
    )
    save_table(complexity, "model_complexity", meta)
    endpoint, refits = [], []
    features, target = frame[list(FEATURES)].to_numpy(), frame[TARGET].to_numpy()
    sx, sy = fit_scalers(features, target, len(frame))
    x, y = sx.transform(features), sy.transform(target[:, None]).ravel()
    for architecture, selected in locked.items():
        config = p["configurations"][selected["configuration"]]
        tf.keras.backend.clear_session()
        set_seed(tf, p["seed"])
        model = build_model(tf, architecture, config, p)
        origins = window_origins(config["lookback"], 0, len(frame))
        wx, wy = make_windows(x, y, origins, config["lookback"], 0, len(frame))
        epochs = int(selected["median_best_epoch"])
        started = time.perf_counter()
        print(
            f"REFIT {architecture} {selected['configuration']}: {epochs} fixed epochs",
            flush=True,
        )
        refit_history = model.fit(
            dataset(tf, wx, wy, p), epochs=epochs, shuffle=False, verbose=0
        ).history
        if not np.isfinite(refit_history["loss"]).all():
            raise ValueError("Nonfinite refit loss")
        duration = time.perf_counter() - started
        forecast = predict_logs(
            model, x[-config["lookback"] :].astype("float32")[None, :, :], sy
        )[0]
        model.save(cache / f"{architecture.lower()}_train_refit.keras")
        refits.append(
            {
                "model": architecture,
                "configuration": selected["configuration"],
                "train_rows": len(frame),
                "sequences": len(origins),
                "refit_epochs": epochs,
                "training_seconds": duration,
                "X_n_fit": int(sx.n_samples_seen_),
                "y_n_fit": int(sy.n_samples_seen_),
                "early_stopping": False,
                "status": "PASS",
            }
        )
        for h, value in enumerate(forecast, 1):
            endpoint.append(
                {
                    "model": architecture,
                    "configuration": selected["configuration"],
                    "origin_date": frame.Date.iloc[-1],
                    "horizon": h,
                    "forecast_log_price": value,
                    "forecast_price": float(price_from_log(value)),
                    "scope": ENDPOINT_SCOPE,
                }
            )
    (cache / "refit_scalers.json").write_text(
        json.dumps(
            {
                "features": list(FEATURES),
                "X_mean": sx.mean_.tolist(),
                "X_scale": sx.scale_.tolist(),
                "y_mean": sy.mean_.tolist(),
                "y_scale": sy.scale_.tolist(),
                **meta,
            },
            indent=2,
        ),
        encoding="utf8",
    )
    for h in range(1, 11):
        endpoint.append(
            {
                "model": "Naive",
                "configuration": "baseline",
                "origin_date": frame.Date.iloc[-1],
                "horizon": h,
                "forecast_log_price": target[-1],
                "forecast_price": float(price_from_log(target[-1])),
                "scope": ENDPOINT_SCOPE,
            }
        )
    save_table(refits, "full_train_refits", meta)
    save_table(endpoint, "train_end_forecasts", meta)
    checks = holdout_guard(
        audit, folds, frame, fold_rows, scaler_rows, predictions, endpoint, refits
    )
    save_table(checks, "holdout_guard", meta)
    if any(r["status"] != "PASS" for r in checks):
        raise ValueError("STOP: holdout guard FAIL")
    create_figures(predictions, summary, training, history, locked, meta)
    print("PHASE 6 PASS: 18 main fits, 2 refits; holdout guard PASS", flush=True)
    print(
        pd.DataFrame(comparison)[
            ["model", "configuration", "average_RMSE_ratio", "h5_RMSE", "h10_RMSE"]
        ].to_string(index=False),
        flush=True,
    )


if __name__ == "__main__":
    run()
