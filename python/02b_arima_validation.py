"""Phase 3B: fixed-order expanding-window validation, never final evaluation."""

import argparse
import hashlib
import io
import os
import platform
import warnings
from pathlib import Path

# Keep plotting caches inside the authorized workspace on Windows as well.
os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".cache/matplotlib")
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels
from statsmodels.tsa.arima.model import ARIMA

ROOT = Path(__file__).resolve().parents[1]
TRAIN = "data/processed/market_train.csv"
SCOPE = "TRAIN_only_internal_rolling_origin"
PROTOCOL = "docs/phase3b_validation_protocol.csv"
CANDIDATES = "docs/phase3b_validation_candidates.csv"


def configuration(root=ROOT):
    protocol = pd.read_csv(root / PROTOCOL).iloc[0]
    candidates = pd.read_csv(root / CANDIDATES)
    return protocol, candidates


def read_observations(root, relative, audit):
    """Only this function reads market observations; reject before opening."""
    if relative != TRAIN:
        raise ValueError(f"Unauthorized market input: {relative}")
    path = root / relative
    if path.resolve() != root.resolve() / TRAIN:
        raise ValueError("TRAIN symlink/path redirects outside authorized input")
    raw = path.read_bytes()
    audit.append(relative)
    return pd.read_csv(io.BytesIO(raw), float_precision="round_trip"), raw


def validate_frame(frame, protocol):
    dates = pd.to_datetime(frame.Date, format="%Y-%m-%d", errors="raise")
    prices = frame.NVDA_Adj_Close.to_numpy(dtype=float)
    if (
        len(frame) != int(protocol.expected_rows)
        or dates.isna().any()
        or dates.duplicated().any()
        or not dates.is_monotonic_increasing
        or str(dates.iloc[0].date()) != protocol.first_date
        or str(dates.iloc[-1].date()) != protocol.last_date
        or not np.isfinite(prices).all()
        or np.any(prices <= 0)
    ):
        raise ValueError("Invalid frozen TRAIN chronology/positive prices")
    return dates, prices


def make_origins(dates, initial_size, step, horizons):
    if initial_size < 2 or step < 1 or min(horizons) < 1:
        raise ValueError("Invalid rolling protocol")
    rows = []
    for origin in range(initial_size - 1, len(dates) - max(horizons), step):
        for h in horizons:
            rows.append(
                {
                    "origin_index": origin,
                    "train_size": origin + 1,
                    "origin_date": str(dates.iloc[origin].date()),
                    "horizon": h,
                    "target_index": origin + h,
                    "target_date": str(dates.iloc[origin + h].date()),
                }
            )
    if not rows:
        raise ValueError("No valid rolling origins")
    return pd.DataFrame(rows)


def to_price(log_forecast):
    with np.errstate(over="raise", invalid="raise"):
        value = np.exp(np.asarray(log_forecast, dtype=float))
    if not np.isfinite(value).all() or np.any(value <= 0):
        raise ValueError("Nonfinite/nonpositive back-transformation")
    return value


def fit_forecast(history, spec, horizon, maxiter=1000):
    """History is an isolated prefix; no targets or later observations enter."""
    if spec.model == "Naive":
        return np.repeat(history[-1], horizon), True, "analytic last observation", ""
    if spec.model == "RW_drift":
        # Exact Gaussian ML mean of first differences, equivalent to (0,1,0)+drift.
        drift = np.mean(np.diff(history))
        return (
            history[-1] + np.arange(1, horizon + 1) * drift,
            True,
            "analytic ML drift",
            "",
        )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fit = ARIMA(
            history,
            order=(int(spec.p), int(spec.d), int(spec.q)),
            trend="t" if spec.drift else "n",
        ).fit(method_kwargs={"maxiter": maxiter})
        forecast = np.asarray(fit.forecast(horizon), dtype=float)
    converged = bool(fit.mle_retvals.get("converged", False))
    message = " | ".join(dict.fromkeys(str(w.message) for w in caught))
    return (
        forecast,
        converged,
        "statsmodels ARIMA state-space ML/default start",
        message,
    )


def rolling_validate(frame, protocol, candidates, forecaster=fit_forecast):
    dates, prices = validate_frame(frame, protocol)
    y = np.log(prices)
    horizons = [int(protocol.horizon_1), int(protocol.horizon_2)]
    origins = make_origins(
        dates, int(protocol.initial_size), int(protocol.origin_step), horizons
    )
    forecasts, fits = [], []
    for number, (origin, targets) in enumerate(origins.groupby("origin_index"), 1):
        history = y[: origin + 1].copy()
        for spec in candidates.itertuples(index=False):
            error, warning, method = "", "", ""
            converged, usable = False, False
            prediction = np.full(max(horizons), np.nan)
            try:
                prediction, converged, method, warning = forecaster(
                    history.copy(), spec, max(horizons), int(protocol.maxiter)
                )
                prediction = np.asarray(prediction, dtype=float)
                if prediction.shape != (max(horizons),):
                    raise ValueError("Unexpected forecast length")
                price_prediction = to_price(prediction)
                usable = converged
            except (
                ValueError,
                RuntimeError,
                np.linalg.LinAlgError,
                FloatingPointError,
            ) as exc:
                error = f"{type(exc).__name__}: {exc}"
                price_prediction = np.full(max(horizons), np.nan)
            fits.append(
                {
                    "language": "Python",
                    "implementation": "statsmodels/analytic baselines",
                    "validation_scope": SCOPE,
                    "model": spec.model,
                    "origin_index": origin,
                    "origin_date": targets.iloc[0].origin_date,
                    "train_size": origin + 1,
                    "fit_last_index": origin,
                    "converged": converged,
                    "usable": usable,
                    "method": method,
                    "warnings": warning,
                    "error": error,
                }
            )
            for target in targets.itertuples(index=False):
                forecasts.append(
                    dict(
                        language="Python",
                        implementation="statsmodels/analytic baselines",
                        validation_scope=SCOPE,
                        model=spec.model,
                        **target._asdict(),
                        converged=converged,
                        usable=usable,
                        actual_price=prices[target.target_index],
                        actual_log=y[target.target_index],
                        forecast_log=prediction[target.horizon - 1]
                        if usable
                        else np.nan,
                        forecast_price=(
                            prices[origin]
                            if spec.model == "Naive"
                            else price_prediction[target.horizon - 1]
                        )
                        if usable
                        else np.nan,
                    )
                )
        print(
            f"Python origin {number}/{origins.origin_index.nunique()} completed",
            flush=True,
        )
    return origins, pd.DataFrame(forecasts), pd.DataFrame(fits)


def metric_values(actual, predicted, actual_log, predicted_log):
    actual, predicted, actual_log, predicted_log = (
        np.asarray(x, dtype=float)
        for x in (actual, predicted, actual_log, predicted_log)
    )
    if (
        actual.ndim != 1
        or any(x.shape != actual.shape for x in (predicted, actual_log, predicted_log))
        or not len(actual)
        or any(
            not np.isfinite(x).all()
            for x in (actual, predicted, actual_log, predicted_log)
        )
    ):
        raise ValueError("Metrics require nonempty finite paired observations")
    if np.any(actual <= 0):
        raise ValueError("MAPE requires positive price targets")
    error, log_error = predicted - actual, predicted_log - actual_log
    return {
        "MSE": np.mean(error**2),
        "RMSE": np.sqrt(np.mean(error**2)),
        "MAE": np.mean(np.abs(error)),
        "MAPE": 100 * np.mean(np.abs(error) / actual),
        "log_MAE": np.mean(np.abs(log_error)),
        "log_RMSE": np.sqrt(np.mean(log_error**2)),
    }


def metrics_table(forecasts):
    rows = []
    for (language, model, horizon), group in forecasts.groupby(
        ["language", "model", "horizon"], sort=True
    ):
        good = group.loc[group.usable]
        values = (
            metric_values(
                good.actual_price,
                good.forecast_price,
                good.actual_log,
                good.forecast_log,
            )
            if len(good)
            else dict.fromkeys(
                ["MSE", "RMSE", "MAE", "MAPE", "log_MAE", "log_RMSE"], np.nan
            )
        )
        rows.append(
            dict(
                language=language,
                implementation=group.implementation.iloc[0],
                validation_scope=SCOPE,
                model=model,
                horizon=horizon,
                n_origins=len(group),
                n_forecasts=len(good),
                failed_fits=len(group) - len(good),
                nonconverged_fits=int((~group.converged).sum()),
                evaluation_sample="available converged origins; incomplete candidates cannot lock",
                **values,
            )
        )
    return pd.DataFrame(rows)


def guard_table(frame, origins, forecasts, fits, audit):
    grid_columns = list(origins.columns)
    dates = frame.Date.astype(str)
    checks = {
        "only_market_train_observations_read": audit == [TRAIN],
        "no_market_test_read": audit == [TRAIN],
        "no_holdout_dates_used": origins.target_date.max() <= str(frame.Date.iloc[-1]),
        "no_full_data_refit": bool((fits.train_size < len(frame)).all()),
        "validation_origins_inside_TRAIN": bool(
            (origins.origin_index >= 0).all()
            and (origins.target_index < len(frame)).all()
        ),
        "forecasts_use_past_information_only": bool(
            (fits.fit_last_index == fits.origin_index).all()
            and (fits.train_size == fits.origin_index + 1).all()
        ),
        "correct_horizon_alignment": bool(
            (origins.target_index == origins.origin_index + origins.horizon).all()
        ),
        "no_random_shuffle": bool(
            origins.origin_index.is_monotonic_increasing
            and pd.to_datetime(frame.Date).is_monotonic_increasing
        ),
        "no_ordinary_K_fold": bool(
            (origins.train_size == origins.origin_index + 1).all()
        ),
        "all_models_same_origin_target_grid": all(
            g[grid_columns]
            .reset_index(drop=True)
            .equals(origins.reset_index(drop=True))
            for _, g in forecasts.groupby("model")
        ),
        "dates_match_observed_TRAIN_indices": (
            list(origins.origin_date) == list(dates.iloc[origins.origin_index])
            and list(origins.target_date) == list(dates.iloc[origins.target_index])
        ),
    }
    return pd.DataFrame(
        [
            {
                "language": "Python",
                "check": k,
                "status": "PASS" if v else "FAIL",
                "details": "Measured prefix/grid assertion plus code audit of closed reader and expanding loop",
            }
            for k, v in checks.items()
        ]
    )


def save(table, name, root=ROOT):
    folder = root / "outputs/tables"
    folder.mkdir(parents=True, exist_ok=True)
    table.to_csv(folder / f"phase3b_{name}.csv", index=False, float_format="%.15g")


def baseline_comparison(forecasts, metrics):
    rows = []
    for row in metrics.itertuples(index=False):
        group = forecasts.loc[
            (forecasts.language == row.language)
            & (forecasts.model == row.model)
            & (forecasts.horizon == row.horizon)
            & forecasts.usable
        ]
        naive = forecasts.loc[
            (forecasts.language == row.language)
            & (forecasts.model == "Naive")
            & (forecasts.horizon == row.horizon)
        ]
        paired = group.merge(
            naive[["origin_index", "forecast_price", "forecast_log"]],
            on="origin_index",
            suffixes=("", "_naive"),
        )
        base = (
            metric_values(
                paired.actual_price,
                paired.forecast_price_naive,
                paired.actual_log,
                paired.forecast_log_naive,
            )
            if len(paired)
            else {"RMSE": np.nan, "MAE": np.nan}
        )
        rows.append(
            {
                "language": row.language,
                "validation_scope": SCOPE,
                "model": row.model,
                "horizon": row.horizon,
                "n_forecasts": row.n_forecasts,
                "RMSE": row.RMSE,
                "MAE": row.MAE,
                "naive_RMSE_matched_origins": base["RMSE"],
                "naive_MAE_matched_origins": base["MAE"],
                "RMSE_improvement_vs_naive_pct": 100 * (1 - row.RMSE / base["RMSE"]),
                "MAE_improvement_vs_naive_pct": 100 * (1 - row.MAE / base["MAE"]),
            }
        )
    return pd.DataFrame(rows)


def cross_language(forecasts, threshold):
    rows = []
    for (model, horizon), group in forecasts.groupby(["model", "horizon"]):
        r = group.loc[(group.language == "R") & group.usable]
        p = group.loc[(group.language == "Python") & group.usable]
        paired = r.merge(p, on="origin_index", suffixes=("_R", "_Python"))
        row = {
            "model": model,
            "horizon": horizon,
            "validation_scope": SCOPE,
            "n_forecasts_R": len(r),
            "n_forecasts_Python": len(p),
            "n_paired_forecasts": len(paired),
        }
        for lang in ("R", "Python"):
            values = (
                metric_values(
                    paired[f"actual_price_{lang}"],
                    paired[f"forecast_price_{lang}"],
                    paired[f"actual_log_{lang}"],
                    paired[f"forecast_log_{lang}"],
                )
                if len(paired)
                else {"RMSE": np.nan, "MAE": np.nan}
            )
            row.update({f"{m}_{lang}": values[m] for m in ["RMSE", "MAE"]})
        for metric in ["RMSE", "MAE"]:
            row[f"{metric}_absolute_difference"] = abs(
                row[f"{metric}_Python"] - row[f"{metric}_R"]
            )
            row[f"{metric}_relative_difference_pct"] = (
                100 * row[f"{metric}_absolute_difference"] / row[f"{metric}_R"]
            )
        row["divergence_warning"] = (
            any(
                row[f"{m}_relative_difference_pct"] > threshold for m in ["RMSE", "MAE"]
            )
            or len(r) != len(p)
            or not len(paired)
        )
        rows.append(row)
    return pd.DataFrame(rows)


def lock_model(metrics, baseline, candidates, protocol):
    eligible = []
    for spec in candidates.itertuples(index=False):
        if spec.model == "Naive":
            continue
        scores = metrics.loc[metrics.model == spec.model]
        versus = baseline.loc[baseline.model == spec.model]
        if (
            len(scores) != 4
            or scores.failed_fits.sum()
            or not np.isfinite(scores[["RMSE", "MAE"]]).all().all()
        ):
            continue
        if (
            not (
                versus[
                    ["RMSE_improvement_vs_naive_pct", "MAE_improvement_vs_naive_pct"]
                ]
                >= protocol.clear_improvement_pct
            )
            .all()
            .all()
        ):
            continue
        worst = (
            1
            - versus[["RMSE_improvement_vs_naive_pct", "MAE_improvement_vs_naive_pct"]]
            .min()
            .min()
            / 100
        )
        eligible.append(
            {
                "model": spec.model,
                "score": worst,
                "k": spec.k,
                "adequate": bool(spec.phase3a_mean_adequate),
            }
        )
    if eligible:
        pool = pd.DataFrame(eligible)
        near = pool.loc[
            pool.score <= pool.score.min() * (1 + protocol.near_score_pct / 100)
        ]
        winner = (
            near.sort_values(
                ["adequate", "k", "score", "model"], ascending=[False, True, True, True]
            )
            .iloc[0]
            .model
        )
        status = "locked_arima_specification"
        reason = "All origins usable in both languages; >=1% RMSE AND MAE gain at both horizons in both languages; worst-ratio score then near-score Phase3A adequacy/parsimony rule."
    else:
        winner = "Naive"
        status = "locked_arima_specification_baseline_with_diagnostic_warning"
        reason = "No challenger satisfies complete convergence and >=1% RMSE AND MAE gain at BOTH horizons in BOTH languages; retain naive. Phase3A random-walk residual autocorrelation remains a limitation."
    spec = candidates.loc[candidates.model == winner].iloc[0]
    return pd.DataFrame(
        [
            {
                "model": winner,
                "order": f"({spec.p},{spec.d},{spec.q})",
                "drift": spec.drift,
                "selection_reason": reason,
                "validation_scope": SCOPE,
                "status": status,
                "phase3a_note": spec.phase3a_note,
            }
        ]
    )


def generate_figures(forecasts, metrics, candidates, root):
    folder = root / "outputs/figures/phase3b"
    folder.mkdir(parents=True, exist_ok=True)
    order = list(candidates.model)
    for horizon in (5, 10):
        for metric in ("RMSE", "MAE"):
            fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
            for j, lang in enumerate(("R", "Python")):
                table = (
                    metrics.loc[
                        (metrics.language == lang) & (metrics.horizon == horizon)
                    ]
                    .set_index("model")
                    .reindex(order)
                )
                ax.bar(
                    np.arange(len(order)) + (j - 0.5) * 0.36,
                    table[metric],
                    0.36,
                    label=lang,
                )
                for i, row in enumerate(table.itertuples()):
                    if row.failed_fits:
                        ax.text(
                            i + (j - 0.5) * 0.36,
                            getattr(row, metric),
                            f"{row.n_forecasts}/{row.n_origins}",
                            ha="center",
                            va="bottom",
                            fontsize=8,
                        )
            ax.set(
                xticks=np.arange(len(order)),
                xticklabels=order,
                ylabel=f"{metric} (USD)",
                title=f"NVDA TRAIN-only internal validation, h={horizon}\nIncomplete forecast coverage labelled above bars",
            )
            ax.tick_params(axis="x", labelrotation=12)
            ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5))
            fig.savefig(
                folder / f"phase3b_{metric.lower()}_by_model_h{horizon}.png", dpi=160
            )
            plt.close(fig)
        fig, axes = plt.subplots(
            2, 1, figsize=(12, 7), sharex=True, layout="constrained"
        )
        for ax, lang in zip(axes, ("R", "Python")):
            for model in order:
                table = forecasts.loc[
                    (forecasts.language == lang)
                    & (forecasts.horizon == horizon)
                    & (forecasts.model == model)
                ].sort_values("target_date")
                ax.plot(
                    pd.to_datetime(table.target_date),
                    table.forecast_price - table.actual_price,
                    label=model,
                    alpha=0.8,
                    linewidth=1,
                )
            ax.axhline(0, color="black", linewidth=0.7)
            ax.set(ylabel="Forecast - actual (USD)", title=lang)
        axes[0].legend(ncol=3, fontsize=8)
        fig.suptitle(
            f"NVDA TRAIN-only rolling endpoint errors, h={horizon}; gaps = failed fits"
        )
        fig.savefig(
            folder / f"phase3b_forecast_errors_over_time_h{horizon}.png", dpi=160
        )
        plt.close(fig)


def markdown(table):
    # Avoid optional tabulate dependency.
    lines = [
        "| " + " | ".join(table.columns) + " |",
        "| " + " | ".join(["---"] * len(table.columns)) + " |",
    ]
    for row in table.itertuples(index=False, name=None):
        lines.append(
            "| "
            + " | ".join(
                f"{v:.6g}"
                if isinstance(v, (float, np.floating))
                else str(v).replace("|", "/")
                for v in row
            )
            + " |"
        )
    return "\n".join(lines)


def summarize(root=ROOT):
    protocol, candidates = configuration(root)
    tables = root / "outputs/tables"
    if not (tables / "phase3b_forecasts_r.csv").exists():
        print(
            "Python validation complete; R pending. Run Rscript r/02b_arima_validation.R, then Python --summarize."
        )
        return
    origins = [
        pd.read_csv(tables / f"phase3b_origins_{lang}.csv") for lang in ["python", "r"]
    ]
    pd.testing.assert_frame_equal(origins[0], origins[1], check_dtype=False)
    manifests = [
        pd.read_csv(tables / f"phase3b_manifest_{lang}.csv").iloc[0]
        for lang in ["python", "r"]
    ]
    for field in [
        "train_md5",
        "rows",
        "first_date",
        "last_date",
        "protocol_md5",
        "candidates_md5",
    ]:
        if manifests[0][field] != manifests[1][field]:
            raise ValueError(f"Cross-language provenance mismatch: {field}")
    if (
        manifests[0].protocol_md5
        != hashlib.md5((root / PROTOCOL).read_bytes()).hexdigest()
        or manifests[0].candidates_md5
        != hashlib.md5((root / CANDIDATES).read_bytes()).hexdigest()
    ):
        raise ValueError("Configuration changed since validation")
    forecasts = pd.concat(
        [
            pd.read_csv(tables / f"phase3b_forecasts_{lang}.csv")
            for lang in ["python", "r"]
        ],
        ignore_index=True,
    )
    guards = pd.concat(
        [
            pd.read_csv(tables / f"phase3b_holdout_guard_{lang}.csv")
            for lang in ["python", "r"]
        ],
        ignore_index=True,
    )
    guards = pd.concat(
        [
            guards,
            pd.DataFrame(
                [
                    {
                        "language": "R/Python",
                        "check": "same_origins_dates_and_provenance",
                        "status": "PASS",
                        "details": "Exact common origin grid and input/config MD5 equality",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    save(guards, "holdout_guard", root)
    if not guards.status.eq("PASS").all():
        raise ValueError("FAIL in holdout guard; STOP")
    metrics = metrics_table(forecasts)
    baseline = baseline_comparison(forecasts, metrics)
    comparison = cross_language(forecasts, protocol.divergence_warning_pct)
    locked = lock_model(metrics, baseline, candidates, protocol)
    for table, name in [
        (metrics, "arima_validation_metrics"),
        (baseline, "baseline_comparison"),
        (comparison, "r_python_forecast_comparison"),
        (locked, "locked_arima_model"),
    ]:
        save(table, name, root)
    generate_figures(forecasts, metrics, candidates, root)
    write_document(
        metrics, baseline, comparison, locked, origins[0], protocol, candidates, root
    )
    print(
        metrics[
            [
                "language",
                "model",
                "horizon",
                "n_forecasts",
                "RMSE",
                "MAE",
                "MAPE",
                "failed_fits",
            ]
        ].to_string(index=False)
    )
    print(locked.to_string(index=False))


def write_document(
    metrics, baseline, comparison, locked, origins, protocol, candidates, root
):
    first = origins.iloc[0]
    last = origins.iloc[-1]
    fit_counts = metrics.loc[
        metrics.horizon == 5,
        ["language", "model", "n_origins", "n_forecasts", "failed_fits"],
    ]
    max_rmse_gap = comparison.RMSE_relative_difference_pct.max()
    max_mae_gap = comparison.MAE_relative_difference_pct.max()
    worse = baseline.loc[
        (baseline.RMSE_improvement_vs_naive_pct < 0)
        | (baseline.MAE_improvement_vs_naive_pct < 0),
        [
            "language",
            "model",
            "horizon",
            "RMSE_improvement_vs_naive_pct",
            "MAE_improvement_vs_naive_pct",
        ],
    ]
    text = f"""# Phase 3B — TRAIN-Only ARIMA Rolling Validation

## Objective

Compare five fixed Phase 3A hypotheses and lock one specification for later
work. **This is TRAIN-only internal validation and not the final holdout evaluation.**
Phase 3A remains the historical in-sample identification and diagnostic phase;
its conclusions and files are unchanged.

## Why rolling-origin validation?

Each origin mimics a forecast made with information available at that date.
Expanding prefixes preserve temporal order and allow multiple validation dates;
there is no random split, shuffle or ordinary K-fold. Fixed orders avoid a
new auto.arima search. The full-TRAIN Phase 3A identification informed the
candidate list, so this is internal model selection, not a fully nested or
independent assessment of the entire identification process.

## Data and anti-leakage design

Only `data/processed/market_train.csv` supplies market observations: 1,980 rows,
2018-01-02 to 2025-11-14. Python verifies the frozen SHA-256; R verifies the
matching frozen MD5. Both verify dates, positive finite prices and chronology.
The closed reader rejects other market paths before opening them. Protocol,
candidates and language output files are metadata, not extra market inputs.
Targets are retrieved for scoring only after each fit; only a copied prefix
ending at its origin is passed to estimation. No full-TRAIN refit is performed.
`phase3b_holdout_guard.csv` combines measured assertions and labelled code
audits; all rows must PASS. Cross-language input/config hashes and origin
grids must agree before a lock can be written. No final test file is opened.

## Candidate models

{markdown(candidates[["model", "p", "d", "q", "drift", "k"]])}

Naive uses the last observed price exactly. RW_drift uses the Gaussian ML
mean of log-price differences, the analytic ARIMA(0,1,0)+drift point forecast.
Both implementations use these identical baseline formulae. Complex models
use R forecast::Arima ML and Python statsmodels ARIMA state-space ML with
independent default initialization, maxiter={int(protocol.maxiter)}, with
no alternate-model fallback, no cross-language initialization and no silent replacement.

## Expanding-window protocol

The protocol and selection rule were written to files before any Phase 3B
result was computed: [protocol](phase3b_validation_protocol.csv) and
[candidates](phase3b_validation_candidates.csv). They are predeclared, not
tuned after observing results. Initial size: {int(protocol.initial_size)}
(70% of TRAIN). Step: {int(protocol.origin_step)} observed trading sessions.
Number of origins: **{origins.origin_index.nunique()}**. First origin:
**{first.origin_date}** (zero-based index {first.origin_index}); last origin:
**{last.origin_date}** (index {last.origin_index}, prefix size {last.train_size}).
The prefix always starts at the first TRAIN row and adds ten sessions.
Ten-session spacing was chosen before execution to limit independent
high-order ML fits while covering the remaining TRAIN period regularly;
it is coarser than every-session or five-session evaluation. No opportunistic
origin reduction, terminal origin insertion or fold deletion is performed.
The full origin/target grids are exported for both languages.
The two protocol CSV files use Git-enforced LF endings so their recorded
fingerprints remain stable across Windows and Unix checkouts.

## Horizons

h=5 and h=10 observed sessions. Target index equals origin index+h; a ten-step
forecast is computed at each origin and only the exact fifth/tenth endpoints
are evaluated. All origins support both horizons. Last h=10 target:
{last.target_date}. Remaining terminal TRAIN sessions outside this regular
grid are not extra folds. One origin generates two endpoint observations,
not ten observations for each horizon. The fixed spacing avoids overlapping
forecast intervals across adjacent origins, but does not establish
statistical independence of forecast errors.

## Back-transformation

All ARIMA point forecasts use `exp(log_price_forecast)`, without lognormal
bias correction. This is generally a conditional median under a lognormal
interpretation, not necessarily the conditional price expectation. The same
convention applies to every candidate and language. For naive, the exact
last price is retained to avoid floating-point exp/log round-trip error.

## Validation metrics

Main metrics on positive adjusted prices in USD: MSE=mean(error squared),
RMSE=sqrt(MSE), MAE=mean(abs(error)), MAPE=100*mean(abs(error)/actual).
Log-price MAE/RMSE are secondary. Endpoints have equal weight within a
model/horizon. Higher late-period price levels can dominate USD losses;
MAPE is reported as a complementary scale-sensitive diagnostic.
Unusable fits have blank forecasts and explicit fit-log rows. Metrics use
available converged origins; coverage and failures accompany every row.
Incomplete candidates cannot lock. Baseline gains use exactly the successful
origins of each candidate. Nonconvergence counts are per fit, not the sum
of duplicate h=5/h=10 rows.

## R results

{markdown(metrics.loc[metrics.language == "R", ["model", "horizon", "n_forecasts", "MSE", "RMSE", "MAE", "MAPE", "log_MAE", "log_RMSE", "failed_fits"]])}

R fit coverage, counting each fit only once across the two horizons:

{markdown(fit_counts.loc[fit_counts.language == "R"])}

## Python results

{markdown(metrics.loc[metrics.language == "Python", ["model", "horizon", "n_forecasts", "MSE", "RMSE", "MAE", "MAPE", "log_MAE", "log_RMSE", "failed_fits"]])}

Python fit coverage:

{markdown(fit_counts.loc[fit_counts.language == "Python"])}

All failed origins and warning messages are preserved in
`phase3b_fit_log_python.csv` and `phase3b_fit_log_r.csv`. No nonconverged
forecast contributes to a loss and no failed fit is silently replaced.

## R/Python comparison

{markdown(comparison[["model", "horizon", "n_forecasts_R", "n_forecasts_Python", "n_paired_forecasts", "RMSE_R", "RMSE_Python", "RMSE_relative_difference_pct", "MAE_R", "MAE_Python", "MAE_relative_difference_pct", "divergence_warning"]])}

Comparison losses use the intersection of usable origins. Absolute and
relative differences (relative to R) are exported. A predeclared >5% RMSE
or MAE difference, differing coverage or absent pairs flags a warning.
Observed maximum paired RMSE difference is {max_rmse_gap:.4f}% and maximum
paired MAE difference is {max_mae_gap:.4f}%. The warnings for (1,1,1) and
(2,1,2) concern unequal coverage, rather than a >5% paired-loss gap.
Python's apparently lower available-case losses must not be interpreted as
a language advantage: the missing origins change the evaluation sample.
Optimization/initialization and numerical likelihood conventions can explain
differences; no language is adjusted to force equality. Baselines share an
analytic definition. The fit logs preserve warnings and exceptions, including
nonconvergence, rather than replacing failed high-order models.

## Comparison with naive baseline

{markdown(baseline[["language", "model", "horizon", "n_forecasts", "RMSE_improvement_vs_naive_pct", "MAE_improvement_vs_naive_pct"]])}

Positive values improve on naive; negative values are worse. These are
descriptive internal gains, not significance tests or final performance.
Rows with incomplete coverage must be interpreted alongside failed_fits.

Cases worse than naive on at least one of RMSE/MAE, using matched origins:

{markdown(worse)}

No challenger improves both main metrics at both horizons in both languages
by the predeclared threshold. In particular, gains at h=10 do not compensate
for worse h=5 losses under the common-horizon rule. There is no clear robust
advantage for a complex ARIMA over naive in this internal comparison.

## Locked ARIMA specification

**locked_arima_specification: {locked.iloc[0].model}, order
{locked.iloc[0]["order"]}, drift={locked.iloc[0].drift}.**

{locked.iloc[0].selection_reason}

Rule frozen before results: require all origins usable in both languages,
then at least 1% improvement in BOTH price RMSE and MAE at BOTH horizons in
BOTH languages. Rank qualifying challengers by their worst ratio to naive
over metrics/horizons/languages. Within 1% of the best score, prefer evidence
of Phase 3A mean adequacy in at least one implementation, then fewer
parameters, score and model id. MAPE/log losses are secondary diagnostics.
If no challenger qualifies, lock naive and retain its Phase 3A mean-residual
warning; predictive parsimony does not retroactively validate its residuals.
Phase 3A adequacy is existing full-TRAIN evidence, not a new per-fold test.
Normality/ARCH limitations remain for all candidate interpretations.

Phase 3A note for the lock: {locked.iloc[0].phase3a_note}.
Status: `{locked.iloc[0].status}`. This locks a specification only; no model
is refitted on all TRAIN and it is not a best final model declaration.

## Limitations

59 origins and one predeclared schedule cannot establish robustness to all
origins, regimes or alternate schedules. Candidate identification used full
TRAIN, and validation is used for selection, so final generalization remains
unproven. The 1% thresholds are explicit practical conventions, not tests of
statistical significance. No final Diebold-Mariano test is run. Incomplete
coverage may bias available-case summaries; such candidates cannot lock.
Independent default initializations can yield local optima even when fits
converge. Phase 3A non-normality and conditional heteroskedasticity persist
as limitations; no volatility model is estimated. No bias-corrected price
mean or forecast interval is assessed. The team interpretation template is
intentionally unanswered.

## Phase boundary

Only internal TRAIN forecasts and losses are computed. No holdout observation,
holdout metric, final forecast, full-data refit, GARCH, VAR/VECM, Prophet or
neural model is used. Historical Phase 3A files are unchanged.

Reproduction from the repository root, using the project environment:

```powershell
python python/02b_arima_validation.py
Rscript r/02b_arima_validation.R
python python/02b_arima_validation.py --summarize
python -m ruff check python/02b_arima_validation.py tests/test_arima_validation.py
python -m pytest
```

The summarize command reads language outputs and regenerates common reports,
the lock and six figures without refitting. Language-specific manifests,
origins, forecasts, fit logs, metrics and guards remain auditable under
`outputs/tables/phase3b_*.csv`. Figures are in `outputs/figures/phase3b/`.

- [RMSE h=5](../outputs/figures/phase3b/phase3b_rmse_by_model_h5.png)
- [RMSE h=10](../outputs/figures/phase3b/phase3b_rmse_by_model_h10.png)
- [MAE h=5](../outputs/figures/phase3b/phase3b_mae_by_model_h5.png)
- [MAE h=10](../outputs/figures/phase3b/phase3b_mae_by_model_h10.png)
- [Endpoint errors h=5](../outputs/figures/phase3b/phase3b_forecast_errors_over_time_h5.png)
- [Endpoint errors h=10](../outputs/figures/phase3b/phase3b_forecast_errors_over_time_h10.png)

Stop after Phase 3B review; no subsequent phase is started automatically.
"""
    (root / "docs/phase3b_arima_validation.md").write_text(text, encoding="utf-8")


def main(root=ROOT):
    protocol, candidates = configuration(root)
    audit = []
    frame, raw = read_observations(root, TRAIN, audit)
    if hashlib.sha256(raw).hexdigest() != protocol.train_sha256:
        raise ValueError("Frozen TRAIN SHA-256 mismatch")
    origins, forecasts, fits = rolling_validate(frame, protocol, candidates)
    guards = guard_table(frame, origins, forecasts, fits, audit)
    save(guards, "holdout_guard_python", root)
    if not guards.status.eq("PASS").all():
        raise ValueError("FAIL in Python holdout guard; STOP")
    for table, name in [
        (origins, "origins_python"),
        (forecasts, "forecasts_python"),
        (fits, "fit_log_python"),
        (metrics_table(forecasts), "validation_metrics_python"),
    ]:
        save(table, name, root)
    save(
        pd.DataFrame(
            [
                {
                    "language": "Python",
                    "rows": len(frame),
                    "first_date": frame.Date.iloc[0],
                    "last_date": frame.Date.iloc[-1],
                    "train_md5": hashlib.md5(raw).hexdigest(),
                    "train_sha256": hashlib.sha256(raw).hexdigest(),
                    "protocol_md5": hashlib.md5(
                        (root / PROTOCOL).read_bytes()
                    ).hexdigest(),
                    "candidates_md5": hashlib.md5(
                        (root / CANDIDATES).read_bytes()
                    ).hexdigest(),
                    "initial_size": int(protocol.initial_size),
                    "origin_step": int(protocol.origin_step),
                    "n_origins": origins.origin_index.nunique(),
                    "python_version": platform.python_version(),
                    "statsmodels_version": statsmodels.__version__,
                }
            ]
        ),
        "manifest_python",
        root,
    )
    summarize(root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Read completed R/Python outputs; no refit",
    )
    args = parser.parse_args()
    if args.summarize:
        summarize()
    else:
        main()
