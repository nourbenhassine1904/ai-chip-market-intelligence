"""Phase 3A: TRAIN-only ARIMA identification; no forecasts or final evaluation.

R is the pedagogical reference; Python independently fits the same specifications.
Use --summarize after R to refresh cross-language tables without refitting.
"""

import argparse
import contextlib
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import warnings
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".cache/matplotlib")
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.stats.stattools import jarque_bera
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import acf, pacf

ROOT = Path(__file__).resolve().parents[1]
INPUTS = {
    "data/processed/market_train.csv",
    "outputs/tables/phase2_split_metadata.csv",
    "outputs/tables/phase2_feature_manifest.csv",
    "outputs/tables/phase2_stationarity_summary.csv",
    "outputs/tables/phase2_stationarity_tests.csv",
    "outputs/tables/phase2_weekday_returns.csv",
    "outputs/tables/phase2_leakage_check.csv",
}
TRAIN = "data/processed/market_train.csv"
SELECTION_RULE = (
    "Converged finite fits; prefer both Ljung-Box p>=0.05; within 2 of best "
    "AICc choose fewest parameters then BIC, AICc and model id. "
    "If none passes both tests, selection remains diagnostically inadequate."
)


def read_input(root, relative, audit):
    """Closed allowlist: no fallback to another market dataset."""
    if relative not in INPUTS:
        raise ValueError(f"Unauthorized Phase 3A input: {relative}")
    audit.append(relative)
    return pd.read_csv(root / relative, float_precision="round_trip")


def log_transform(prices):
    values = np.asarray(prices, dtype=float)
    if not np.isfinite(values).all() or np.any(values <= 0):
        raise ValueError("Log-price requires finite positive prices, no imputation.")
    return np.log(values)


def difference(log_prices):
    return np.diff(np.asarray(log_prices, dtype=float))


def load_train(root=ROOT):
    audit = []
    meta = read_input(root, "outputs/tables/phase2_split_metadata.csv", audit).iloc[0]
    manifest = read_input(root, "outputs/tables/phase2_feature_manifest.csv", audit)
    digest = hashlib.sha256((root / TRAIN).read_bytes()).hexdigest()
    if len(manifest) != 1 or digest != manifest.iloc[0].train_sha256:
        raise ValueError("TRAIN SHA-256 differs from frozen Phase 2 manifest.")
    data = read_input(root, TRAIN, audit)
    dates = pd.to_datetime(data.Date, format="%Y-%m-%d", errors="raise")
    if (
        dates.isna().any()
        or dates.duplicated().any()
        or not dates.is_monotonic_increasing
        or len(data) != int(meta.train_rows)
        or dates.iloc[0].strftime("%Y-%m-%d") != meta.train_start
        or dates.iloc[-1].strftime("%Y-%m-%d") != meta.train_end
    ):
        raise ValueError("TRAIN chronology or frozen split metadata mismatch.")
    y = log_transform(data.NVDA_Adj_Close)
    delta = difference(y)
    if not np.allclose(y, data.NVDA_Log_Price, atol=1e-12, rtol=0):
        raise ValueError("Phase 2 log-price mismatch.")
    if not np.allclose(delta, data.NVDA_Log_Return.iloc[1:] / 100, atol=1e-12):
        raise ValueError("Phase 2 log-return / 100 mismatch.")
    return data, dates, y, delta, audit, digest


def candidate_orders():
    # Three AR/MA alternatives include drift, matching both languages.
    return [
        (0, 1, 0, False),
        (0, 1, 0, True),
        (1, 1, 0, True),
        (0, 1, 1, True),
        (1, 1, 1, True),
    ]


def model_id(p, d, q, drift):
    return f"ARIMA({p},{d},{q})_{'drift' if drift else 'no_drift'}"


def aicc(aic, n, k):
    return aic + 2 * k * (k + 1) / (n - k - 1) if n > k + 1 else np.inf


def residual_diagnostics(residuals, p, q, model, language="Python"):
    r = np.asarray(residuals, dtype=float)
    if len(r) <= 25 or not np.isfinite(r).all():
        raise ValueError("Require >25 finite post-initialization residuals.")
    lb = acorr_ljungbox(r, lags=[10, 20], model_df=p + q, return_df=True)
    rows = []
    for lag in (10, 20):
        rows.append(
            (
                "Ljung-Box",
                lag,
                lb.loc[lag, "lb_stat"],
                lb.loc[lag, "lb_pvalue"],
                lag - p - q,
                p + q,
            )
        )
    jb = jarque_bera(r)
    rows.append(("Jarque-Bera", 0, jb[0], jb[1], 2, 0))
    for lag in (5, 10, 20):
        # ddof=0 matches FinTS::ArchTest's n*R^2 convention.
        lm, pv, _, _ = het_arch(r, nlags=lag, ddof=0)
        rows.append(("ARCH-LM", lag, lm, pv, lag, 0))
    return pd.DataFrame(
        [
            {
                "language": language,
                "model": model,
                "scope": "train",
                "test": test,
                "lag": lag,
                "statistic": float(stat),
                "p_value": float(pv),
                "df": df,
                "model_df": model_df,
                "nobs": len(r),
                "reject_5pct": bool(pv < 0.05),
            }
            for test, lag, stat, pv, df, model_df in rows
        ]
    )


def fit_candidate(y, spec, source="manual", start_params=None):
    p, d, q, drift = spec
    row = {
        "language": "Python",
        "source": source,
        "model": model_id(*spec),
        "p": p,
        "d": d,
        "q": q,
        "drift": drift,
        "seasonal_order": "(0,0,0,0)",
        "scope": "train",
        "converged": False,
        "k": np.nan,
        "n_eff": len(y) - d,
        "log_likelihood": np.nan,
        "AIC": np.nan,
        "AICc": np.nan,
        "BIC": np.nan,
        "ljung_box_10": np.nan,
        "ljung_box_20": np.nan,
        "warnings": "",
        "error": "",
    }
    fit = None
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            fit = ARIMA(y, order=(p, d, q), trend="t" if drift else "n").fit(
                start_params=start_params, method_kwargs={"maxiter": 1000}
            )
            k = len(fit.params)  # Includes innovation variance and any drift.
            row.update(
                converged=bool(fit.mle_retvals.get("converged", False)),
                k=k,
                log_likelihood=fit.llf,
                AIC=fit.aic,
                AICc=aicc(fit.aic, len(y) - d, k),
                BIC=fit.bic,
            )
            diag = residual_diagnostics(fit.resid[1:], p, q, row["model"])
            row["ljung_box_10"], row["ljung_box_20"] = diag.p_value.iloc[:2]
        except (
            ValueError,
            RuntimeError,
            np.linalg.LinAlgError,
            FloatingPointError,
        ) as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
    row["warnings"] = " | ".join(dict.fromkeys(str(w.message) for w in caught))
    return row, fit


def select_candidate(table):
    valid = table.loc[
        table.converged & np.isfinite(table.AICc) & np.isfinite(table.BIC)
    ].copy()
    if valid.empty:
        raise RuntimeError("No converged finite ARIMA fit; no selection possible.")
    adequate = valid.loc[(valid.ljung_box_10 >= 0.05) & (valid.ljung_box_20 >= 0.05)]
    pool = adequate if not adequate.empty else valid
    near = pool.loc[pool.AICc <= pool.AICc.min() + 2]
    return near.sort_values(["k", "BIC", "AICc", "model"], kind="stable").iloc[0]


def automatic_search(y):
    try:
        import pmdarima as pm
    except ImportError as exc:
        raise RuntimeError(
            "pmdarima missing. Run: python -m pip install -r requirements.txt. "
            "No package is installed by this script."
        ) from exc
    rows = []
    trace_output = io.StringIO()
    # Exhaust both intercept policies: non-stepwise 'auto' alone need not do so.
    for drift in (False, True):
        with (
            warnings.catch_warnings(record=True) as caught,
            contextlib.redirect_stdout(trace_output),
        ):
            warnings.simplefilter("always")
            try:
                fits = pm.auto_arima(
                    y,
                    d=1,
                    start_p=0,
                    start_q=0,
                    max_p=3,
                    max_q=3,
                    max_order=6,
                    seasonal=False,
                    stepwise=False,
                    with_intercept=drift,
                    information_criterion="aicc",
                    method="lbfgs",
                    maxiter=1000,
                    error_action="trace",
                    suppress_warnings=False,
                    trace=True,
                    return_valid_fits=True,
                    out_of_sample_size=0,
                    n_jobs=1,
                )
                for fit in fits:
                    result = fit.arima_res_
                    p, d, q = fit.order
                    rows.append(
                        {
                            "language": "Python",
                            "source": "pmdarima",
                            "scope": "train",
                            "model": model_id(p, d, q, drift),
                            "p": p,
                            "d": d,
                            "q": q,
                            "drift": drift,
                            "seasonal_order": str(fit.seasonal_order),
                            "converged": bool(
                                result.mle_retvals.get("converged", False)
                            ),
                            "k": len(result.params),
                            "n_eff": len(y) - 1,
                            "aicc_package_nobs": int(fit.nobs_)
                            if hasattr(fit, "nobs_")
                            else len(y),
                            "log_likelihood": result.llf,
                            "AIC": fit.aic(),
                            "AICc": fit.aicc(),
                            "BIC": fit.bic(),
                            "coefficients": json.dumps(
                                dict(zip(result.param_names, map(float, result.params)))
                            ),
                            "error": "",
                            "warnings": "",
                        }
                    )
            except (
                ValueError,
                RuntimeError,
                np.linalg.LinAlgError,
                FloatingPointError,
            ) as exc:
                rows.append(
                    {
                        "language": "Python",
                        "source": "pmdarima",
                        "scope": "train",
                        "drift": drift,
                        "converged": False,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
        message = " | ".join(dict.fromkeys(str(w.message) for w in caught))
        for row in rows:
            if row["drift"] == drift:
                row["warnings"] = message
    table = pd.DataFrame(rows)
    if "AICc" not in table:
        table["AICc"] = np.nan
    table["selected_by_auto"] = False
    valid = table.loc[table.converged & np.isfinite(table.AICc)]
    if not valid.empty:
        idx = valid.sort_values(["AICc", "BIC", "model"]).index[0]
        table.loc[idx, "selected_by_auto"] = True
    table.attrs["search_trace"] = trace_output.getvalue().splitlines()
    print(trace_output.getvalue())
    return table


def identification(delta):
    a = acf(delta, nlags=20, fft=True)
    p = pacf(delta, nlags=20, method="ywm")
    return pd.DataFrame(
        {
            "lag": np.arange(1, 21),
            "acf": a[1:],
            "pacf": p[1:],
            "pointwise_95_bound": 1.96 / np.sqrt(len(delta)),
            "scope": "train",
        }
    )


def seasonality_gate(y, delta, dates, weekday):
    stl = STL(y, period=5, robust=True).fit()
    strength = max(0, 1 - np.var(stl.resid) / np.var(stl.seasonal + stl.resid))
    a = acf(delta, nlags=20, fft=True)[[5, 10, 15, 20]]
    bound = stats.norm.ppf(1 - 0.05 / (2 * 4)) / np.sqrt(len(delta))
    groups = [delta[np.asarray(dates.iloc[1:].dt.dayofweek) == d] for d in range(5)]
    weekday_p = stats.f_oneway(*groups).pvalue
    rows = [
        (
            "Phase2_STL_period_5",
            strength,
            "Robust STL recomputed on TRAIN; a seasonal component alone is not proof.",
        ),
        (
            "returns_seasonal_acf",
            json.dumps(dict(zip([5, 10, 15, 20], map(float, a)))),
            (
                f"Bonferroni 4-lag bound={bound:.6g}; "
                f"{int(np.sum(np.abs(a) > bound))}/4 exceed; isolated spikes insufficient."
            ),
        ),
        (
            "Phase2_weekday_means_pct",
            json.dumps(dict(zip(weekday.weekday, map(float, weekday["mean"])))),
            "Descriptive calendar weekdays differ from five consecutive sessions.",
        ),
        (
            "weekday_ANOVA_auxiliary_p",
            weekday_p,
            "TRAIN auxiliary mean test; unequal variance/heavy tails limit inference.",
        ),
        ("R_nsdiffs_frequency_5", "pending R execution", "Auxiliary, not automatic D."),
        (
            "sarima_justified",
            False,
            "Insufficient joint evidence; no seasonal fit. R nsdiffs checked in summary.",
        ),
    ]
    convincing = strength > 0.64 and np.sum(np.abs(a) > bound) >= 3 and weekday_p < 0.05
    if convincing:
        raise RuntimeError(
            "Seasonal evidence changed: document and review before SARIMA."
        )
    return pd.DataFrame(rows, columns=["evidence", "result", "interpretation"])


def save(table, name, root=ROOT):
    directory = root / "outputs/tables"
    directory.mkdir(parents=True, exist_ok=True)
    table.to_csv(directory / f"phase3_{name}.csv", index=False)


def generate_figures(y, delta, dates, residuals, model, root):
    directory = root / "outputs/figures/phase3"
    directory.mkdir(parents=True, exist_ok=True)

    def finish(fig, name):
        fig.tight_layout()
        fig.savefig(directory / f"{name}.png", dpi=150)
        plt.close(fig)

    for values, title, name in [
        (y, "log-price", "nvda_log_price_acf_pacf_train"),
        (delta, "delta log-price", "nvda_delta_log_price_acf_pacf_train"),
    ]:
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        plot_acf(values, lags=40, zero=False, ax=axes[0])
        plot_pacf(values, lags=40, zero=False, method="ywm", ax=axes[1])
        fig.suptitle(f"NVDA {title} — TRAIN; pointwise 95% bands")
        finish(fig, name)
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(dates.iloc[1:], residuals, linewidth=0.6)
    ax.axhline(0, color="black", linewidth=0.7)
    ax.set(title=f"NVDA {model} — TRAIN residuals", ylabel="Log-price innovation")
    finish(fig, "nvda_arima_residuals_python")
    for values, title, name in [
        (residuals, "Residual ACF", "nvda_arima_residual_acf"),
        (residuals**2, "Squared residual ACF", "nvda_arima_squared_residual_acf"),
    ]:
        fig, ax = plt.subplots(figsize=(9, 4))
        plot_acf(values, lags=40, zero=False, ax=ax)
        ax.set_title(f"{title} — {model}; TRAIN")
        finish(fig, name + "_python")
    fig, ax = plt.subplots(figsize=(6, 5))
    stats.probplot(residuals, dist="norm", plot=ax)
    ax.set_title(f"Normal QQ — {model}; TRAIN")
    finish(fig, "nvda_arima_residual_qqplot_python")


def diagnostic_summary(diagnostics, selected, residuals):
    values = {(r.test, r.lag): r.p_value for r in diagnostics.itertuples()}
    return pd.DataFrame(
        [
            dict(
                language="Python",
                model=selected.model,
                scope="train",
                **{f"ljung_box_{lag}": values["Ljung-Box", lag] for lag in (10, 20)},
                jarque_bera=values["Jarque-Bera", 0],
                **{f"arch_lm_{lag}": values["ARCH-LM", lag] for lag in (5, 10, 20)},
                residual_mean=np.mean(residuals),
                residual_std=np.std(residuals, ddof=1),
                white_noise_mean_supported=all(
                    values["Ljung-Box", lag] >= 0.05 for lag in (10, 20)
                ),
                normality_supported=values["Jarque-Bera", 0] >= 0.05,
                arch_effect_supported=all(
                    values["ARCH-LM", lag] < 0.05 for lag in (5, 10, 20)
                ),
                qualification="provisional selected mean model",
            )
        ]
    )


def summarize(root=ROOT):
    """Combine saved language outputs; never consume observations or refit."""
    directory = root / "outputs/tables"
    comparison, summaries, manifests, guards = [], [], [], []
    for lang in ("r", "python"):
        for source, filename in [
            ("manual", f"arima_manual_candidates_{lang}"),
            ("auto", f"auto_arima_{lang}"),
        ]:
            path = directory / f"phase3_{filename}.csv"
            if path.exists():
                table = pd.read_csv(path)
                table["comparison_source"] = source
                comparison.append(table)
        for base, target in [
            ("arima_diagnostic_summary", summaries),
            ("train_manifest", manifests),
            ("holdout_guard", guards),
        ]:
            path = directory / f"phase3_{base}_{lang}.csv"
            if path.exists():
                target.append(pd.read_csv(path))
    if comparison:
        comparison_table = pd.concat(comparison, ignore_index=True)
        selected_models = {
            row.language: row.model for frame in summaries for row in frame.itertuples()
        }
        comparison_table["selected_candidate"] = comparison_table.apply(
            lambda row: row.model == selected_models.get(row.language), axis=1
        )
        comparison_table["qualification"] = "provisional selected mean model"
        save(comparison_table, "arima_selection_comparison", root)
    if summaries:
        summary = pd.concat(summaries, ignore_index=True)
        summary["primary_pedagogical_model"] = summary.language.eq("R")
        save(summary, "arima_diagnostic_summary", root)
    if manifests:
        save(pd.concat(manifests, ignore_index=True), "train_manifest", root)
    if len(manifests) == 2:
        joined = pd.concat(manifests, ignore_index=True)
        same = all(
            joined[c].nunique() == 1 for c in ["md5", "rows", "first_date", "last_date"]
        )
        guards.append(
            pd.DataFrame(
                [
                    {
                        "check": "same_exact_TRAIN_bytes_R_Python",
                        "status": "PASS" if same else "FAIL",
                        "details": "MD5, row count and date bounds agree across independent readers.",
                    }
                ]
            )
        )
        if not same:
            save(pd.concat(guards, ignore_index=True), "holdout_guard", root)
            raise RuntimeError("R and Python did not use identical TRAIN input.")
    else:
        guards.append(
            pd.DataFrame(
                [
                    {
                        "check": "same_exact_TRAIN_bytes_R_Python",
                        "status": "PENDING",
                        "details": "Run both languages.",
                    }
                ]
            )
        )
    if guards:
        save(pd.concat(guards, ignore_index=True), "holdout_guard", root)
    gate_path = directory / "phase3_seasonality_gate_python.csv"
    if gate_path.exists():
        gate = pd.read_csv(gate_path)
        r_path = directory / "phase3_seasonality_gate_r.csv"
        if r_path.exists():
            r_gate = pd.read_csv(r_path)
            r_decision = str(
                r_gate.loc[r_gate.evidence == "sarima_justified", "result"].iloc[0]
            ).lower()
            py_decision = str(
                gate.loc[gate.evidence == "sarima_justified", "result"].iloc[0]
            ).lower()
            if r_decision != py_decision:
                raise RuntimeError(
                    "R/Python seasonality gates disagree; do not silently fit."
                )
            auxiliary = r_gate.loc[r_gate.evidence.str.startswith("R_nsdiffs")]
            gate = gate.loc[gate.evidence != "R_nsdiffs_frequency_5"]
            gate = pd.concat([gate, auxiliary], ignore_index=True)
        save(gate, "seasonality_gate", root)
    print("Summary refreshed. Selection rule:", SELECTION_RULE)


def compare_r_optimizer(root=ROOT):
    """Supplementary sensitivity only: never changes independent selections.

    Compare statsmodels' own initialization against coefficients from the
    selected R fit at the SAME order. The second fit is explicitly dependent
    on R and is not presented as independent replication evidence.
    """
    directory = root / "outputs/tables"
    r_manifest = pd.read_csv(directory / "phase3_train_manifest_r.csv").iloc[0]
    if hashlib.md5((root / TRAIN).read_bytes()).hexdigest() != r_manifest.md5:
        raise ValueError("R sensitivity input differs from current frozen TRAIN.")
    _data, _dates, y, _delta, _audit, _digest = load_train(root)
    pool = pd.read_csv(directory / "phase3_arima_selection_pool_r.csv")
    selected = pool.loc[pool.selected_candidate].iloc[0]
    spec = (int(selected.p), 1, int(selected.q), bool(selected.drift))
    r_coefficients = pd.read_csv(directory / "phase3_arima_coefficients_r.csv")
    values = (
        r_coefficients.loc[r_coefficients.model == selected.model]
        .set_index("term")
        .estimate
    )
    start = (
        ([values["drift"]] if spec[3] else [])
        + [values[f"ar{i}"] for i in range(1, spec[0] + 1)]
        + [values[f"ma{i}"] for i in range(1, spec[2] + 1)]
        + [values["sigma2"]]
    )
    rows, coefficient_rows, diagnostic_rows = [], [], []
    for label, initial in [
        ("independent_default_start", None),
        ("R_initialized_sensitivity", start),
    ]:
        row, fit = fit_candidate(y, spec, source=label, start_params=initial)
        rows.append(row)
        if fit is not None:
            for term, estimate in zip(fit.param_names, fit.params):
                coefficient_rows.append(
                    {
                        "initialization": label,
                        "model": row["model"],
                        "term": term,
                        "estimate": estimate,
                    }
                )
            diag = residual_diagnostics(fit.resid[1:], spec[0], spec[2], row["model"])
            diag["initialization"] = label
            diagnostic_rows.append(diag)
    save(pd.DataFrame(rows), "optimizer_sensitivity_python", root)
    save(
        pd.DataFrame(coefficient_rows),
        "optimizer_sensitivity_coefficients_python",
        root,
    )
    if diagnostic_rows:
        save(
            pd.concat(diagnostic_rows, ignore_index=True),
            "optimizer_sensitivity_diagnostics_python",
            root,
        )
    print(
        pd.DataFrame(rows)[
            ["source", "model", "converged", "log_likelihood", "AICc"]
        ].to_string(index=False)
    )
    print("Sensitivity only; the independent R/Python selections are unchanged.")


def main(root=ROOT):
    _data, dates, y, delta, audit, digest = load_train(root)
    phase2 = read_input(root, "outputs/tables/phase2_stationarity_summary.csv", audit)
    phase2 = phase2.loc[(phase2.ticker == "NVDA") & (phase2.scope == "train")]
    conclusions = dict(zip(phase2.series, phase2.mechanical_summary))
    if (
        conclusions.get("Log_Price") != "nonstationary_supported"
        or conclusions.get("Log_Return") != "stationary_supported"
    ):
        raise ValueError(
            "Phase 2 evidence for d=1 changed; scientific review required."
        )
    prior_guard = read_input(root, "outputs/tables/phase2_leakage_check.csv", audit)
    if not prior_guard.status.eq("PASS").all():
        raise ValueError("Phase 2 leakage checks are not all PASS.")
    tests = read_input(root, "outputs/tables/phase2_stationarity_tests.csv", audit)
    save(
        tests.loc[
            (tests.ticker == "NVDA")
            & (tests.scope == "train")
            & tests.series.isin(["Log_Price", "Log_Return"])
        ],
        "d_phase2_evidence",
        root,
    )
    weekday = read_input(root, "outputs/tables/phase2_weekday_returns.csv", audit)
    weekday = weekday.loc[(weekday.ticker == "NVDA") & (weekday.scope == "train")]
    save(identification(delta), "acf_pacf_numeric", root)
    save(seasonality_gate(y, delta, dates, weekday), "seasonality_gate_python", root)
    rows, fits = [], {}
    for spec in candidate_orders():
        row, fit = fit_candidate(y, spec)
        rows.append(row)
        fits[row["model"]] = fit
    manual = pd.DataFrame(rows)
    automatic = automatic_search(y)
    save(
        pd.DataFrame({"trace_line": automatic.attrs.get("search_trace", [])}),
        "auto_arima_trace_python",
        root,
    )
    pool = manual.copy()
    winners = automatic.loc[automatic.selected_by_auto]
    if not winners.empty:
        winner = winners.iloc[0]
        if winner.model not in fits:
            spec = (int(winner.p), 1, int(winner.q), bool(winner.drift))
            row, fit = fit_candidate(y, spec, "auto_refit_statsmodels")
            pool = pd.concat([pool, pd.DataFrame([row])], ignore_index=True)
            fits[row["model"]] = fit
    selected = select_candidate(pool)
    manual["selected_candidate"] = manual.model.eq(selected.model)
    pool["selected_candidate"] = pool.model.eq(selected.model)
    save(manual, "arima_manual_candidates_python", root)
    save(automatic, "auto_arima_python", root)
    save(pool, "arima_selection_pool_python", root)
    fit = fits[selected.model]
    residuals = np.asarray(fit.resid[1:])
    diagnostics = residual_diagnostics(
        residuals, int(selected.p), int(selected.q), selected.model
    )
    save(diagnostics, "arima_residual_diagnostics_python", root)
    save(
        diagnostic_summary(diagnostics, selected, residuals),
        "arima_diagnostic_summary_python",
        root,
    )
    coefficients = []
    for row in pool.itertuples():
        fitted = fits[row.model]
        if fitted is not None:
            for term, value, se in zip(fitted.param_names, fitted.params, fitted.bse):
                coefficients.append(
                    {
                        "language": "Python",
                        "model": row.model,
                        "term": term,
                        "estimate": value,
                        "standard_error": se,
                        "selected_candidate": row.model == selected.model,
                    }
                )
    save(pd.DataFrame(coefficients), "arima_coefficients_python", root)
    save(
        pd.DataFrame(
            [
                {
                    "language": "Python",
                    "input": TRAIN,
                    "scope": "train",
                    "rows": len(y),
                    "effective_rows": len(delta),
                    "first_date": dates.iloc[0].strftime("%Y-%m-%d"),
                    "last_date": dates.iloc[-1].strftime("%Y-%m-%d"),
                    "sha256": digest,
                    "md5": hashlib.md5((root / TRAIN).read_bytes()).hexdigest(),
                    "sum_log_price": y.sum(),
                    "sum_delta_log_price": delta.sum(),
                }
            ]
        ),
        "train_manifest_python",
        root,
    )
    guard = [
        {
            "check": f"python_{operation}_TRAIN_only",
            "status": "PASS",
            "details": "Closed input allowlist; same validated y/delta used by all stages.",
        }
        for operation in [
            "fit",
            "order_selection",
            "residual_diagnostics",
            "seasonality_gate",
        ]
    ]
    guard.extend(
        [
            {
                "check": "python_frozen_TRAIN_integrity",
                "status": "PASS",
                "details": f"SHA-256={digest}",
            },
            {
                "check": "python_all_observation_reads_allowlisted",
                "status": "PASS",
                "details": "; ".join(audit),
            },
            {
                "check": "python_no_forecast_or_final_metrics",
                "status": "PASS",
                "details": "Code audit: no predict/forecast, final errors or Diebold-Mariano calls.",
            },
        ]
    )
    save(pd.DataFrame(guard), "holdout_guard_python", root)
    versions = [("Python", platform.python_version())] + [
        (package, importlib.metadata.version(package))
        for package in [
            "numpy",
            "pandas",
            "scipy",
            "statsmodels",
            "pmdarima",
            "matplotlib",
        ]
    ]
    save(
        pd.DataFrame(versions, columns=["package", "version"]),
        "runtime_versions_python",
        root,
    )
    generate_figures(y, delta, dates, residuals, selected.model, root)
    summarize(root)
    print(pool.to_string(index=False))
    print(diagnostics.to_string(index=False))
    print("Provisional selected mean model:", selected.model)
    print("No forecasting or final evaluation performed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summarize", action="store_true")
    parser.add_argument(
        "--compare-r",
        action="store_true",
        help="Optional initialization sensitivity after R.",
    )
    args = parser.parse_args()
    if args.compare_r:
        compare_r_optimizer()
    elif args.summarize:
        summarize()
    else:
        main()
