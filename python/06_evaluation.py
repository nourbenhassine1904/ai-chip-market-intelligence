"""Phase 7: precommitted final holdout evaluation, frozen model parameters.

Only official TRAIN/TEST observation paths. All fitting precedes TEST access.
Metrics, DM and coverage reload the SHA-256-frozen predictions, never refit.
"""

import argparse
import hashlib
import importlib.util
import io
import json
import os
import platform
import subprocess
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import statsmodels
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.api import VAR
from statsmodels.tsa.arima.model import ARIMA

PROTOCOL = "docs/phase7_final_evaluation_protocol.json"
PROTOCOL_MD = "docs/phase7_final_evaluation_protocol.md"
TRAIN = "data/processed/market_train.csv"
TEST = "data/processed/market_test.csv"
PREDICTIONS = "outputs/tables/phase7_final_predictions.csv"
RUNTIME_AUDIT = "outputs/tables/phase7_runtime_audit.json"
CACHE = ROOT / ".cache/phase7"
MODELS = ["Naive", "ARIMA(2,1,2)", "VAR(9)", "LSTM C", "GRU C"]
FEATURES = [
    "NVDA_Log_Price",
    "NVDA_Log_Return",
    "NVDA_Rolling_Vol_20D",
    "AMD_Log_Return",
    "SOXX_Log_Return",
]
RETURNS = ["NVDA_Log_Return", "AMD_Log_Return", "SOXX_Log_Return"]
SCOPE = "FINAL_holdout_frozen_parameters_walk_forward_information"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def git(*args, root=ROOT):
    return subprocess.check_output(["git", *args], cwd=root)


def load_protocol(root=ROOT):
    p = json.loads((root / PROTOCOL).read_text(encoding="utf8"))
    if (
        p["models"] != MODELS
        or p["horizons"] != [5, 10]
        or p["retuning"]
        or p["refit_after_test_access"]
    ):
        raise ValueError("Unsupported frozen protocol")
    return p


def verify_protocol_commit(root=ROOT):
    """Require committed, unchanged protocol; preserve the original clean gate."""
    p = load_protocol(root)
    commits = (
        git(
            "log",
            "--format=%H",
            "--fixed-strings",
            "--grep=" + p["protocol_commit_subject"],
            root=root,
        )
        .decode()
        .splitlines()
    )
    if not commits:
        raise ValueError("Protocol must be committed before TEST access")
    commit = commits[-1]
    hashes = {}
    for name in [PROTOCOL, PROTOCOL_MD]:
        raw = (root / name).read_bytes()
        if raw != git("show", f"{commit}:{name}", root=root):
            raise ValueError("Protocol differs from predeclared commit")
        hashes[name] = sha(raw)
    directory = root / ".cache/phase7"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "protocol_gate.json"
    if path.exists():
        gate = json.loads(path.read_text(encoding="utf8"))
    elif (root / RUNTIME_AUDIT).exists():
        # A fresh checkout replays the original recorded gate, not a new gate.
        gate = json.loads((root / RUNTIME_AUDIT).read_text(encoding="utf8"))[
            "protocol_gate"
        ]
    else:
        if git("status", "--porcelain", root=root).strip():
            raise ValueError(
                "A clean working tree is required to create the protocol gate"
            )
        gate = {
            "protocol_commit": commit,
            "protocol_hashes": hashes,
            "working_tree_clean_verified": True,
            "verified_utc": utc(),
            "test_read_before_this_gate": False,
        }
        path.write_text(json.dumps(gate, indent=2), encoding="utf8")
    if (
        gate["protocol_commit"] != commit
        or gate["protocol_hashes"] != hashes
        or not gate["working_tree_clean_verified"]
    ):
        raise ValueError("Invalid pre-access protocol gate")
    return gate


def read_observations(relative, audit, gate=None, models_ready=False, root=ROOT):
    if relative not in [TRAIN, TEST]:
        raise ValueError("Unauthorized observation input")
    if relative == TEST and (
        not gate or not gate.get("working_tree_clean_verified") or not models_ready
    ):
        raise ValueError(
            "TEST forbidden before committed protocol and TRAIN model freeze"
        )
    path = root / relative
    if path.resolve() != root.resolve() / relative:
        raise ValueError("Redirected observation path")
    audit.append(
        {
            "event": "test_access" if relative == TEST else "train_access",
            "utc": utc(),
            "path": relative,
        }
    )
    raw = path.read_bytes()
    return pd.read_csv(io.BytesIO(raw), float_precision="round_trip"), raw


def validate_features(frame):
    dates = pd.to_datetime(frame.Date, format="%Y-%m-%d", errors="raise")
    if dates.isna().any() or not dates.is_unique or not dates.is_monotonic_increasing:
        raise ValueError("Invalid chronology")
    for asset in ["NVDA", "AMD", "SOXX"]:
        prices = frame[f"{asset}_Adj_Close"].to_numpy(float)
        levels = frame[f"{asset}_Log_Price"].to_numpy(float)
        returns = frame[f"{asset}_Log_Return"].to_numpy(float)
        if (
            not np.isfinite(prices).all()
            or np.any(prices <= 0)
            or not np.isfinite(levels).all()
            or not np.isnan(returns[0])
            or not np.isfinite(returns[1:]).all()
            or not np.allclose(np.log(prices), levels, rtol=0, atol=1e-12)
            or not np.allclose(100 * np.diff(levels), returns[1:], rtol=0, atol=1e-10)
        ):
            raise ValueError("Backward-only return transformation mismatch")
    trailing = frame.NVDA_Log_Return.rolling(20, min_periods=20).std(ddof=1) * np.sqrt(
        252
    )
    if not np.allclose(
        trailing, frame.NVDA_Rolling_Vol_20D, equal_nan=True, rtol=1e-10, atol=1e-8
    ):
        raise ValueError("Non-trailing volatility or boundary mismatch")
    if not np.isfinite(frame[FEATURES].iloc[20:].to_numpy()).all():
        raise ValueError("Missing usable features")


def validate_split(train, test, p):
    if (
        len(train) != p["train_rows"]
        or len(test) != p["test_rows"]
        or len(train.columns) != p["columns"]
        or list(train.columns) != list(test.columns)
        or train.Date.iloc[0] != p["train_first_date"]
        or train.Date.iloc[-1] != p["train_last_date"]
        or test.Date.iloc[0] != p["test_first_date"]
        or test.Date.iloc[-1] != p["test_last_date"]
    ):
        raise ValueError("STOP: documented TRAIN/TEST structure mismatch")
    combined = pd.concat([train, test], ignore_index=True)
    validate_features(combined)
    if train.Date.max() >= test.Date.min():
        raise ValueError("TRAIN/TEST overlap")
    return combined


def origin_grid(dates, train_rows, expected=211):
    origins = np.arange(train_rows - 1, len(dates) - 10, dtype=int)
    if len(origins) != expected:
        raise ValueError("STOP: unexpected common-origin count")
    dates = np.asarray(dates)
    return pd.DataFrame(
        {
            "origin_date": dates[origins],
            "target_date_h5": dates[origins + 5],
            "target_date_h10": dates[origins + 10],
            "origin_index": origins,
            "target_index_h5": origins + 5,
            "target_index_h10": origins + 10,
        }
    )


def observed_prefix(frame, origin):
    if not 0 <= origin < len(frame):
        raise ValueError("Invalid origin")
    prefix = frame.iloc[: origin + 1].copy()
    assert prefix.Date.max() == frame.Date.iloc[origin]
    return prefix


def returns_to_log_price(origin_log, forecast_returns):
    values = np.asarray(forecast_returns, dtype=float)
    if values.shape != (10, 3) or not np.isfinite(values).all():
        raise ValueError("Invalid VAR return forecasts")
    return float(origin_log) + np.cumsum(values[:, 0]) / 100


def frozen_arima_update(result, value):
    before = np.asarray(result.params).copy()
    updated = result.append([float(value)], refit=False)
    if not np.array_equal(before, np.asarray(updated.params)):
        raise ValueError("ARIMA coefficients changed")
    return updated


def array_hash(values):
    return sha(np.ascontiguousarray(values, dtype="float64").tobytes())


def weights_hash(model):
    return sha(b"".join(np.ascontiguousarray(w).tobytes() for w in model.get_weights()))


def phase6_module(root=ROOT):
    spec = importlib.util.spec_from_file_location(
        "phase6_frozen", root / "python/05_lstm_gru.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_neural(train, p):
    """Load verified Phase 6 artifacts or reconstruct before any TEST read."""
    m = phase6_module()
    p6 = m.protocol()
    tf = m.load_tensorflow(p6)
    usable = m.prepare_frame(train, p6)
    sx, sy = m.fit_scalers(
        usable[FEATURES].to_numpy(), usable.NVDA_Log_Price.to_numpy(), len(usable)
    )
    cached_scalers = ROOT / ".cache/phase6/refit_scalers.json"
    common_valid = (
        cached_scalers.exists()
        and sha(cached_scalers.read_bytes())
        == p["phase6_cache_sha256"]["refit_scalers.json"]
    )
    if common_valid:
        saved = json.loads(cached_scalers.read_text(encoding="utf8"))
        for key, value in m.provenance(p6).items():
            if saved.get(key) != value:
                common_valid = False
        for key, value in [
            ("X_mean", sx.mean_),
            ("X_scale", sx.scale_),
            ("y_mean", sy.mean_),
            ("y_scale", sy.scale_),
        ]:
            common_valid &= np.allclose(saved[key], value, rtol=0, atol=1e-12)
        if common_valid:
            # Use the original frozen scaler values after verifying TRAIN statistics.
            sx.mean_ = np.asarray(saved["X_mean"], dtype=float)
            sx.scale_ = np.asarray(saved["X_scale"], dtype=float)
            sy.mean_ = np.asarray(saved["y_mean"], dtype=float)
            sy.scale_ = np.asarray(saved["y_scale"], dtype=float)
    models, records = {}, []
    endpoint = pd.read_csv(ROOT / "outputs/tables/phase6_train_end_forecasts.csv")
    refits = pd.read_csv(ROOT / "outputs/tables/phase6_full_train_refits.csv")
    for architecture in ["LSTM", "GRU"]:
        lock = pd.read_csv(
            ROOT / f"outputs/tables/phase6_locked_{architecture.lower()}.csv"
        ).iloc[0]
        if (
            lock.configuration != "C"
            or lock.lookback != 60
            or lock.units != 64
            or lock.dropout != 0.2
            or lock.median_best_epoch != p["neural"][architecture + "_epochs"]
        ):
            raise ValueError("Phase 6 lock differs from predeclared specification")
        for table in [pd.DataFrame([lock]), refits.loc[refits.model.eq(architecture)]]:
            for key, value in m.provenance(p6).items():
                if not table[key].eq(value).all():
                    raise ValueError("Stale Phase 6 provenance")
        path = ROOT / f".cache/phase6/{architecture.lower()}_train_refit.keras"
        started = time.perf_counter()
        model, reason = None, "cache missing or fingerprint/provenance mismatch"
        if (
            common_valid
            and path.exists()
            and sha(path.read_bytes()) == p["phase6_cache_sha256"][path.name]
        ):
            candidate = tf.keras.models.load_model(path, compile=False)
            recurrent = candidate.layers[0]
            config = recurrent.get_config()
            valid = (
                candidate.count_params() == m.parameter_count(architecture, 64)
                and type(recurrent).__name__ == architecture
                and config["units"] == 64
                and candidate.input_shape == (None, 60, 5)
                and candidate.output_shape == (None, 10)
                and candidate.layers[1].rate == 0.2
            )
            forecast = m.predict_logs(
                candidate,
                sx.transform(usable[FEATURES].to_numpy())[-60:].astype("float32")[None],
                sy,
            )[0]
            expected = endpoint.loc[
                endpoint.model.eq(architecture), "forecast_log_price"
            ].to_numpy()
            valid &= np.allclose(forecast, expected, rtol=0, atol=1e-6)
            if valid:
                model, reason = (
                    candidate,
                    "fingerprints, provenance, TRAIN scalers, architecture and endpoint match",
                )
        mode = "loaded_from_phase6_cache"
        reconstructed_seconds = np.nan
        if model is None:
            mode = "reconstructed_from_locked_specification"
            tf.keras.backend.clear_session()
            m.set_seed(tf, 42)
            config = p6["configurations"]["C"]
            model = m.build_model(tf, architecture, config, p6)
            x, y = (
                sx.transform(usable[FEATURES].to_numpy()),
                sy.transform(usable.NVDA_Log_Price.to_numpy()[:, None]).ravel(),
            )
            origins = m.window_origins(60, 0, len(usable))
            wx, wy = m.make_windows(x, y, origins, 60, 0, len(usable))
            fit_start = time.perf_counter()
            history = model.fit(
                m.dataset(tf, wx, wy, p6),
                epochs=p["neural"][architecture + "_epochs"],
                shuffle=False,
                verbose=0,
            ).history
            reconstructed_seconds = time.perf_counter() - fit_start
            if not np.isfinite(history["loss"]).all():
                raise ValueError("Neural reconstruction failed")
            model.save(CACHE / f"{architecture.lower()}_reconstructed.keras")
        models[architecture + " C"] = model
        records.append(
            {
                "model": architecture + " C",
                "mode": mode,
                "cache_reason": reason,
                "load_or_reconstruction_seconds": time.perf_counter() - started,
                "training_seconds": float(
                    refits.loc[refits.model.eq(architecture), "training_seconds"].iloc[
                        0
                    ]
                )
                if mode == "loaded_from_phase6_cache"
                else reconstructed_seconds,
                "training_source": "phase6_full_train_refits"
                if mode == "loaded_from_phase6_cache"
                else "measured_phase7_reconstruction",
                "parameters": model.count_params(),
                "epochs": p["neural"][architecture + "_epochs"],
                "weights_sha256": weights_hash(model),
                "cache_file_sha256": sha(path.read_bytes())
                if path.exists()
                else "missing",
            }
        )
    scalers = {
        "X_mean": sx.mean_.tolist(),
        "X_scale": sx.scale_.tolist(),
        "y_mean": sy.mean_.tolist(),
        "y_scale": sy.scale_.tolist(),
        "X_n_fit": int(sx.n_samples_seen_),
        "y_n_fit": int(sy.n_samples_seen_),
        "fit_last_date": usable.Date.iloc[-1],
    }
    return models, sx, sy, records, scalers, tf.__version__


def fit_classical(train, p):
    rows = []
    started = time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        arima = ARIMA(
            train.NVDA_Log_Price.to_numpy(),
            order=(2, 1, 2),
            trend="t",
            enforce_stationarity=True,
            enforce_invertibility=True,
        ).fit(method_kwargs={"maxiter": p["arima"]["maxiter"]})
    row = {
        "model": "ARIMA(2,1,2)",
        "training_seconds": time.perf_counter() - started,
        "parameters": len(arima.params),
        "converged": bool(arima.mle_retvals.get("converged", False)),
        "warnings": " | ".join(dict.fromkeys(str(w.message) for w in caught)),
        "parameter_names": json.dumps(arima.param_names),
        "parameter_values": json.dumps(arima.params.tolist()),
        "parameter_sha256": array_hash(arima.params),
        "training_source": "measured_phase7_TRAIN_fit",
    }
    rows.append(row)
    if not row["converged"] or not np.isfinite(arima.params).all():
        save_table(rows, "model_fit_log")
        raise ValueError("STOP: initial TRAIN ARIMA did not converge; no fallback")
    started = time.perf_counter()
    var = VAR(train[RETURNS].iloc[1:].to_numpy()).fit(9, trend="c")
    rows.append(
        {
            "model": "VAR(9)",
            "training_seconds": time.perf_counter() - started,
            "parameters": var.params.size,
            "converged": True,
            "warnings": "",
            "parameter_sha256": array_hash(var.params),
            "parameter_values": json.dumps(var.params.tolist()),
            "training_source": "measured_phase7_TRAIN_fit",
        }
    )
    if not np.isfinite(var.params).all() or not var.is_stable():
        raise ValueError("STOP: invalid TRAIN VAR")
    return arima, var, rows


def neural_forecast(model, prefix, sx, sy):
    if (
        len(prefix) < 60
        or not np.isfinite(prefix[FEATURES].iloc[-60:].to_numpy()).all()
    ):
        raise ValueError("Invalid observed neural window")
    x = sx.transform(prefix[FEATURES].iloc[-60:].to_numpy()).astype("float32")[None]
    values = np.asarray(model(x, training=False).numpy(), dtype=float)
    if values.shape != (1, 10):
        raise ValueError("Invalid direct ten-output forecast")
    return sy.inverse_transform(values.reshape(-1, 1)).ravel()


def generate_forecasts(frame, grid, arima, var, networks, sx, sy):
    rows, times = [], {model: 0.0 for model in MODELS}
    original_arima = array_hash(arima.params)
    original_var = array_hash(var.params)
    original_weights = {name: weights_hash(model) for name, model in networks.items()}
    scaler_hash = array_hash(np.r_[sx.mean_, sx.scale_, sy.mean_, sy.scale_])
    for position, origin in enumerate(grid.itertuples(index=False)):
        prefix = observed_prefix(frame, origin.origin_index)
        if position:
            started = time.perf_counter()
            arima = frozen_arima_update(arima, prefix.NVDA_Log_Price.iloc[-1])
            times["ARIMA(2,1,2)"] += time.perf_counter() - started
        forecasts, intervals = {}, {}
        started = time.perf_counter()
        naive_price = float(prefix.NVDA_Adj_Close.iloc[-1])
        forecasts["Naive"] = np.repeat(float(prefix.NVDA_Log_Price.iloc[-1]), 10)
        times["Naive"] += time.perf_counter() - started
        started = time.perf_counter()
        predicted = arima.get_forecast(steps=10)
        forecasts["ARIMA(2,1,2)"] = np.asarray(predicted.predicted_mean)
        intervals["ARIMA(2,1,2)"] = np.exp(np.asarray(predicted.conf_int(alpha=0.05)))
        times["ARIMA(2,1,2)"] += time.perf_counter() - started
        started = time.perf_counter()
        forecasts["VAR(9)"] = returns_to_log_price(
            prefix.NVDA_Log_Price.iloc[-1],
            var.forecast(prefix[RETURNS].iloc[-9:].to_numpy(), 10),
        )
        times["VAR(9)"] += time.perf_counter() - started
        for name, model in networks.items():
            started = time.perf_counter()
            forecasts[name] = neural_forecast(model, prefix, sx, sy)
            times[name] += time.perf_counter() - started
        # Targets are retrieved only after every model forecasts this observed prefix.
        for name, values in forecasts.items():
            if len(values) != 10 or not np.isfinite(values).all():
                raise ValueError("Incomplete forecast vector")
            for h in [5, 10]:
                forecast_price = (
                    naive_price if name == "Naive" else float(np.exp(values[h - 1]))
                )
                actual = float(frame.NVDA_Adj_Close.iloc[origin.origin_index + h])
                error = forecast_price - actual
                lower, upper = (
                    intervals[name][h - 1] if name in intervals else (np.nan, np.nan)
                )
                rows.append(
                    {
                        "model": name,
                        "origin_date": origin.origin_date,
                        "horizon": h,
                        "target_date": frame.Date.iloc[origin.origin_index + h],
                        "origin_index": origin.origin_index,
                        "target_index": origin.origin_index + h,
                        "forecast_log_price": values[h - 1],
                        "forecast_price": forecast_price,
                        "actual_price": actual,
                        "error": error,
                        "squared_error": error**2,
                        "absolute_error": abs(error),
                        "interval_lower_95": lower,
                        "interval_upper_95": upper,
                        "max_feature_source_date": prefix.Date.iloc[-1],
                    }
                )
        if position % 50 == 0:
            print(f"Frozen forecasts: {position + 1}/{len(grid)} origins", flush=True)
    frozen = {
        "ARIMA coefficients frozen": original_arima == array_hash(arima.params),
        "VAR coefficients frozen": original_var == array_hash(var.params),
        "LSTM weights frozen": original_weights["LSTM C"]
        == weights_hash(networks["LSTM C"]),
        "GRU weights frozen": original_weights["GRU C"]
        == weights_hash(networks["GRU C"]),
        "scalers frozen": scaler_hash
        == array_hash(np.r_[sx.mean_, sx.scale_, sy.mean_, sy.scale_]),
    }
    return pd.DataFrame(rows), times, frozen


def validate_prediction_panel(table, p):
    if (
        set(table.model) != set(MODELS)
        or set(table.horizon) != {5, 10}
        or len(table) != p["expected_common_origins"] * 10
    ):
        raise ValueError("Incomplete five-model price panel; GARCH forbidden")
    if table.duplicated(["model", "horizon", "origin_index"]).any():
        raise ValueError("Duplicated forecast")
    if (
        not np.isfinite(
            table[
                [
                    "forecast_price",
                    "actual_price",
                    "error",
                    "squared_error",
                    "absolute_error",
                ]
            ]
        )
        .all()
        .all()
        or table.forecast_price.le(0).any()
        or table.actual_price.le(0).any()
    ):
        raise ValueError("Nonfinite or nonpositive forecasts")
    for h in [5, 10]:
        base = table.loc[table.model.eq("Naive") & table.horizon.eq(h)].sort_values(
            "origin_index"
        )
        expected = np.arange(
            p["first_origin_index"],
            p["first_origin_index"] + p["expected_common_origins"],
        )
        if not np.array_equal(base.origin_index.to_numpy(), expected):
            raise ValueError("Missing or different common origins across horizons")
        for name in MODELS:
            group = table.loc[table.model.eq(name) & table.horizon.eq(h)].sort_values(
                "origin_index"
            )
            for column in [
                "origin_index",
                "origin_date",
                "target_date",
                "target_index",
                "actual_price",
            ]:
                if not np.array_equal(
                    group[column].to_numpy(), base[column].to_numpy()
                ):
                    raise ValueError("Unmatched origins, targets or actuals")
            if not (group.target_index == group.origin_index + h).all():
                raise ValueError("Wrong horizon alignment")
    if not np.allclose(
        table.error, table.forecast_price - table.actual_price, rtol=1e-12, atol=1e-12
    ):
        raise ValueError("Frozen error mismatch")
    if not np.allclose(
        table.squared_error, table.error**2, rtol=1e-12, atol=1e-12
    ) or not np.allclose(
        table.absolute_error, np.abs(table.error), rtol=1e-12, atol=1e-12
    ):
        raise ValueError("Frozen loss mismatch")
    if not table.max_feature_source_date.le(table.origin_date).all():
        raise ValueError("Future feature date")


def save_table(rows, name, meta=None, root=ROOT):
    table = pd.DataFrame(rows)
    for key, value in (meta or {}).items():
        if key not in table:
            table[key] = value
    folder = root / "outputs/tables"
    folder.mkdir(parents=True, exist_ok=True)
    table.to_csv(folder / f"phase7_{name}.csv", index=False, lineterminator="\n")
    return table


def freeze_predictions(table, meta, root=ROOT):
    path = root / PREDICTIONS
    if path.exists():
        raise ValueError(
            "Existing frozen predictions: use --summarize; do not overwrite"
        )
    save_table(table, "final_predictions", meta, root)
    digest = sha(path.read_bytes())
    freeze = {
        "predictions_sha256": digest,
        "frozen_utc": utc(),
        "rows": len(table),
        **meta,
    }
    cache = root / ".cache/phase7"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "prediction_freeze.json").write_text(
        json.dumps(freeze, indent=2), encoding="utf8"
    )
    save_table([freeze], "prediction_freeze", root=root)
    return digest


def load_frozen_predictions(root=ROOT):
    manifest = pd.read_csv(root / "outputs/tables/phase7_prediction_freeze.csv").iloc[0]
    raw = (root / PREDICTIONS).read_bytes()
    if sha(raw) != manifest.predictions_sha256:
        raise ValueError("Frozen prediction SHA256 mismatch")
    table = pd.read_csv(io.BytesIO(raw), float_precision="round_trip")
    validate_prediction_panel(table, load_protocol(root))
    return table, manifest.predictions_sha256


def final_metrics(table):
    rows = []
    for (model, horizon), group in table.groupby(["model", "horizon"]):
        rows.append(
            {
                "model": model,
                "horizon": horizon,
                "n_forecasts": len(group),
                "MSE": group.squared_error.mean(),
                "RMSE": np.sqrt(group.squared_error.mean()),
                "MAE": group.absolute_error.mean(),
                "MAPE": 100 * (group.absolute_error / group.actual_price).mean(),
            }
        )
    result = pd.DataFrame(rows)
    for metric in ["RMSE", "MAE"]:
        result[f"rank_{metric}"] = (
            result.groupby("horizon")[metric].rank(method="min").astype(int)
        )
    return result


def diebold_mariano(loss_a, loss_b, horizon):
    a, b = np.asarray(loss_a, dtype=float), np.asarray(loss_b, dtype=float)
    if (
        a.shape != b.shape
        or a.ndim != 1
        or len(a) <= horizon
        or horizon < 1
        or not np.isfinite(a).all()
        or not np.isfinite(b).all()
    ):
        raise ValueError("Invalid aligned DM losses")
    d = a - b
    n, lag = len(d), horizon - 1
    centered = d - d.mean()
    gamma = np.array(
        [np.dot(centered[k:], centered[: n - k]) / n for k in range(lag + 1)]
    )
    lrv = gamma[0] + 2 * np.sum((1 - np.arange(1, lag + 1) / (lag + 1)) * gamma[1:])
    hln = np.sqrt((n + 1 - 2 * horizon + horizon * (horizon - 1) / n) / n)
    status = "defined"
    if np.array_equal(d, np.zeros(n)):
        statistic, raw, pv, status = (
            0.0,
            0.0,
            1.0,
            "degenerate_identical_observed_losses",
        )
    elif lrv <= 0:
        statistic, raw, pv, status = (
            np.nan,
            np.nan,
            np.nan,
            "undefined_nonpositive_long_run_variance",
        )
    else:
        raw = d.mean() / np.sqrt(lrv / n)
        statistic = raw * hln
        pv = 2 * stats.t.sf(abs(statistic), n - 1)
    return {
        "n_forecasts": n,
        "loss": "squared_error",
        "mean_loss_diff": d.mean(),
        "dm_statistic": statistic,
        "dm_uncorrected": raw,
        "p_value": pv,
        "hac_lag": lag,
        "long_run_variance": lrv,
        "hln_factor": hln,
        "reference_df": n - 1,
        "status": status,
    }


def dm_table(table, p):
    rows = []
    for h in p["horizons"]:
        for a, b in p["dm"]["pairs"]:
            ga = table.loc[table.model.eq(a) & table.horizon.eq(h)].sort_values(
                "origin_index"
            )
            gb = table.loc[table.model.eq(b) & table.horizon.eq(h)].sort_values(
                "origin_index"
            )
            result = diebold_mariano(ga.squared_error, gb.squared_error, h)
            result.update(
                model_a=a,
                model_b=b,
                horizon=h,
                better_mean_loss=a
                if result["mean_loss_diff"] < 0
                else b
                if result["mean_loss_diff"] > 0
                else "equal_observed_mean_loss",
            )
            rows.append(result)
    result = pd.DataFrame(rows)
    result["p_value_holm_if_applicable"] = np.nan
    for h in p["horizons"]:
        selected = result.horizon.eq(h) & result.model_b.eq("Naive")
        raw = result.loc[selected, "p_value"].to_numpy()
        adjusted = multipletests(np.where(np.isfinite(raw), raw, 1.0), method="holm")[1]
        result.loc[selected, "p_value_holm_if_applicable"] = np.where(
            np.isfinite(raw), adjusted, np.nan
        )
    result["raw_reject_5pct"] = result.p_value.lt(0.05)
    decision_p = result.p_value_holm_if_applicable.where(
        result.model_b.eq("Naive"), result.p_value
    )
    result["decision_5pct"] = np.where(
        decision_p.isna(),
        "undefined",
        np.where(decision_p < 0.05, "reject_equal_accuracy", "not_rejected"),
    )
    result["decision_basis"] = np.where(
        result.model_b.eq("Naive"),
        "Holm family of four at this horizon",
        "raw separate GRU-vs-LSTM comparison",
    )
    return result


def interval_coverage(table):
    rows = []
    for h, group in table.loc[table.model.eq("ARIMA(2,1,2)")].groupby("horizon"):
        lower, upper = group.interval_lower_95, group.interval_upper_95
        if (
            not np.isfinite(lower).all()
            or not np.isfinite(upper).all()
            or not lower.le(upper).all()
        ):
            raise ValueError("Invalid ARIMA intervals")
        rows.append(
            {
                "model": "ARIMA(2,1,2)",
                "horizon": h,
                "n_forecasts": len(group),
                "95pct_coverage": (
                    (group.actual_price >= lower) & (group.actual_price <= upper)
                ).mean(),
                "mean_interval_width": (upper - lower).mean(),
                "nominal_coverage": 0.95,
            }
        )
    return pd.DataFrame(rows)


def recommendation(metrics, dm, p):
    rows = []
    baseline = metrics.loc[metrics.model.eq("Naive")].set_index("horizon")
    for name in MODELS:
        group = metrics.loc[metrics.model.eq(name)].set_index("horizon")
        rmse_ratios = group.RMSE / baseline.RMSE
        mae_ratios = group.MAE / baseline.MAE
        tests = dm.loc[dm.model_a.eq(name) & dm.model_b.eq("Naive")]
        supported = (
            (tests.mean_loss_diff < 0) & tests.p_value_holm_if_applicable.lt(0.05)
        ).any()
        eligible = (
            name != "Naive"
            and rmse_ratios.le(1).all()
            and mae_ratios.le(1).all()
            and rmse_ratios.mean()
            <= 1 - p["recommendation"]["minimum_mean_RMSE_improvement"]
            and supported
            and len(tests) == 2
            and tests.status.eq("defined").all()
        )
        rows.append(
            {
                "model": name,
                "average_RMSE_ratio": rmse_ratios.mean(),
                "average_MAE_ratio": mae_ratios.mean(),
                "RMSE_no_worse_both": rmse_ratios.le(1).all(),
                "MAE_no_worse_both": mae_ratios.le(1).all(),
                "Holm_DM_improvement_supported": supported,
                "eligible_challenger": bool(eligible),
                "parsimony_order": p["recommendation"]["parsimony_order"].index(name),
            }
        )
    checks = pd.DataFrame(rows)
    eligible = checks.loc[checks.eligible_challenger]
    selected = "Naive"
    if not eligible.empty:
        tolerance = p["recommendation"]["score_tie_tolerance"]
        eligible = eligible.loc[
            eligible.average_RMSE_ratio <= eligible.average_RMSE_ratio.min() + tolerance
        ]
        eligible = eligible.loc[
            eligible.average_MAE_ratio <= eligible.average_MAE_ratio.min() + tolerance
        ]
        selected = eligible.sort_values("parsimony_order").iloc[0].model
    record = {
        "final_recommended_price_model": selected,
        "rule": "predeclared RMSE/MAE both horizons, >=1% mean gain, Holm DM support; otherwise naive",
        "reason": "No challenger satisfies every predeclared requirement; retain parsimonious naive"
        if selected == "Naive"
        else "Selected qualifying challenger by predeclared normalized RMSE/MAE and parsimony rule",
    }
    return record, checks


def figures(table, metrics):
    folder = ROOT / "outputs/figures/phase7"
    folder.mkdir(parents=True, exist_ok=True)
    colors = {
        "Naive": "black",
        "ARIMA(2,1,2)": "steelblue",
        "VAR(9)": "seagreen",
        "LSTM C": "darkorange",
        "GRU C": "purple",
    }
    for h in [5, 10]:
        for metric in ["RMSE", "MAE"]:
            fig, ax = plt.subplots(figsize=(10, 4.5))
            data = metrics.loc[metrics.horizon.eq(h)].set_index("model").loc[MODELS]
            ax.bar(MODELS, data[metric], color=[colors[m] for m in MODELS])
            ax.set(
                ylabel=f"{metric} (adjusted USD)",
                title=f"Final holdout — h={h}; 211 common daily origins",
            )
            fig.tight_layout()
            fig.savefig(
                folder / f"phase7_{metric.lower()}_comparison_h{h}.png", dpi=150
            )
            plt.close(fig)
        for kind in ["actual_vs_forecasts", "absolute_errors_over_time"]:
            fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
            for ax, names in zip(
                axes,
                [["Naive", "ARIMA(2,1,2)", "VAR(9)"], ["Naive", "LSTM C", "GRU C"]],
                strict=True,
            ):
                if kind == "actual_vs_forecasts":
                    actual = table.loc[table.model.eq("Naive") & table.horizon.eq(h)]
                    ax.plot(
                        pd.to_datetime(actual.target_date),
                        actual.actual_price,
                        color="gray",
                        label="Actual",
                        linewidth=2,
                    )
                for name in names:
                    data = table.loc[table.model.eq(name) & table.horizon.eq(h)]
                    ax.plot(
                        pd.to_datetime(data.target_date),
                        data.forecast_price
                        if kind == "actual_vs_forecasts"
                        else data.absolute_error,
                        color=colors[name],
                        label=name,
                        alpha=0.85,
                    )
                ax.set(
                    ylabel="Adjusted USD"
                    if kind == "actual_vs_forecasts"
                    else "Absolute error (USD)",
                    title="Classical models"
                    if names[1].startswith("ARIMA")
                    else "Recurrent networks",
                )
                ax.legend(loc="best", fontsize=8)
            fig.suptitle(
                f"Final holdout — h={h}; fixed parameters, observed-prefix information"
            )
            fig.tight_layout()
            fig.savefig(folder / f"phase7_{kind}_h{h}.png", dpi=150)
            plt.close(fig)


def tradeoffs(metrics, fit_log, costs, selected):
    rows = []
    interpretations = {
        "Naive": "high",
        "ARIMA(2,1,2)": "medium",
        "VAR(9)": "medium",
        "LSTM C": "low",
        "GRU C": "low",
    }
    complexities = {
        "Naive": "none",
        "ARIMA(2,1,2)": "univariate linear",
        "VAR(9)": "multivariate linear",
        "LSTM C": "nonlinear recurrent",
        "GRU C": "nonlinear recurrent",
    }
    for name in MODELS:
        data = metrics.loc[metrics.model.eq(name)].set_index("horizon")
        fit = fit_log.loc[fit_log.model.eq(name)].iloc[0] if name != "Naive" else None
        rows.append(
            {
                "model": name,
                "RMSE_h5": data.loc[5, "RMSE"],
                "RMSE_h10": data.loc[10, "RMSE"],
                "MAE_h5": data.loc[5, "MAE"],
                "MAE_h10": data.loc[10, "MAE"],
                "training_cost": float(fit.training_seconds)
                if fit is not None
                else 0.0,
                "training_cost_source": fit.training_source
                if fit is not None
                else "no estimation required",
                "prediction_cost": costs[name],
                "prediction_cost_unit": "measured total seconds for 211 origins; ARIMA includes state updates",
                "interpretability": interpretations[name],
                "model_complexity": complexities[name],
                "parameters_if_available": int(fit.parameters)
                if fit is not None
                else 0,
                "parameter_definition": "ARIMA includes innovation variance; VAR is 84 mean coefficients; neural is trainable weights",
                "final_comment": "recommended by predeclared rule"
                if name == selected
                else "evaluated without retuning; see metrics and DM",
            }
        )
    return pd.DataFrame(rows)


def summarize():
    """Recompute only from immutable forecasts; never read TEST or call fit."""
    p = load_protocol()
    gate = verify_protocol_commit()
    table, digest = load_frozen_predictions()
    freeze = pd.read_csv(ROOT / "outputs/tables/phase7_prediction_freeze.csv").iloc[0]
    meta = {
        "scope": SCOPE,
        "protocol_commit": gate["protocol_commit"],
        "protocol_sha256": sha((ROOT / PROTOCOL).read_bytes()),
        "implementation_sha256": freeze.implementation_sha256,
        "summary_implementation_sha256": sha(Path(__file__).read_bytes()),
        "predictions_sha256": digest,
    }
    checks_runtime = json.loads((ROOT / RUNTIME_AUDIT).read_text(encoding="utf8"))
    if (
        sha(checks_runtime["forecast_implementation_source"].encode("utf8"))
        != freeze.implementation_sha256
        or checks_runtime["forecast_implementation_sha256"]
        != freeze.implementation_sha256
        or not table.implementation_sha256.eq(freeze.implementation_sha256).all()
    ):
        raise ValueError("Original forecast implementation provenance mismatch")
    if not any(e["event"] == "metrics_started" for e in checks_runtime["events"]):
        checks_runtime["events"].append({"event": "metrics_started", "utc": utc()})
        (ROOT / RUNTIME_AUDIT).write_text(
            json.dumps(checks_runtime, indent=2), encoding="utf8"
        )
        save_table(checks_runtime["events"], "access_events", meta)
    metrics = final_metrics(table)
    # Each derivative starts from verified frozen bytes, not a mutable forecast object.
    dm = dm_table(load_frozen_predictions()[0], p)
    coverage = interval_coverage(load_frozen_predictions()[0])
    selected, checks = recommendation(metrics, dm, p)
    save_table(metrics, "final_metrics", meta)
    save_table(dm, "diebold_mariano", meta)
    save_table(coverage, "arima_interval_coverage", meta)
    save_table([selected], "final_model_recommendation", meta)
    save_table(checks, "recommendation_checks", meta)
    fit_log = pd.read_csv(ROOT / "outputs/tables/phase7_model_fit_log.csv")
    costs = (
        pd.read_csv(ROOT / "outputs/tables/phase7_prediction_costs.csv")
        .set_index("model")
        .prediction_seconds.to_dict()
    )
    save_table(
        tradeoffs(metrics, fit_log, costs, selected["final_recommended_price_model"]),
        "model_tradeoffs",
        meta,
    )
    save_table(
        [
            {
                "model": name,
                "target": "price reconstructed from returns"
                if name == "VAR(9)"
                else "price",
            }
            for name in MODELS
        ]
        + [
            {
                "model": "GARCH",
                "target": "conditional volatility / risk",
                "note": "GARCH is not ranked against price-forecast models because it forecasts a different statistical target.",
            }
        ],
        "target_scope_note",
        meta,
    )
    figures(table, metrics)
    audit_path = ROOT / "outputs/tables/phase7_holdout_evaluation_audit.csv"
    audit = pd.read_csv(audit_path).to_dict("records") if audit_path.exists() else []
    if audit and any(row["status"] != "PASS" for row in audit):
        raise ValueError("Existing holdout audit FAIL")
    manifest = pd.read_csv(ROOT / "outputs/tables/phase7_holdout_manifest.csv").iloc[0]
    events = checks_runtime["events"]
    required = [
        (
            "protocol committed before test access",
            gate["verified_utc"] < events[2]["utc"]
            and gate["protocol_commit"] == manifest.protocol_commit,
            "committed bytes, original clean gate and ordered access log",
        ),
        (
            "parameters fit on TRAIN only",
            events[1]["event"] == "models_frozen"
            and events[2]["event"] == "test_access",
            "all fitting/loading precedes TEST access",
        ),
        *[
            (key, value, "pre/post numeric parameter or weight hashes")
            for key, value in checks_runtime["frozen"].items()
        ],
        (
            "scalers fit TRAIN only",
            checks_runtime["scalers"]["X_n_fit"]
            == checks_runtime["scalers"]["y_n_fit"]
            == 1960,
            "measured fit counts and Phase 6 TRAIN endpoint",
        ),
        (
            "holdout past allowed only up to current origin",
            table.max_feature_source_date.le(table.origin_date).all(),
            "observed_prefix passed to every predictor",
        ),
        (
            "future holdout features forbidden",
            checks_runtime["features_validated"]
            and table.max_feature_source_date.le(table.origin_date).all(),
            "backward returns/trailing volatility plus prefix assertions",
        ),
        (
            "same origins across models",
            table.groupby(["model", "horizon"]).size().eq(211).all(),
            "panel indices/dates checked before freeze and after reload",
        ),
        (
            "same targets across models",
            True,
            "validate_prediction_panel compares target dates/indices/actual values exactly",
        ),
        (
            "no retuning from holdout",
            True,
            "source-scope audit: no fitting code after test access",
        ),
        (
            "no hyperparameter modification",
            True,
            "committed protocol byte equality and fixed specifications",
        ),
        (
            "predictions frozen before metrics",
            freeze.frozen_utc < events[4]["utc"]
            and events[3]["event"] == "predictions_frozen"
            and events[4]["event"] == "metrics_started"
            and sha((ROOT / PREDICTIONS).read_bytes()) == digest,
            "metrics reloaded from verified immutable CSV",
        ),
        (
            "DM computed from frozen predictions",
            dm.shape[0] == 10 and sha((ROOT / PREDICTIONS).read_bytes()) == digest,
            "ten prescribed tests from verified CSV",
        ),
    ]
    audit = [
        {
            "check": name,
            "status": "PASS" if bool(passed) else "FAIL",
            "evidence": evidence,
        }
        for name, passed, evidence in required
    ]
    save_table(audit, "holdout_evaluation_audit", meta)
    if any(row["status"] != "PASS" for row in audit):
        raise ValueError("STOP: holdout evaluation audit FAIL")
    print(metrics.to_string(index=False), flush=True)
    print(
        "Final recommended price model:",
        selected["final_recommended_price_model"],
        flush=True,
    )
    print(
        "PHASE 7 PASS: frozen predictions, complete common panel, audit all PASS",
        flush=True,
    )


def run():
    if (ROOT / PREDICTIONS).exists():
        raise ValueError(
            "Predictions already frozen; use --summarize, no re-estimation"
        )
    p, gate = load_protocol(), verify_protocol_commit()
    CACHE.mkdir(parents=True, exist_ok=True)
    audit = []
    train, raw_train = read_observations(TRAIN, audit)
    if sha(raw_train) != p["train_sha256"] or len(train) != p["train_rows"]:
        raise ValueError("Frozen TRAIN mismatch")
    validate_features(train)
    arima, var, fit_log = fit_classical(train, p)
    networks, sx, sy, neural_log, scalers, tf_version = prepare_neural(train, p)
    fit_log.extend(neural_log)
    audit.append({"event": "models_frozen", "utc": utc()})
    print(
        "TRAIN models frozen; opening authorized TEST after protocol commit", flush=True
    )
    test, raw_test = read_observations(TEST, audit, gate=gate, models_ready=True)
    if sha(raw_test) != p["historical_test_sha256"]:
        raise ValueError("STOP: historical TEST fingerprint mismatch")
    combined = validate_split(train, test, p)
    grid = origin_grid(combined.Date, len(train), p["expected_common_origins"])
    meta = {
        "scope": SCOPE,
        "protocol_commit": gate["protocol_commit"],
        "protocol_sha256": sha((ROOT / PROTOCOL).read_bytes()),
        "protocol_md_sha256": sha((ROOT / PROTOCOL_MD).read_bytes()),
        "implementation_sha256": sha(Path(__file__).read_bytes()),
        "train_sha256": sha(raw_train),
        "test_sha256": sha(raw_test),
    }
    save_table(
        [
            {
                "train_rows": len(train),
                "test_rows": len(test),
                "columns": len(test.columns),
                "train_first_date": train.Date.iloc[0],
                "train_last_date": train.Date.iloc[-1],
                "test_first_date": test.Date.iloc[0],
                "test_last_date": test.Date.iloc[-1],
                "common_origins": len(grid),
                "protocol_gate_verified_utc": gate["verified_utc"],
                "first_test_access_utc": audit[2]["utc"],
            }
        ],
        "holdout_manifest",
        meta,
    )
    save_table(grid, "evaluation_origins", meta)
    save_table(fit_log, "model_fit_log", meta)
    save_table([scalers], "scaler_audit", meta)
    save_table(
        [
            {"package": k, "version": v}
            for k, v in [
                ("python", platform.python_version()),
                ("tensorflow", tf_version),
                ("statsmodels", statsmodels.__version__),
                ("numpy", np.__version__),
                ("pandas", pd.__version__),
                ("scipy", scipy.__version__),
                ("device", "CPU"),
            ]
        ],
        "runtime_versions",
        meta,
    )
    predictions, costs, frozen = generate_forecasts(
        combined, grid, arima, var, networks, sx, sy
    )
    if not all(frozen.values()):
        raise ValueError("Parameters changed during evaluation")
    validate_prediction_panel(predictions, p)
    freeze_predictions(predictions, meta)
    audit.append({"event": "predictions_frozen", "utc": utc()})
    save_table(
        [{"model": name, "prediction_seconds": value} for name, value in costs.items()],
        "prediction_costs",
        meta,
    )
    save_table(audit, "access_events", meta)
    (ROOT / RUNTIME_AUDIT).write_text(
        json.dumps(
            {
                "events": audit,
                "frozen": frozen,
                "scalers": scalers,
                "features_validated": True,
                "protocol_gate": gate,
                "forecast_implementation_sha256": meta["implementation_sha256"],
                "forecast_implementation_source": Path(__file__)
                .read_bytes()
                .decode("utf8"),
            },
            indent=2,
        ),
        encoding="utf8",
    )
    summarize()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Recompute derivatives from frozen predictions, without TEST/model access",
    )
    args = parser.parse_args()
    summarize() if args.summarize else run()
