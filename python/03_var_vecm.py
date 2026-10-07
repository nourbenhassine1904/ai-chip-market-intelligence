"""Phase 4: independent TRAIN-only VAR, Granger and conditional VECM.

Run Python, R, then --summarize. Only a shared positive rank permits --vecm.
"""

import argparse
import hashlib
import io
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
import scipy
import statsmodels
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.api import VAR
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen

ROOT = Path(__file__).resolve().parents[1]
TRAIN = "data/processed/market_train.csv"
PROTOCOL = "docs/phase4_protocol.csv"
ASSETS = ["NVDA", "AMD", "SOXX"]
RETURNS = [f"{a}_Log_Return" for a in ASSETS]
LEVELS = [f"{a}_Log_Price" for a in ASSETS]
SCOPE = "TRAIN_only_no_final_evaluation"
SELECTION_RULE = (
    "Estimable, stable, adjusted Portmanteau p>=.05 at 20 and 30; among adequate "
    "fits within 2 total BIC units of best, prefer fewer lags then BIC/HQIC/AIC. "
    "If none adequate retain provisional stable fit and block IRF/FEVD. "
    "IC uses common response sample; diagnostics use full available sample."
)


def read_observations(root, relative, audit):
    """Check closed allowlist before touching the filesystem."""
    if relative != TRAIN:
        raise ValueError(f"Unauthorized market input: {relative}")
    path = root / relative
    if path.resolve() != root.resolve() / TRAIN:
        raise ValueError("Redirected TRAIN path")
    raw = path.read_bytes()
    audit.append(relative)
    return pd.read_csv(io.BytesIO(raw), float_precision="round_trip"), raw


def validate_frame(frame, protocol):
    required = ["Date", *RETURNS, *LEVELS, *[f"{a}_Adj_Close" for a in ASSETS]]
    if not set(required).issubset(frame.columns):
        raise ValueError("Missing Phase 4 variables")
    dates = pd.to_datetime(frame.Date, format="%Y-%m-%d", errors="raise")
    if (
        len(frame) != int(protocol.expected_rows)
        or dates.isna().any()
        or dates.duplicated().any()
        or not dates.is_monotonic_increasing
        or str(dates.iloc[0].date()) != protocol.first_date
        or str(dates.iloc[-1].date()) != protocol.last_date
    ):
        raise ValueError("Invalid frozen TRAIN chronology")
    for a in ASSETS:
        prices = frame[f"{a}_Adj_Close"].to_numpy(float)
        levels = frame[f"{a}_Log_Price"].to_numpy(float)
        returns = frame[f"{a}_Log_Return"].to_numpy(float)
        if (
            not np.isfinite(prices).all()
            or np.any(prices <= 0)
            or not np.isfinite(levels).all()
            or not np.isnan(returns[0])
            or not np.isfinite(returns[1:]).all()
            or not np.allclose(levels, np.log(prices), atol=1e-12, rtol=0)
            or not np.allclose(returns[1:], 100 * np.diff(levels), atol=1e-10, rtol=0)
        ):
            raise ValueError(f"Invalid backward-only transformations: {a}")
    return dates


def load_train(root=ROOT):
    protocol = pd.read_csv(root / PROTOCOL).iloc[0]
    if (
        protocol.max_var_lag != 10
        or protocol.serial_gate_1 != 20
        or protocol.serial_gate_2 != 30
        or protocol.johansen_level_lags < 2
        or protocol.cholesky_order != ";".join(ASSETS)
    ):
        raise ValueError("Unsupported protocol conventions")
    audit = []
    frame, raw = read_observations(root, TRAIN, audit)
    if hashlib.sha256(raw).hexdigest() != protocol.train_sha256:
        raise ValueError("Frozen TRAIN SHA-256 mismatch")
    if hashlib.md5(raw).hexdigest() != protocol.train_md5:
        raise ValueError("Frozen TRAIN MD5 mismatch")
    return frame, validate_frame(frame, protocol), protocol, audit


def save(rows, name, root=ROOT):
    folder = root / "outputs/tables"
    folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(
        folder / f"phase4_{name}.csv", index=False, lineterminator="\n"
    )


def metadata(protocol, language="Python", root=ROOT):
    script = "python/03_var_vecm.py" if language == "Python" else "r/03_var_vecm.R"
    return {
        "language": language,
        "scope": SCOPE,
        "train_md5": protocol.train_md5,
        "protocol_md5": hashlib.md5((root / PROTOCOL).read_bytes()).hexdigest(),
        "implementation_md5": hashlib.md5((root / script).read_bytes()).hexdigest(),
    }


def companion_eigenvalues(coefs):
    coefs = np.asarray(coefs, dtype=float)
    p, k, k2 = coefs.shape
    if p < 1 or k != k2 or not np.isfinite(coefs).all():
        raise ValueError("Invalid VAR coefficients")
    companion = np.zeros((k * p, k * p))
    companion[:k] = np.concatenate(coefs, axis=1)
    if p > 1:
        companion[k:, :-k] = np.eye(k * (p - 1))
    return np.linalg.eigvals(companion)


def is_stable(coefs):
    return bool(np.max(np.abs(companion_eigenvalues(coefs))) < 1)


def choose_lag(table, protocol):
    candidates = table.loc[table.estimable & table.stable]
    if candidates.empty:
        raise ValueError("No estimable stable VAR in fixed grid")
    adequate = candidates.loc[candidates.serial_adequate]
    pool = adequate if not adequate.empty else candidates
    tied = pool.loc[
        (pool.bic - pool.bic.min()) * pool.ic_nobs <= protocol.bic_tie_units
    ]
    return int(tied.sort_values(["lag", "bic", "hqic", "aic"]).iloc[0].lag)


def lag_selection(returns, protocol):
    rows, fits = [], {}
    maxlag = int(protocol.max_var_lag)
    for p in range(1, maxlag + 1):
        ic = VAR(returns[maxlag - p :]).fit(p, trend="c")
        fit = VAR(returns).fit(p, trend="c")
        fits[p] = fit
        p20 = fit.test_whiteness(int(protocol.serial_gate_1), adjusted=True).pvalue
        p30 = fit.test_whiteness(int(protocol.serial_gate_2), adjusted=True).pvalue
        rows.append(
            {
                "lag": p,
                "aic": ic.aic,
                "bic": ic.bic,
                "hqic": ic.hqic,
                "fpe": ic.fpe,
                "ic_nobs": ic.nobs,
                "estimation_nobs": fit.nobs,
                "estimable": bool(np.isfinite(fit.params).all()),
                "stable": is_stable(fit.coefs),
                "max_companion_modulus": max(abs(companion_eigenvalues(fit.coefs))),
                "serial_p20": p20,
                "serial_p30": p30,
                "serial_adequate": min(p20, p30) >= protocol.alpha,
            }
        )
    table = pd.DataFrame(rows)
    selected = choose_lag(table, protocol)
    table["selected"] = table.lag == selected
    for criterion in ["aic", "bic", "hqic", "fpe"]:
        table[f"{criterion}_proposed"] = (
            table.lag == table.loc[table[criterion].idxmin(), "lag"]
        )
    return table, fits[selected]


def sequential_rank(statistics, critical):
    for rank, (stat, cv) in enumerate(zip(statistics, critical, strict=True)):
        if stat <= cv:
            return rank
    return len(statistics)


def johansen_table(levels, protocol):
    rows = []
    main = int(protocol.johansen_level_lags)
    for k in [main, *map(int, str(protocol.johansen_sensitivity_lags).split(";"))]:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = coint_johansen(levels, det_order=0, k_ar_diff=k - 1)
        # Some BLAS/eig builds return complex dtype with zero imaginary part.
        # Fail rather than accepting genuinely complex or invalid eigenvalues.
        eig = np.asarray(result.eig)
        if (
            np.max(np.abs(eig.imag)) > 1e-10
            or not np.isfinite(result.lr1).all()
            or np.any(eig.real < -1e-10)
            or np.any(eig.real >= 1)
        ):
            raise ValueError("Invalid Johansen eigensystem")
        warning_text = " | ".join(
            sorted({f"{w.category.__name__}: {w.message}" for w in caught})
        )
        rank = sequential_rank(result.lr1, result.cvt[:, 1])
        for r in range(3):
            rows.append(
                {
                    "specification": "main" if k == main else "sensitivity",
                    "level_lags": k,
                    "k_ar_diff": k - 1,
                    "deterministic": "det_order=0; demeaned levels/differences",
                    "input_variables": ";".join(LEVELS),
                    "nobs_levels": len(levels),
                    "effective_nobs": len(levels) - k,
                    "null_rank_at_most": r,
                    "trace_statistic": result.lr1[r],
                    "critical_10pct": result.cvt[r, 0],
                    "critical_5pct": result.cvt[r, 1],
                    "critical_1pct": result.cvt[r, 2],
                    "reject_5pct": result.lr1[r] > result.cvt[r, 1],
                    "selected_rank": rank,
                    "critical_table": "statsmodels native c_sjt(det_order=0)",
                    "max_eigen_imaginary_abs": float(np.max(np.abs(eig.imag))),
                    "numerical_warnings": warning_text,
                }
            )
    return pd.DataFrame(rows)


def vecm_allowed(rank):
    return isinstance(rank, (int, np.integer)) and 0 < rank < len(ASSETS)


def fit_vecm(levels, rank, protocol):
    if not vecm_allowed(rank):
        raise ValueError("VECM requires supported rank 1 or 2")
    return VECM(
        levels,
        k_ar_diff=int(protocol.johansen_level_lags) - 1,
        coint_rank=rank,
        deterministic="co",
    ).fit()


def granger_table(fit):
    rows = []
    for cause in ASSETS:
        for effect in ASSETS:
            if cause != effect:
                test = fit.test_causality(
                    ASSETS.index(effect), ASSETS.index(cause), kind="wald"
                )
                rows.append(
                    {
                        "cause": cause,
                        "effect": effect,
                        "test_statistic": test.test_statistic,
                        "df": test.df,
                        "p_value": test.pvalue,
                        "decision_5pct": "reject_H0"
                        if test.pvalue < 0.05
                        else "fail_to_reject_H0",
                    }
                )
    result = pd.DataFrame(rows)
    result["p_value_holm"] = multipletests(result.p_value, method="holm")[1]
    result["reject_holm_5pct"] = result.p_value_holm < 0.05
    return result


def save_figure(fig, name):
    folder = ROOT / "outputs/figures/phase4"
    folder.mkdir(parents=True, exist_ok=True)
    fig.savefig(folder / f"phase4_{name}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def basic_figures(frame, dates, fit):
    for columns, name, label in [
        (RETURNS, "returns_multivariate", "Log-return (%)"),
        (LEVELS, "cointegration_log_prices", "Log adjusted price"),
    ]:
        fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
        for ax, asset, col in zip(axes, ASSETS, columns, strict=True):
            ax.plot(dates, frame[col], lw=0.65)
            ax.set_ylabel(f"{asset}\n{label}")
            ax.grid(alpha=0.2)
        fig.suptitle("TRAIN only | " + label)
        fig.tight_layout()
        save_figure(fig, name)
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    for j, (ax, asset) in enumerate(zip(axes, ASSETS, strict=True)):
        ax.plot(dates.iloc[1 + fit.k_ar :], fit.resid[:, j], lw=0.65)
        ax.set_ylabel(f"{asset}\nResidual (%)")
        ax.axhline(0, color="black", lw=0.5)
    fig.suptitle(f"Python VAR({fit.k_ar}) residuals | TRAIN only")
    fig.tight_layout()
    save_figure(fig, "var_residuals")
    fig, axes = plt.subplots(3, 1, figsize=(11, 8))
    for j, (ax, asset) in enumerate(zip(axes, ASSETS, strict=True)):
        plot_acf(
            fit.resid[:, j], lags=40, zero=False, ax=ax, title=f"{asset} residual ACF"
        )
        ax.set_ylim(-0.15, 0.15)
    fig.suptitle(
        "TRAIN only | pointwise 95% bands; multivariate test reported separately"
    )
    fig.tight_layout()
    save_figure(fig, "var_residual_acf")


def dynamic_outputs(fit, protocol):
    horizon = int(protocol.irf_horizon)
    irf = fit.irf(horizon)
    response, stderr = irf.orth_irfs, irf.stderr(orth=True)
    rows = []
    fig, axes = plt.subplots(3, 3, figsize=(13, 9), sharex=True)
    for i, effect in enumerate(ASSETS):
        for j, shock in enumerate(ASSETS):
            lower = response[:, i, j] - 1.96 * stderr[:, i, j]
            upper = response[:, i, j] + 1.96 * stderr[:, i, j]
            ax = axes[i, j]
            ax.plot(range(horizon + 1), response[:, i, j])
            ax.fill_between(range(horizon + 1), lower, upper, alpha=0.2)
            ax.axhline(0, color="black", lw=0.6)
            ax.set_title(f"{shock} innovation → {effect}")
            for h in range(horizon + 1):
                rows.append(
                    {
                        "shock": shock,
                        "response": effect,
                        "horizon": h,
                        "irf": response[h, i, j],
                        "lower_95": lower[h],
                        "upper_95": upper[h],
                        "order": ";".join(ASSETS),
                        "interval_method": "asymptotic normal pointwise",
                    }
                )
    fig.suptitle("TRAIN VAR | Cholesky NVDA, AMD, SOXX | response in percentage points")
    fig.supxlabel("Trading sessions")
    fig.tight_layout()
    save_figure(fig, "var_irf")
    save(pd.DataFrame(rows).assign(**metadata(protocol)), "var_irf_python")
    decomp = fit.fevd(horizon).decomp * 100
    rows = [
        {
            "response": effect,
            "shock": shock,
            "horizon": h + 1,
            "variance_share_pct": decomp[i, h, j],
            "order": ";".join(ASSETS),
        }
        for i, effect in enumerate(ASSETS)
        for h in range(horizon)
        for j, shock in enumerate(ASSETS)
    ]
    if not np.allclose(decomp.sum(axis=2), 100, atol=1e-8):
        raise ValueError("FEVD shares do not sum to 100")
    save(pd.DataFrame(rows).assign(**metadata(protocol)), "var_fevd_python")
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for i, ax in enumerate(axes):
        ax.stackplot(range(1, horizon + 1), decomp[i].T, labels=ASSETS, alpha=0.8)
        ax.set_title(ASSETS[i])
        ax.set_xlabel("Trading sessions")
        ax.set_ylim(0, 100)
    axes[0].set_ylabel("Forecast error variance (%)")
    axes[-1].legend(loc="lower right")
    fig.suptitle("TRAIN VAR FEVD | Cholesky NVDA, AMD, SOXX")
    fig.tight_layout()
    save_figure(fig, "var_fevd")


def guard_table(audit, frame, protocol):
    measured = {
        "market_train.csv only": audit == [TRAIN],
        "market_test.csv not read": audit == [TRAIN],
        "chronological order preserved": pd.to_datetime(
            frame.Date
        ).is_monotonic_increasing,
        "frozen TRAIN fingerprint": hashlib.sha256(
            (ROOT / TRAIN).read_bytes()
        ).hexdigest()
        == protocol.train_sha256,
        "no future information": all(
            np.allclose(
                frame[f"{a}_Log_Return"].iloc[1:],
                100 * np.diff(frame[f"{a}_Log_Price"]),
                atol=1e-10,
                rtol=0,
            )
            for a in ASSETS
        ),
    }
    rows = [
        {
            "check": key,
            "status": "PASS" if value else "FAIL",
            "evidence_type": "runtime assertion",
            "details": "Validated frozen TRAIN input",
        }
        for key, value in measured.items()
    ]
    for name in ["lag selection", "Granger", "Johansen", "VECM", "IRF", "FEVD"]:
        rows.append(
            {
                "check": f"{name} TRAIN only",
                "status": "PASS",
                "evidence_type": "code scope audit",
                "details": "Only validated TRAIN arrays enter model functions; conditional gates apply",
            }
        )
    rows.append(
        {
            "check": "no final evaluation",
            "status": "PASS",
            "evidence_type": "code scope audit",
            "details": "No held-out forecast, loss, comparison or final test function",
        }
    )
    result = pd.DataFrame(rows).assign(**metadata(protocol))
    if not result.status.eq("PASS").all():
        raise ValueError("Holdout guard FAIL; stop")
    return result


def run_python():
    frame, dates, protocol, audit = load_train()
    meta = metadata(protocol)
    save(guard_table(audit, frame, protocol), "holdout_guard_python")
    save(
        [
            {
                "rows": len(frame),
                "return_rows": len(frame) - 1,
                "first_date": protocol.first_date,
                "last_date": protocol.last_date,
                "sha256_reference": protocol.train_sha256,
                "sha256_verified": True,
                "md5_verified": True,
                "variables": ";".join(RETURNS + LEVELS),
                "observation_reads": ";".join(audit),
                "holdout_read": False,
                **meta,
            }
        ],
        "train_manifest_python",
    )
    save(
        [
            {"package": p, "version": v, **meta}
            for p, v in [
                ("Python", platform.python_version()),
                ("numpy", np.__version__),
                ("pandas", pd.__version__),
                ("scipy", scipy.__version__),
                ("statsmodels", statsmodels.__version__),
            ]
        ],
        "runtime_versions_python",
    )
    lags, fit = lag_selection(frame[RETURNS].iloc[1:].to_numpy(float), protocol)
    save(lags.assign(**meta), "var_lag_selection_python")
    selected = lags.loc[lags.selected].iloc[0]
    eigen = companion_eigenvalues(fit.coefs)
    save(
        [
            {
                "root_index": i + 1,
                "companion_real": z.real,
                "companion_imag": z.imag,
                "companion_modulus": abs(z),
                "inverse_characteristic_modulus": 1 / abs(z) if abs(z) else np.inf,
                "stable": bool(selected.stable),
                "lag": fit.k_ar,
                **meta,
            }
            for i, z in enumerate(eigen)
        ],
        "var_stability_python",
    )
    serial = []
    for h in [5, 10, 20, 30]:
        if h <= fit.k_ar:
            serial.append(
                {
                    "horizon": h,
                    "test_statistic": np.nan,
                    "df": np.nan,
                    "p_value": np.nan,
                    "decision_5pct": "not_applicable_h_le_p",
                }
            )
        else:
            test = fit.test_whiteness(h, adjusted=True)
            serial.append(
                {
                    "horizon": h,
                    "test_statistic": test.test_statistic,
                    "df": test.df,
                    "p_value": test.pvalue,
                    "decision_5pct": "reject_serial_null"
                    if test.pvalue < 0.05
                    else "fail_to_reject_serial_null",
                }
            )
    save(
        pd.DataFrame(serial).assign(lag=fit.k_ar, test="adjusted Portmanteau", **meta),
        "var_residual_serial_correlation_python",
    )
    normal = fit.test_normality()
    save(
        [
            {
                "test": "multivariate Jarque-Bera",
                "test_statistic": normal.test_statistic,
                "df": normal.df,
                "p_value": normal.pvalue,
                "lag": fit.k_ar,
                "decision_5pct": "reject_normality"
                if normal.pvalue < 0.05
                else "fail_to_reject_normality",
                **meta,
            }
        ],
        "var_residual_normality_python",
    )
    granger = granger_table(fit)
    save(
        granger.assign(
            lag=fit.k_ar, test="conditional equation Wald chi-square", **meta
        ),
        "granger_causality_python",
    )
    save(
        johansen_table(frame[LEVELS].to_numpy(float), protocol).assign(**meta),
        "johansen_trace_python",
    )
    save(
        [
            {
                "lag": fit.k_ar,
                "nobs": fit.nobs,
                "response": ASSETS[j],
                "term": "constant"
                if i == 0
                else f"{ASSETS[(i - 1) % 3]}.L{(i - 1) // 3 + 1}",
                "coefficient": fit.params[i, j],
                "std_error": fit.stderr[i, j],
                **meta,
            }
            for i in range(fit.params.shape[0])
            for j in range(3)
        ],
        "var_coefficients_python",
    )
    save(
        pd.DataFrame(fit.resid, columns=ASSETS).assign(
            Date=dates.iloc[1 + fit.k_ar :].dt.strftime("%Y-%m-%d").to_numpy(), **meta
        ),
        "var_residuals_python",
    )
    basic_figures(frame, dates, fit)
    dynamic_ok = bool(selected.stable and selected.serial_adequate)
    save(
        [
            {
                "stable": bool(selected.stable),
                "serial_adequate": bool(selected.serial_adequate),
                "irf_fevd_permitted": dynamic_ok,
                "lag": fit.k_ar,
                **meta,
            }
        ],
        "var_dynamic_decision_python",
    )
    if dynamic_ok:
        dynamic_outputs(fit, protocol)
    print(
        f"Python PASS: VAR({fit.k_ar}); stable={selected.stable}; serial adequate={selected.serial_adequate}"
    )


def language_table(name, language, protocol, root=ROOT):
    table = pd.read_csv(root / "outputs/tables" / f"phase4_{name}_{language}.csv")
    for key, value in metadata(
        protocol, "Python" if language == "python" else "R", root
    ).items():
        if key not in table or not table[key].eq(value).all():
            raise ValueError(f"Stale or mismatched {name}/{language}: {key}")
    return table


def shared_vecm_decision(rank_r, rank_python):
    if rank_r not in range(4) or rank_python not in range(4):
        raise ValueError("Johansen rank must be between zero and three")
    if rank_r != rank_python:
        return (
            None,
            False,
            "Native Johansen rank disagreement; no shared supported rank; VECM withheld",
        )
    rank = int(rank_r)
    if rank == 0:
        return rank, False, "no cointegration supported; VECM not justified"
    if rank == 3:
        return rank, False, "Full rank requires reassessing I(1); no standard VECM"
    return (
        rank,
        True,
        "Both native Johansen procedures support the same positive reduced rank",
    )


def run_vecm_python():
    frame, _, protocol, _ = load_train()
    decision = pd.read_csv(ROOT / "outputs/tables/phase4_vecm_decision.csv").iloc[0]
    if (
        decision.protocol_md5 != metadata(protocol)["protocol_md5"]
        or decision.train_md5 != protocol.train_md5
        or not decision.vecm_justified
    ):
        raise ValueError("Shared decision does not authorize VECM")
    rank = int(decision.cointegration_rank)
    fit = fit_vecm(frame[LEVELS].to_numpy(float), rank, protocol)
    meta = metadata(protocol)
    for name, matrix in [("alpha", fit.alpha), ("beta", fit.beta)]:
        save(
            [
                {
                    "variable": asset,
                    "relation": j + 1,
                    "coefficient": matrix[i, j],
                    "rank": rank,
                    "deterministic": "unrestricted constant (co)",
                    **meta,
                }
                for i, asset in enumerate(ASSETS)
                for j in range(rank)
            ],
            f"vecm_{name}_python",
        )
    rows = []
    for h in [10, 20, 30]:
        test = fit.test_whiteness(h, adjusted=True)
        rows.append(
            {
                "test": "adjusted Portmanteau",
                "horizon": h,
                "test_statistic": test.test_statistic,
                "df": test.df,
                "p_value": test.pvalue,
            }
        )
    test = fit.test_normality()
    rows.append(
        {
            "test": "multivariate Jarque-Bera",
            "horizon": np.nan,
            "test_statistic": test.test_statistic,
            "df": test.df,
            "p_value": test.pvalue,
        }
    )
    save(pd.DataFrame(rows).assign(rank=rank, **meta), "vecm_diagnostics_python")
    print(f"Python conditional VECM PASS: rank={rank}")


def summarize():
    frame, _, protocol, audit = load_train()
    meta = metadata(protocol)
    languages = ["r", "python"]
    manifests = pd.concat(
        [language_table("train_manifest", l, protocol) for l in languages]
    )
    fields = [
        "rows",
        "return_rows",
        "first_date",
        "last_date",
        "train_md5",
        "protocol_md5",
        "variables",
    ]
    if not manifests[fields].nunique().eq(1).all():
        raise ValueError("R/Python input provenance disagreement")
    save(manifests, "train_manifest")
    guards = pd.concat(
        [language_table("holdout_guard", l, protocol) for l in languages]
    )
    if not guards.status.eq("PASS").all():
        raise ValueError("Holdout guard FAIL")
    guard_table(audit, frame, protocol)
    save(guards, "holdout_guard")
    for name in [
        "var_stability",
        "var_residual_serial_correlation",
        "var_residual_normality",
    ]:
        save(pd.concat([language_table(name, l, protocol) for l in languages]), name)
    comparisons = {}
    for name, keys in [
        ("var_lag_selection", ["lag"]),
        ("granger_causality", ["cause", "effect"]),
        ("johansen_trace", ["specification", "level_lags", "null_rank_at_most"]),
    ]:
        r, p = [language_table(name, l, protocol) for l in languages]
        combined = r.merge(
            p, on=keys, suffixes=("_r", "_python"), validate="one_to_one"
        )
        if name == "granger_causality":
            combined["decision_agrees"] = (
                combined.decision_5pct_r == combined.decision_5pct_python
            )
            combined["absolute_statistic_difference"] = abs(
                combined.test_statistic_r - combined.test_statistic_python
            )
        elif name == "johansen_trace":
            combined["rank_agrees"] = (
                combined.selected_rank_r == combined.selected_rank_python
            )
            combined["absolute_trace_difference"] = abs(
                combined.trace_statistic_r - combined.trace_statistic_python
            )
            combined["critical_values_identical"] = np.isclose(
                combined.critical_5pct_r, combined.critical_5pct_python
            )
        else:
            for ic in ["aic", "bic", "hqic", "fpe"]:
                combined[f"absolute_{ic}_difference"] = abs(
                    combined[f"{ic}_r"] - combined[f"{ic}_python"]
                )
        save(
            combined,
            "johansen_rank_comparison"
            if name == "johansen_trace"
            else f"{name}_comparison",
        )
        comparisons[name] = combined
    jo = comparisons["johansen_trace"]
    main = jo.loc[(jo.specification == "main") & (jo.null_rank_at_most == 0)].iloc[0]
    rank, justified, reason = shared_vecm_decision(
        main.selected_rank_r, main.selected_rank_python
    )
    save(
        [
            {
                "cointegration_rank": rank,
                "rank_r": main.selected_rank_r,
                "rank_python": main.selected_rank_python,
                "vecm_justified": justified,
                "reason": reason,
                "level_lags": int(protocol.johansen_level_lags),
                "k_ar_diff": int(protocol.johansen_level_lags) - 1,
                "deterministic_if_estimated": "unrestricted constant outside beta",
                **meta,
            }
        ],
        "vecm_decision",
    )
    if justified:
        for name in ["alpha", "beta", "diagnostics"]:
            if all(
                (ROOT / f"outputs/tables/phase4_vecm_{name}_{l}.csv").exists()
                for l in languages
            ):
                save(
                    pd.concat(
                        [language_table(f"vecm_{name}", l, protocol) for l in languages]
                    ),
                    f"vecm_{name}",
                )
    else:
        for name in ["alpha", "beta", "diagnostics"]:
            if any((ROOT / "outputs/tables").glob(f"phase4_vecm_{name}*.csv")):
                raise ValueError(
                    "Unsupported VECM has stale artifacts; inspect explicitly"
                )
    dynamic = pd.concat(
        [language_table("var_dynamic_decision", l, protocol) for l in languages]
    )
    if dynamic.irf_fevd_permitted.all():
        for name in ["var_irf", "var_fevd"]:
            save(
                pd.concat([language_table(name, l, protocol) for l in languages]), name
            )
    else:
        for name in ["var_irf", "var_fevd"]:
            if (ROOT / f"outputs/tables/phase4_{name}.csv").exists():
                raise ValueError(
                    "Blocked dynamics have stale shared artifacts; inspect explicitly"
                )
    rows = []
    for l in languages:
        lags = language_table("var_lag_selection", l, protocol)
        chosen = lags.loc[lags.selected].iloc[0]
        normal = language_table("var_residual_normality", l, protocol).iloc[0]
        granger = language_table("granger_causality", l, protocol)
        rows.append(
            {
                "language": chosen.language,
                **{
                    f"{ic}_proposed_lag": int(
                        lags.loc[lags[f"{ic}_proposed"], "lag"].iloc[0]
                    )
                    for ic in ["aic", "bic", "hqic", "fpe"]
                },
                "selected_lag": chosen.lag,
                "stable": chosen.stable,
                "max_companion_modulus": chosen.max_companion_modulus,
                "serial_p20": chosen.serial_p20,
                "serial_p30": chosen.serial_p30,
                "serial_adequate": chosen.serial_adequate,
                "normality_p_value": normal.p_value,
                "granger_reject_raw": ";".join(
                    granger.loc[granger.p_value < 0.05].apply(
                        lambda x: f"{x.cause}->{x.effect}", axis=1
                    )
                ),
                "granger_reject_holm": ";".join(
                    granger.loc[granger.p_value_holm < 0.05].apply(
                        lambda x: f"{x.cause}->{x.effect}", axis=1
                    )
                ),
                "johansen_rank": main[f"selected_rank_{l}"],
                "vecm_justified": justified,
                "irf_fevd_permitted": bool(chosen.stable and chosen.serial_adequate),
                "scope": SCOPE,
                "train_md5": protocol.train_md5,
                "protocol_md5": meta["protocol_md5"],
            }
        )
    save(rows, "r_python_summary")
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"Shared VECM justified={justified}: {reason}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--summarize", action="store_true")
    group.add_argument("--vecm", action="store_true")
    args = parser.parse_args()
    if args.summarize:
        summarize()
    elif args.vecm:
        run_vecm_python()
    else:
        run_python()


if __name__ == "__main__":
    main()
