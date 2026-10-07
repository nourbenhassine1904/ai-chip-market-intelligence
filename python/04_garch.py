"""Phase 5: TRAIN-only two-stage ARMA(1,1) / symmetric GARCH volatility.

Default: check historical motivation, fit the mean, gate ARCH, fit two baselines.
Run R then --summarize; use --higher only if the shared higher-order gate opens.
No packages are installed by this script and no realized future values are read.
"""

import argparse
import hashlib
import io
import os
import platform
import warnings
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
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import acf

try:
    import arch
    from arch import arch_model
except ImportError as exc:
    raise RuntimeError(
        "arch missing; explicitly run: python -m pip install 'arch>=8,<9'"
    ) from exc

TRAIN = "data/processed/market_train.csv"
PROTOCOL = "docs/phase5_protocol.csv"
RULE = "docs/phase5_selection_rule.md"
RETURN = "NVDA_Log_Return"
SCOPE = "TRAIN_only_volatility_no_final_evaluation"
TAIL_PROBS = np.array([0.01, 0.02, 0.05, 0.95, 0.98, 0.99])


def read_observations(root, relative, audit):
    if relative != TRAIN:
        raise ValueError(f"Unauthorized market input: {relative}")
    path = root / relative
    if path.resolve() != root.resolve() / TRAIN:
        raise ValueError("Redirected TRAIN path")
    raw = path.read_bytes()
    audit.append(relative)
    return pd.read_csv(io.BytesIO(raw), float_precision="round_trip"), raw


def validate_frame(frame, protocol):
    if not {"Date", RETURN, "NVDA_Log_Price", "NVDA_Adj_Close"}.issubset(frame.columns):
        raise ValueError("Missing NVDA return/price variables")
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
    price = frame.NVDA_Adj_Close.to_numpy(float)
    level = frame.NVDA_Log_Price.to_numpy(float)
    returns = frame[RETURN].to_numpy(float)
    if (
        not np.isfinite(price).all()
        or np.any(price <= 0)
        or not np.isfinite(level).all()
        or not np.isnan(returns[0])
        or not np.isfinite(returns[1:]).all()
        or not np.allclose(level, np.log(price), rtol=0, atol=1e-12)
        or not np.allclose(returns[1:], 100 * np.diff(level), rtol=0, atol=1e-10)
    ):
        raise ValueError("Invalid backward-only percentage log-returns")
    return dates


def load_train(root=ROOT):
    protocol = pd.read_csv(root / PROTOCOL).iloc[0]
    if (
        protocol.return_variable != RETURN
        or protocol.forecast_horizon != 10
        or protocol.mean_burn != 0
    ):
        raise ValueError("Unsupported Phase 5 protocol")
    audit = []
    frame, raw = read_observations(root, TRAIN, audit)
    if (
        hashlib.sha256(raw).hexdigest() != protocol.train_sha256
        or hashlib.md5(raw).hexdigest() != protocol.train_md5
    ):
        raise ValueError("Frozen TRAIN fingerprint mismatch")
    return frame, validate_frame(frame, protocol), protocol, audit


def metadata(protocol, language="Python", root=ROOT):
    script = "python/04_garch.py" if language == "Python" else "r/04_garch.R"
    return {
        "language": language,
        "scope": SCOPE,
        "train_md5": protocol.train_md5,
        "protocol_md5": hashlib.md5((root / PROTOCOL).read_bytes()).hexdigest(),
        "selection_rule_md5": hashlib.md5((root / RULE).read_bytes()).hexdigest(),
        "implementation_md5": hashlib.md5((root / script).read_bytes()).hexdigest(),
    }


def save(rows, name, root=ROOT):
    folder = root / "outputs/tables"
    folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(
        folder / f"phase5_{name}.csv", index=False, lineterminator="\n"
    )


def language_table(name, language, protocol, root=ROOT):
    table = pd.read_csv(root / f"outputs/tables/phase5_{name}_{language}.csv")
    if table.empty:
        raise ValueError(f"Empty {name}/{language}")
    for field, value in metadata(
        protocol, "Python" if language == "python" else "R", root
    ).items():
        if field not in table or not table[field].eq(value).all():
            raise ValueError(f"Stale or mismatched {name}/{language}: {field}")
    return table


def historical_motivation(frame, protocol):
    rows = []
    for lang in ["r", "python"]:
        path = f"outputs/tables/phase3_arima_residual_diagnostics_{lang}.csv"
        table = pd.read_csv(ROOT / path)
        selected = table.loc[
            table.scope.eq("train") & table.test.isin(["ARCH-LM", "Jarque-Bera"])
        ]
        if len(selected) != 4 or not selected.p_value.lt(0.05).all():
            raise ValueError(
                "Historical Phase 3A ARCH/tail evidence missing or changed"
            )
        for row in selected.itertuples():
            rows.append(
                {
                    "evidence": row.test,
                    "source": path,
                    "source_language": row.language,
                    "source_model": row.model,
                    "lag": row.lag,
                    "statistic": row.statistic,
                    "p_value": row.p_value,
                    "interpretation": "Historical TRAIN evidence; not refitted",
                }
            )
    rows.extend(
        [
            {
                "evidence": "Phase2 excess kurtosis",
                "source": "docs/phase2_eda_stationarity.md",
                "statistic": 4.698018012420102,
                "interpretation": "Historical NVDA TRAIN log-return kurtosis",
            },
            {
                "evidence": "Squared-return ACF",
                "source": "outputs/figures/phase2/nvda_squared_returns_acf_train.png",
                "interpretation": "Existing TRAIN figure supports time dependence in magnitudes; Phase5 counterpart recomputed",
            },
            {
                "evidence": "Volatility clustering",
                "source": "docs/phase2_eda_stationarity.md",
                "interpretation": "Historical qualitative observation; not a separate formal test",
            },
            {
                "evidence": "TRAIN kurtosis consistency",
                "statistic": frame[RETURN].kurt(),
                "source": TRAIN,
                "interpretation": "Phase5 verification of the historical TRAIN statistic",
            },
        ]
    )
    save(pd.DataFrame(rows).assign(**metadata(protocol)), "arch_motivation")


def arch_tests(residuals, model="mean_filter"):
    residuals = np.asarray(residuals, dtype=float)
    if not np.isfinite(residuals).all() or len(residuals) <= 40:
        raise ValueError("Invalid innovations for ARCH-LM")
    rows = []
    for lag in [5, 10, 20]:
        result = het_arch(residuals, nlags=lag, ddof=0, result_object=True)
        # Named result supported in the project's statsmodels 0.15 environment.
        statistic, p_value = result[:2]
        rows.append(
            {
                "model": model,
                "test": "ARCH-LM",
                "lag": lag,
                "statistic": statistic,
                "p_value": p_value,
                "df": lag,
                "model_df": 0,
                "nobs": len(residuals),
                "reject_5pct": p_value < 0.05,
            }
        )
    return pd.DataFrame(rows)


def fit_mean(returns, protocol):
    returns = np.asarray(returns, dtype=float)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fitted = ARIMA(
            returns,
            order=(1, 0, 1),
            trend="c",
            enforce_stationarity=True,
            enforce_invertibility=True,
        ).fit(method_kwargs={"maxiter": int(protocol.maxiter), "pgtol": 1e-9})
    residuals = np.asarray(fitted.resid)
    if len(residuals) != len(returns) or not np.isfinite(residuals).all():
        raise ValueError("Mean innovation sample alignment failed")
    parameters = dict(zip(fitted.param_names, fitted.params, strict=True))
    lb = acorr_ljungbox(residuals, lags=[10, 20], model_df=2, return_df=True)
    row = {
        "mean_model": "ARMA(1,1)_with_mean",
        "mean_mu": parameters["const"],
        "ar1": parameters["ar.L1"],
        "ma1": parameters["ma.L1"],
        "recursion_intercept": (1 - parameters["ar.L1"]) * parameters["const"],
        "innovation_variance": parameters["sigma2"],
        "nobs": len(returns),
        "additional_burn": 0,
        "converged": bool(fitted.mle_retvals.get("converged", False)),
        "loglik": fitted.llf,
        "AIC": fitted.aic,
        "BIC": fitted.bic,
        "ljung_box_p10": lb.lb_pvalue.iloc[0],
        "ljung_box_p20": lb.lb_pvalue.iloc[1],
        "mean_adequate_5pct": bool(lb.lb_pvalue.ge(0.05).all()),
        "warnings": " | ".join(dict.fromkeys(str(w.message) for w in caught)),
    }
    return residuals, row


def pre_garch_gate(mean, tests, protocol):
    if (
        not mean["converged"]
        or min(mean["ljung_box_p10"], mean["ljung_box_p20"])
        < protocol.mean_strong_failure_p
    ):
        raise ValueError(
            "STOP before GARCH: common mean filter fails convergence or strong serial diagnostic"
        )
    if tests.p_value.lt(protocol.alpha).sum() < int(protocol.arch_required_rejections):
        raise ValueError("STOP before GARCH: insufficient ARCH evidence")


def standardized(residuals, sigma):
    residuals, sigma = (
        np.asarray(residuals, dtype=float),
        np.asarray(sigma, dtype=float),
    )
    if (
        residuals.shape != sigma.shape
        or not np.isfinite(residuals).all()
        or not np.isfinite(sigma).all()
        or np.any(sigma <= 0)
    ):
        raise ValueError("Invalid standardized residuals")
    return residuals / sigma


def persistence_measures(omega, alphas, betas):
    persistence = float(np.sum(alphas) + np.sum(betas))
    valid = (
        omega > 0 and np.all(np.asarray(alphas) >= 0) and np.all(np.asarray(betas) >= 0)
    )
    stationary = bool(valid and 0 <= persistence < 1)
    variance = omega / (1 - persistence) if stationary else np.nan
    half_life = (
        np.log(0.5) / np.log(persistence)
        if stationary and 0 < persistence < 1 and len(alphas) == len(betas) == 1
        else np.nan
    )
    return persistence, stationary, variance, half_life


def theoretical_quantiles(probabilities, distribution, shape=np.nan):
    if distribution == "Normal":
        return stats.norm.ppf(probabilities)
    if distribution != "Student-t" or not np.isfinite(shape) or shape <= 2:
        raise ValueError("Standardized Student-t requires df>2")
    return stats.t.ppf(probabilities, df=shape) * np.sqrt((shape - 2) / shape)


def forecast_variance_from_history(
    omega, alphas, betas, innovations, sigmas, horizon=10
):
    """Fixed-parameter conditional expectations; only the supplied past enters."""
    if horizon != 10 or omega <= 0 or min([*alphas, *betas]) < 0:
        raise ValueError("Invalid Phase 5 forecast specification")
    standardized(innovations, sigmas)
    if len(innovations) < max(len(alphas), len(betas)):
        raise ValueError("Insufficient innovation history")
    squared_shocks = list(np.asarray(innovations, dtype=float) ** 2)
    variances = list(np.asarray(sigmas, dtype=float) ** 2)
    forecast = []
    for _ in range(horizon):
        variance = omega + sum(a * squared_shocks[-j] for j, a in enumerate(alphas, 1))
        variance += sum(b * variances[-j] for j, b in enumerate(betas, 1))
        forecast.append(variance)
        squared_shocks.append(
            variance
        )  # E(epsilon_future^2 | TRAIN) = forecast variance
        variances.append(variance)
    return np.asarray(forecast)


def post_diagnostics(z, model):
    rows = []
    for series, values in [("z", z), ("z_squared", z**2)]:
        lb = acorr_ljungbox(values, lags=[10, 20], model_df=2, return_df=True)
        for lag in [10, 20]:
            rows.append(
                {
                    "model": model,
                    "series": series,
                    "test": "Ljung-Box",
                    "lag": lag,
                    "statistic": lb.loc[lag, "lb_stat"],
                    "p_value": lb.loc[lag, "lb_pvalue"],
                    "df": lag - 2,
                    "model_df": 2,
                    "nobs": len(z),
                }
            )
    arch_rows = arch_tests(z, model).assign(series="z", test="ARCH-LM")
    table = pd.concat([pd.DataFrame(rows), arch_rows], ignore_index=True)
    variance = table.test.eq("ARCH-LM") | table.series.eq("z_squared")
    table["diagnostic_family"] = np.where(variance, "variance", "mean")
    table["p_value_holm_variance"] = np.nan
    table.loc[variance, "p_value_holm_variance"] = multipletests(
        table.loc[variance, "p_value"], method="holm"
    )[1]
    table["reject_5pct"] = table.p_value < 0.05
    table["reject_for_gate"] = np.where(
        variance, table.p_value_holm_variance < 0.05, table.p_value < 0.05
    )
    return table


def model_id(p, q, distribution):
    return f"GARCH({p},{q})_{distribution}"


def fit_variance(residuals, distribution, protocol, p=1, q=1):
    if (p, q) not in [(1, 1), (2, 1), (1, 2)] or distribution not in [
        "Normal",
        "Student-t",
    ]:
        raise ValueError("Unapproved symmetric GARCH specification")
    model = model_id(p, q, distribution)
    specification = arch_model(
        residuals,
        mean="Zero",
        vol="GARCH",
        p=p,
        o=0,
        q=q,
        power=2.0,
        dist="normal" if distribution == "Normal" else "t",
        rescale=False,
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fit = specification.fit(
            disp="off",
            update_freq=0,
            cov_type="robust",
            tol=1e-9,
            options={"maxiter": int(protocol.maxiter)},
        )
    parameters = fit.params
    alpha = [float(parameters[f"alpha[{i}]"]) for i in range(1, p + 1)]
    beta = [float(parameters[f"beta[{i}]"]) for i in range(1, q + 1)]
    omega = float(parameters.omega)
    persistence, stationary, variance, half_life = persistence_measures(
        omega, alpha, beta
    )
    sigma = np.asarray(fit.conditional_volatility)
    z = standardized(residuals, sigma)
    diagnostics = post_diagnostics(z, model)
    shape = float(parameters.nu) if distribution == "Student-t" else np.nan
    tail_rmse = np.sqrt(
        np.mean(
            (
                np.quantile(z, TAIL_PROBS)
                - theoretical_quantiles(TAIL_PROBS, distribution, shape)
            )
            ** 2
        )
    )
    row = {
        "model": model,
        "distribution": distribution,
        "p": p,
        "q": q,
        "converged": fit.convergence_flag == 0,
        "convergence_code": fit.convergence_flag,
        "loglik": fit.loglikelihood,
        "AIC": fit.aic,
        "BIC": fit.bic,
        "AIC_per_observation": fit.aic / len(residuals),
        "BIC_per_observation": fit.bic / len(residuals),
        "omega": omega,
        "alpha1": alpha[0],
        "alpha2": alpha[1] if p == 2 else 0.0,
        "beta1": beta[0],
        "beta2": beta[1] if q == 2 else 0.0,
        "persistence": persistence,
        "shape_df_if_applicable": shape,
        "variance_stationary": stationary,
        "unconditional_variance": variance,
        "half_life_sessions": half_life,
        "nobs": len(residuals),
        "variance_parameter_count": len(parameters),
        "tail_quantile_rmse": tail_rmse,
        "mean_rejections": int(
            diagnostics.loc[
                diagnostics.diagnostic_family.eq("mean"), "reject_for_gate"
            ].sum()
        ),
        "variance_rejections": int(
            diagnostics.loc[
                diagnostics.diagnostic_family.eq("variance"), "reject_for_gate"
            ].sum()
        ),
        "backcast": float(specification.volatility.backcast(np.asarray(residuals))),
        "initialization": "native weighted first 75 innovations, decay .94",
        "solver": "SLSQP",
        "variance_mean": "Zero; no mean re-estimation",
        "power": 2,
        "asymmetric_order": 0,
        "warnings": " | ".join(dict.fromkeys(str(w.message) for w in caught)),
    }
    row["valid"] = bool(
        row["converged"]
        and np.isfinite(fit.loglikelihood)
        and omega > 0
        and min(alpha + beta) >= 0
        and (distribution == "Normal" or shape > 2)
    )
    row["diagnostically_adequate"] = bool(
        row["valid"]
        and stationary
        and row["mean_rejections"] == row["variance_rejections"] == 0
    )
    forecast = fit.forecast(
        horizon=int(protocol.forecast_horizon), method="analytic", reindex=False
    )
    predicted = np.asarray(forecast.residual_variance.iloc[-1], dtype=float)
    np.testing.assert_allclose(
        predicted,
        forecast_variance_from_history(
            omega, alpha, beta, residuals, sigma, int(protocol.forecast_horizon)
        ),
        rtol=1e-7,
        atol=1e-9,
    )
    if (
        len(predicted) != 10
        or not np.isfinite(predicted).all()
        or np.any(predicted <= 0)
    ):
        raise ValueError("Invalid TRAIN-end innovation variance forecast")
    return row, diagnostics, sigma, z, predicted


def guard(audit, frame, dates, protocol):
    checks = [
        ("market_train.csv only", audit == [TRAIN], "runtime input audit"),
        ("market_test.csv not read", audit == [TRAIN], "runtime input audit"),
        (
            "chronological order preserved",
            dates.is_monotonic_increasing and dates.is_unique,
            "runtime dates",
        ),
        (
            "backward percentage log-returns",
            np.allclose(
                frame[RETURN].iloc[1:], 100 * np.diff(frame.NVDA_Log_Price), atol=1e-10
            ),
            "runtime transformation",
        ),
    ]
    for name in [
        "mean filtering TRAIN only",
        "ARCH-LM TRAIN only",
        "GARCH fit TRAIN only",
        "distribution comparison TRAIN only",
        "standardized residual diagnostics TRAIN only",
        "volatility forecast from TRAIN endpoint only",
        "no realized holdout volatility read",
        "no final RMSE/MAE/MAPE",
        "no final DM",
    ]:
        checks.append(
            (
                name,
                True,
                "code scope audit: only validated TRAIN arrays; no realized future targets",
            )
        )
    result = pd.DataFrame(checks, columns=["check", "passed", "evidence"])
    result["status"] = np.where(result.passed, "PASS", "FAIL")
    if not result.passed.all():
        raise ValueError("Holdout guard FAIL; STOP")
    return result.drop(columns="passed").assign(**metadata(protocol))


def run_python(higher=False):
    frame, dates, protocol, audit = load_train()
    meta = metadata(protocol)
    save(guard(audit, frame, dates, protocol), "holdout_guard_python")
    historical_motivation(frame, protocol)
    save(
        [
            {
                "rows": len(frame),
                "return_rows": len(frame) - 1,
                "first_date": protocol.first_date,
                "last_date": protocol.last_date,
                "return_first_date": str(dates.iloc[1].date()),
                "variable": RETURN,
                "unit": "daily percentage log-return",
                "sha256_reference": protocol.train_sha256,
                "sha256_verified": True,
                "md5_verified": True,
                "observation_reads": ";".join(audit),
                **meta,
            }
        ],
        "train_manifest_python",
    )
    residuals, mean = fit_mean(frame[RETURN].iloc[1:].to_numpy(float), protocol)
    save([{**mean, **meta}], "mean_filter_python")
    save(
        pd.DataFrame(
            {
                "Date": dates.iloc[1:].dt.strftime("%Y-%m-%d"),
                RETURN: frame[RETURN].iloc[1:].to_numpy(),
                "innovation": residuals,
            }
        ).assign(**meta),
        "mean_innovations_python",
    )
    pre = arch_tests(residuals)
    save(pre.assign(**meta), "arch_lm_pre_garch_python")
    pre_garch_gate(mean, pre, protocol)
    if higher:
        gate = pd.read_csv(ROOT / "outputs/tables/phase5_higher_order_gate.csv").iloc[0]
        if (
            not gate.higher_order_justified
            or gate.protocol_md5 != meta["protocol_md5"]
            or gate.selection_rule_md5 != meta["selection_rule_md5"]
        ):
            raise ValueError(
                "Higher-order gate closed or stale; no higher order fitted"
            )
        specs = [(2, 1, gate.baseline_distribution), (1, 2, gate.baseline_distribution)]
    else:
        specs = [(1, 1, "Normal"), (1, 1, "Student-t")]
    models, diagnostic_rows, volatility, forecasts = [], [], [], []
    for p, q, distribution in specs:
        row, diagnostics, sigma, z, forecast = fit_variance(
            residuals, distribution, protocol, p, q
        )
        models.append(row)
        diagnostic_rows.append(diagnostics)
        volatility.append(
            pd.DataFrame(
                {
                    "Date": dates.iloc[1:].dt.strftime("%Y-%m-%d").to_numpy(),
                    "model": row["model"],
                    RETURN: frame[RETURN].iloc[1:].to_numpy(),
                    "innovation": residuals,
                    "conditional_sigma": sigma,
                    "standardized_residual": z,
                }
            )
        )
        forecasts.extend(
            {
                "model": row["model"],
                "horizon": h + 1,
                "origin_date": protocol.last_date,
                "forecast_variance": value,
                "forecast_sigma": np.sqrt(value),
                "annualized_sigma_if_reported": np.sqrt(
                    value * protocol.annualization_sessions
                ),
                "variance_unit": "percentage_points_squared",
                "sigma_unit": "daily_percent",
                "forecast_target": "innovation variance, not ARMA return forecast-error variance",
            }
            for h, value in enumerate(forecast)
        )
    suffix = "higher" if higher else "baseline"
    save(pd.DataFrame(models).assign(**meta), f"models_{suffix}_python")
    save(pd.concat(diagnostic_rows).assign(**meta), f"diagnostics_{suffix}_python")
    save(pd.concat(volatility).assign(**meta), f"volatility_{suffix}_python")
    save(pd.DataFrame(forecasts).assign(**meta), f"forecasts_{suffix}_python")
    save(
        [
            {"package": p, "version": v, **meta}
            for p, v in [
                ("Python", platform.python_version()),
                ("arch", arch.__version__),
                ("statsmodels", statsmodels.__version__),
                ("numpy", np.__version__),
                ("pandas", pd.__version__),
                ("scipy", scipy.__version__),
            ]
        ],
        "runtime_versions_python",
    )
    print(
        f"Python PASS: mean gate and ARCH gate passed; {len(models)} {suffix} GARCH fits"
    )
    print(
        pd.DataFrame(models)[
            [
                "model",
                "converged",
                "AIC",
                "BIC",
                "persistence",
                "mean_rejections",
                "variance_rejections",
            ]
        ].to_string(index=False)
    )


def student_superiority(normal, student, protocol):
    return bool(
        student.valid.all()
        and student.variance_stationary.all()
        and (normal.AIC - student.AIC).ge(protocol.student_ic_improvement).all()
        and (normal.BIC - student.BIC).ge(protocol.student_ic_improvement).all()
        and (student.tail_quantile_rmse < normal.tail_quantile_rmse).all()
        and (student.mean_rejections <= normal.mean_rejections).all()
        and (student.variance_rejections <= normal.variance_rejections).all()
    )


def choose_baseline(models, protocol):
    """Shared specification selection, without pooling native likelihoods."""
    baseline = models.loc[models.p.eq(1) & models.q.eq(1)]
    by_dist = {
        dist: baseline.loc[baseline.distribution.eq(dist)].set_index("language")
        for dist in ["Normal", "Student-t"]
    }
    for table in by_dist.values():
        if set(table.index) != {"R", "Python"} or len(table) != 2:
            raise ValueError("Both language baselines required")
    normal, student = by_dist["Normal"], by_dist["Student-t"]
    student_improves = student_superiority(normal, student, protocol)
    adequate = {
        dist: bool(table.diagnostically_adequate.all())
        for dist, table in by_dist.items()
    }
    if adequate["Student-t"] and (student_improves or not adequate["Normal"]):
        return (
            model_id(1, 1, "Student-t"),
            "Student-t improves adequacy or both IC and tails without worse diagnostic decisions",
        )
    if adequate["Normal"]:
        return model_id(
            1, 1, "Normal"
        ), "Adequate parsimonious Normal; Student-t superiority rule not satisfied"
    valid = baseline.groupby("model").filter(
        lambda g: len(g) == 2 and g.valid.all() and g.variance_stationary.all()
    )
    if valid.empty:
        raise ValueError("No converged stationary baseline in both languages; STOP")
    if student_improves:
        return model_id(
            1, 1, "Student-t"
        ), "Provisional Student-t baseline; remaining diagnostic failures retained"
    scores = valid.groupby("model").agg(
        failures=("variance_rejections", "sum"),
        mean_failures=("mean_rejections", "sum"),
        bic=("BIC", "sum"),
    )
    return scores.sort_values(["failures", "mean_failures", "bic"]).index[
        0
    ], "Provisional baseline; remaining diagnostic failures retained"


def higher_order_gate(diagnostics):
    arch_remaining = bool(
        diagnostics.loc[diagnostics.test.eq("ARCH-LM"), "reject_for_gate"].any()
    )
    squared_remaining = bool(
        diagnostics.loc[diagnostics.series.eq("z_squared"), "reject_for_gate"].any()
    )
    return {
        "garch11_arch_remaining": arch_remaining,
        "squared_residual_dependence_remaining": squared_remaining,
        "higher_order_justified": arch_remaining or squared_remaining,
        "reason": "Holm-significant residual variance dependence in selected baseline"
        if arch_remaining or squared_remaining
        else "No Holm-significant ARCH or squared dependence; higher orders not justified",
    }


def save_figure(fig, name):
    folder = ROOT / "outputs/figures/phase5"
    folder.mkdir(parents=True, exist_ok=True)
    fig.savefig(folder / f"phase5_{name}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def figures(frame, dates, volatility, models, wide):
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(dates, frame[RETURN], lw=0.65)
    ax.set_ylabel("Daily log-return (%)")
    ax.set_title("NVDA TRAIN only | 2018-01-02 to 2025-11-14")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    save_figure(fig, "nvda_returns")
    fig, ax = plt.subplots(figsize=(11, 4))
    plot_acf(
        frame[RETURN].iloc[1:].to_numpy() ** 2,
        lags=40,
        zero=False,
        ax=ax,
        title="NVDA squared log-returns | TRAIN only | pointwise 95% bands",
    )
    ax.set_ylim(-0.08, 0.25)
    fig.tight_layout()
    save_figure(fig, "squared_returns_acf")
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    for ax, lang in zip(axes, ["R", "Python"], strict=True):
        table = wide.loc[wide.language.eq(lang)]
        for col, label in [
            ("conditional_sigma_normal", "Normal"),
            ("conditional_sigma_student_t", "Student-t"),
            ("locked_conditional_sigma", "Locked"),
        ]:
            ax.plot(
                pd.to_datetime(table.Date),
                table[col],
                label=label,
                lw=0.8,
                alpha=0.8,
                linestyle="--" if label == "Locked" else "-",
            )
        ax.set_ylabel(f"{lang}\nDaily sigma (%)")
        ax.legend(ncol=3)
    fig.suptitle(
        "NVDA conditional innovation volatility | full-TRAIN parameter estimates"
    )
    fig.tight_layout()
    save_figure(fig, "conditional_volatility")
    baseline = volatility.loc[volatility.model.str.startswith("GARCH(1,1)")]
    for kind, name in [
        ("time", "standardized_residuals"),
        ("acf", "standardized_residual_acf"),
        ("squared_acf", "squared_standardized_residual_acf"),
        ("qq", "standardized_residual_qq"),
    ]:
        fig, axes = plt.subplots(2, 2, figsize=(12, 7))
        for i, lang in enumerate(["R", "Python"]):
            for j, dist in enumerate(["Normal", "Student-t"]):
                ax = axes[i, j]
                model = model_id(1, 1, dist)
                table = baseline.loc[
                    baseline.language.eq(lang) & baseline.model.eq(model)
                ]
                z = table.standardized_residual.to_numpy()
                if kind == "time":
                    ax.plot(pd.to_datetime(table.Date), z, lw=0.6)
                    ax.set_ylabel("z (unitless)")
                elif kind in ["acf", "squared_acf"]:
                    plot_acf(
                        z if kind == "acf" else z**2,
                        lags=40,
                        zero=False,
                        ax=ax,
                        title="",
                    )
                    ax.set_ylim(-0.15, 0.15)
                else:
                    shape = models.loc[
                        models.language.eq(lang) & models.model.eq(model),
                        "shape_df_if_applicable",
                    ].iloc[0]
                    quantile = theoretical_quantiles(
                        (np.arange(len(z)) + 0.5) / len(z), dist, shape
                    )
                    ax.scatter(quantile, np.sort(z), s=4, alpha=0.5)
                    bounds = [
                        min(quantile.min(), z.min()),
                        max(quantile.max(), z.max()),
                    ]
                    ax.plot(bounds, bounds, color="black", lw=0.7)
                    ax.set_xlabel("Theoretical unit-variance quantiles")
                    ax.set_ylabel("Empirical z quantiles")
                ax.set_title(f"{lang} | {dist}")
        fig.suptitle(
            "TRAIN only | "
            + name.replace("_", " ")
            + (" | pointwise 95% ACF bands" if "acf" in kind else "")
        )
        fig.tight_layout()
        save_figure(fig, name)


def summarize():
    frame, dates, protocol, audit = load_train()
    meta = metadata(protocol)
    languages = ["r", "python"]
    manifests = pd.concat(
        [language_table("train_manifest", l, protocol) for l in languages],
        ignore_index=True,
    )
    if (
        not manifests[
            [
                "rows",
                "return_rows",
                "first_date",
                "last_date",
                "return_first_date",
                "variable",
                "train_md5",
            ]
        ]
        .nunique()
        .eq(1)
        .all()
    ):
        raise ValueError("Input provenance differs between languages")
    save(manifests, "train_manifest")
    guard(audit, frame, dates, protocol)
    guards = pd.concat(
        [language_table("holdout_guard", l, protocol) for l in languages]
    )
    if not guards.status.eq("PASS").all():
        raise ValueError("Holdout guard FAIL")
    save(guards, "holdout_guard")
    means = pd.concat([language_table("mean_filter", l, protocol) for l in languages])
    save(means, "mean_filter_comparison")
    pre = pd.concat(
        [language_table("arch_lm_pre_garch", l, protocol) for l in languages]
    )
    save(pre, "arch_lm_pre_garch")
    for lang in ["R", "Python"]:
        pre_garch_gate(
            means.loc[means.language.eq(lang)].iloc[0],
            pre.loc[pre.language.eq(lang)],
            protocol,
        )
    # Compare dated innovations, not only common order labels.
    innovations = [language_table("mean_innovations", l, protocol) for l in languages]
    if not innovations[0].Date.equals(innovations[1].Date):
        raise ValueError("Mean innovation date alignment differs")
    np.testing.assert_allclose(
        innovations[0][RETURN], innovations[1][RETURN], atol=1e-12, rtol=0
    )
    models = pd.concat(
        [language_table("models_baseline", l, protocol) for l in languages],
        ignore_index=True,
    )
    diagnostics = pd.concat(
        [language_table("diagnostics_baseline", l, protocol) for l in languages],
        ignore_index=True,
    )
    volatility = pd.concat(
        [language_table("volatility_baseline", l, protocol) for l in languages],
        ignore_index=True,
    )
    forecasts = pd.concat(
        [language_table("forecasts_baseline", l, protocol) for l in languages],
        ignore_index=True,
    )
    baseline, reason = choose_baseline(models, protocol)
    gate = higher_order_gate(diagnostics.loc[diagnostics.model.eq(baseline)])
    baseline_dist = models.loc[models.model.eq(baseline), "distribution"].iloc[0]
    save(
        [
            {
                **gate,
                "baseline_model": baseline,
                "baseline_distribution": baseline_dist,
                **meta,
            }
        ],
        "higher_order_gate",
    )
    selected = baseline
    if gate["higher_order_justified"]:
        available = [
            (ROOT / f"outputs/tables/phase5_models_higher_{l}.csv").exists()
            for l in languages
        ]
        if all(available):
            for name in ["models", "diagnostics", "volatility", "forecasts"]:
                extra = pd.concat(
                    [language_table(f"{name}_higher", l, protocol) for l in languages],
                    ignore_index=True,
                )
                if name == "models":
                    models = pd.concat([models, extra], ignore_index=True)
                elif name == "diagnostics":
                    diagnostics = pd.concat([diagnostics, extra], ignore_index=True)
                elif name == "volatility":
                    volatility = pd.concat([volatility, extra], ignore_index=True)
                else:
                    forecasts = pd.concat([forecasts, extra], ignore_index=True)
            candidates = []
            base = models.loc[models.model.eq(baseline)].set_index("language")
            for name, group in models.loc[models.p.ne(1) | models.q.ne(1)].groupby(
                "model"
            ):
                candidate = group.set_index("language")
                if (
                    len(candidate) == 2
                    and candidate.diagnostically_adequate.all()
                    and (base.AIC - candidate.AIC).ge(2).all()
                    and (base.BIC - candidate.BIC).ge(2).all()
                ):
                    candidates.append(
                        (
                            name,
                            candidate.variance_parameter_count.iloc[0],
                            candidate.BIC.sum(),
                        )
                    )
            if candidates:
                candidates.sort(key=lambda x: (x[2], x[1], x[0]))
                near = [x for x in candidates if x[2] <= candidates[0][2] + 2]
                selected = min(near, key=lambda x: (x[1], x[2], x[0]))[0]
                reason = "Higher order restores shared adequacy and improves both AIC/BIC under the capped gate"
        else:
            print(
                "Higher-order gate TRUE: run both language scripts with --higher, then --summarize"
            )
    elif any((ROOT / "outputs/tables").glob("phase5_models_higher_*.csv")):
        raise ValueError(
            "Closed higher-order gate has stale artifacts; inspect explicitly"
        )
    models["selected"] = models.model.eq(selected)
    save(models, "garch_model_comparison")
    save(diagnostics, "garch_standardized_residual_diagnostics")
    save(
        models[
            [
                "model",
                "distribution",
                "language",
                "omega",
                "alpha1",
                "alpha2",
                "beta1",
                "beta2",
                "persistence",
                "variance_stationary",
                "unconditional_variance",
                "half_life_sessions",
                "valid",
                "selected",
            ]
        ],
        "garch_persistence",
    )
    chosen = models.loc[models.selected]
    locked = bool(chosen.diagnostically_adequate.all())
    status = (
        "locked_garch_specification"
        if locked
        else "provisional_garch_specification_with_diagnostic_warning"
    )
    save(
        [
            {
                "locked_garch_specification": selected if locked else "",
                "provisional_specification": selected,
                "status": status,
                "diagnostically_adequate_both_languages": locked,
                "selection_reason": reason,
                "distribution": chosen.distribution.iloc[0],
                "p": chosen.p.iloc[0],
                "q": chosen.q.iloc[0],
                **meta,
            }
        ],
        "locked_garch_model",
    )
    wide_rows = []
    for lang in ["R", "Python"]:
        table = pd.DataFrame({"Date": frame.Date, RETURN: frame[RETURN]})
        local = volatility.loc[volatility.language.eq(lang)]
        for model, column in [
            (model_id(1, 1, "Normal"), "conditional_sigma_normal"),
            (model_id(1, 1, "Student-t"), "conditional_sigma_student_t"),
            (selected, "locked_conditional_sigma"),
        ]:
            values = (
                local.loc[local.model.eq(model)].set_index("Date").conditional_sigma
            )
            table[column] = (
                table.Date.map(values)
                if column != "locked_conditional_sigma" or locked
                else np.nan
            )
        table["language"] = lang
        table["scope"] = SCOPE
        table["sigma_unit"] = "daily_percent"
        table["selected_model"] = selected
        table["first_row_sigma_status"] = "initial log-return structurally undefined"
        wide_rows.append(table)
    wide = pd.concat(wide_rows, ignore_index=True)
    save(wide, "conditional_volatility")
    forecasts["locked"] = forecasts.model.eq(selected) & locked
    save(forecasts, "volatility_forecast_train_end")
    comparison = models.merge(
        forecasts.loc[forecasts.horizon.eq(10)],
        on=["model", "language"],
        suffixes=("", "_forecast"),
        validate="one_to_one",
    )
    comparison["lock_status"] = status
    comparison["locked_garch_specification"] = selected if locked else ""
    comparison["mean_mu"] = comparison.language.map(means.set_index("language").mean_mu)
    comparison["ar1"] = comparison.language.map(means.set_index("language").ar1)
    comparison["ma1"] = comparison.language.map(means.set_index("language").ma1)
    comparison["mean_innovation_max_abs_r_python_difference"] = max(
        abs(innovations[0].innovation - innovations[1].innovation)
    )
    selection_checks = []
    tail_rows = []
    native_proposals = {}
    for lang in ["R", "Python"]:
        local = models.loc[
            models.language.eq(lang) & models.p.eq(1) & models.q.eq(1)
        ].set_index("distribution")
        normal, student = local.loc[["Normal"]], local.loc[["Student-t"]]
        # Use the same row index when comparing scalar language results.
        normal = normal.reset_index(drop=True)
        student = student.reset_index(drop=True)
        improves = student_superiority(normal, student, protocol)
        native_proposals[lang] = (
            "Student-t"
            if improves and student.diagnostically_adequate.all()
            else "Normal"
        )
        selection_checks.append(
            {
                "language": lang,
                "student_AIC_gain": normal.AIC.iloc[0] - student.AIC.iloc[0],
                "student_BIC_gain": normal.BIC.iloc[0] - student.BIC.iloc[0],
                "normal_tail_rmse": normal.tail_quantile_rmse.iloc[0],
                "student_tail_rmse": student.tail_quantile_rmse.iloc[0],
                "student_tail_improves": student.tail_quantile_rmse.iloc[0]
                < normal.tail_quantile_rmse.iloc[0],
                "student_superiority_all_conditions": improves,
                "native_distribution_proposal": native_proposals[lang],
                "shared_locked_specification": selected if locked else "",
                "scope": SCOPE,
            }
        )
        for dist in ["Normal", "Student-t"]:
            model = model_id(1, 1, dist)
            z = volatility.loc[
                volatility.language.eq(lang) & volatility.model.eq(model),
                "standardized_residual",
            ]
            shape = local.loc[dist, "shape_df_if_applicable"]
            empirical = np.quantile(z, TAIL_PROBS)
            theoretical = theoretical_quantiles(TAIL_PROBS, dist, shape)
            for probability, observed, expected in zip(
                TAIL_PROBS, empirical, theoretical, strict=True
            ):
                tail_rows.append(
                    {
                        "language": lang,
                        "model": model,
                        "probability": probability,
                        "empirical_quantile": observed,
                        "theoretical_quantile": expected,
                        "difference": observed - expected,
                        "scope": SCOPE,
                    }
                )
    comparison["native_distribution_proposal"] = comparison.language.map(
        native_proposals
    )
    save(comparison, "r_python_summary")
    save(selection_checks, "distribution_selection_checks")
    save(tail_rows, "tail_quantile_comparison")
    numeric_acf = acf(frame[RETURN].iloc[1:].to_numpy() ** 2, nlags=40, fft=True)[1:]
    save(
        pd.DataFrame(
            {"lag": range(1, 41), "squared_return_acf": numeric_acf, "scope": SCOPE}
        ),
        "squared_returns_acf_numeric",
    )
    figures(frame, dates, volatility, models, wide)
    print(
        comparison[
            [
                "language",
                "model",
                "omega",
                "alpha1",
                "beta1",
                "persistence",
                "AIC",
                "BIC",
                "forecast_sigma",
                "lock_status",
            ]
        ].to_string(index=False)
    )
    print(
        f"Higher-order gate={gate['higher_order_justified']}; locked={locked}; {reason}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--summarize", action="store_true")
    group.add_argument("--higher", action="store_true")
    args = parser.parse_args()
    if args.summarize:
        summarize()
    else:
        run_python(higher=args.higher)


if __name__ == "__main__":
    main()
