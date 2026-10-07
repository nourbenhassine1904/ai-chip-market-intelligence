"""
AI-Chip Market Intelligence
Phase 2 — Exploratory Analysis, Financial Transformations and Stationarity

This phase creates financial transformations, defines the chronological
train/test split and performs exploratory/statistical diagnostics.

No forecasting model is estimated here.
"""

import hashlib
import itertools
import json
import os
import platform
import sys
import warnings
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".cache" / "matplotlib")
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import statsmodels
from scipy import stats
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import adfuller, kpss

ROOT = Path(__file__).resolve().parents[1]
TICKERS = ["NVDA", "AMD", "SOXX"]
FIELDS = ["Open", "High", "Low", "Close", "Adj_Close", "Volume"]
CANONICAL_COLUMNS = ["Date", *[f"{t}_{f}" for t in TICKERS for f in FIELDS]]
DERIVED = [
    "Log_Price",
    "Log_Return",
    "Return_Pct",
    "Volume_Change_Pct",
    "Rolling_Vol_20D",
]
COLORS = {"NVDA": "#3478a5", "AMD": "#bc7540", "SOXX": "#578568"}
TEST_COLUMNS = [
    "ticker",
    "series",
    "transformation",
    "test",
    "scope",
    "test_statistic",
    "p_value",
    "used_lag",
    "lags",
    "nobs",
    "critical_1pct",
    "critical_5pct",
    "critical_10pct",
    "critical_values",
    "regression",
    "decision_5pct",
    "p_value_bound",
    "warnings",
]
STAT_COLUMNS = [
    "ticker",
    "series",
    "scope",
    "count",
    "mean",
    "median",
    "variance",
    "standard_deviation",
    "minimum",
    "Q1",
    "Q3",
    "maximum",
    "skewness",
    "kurtosis",
]


class EDAError(RuntimeError):
    """Invalid input or failed integrity/leakage check; never repair silently."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_dates(data: pd.DataFrame) -> None:
    dates = data["Date"]
    if (
        data.empty
        or not pd.api.types.is_datetime64_dtype(dates)
        or dates.isna().any()
        or dates.duplicated().any()
        or not dates.is_monotonic_increasing
        or (dates != dates.dt.normalize()).any()
    ):
        raise EDAError("Require nonempty, unique, sorted, timezone-free daily dates.")


def load_canonical(path: Path, manifest_path: Path) -> tuple[pd.DataFrame, str]:
    """Verify saved bytes against the manifest before reading observations."""
    manifest = pd.read_csv(manifest_path)
    required = {"file_name", "rows", "columns", "first_date", "last_date", "sha256"}
    if not required.issubset(manifest.columns):
        raise EDAError("Phase 1.5 manifest has an invalid schema.")
    records = manifest.loc[manifest["file_name"] == path.name]
    if len(records) != 1 or records[list(required)].isna().any().any():
        raise EDAError("Require one complete canonical record in Phase 1.5 manifest.")
    record = records.iloc[0]
    digest = sha256(path)
    if digest != record["sha256"]:
        raise EDAError(
            f"Canonical SHA-256 mismatch: {digest}; expected {record['sha256']}."
        )
    data = pd.read_csv(path, float_precision="round_trip")
    if data.columns.tolist() != CANONICAL_COLUMNS:
        raise EDAError("Canonical ordered schema differs from Phase 1.5.")
    data["Date"] = pd.to_datetime(data["Date"], format="%Y-%m-%d", errors="raise")
    validate_dates(data)
    measured = {
        "rows": len(data),
        "columns": len(data.columns),
        "first_date": data.Date.iloc[0].strftime("%Y-%m-%d"),
        "last_date": data.Date.iloc[-1].strftime("%Y-%m-%d"),
    }
    if any(measured[key] != record[key] for key in measured):
        raise EDAError("Canonical metadata differs from Phase 1.5 manifest.")
    values = data[CANONICAL_COLUMNS[1:]]
    if not all(pd.api.types.is_numeric_dtype(values[c]) for c in values):
        raise EDAError("Canonical market values must be numeric.")
    if not np.isfinite(values.to_numpy()).all():
        raise EDAError("Missing or nonfinite canonical values.")
    for ticker in TICKERS:
        if (data[f"{ticker}_Adj_Close"] <= 0).any():
            raise EDAError(f"{ticker}: adjusted prices must be positive.")
        if (data[f"{ticker}_Volume"] <= 0).any():
            raise EDAError(
                f"{ticker}: zero/negative volume needs review before ratios."
            )
    return data, digest


def log_price(price: pd.Series) -> pd.Series:
    if (price.dropna() <= 0).any():
        raise EDAError("Logarithms require positive prices.")
    return np.log(price)


def log_return(price: pd.Series) -> pd.Series:
    return 100 * log_price(price).diff()


def percentage_change(values: pd.Series) -> pd.Series:
    """No implicit filling; a zero previous value has an undefined ratio."""
    previous = values.shift(1).replace(0, np.nan)
    return 100 * (values / previous - 1)


def rolling_volatility(returns_pct: pd.Series, window: int = 20) -> pd.Series:
    """Sample std, full trailing window, sqrt(252), annualized percent."""
    return (
        (returns_pct / 100).rolling(window, min_periods=window).std(ddof=1)
        * np.sqrt(252)
        * 100
    )


def financial_features(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy(deep=True)
    for ticker in TICKERS:
        price = data[f"{ticker}_Adj_Close"]
        result[f"{ticker}_Log_Price"] = log_price(price)
        result[f"{ticker}_Log_Return"] = log_return(price)
        result[f"{ticker}_Return_Pct"] = percentage_change(price)
        result[f"{ticker}_Volume_Change_Pct"] = percentage_change(
            data[f"{ticker}_Volume"]
        )
        result[f"{ticker}_Rolling_Vol_20D"] = rolling_volatility(
            result[f"{ticker}_Log_Return"]
        )
    return result


def chronological_split(
    data: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    validate_dates(data)
    size = int(np.floor(0.90 * len(data)))
    if size == 0 or size == len(data):
        raise EDAError("Split requires nonempty train and test partitions.")
    train, test = data.iloc[:size].copy(), data.iloc[size:].copy()
    metadata = pd.DataFrame(
        [
            {
                "total_rows": len(data),
                "train_rows": len(train),
                "test_rows": len(test),
                "train_ratio": len(train) / len(data),
                "test_ratio": len(test) / len(data),
                "train_start": train.Date.iloc[0],
                "train_end": train.Date.iloc[-1],
                "test_start": test.Date.iloc[0],
                "test_end": test.Date.iloc[-1],
                "split_method": "chronological_90_10_holdout",
            }
        ]
    )
    return train, test, metadata


def descriptive_stats(train: pd.DataFrame, full: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope, data in [("train", train), ("full_descriptive", full)]:
        for ticker, series in itertools.product(TICKERS, ["Adj_Close", "Log_Return"]):
            s = data[f"{ticker}_{series}"].dropna()
            rows.append(
                {
                    "ticker": ticker,
                    "series": series,
                    "scope": scope,
                    "count": len(s),
                    "mean": s.mean(),
                    "median": s.median(),
                    "variance": s.var(ddof=1),
                    "standard_deviation": s.std(ddof=1),
                    "minimum": s.min(),
                    "Q1": s.quantile(0.25),
                    "Q3": s.quantile(0.75),
                    "maximum": s.max(),
                    "skewness": s.skew(),
                    "kurtosis": s.kurt(),
                }
            )
    return pd.DataFrame(rows, columns=STAT_COLUMNS)


def iqr_outliers(returns: pd.Series, ticker: str) -> tuple[dict, pd.Series]:
    valid = returns.dropna()
    q1, q3 = valid.quantile([0.25, 0.75])
    spread = q3 - q1
    lower, upper = q1 - 1.5 * spread, q3 + 1.5 * spread
    mask = (returns < lower) | (returns > upper)
    return {
        "ticker": ticker,
        "scope": "train",
        "Q1": q1,
        "Q3": q3,
        "IQR": spread,
        "lower_bound": lower,
        "upper_bound": upper,
        "outlier_count": int(mask.sum()),
        "outlier_pct": 100 * mask.sum() / len(valid),
    }, mask


def rolling_correlations(returns: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    return pd.DataFrame(
        {
            f"{a}/{b}": returns[a].rolling(window, min_periods=window).corr(returns[b])
            for a, b in itertools.combinations(returns.columns, 2)
        }
    )


def rolling_summary(rolling: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "pair": pair,
                "scope": "train",
                "mean": s.mean(),
                "median": s.median(),
                "min": s.min(),
                "max": s.max(),
                "std": s.std(ddof=1),
            }
            for pair, s in rolling.items()
        ]
    )


def weekday_returns(train: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ticker in TICKERS:
        for day, group in train.groupby(train.Date.dt.dayofweek):
            s = group[f"{ticker}_Log_Return"].dropna()
            rows.append(
                {
                    "ticker": ticker,
                    "scope": "train",
                    "weekday_number": day,
                    "weekday": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][
                        day
                    ],
                    "mean": s.mean(),
                    "median": s.median(),
                    "std": s.std(ddof=1),
                    "count": len(s),
                }
            )
    return pd.DataFrame(rows)


def diagnostic_series(series: pd.Series) -> pd.Series:
    clean = series.dropna()
    if (
        len(clean) < 30
        or not np.isfinite(clean.to_numpy()).all()
        or clean.nunique() < 2
    ):
        raise EDAError(
            "Stationarity tests require >=30 finite, nonconstant observations."
        )
    return clean


def adf_test(
    series: pd.Series, ticker: str, transformation: str, regression: str
) -> dict:
    clean = diagnostic_series(series)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        statistic, p, lag, nobs, critical, _ = adfuller(
            clean, regression=regression, autolag="AIC"
        )
    return {
        "ticker": ticker,
        "series": transformation,
        "transformation": transformation,
        "test": "ADF",
        "scope": "train",
        "test_statistic": statistic,
        "p_value": p,
        "used_lag": lag,
        "lags": lag,
        "nobs": nobs,
        **{f"critical_{k}pct": critical[f"{k}%"] for k in [1, 5, 10]},
        "critical_values": json.dumps(critical),
        "regression": regression,
        "decision_5pct": "reject_H0" if p < 0.05 else "fail_to_reject_H0",
        "p_value_bound": "none",
        "warnings": " | ".join(str(w.message) for w in caught),
    }


def kpss_test(
    series: pd.Series, ticker: str, transformation: str, regression: str
) -> dict:
    clean = diagnostic_series(series)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        statistic, p, lag, critical = kpss(clean, regression=regression, nlags="auto")
    messages = " | ".join(str(w.message) for w in caught)
    bound = "none"
    if "smaller" in messages:
        bound = "actual_p_smaller_than_reported"
    elif "greater" in messages:
        bound = "actual_p_greater_than_reported"
    return {
        "ticker": ticker,
        "series": transformation,
        "transformation": transformation,
        "test": "KPSS",
        "scope": "train",
        "test_statistic": statistic,
        "p_value": p,
        "used_lag": lag,
        "lags": lag,
        "nobs": len(clean),
        **{f"critical_{k}pct": critical[f"{k}%"] for k in [1, 5, 10]},
        "critical_values": json.dumps(critical),
        "regression": regression,
        "decision_5pct": "reject_stationarity"
        if p < 0.05
        else "fail_to_reject_stationarity",
        "p_value_bound": bound,
        "warnings": messages,
    }


def stationarity_tables(train: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, summary = [], []
    for ticker, transformation in itertools.product(
        TICKERS, ["Adj_Close", "Log_Price", "Log_Return"]
    ):
        regression = "c" if transformation == "Log_Return" else "ct"
        s = train[f"{ticker}_{transformation}"]
        adf = adf_test(s, ticker, transformation, regression)
        kp = kpss_test(s, ticker, transformation, regression)
        rows.extend([adf, kp])
        if (
            adf["decision_5pct"] == "reject_H0"
            and kp["decision_5pct"] == "fail_to_reject_stationarity"
        ):
            conclusion = "stationary_supported"
        elif (
            adf["decision_5pct"] == "fail_to_reject_H0"
            and kp["decision_5pct"] == "reject_stationarity"
        ):
            conclusion = "nonstationary_supported"
        else:
            conclusion = "mixed_evidence"
        summary.append(
            {
                "ticker": ticker,
                "series": transformation,
                "scope": "train",
                "ADF_decision": adf["decision_5pct"],
                "KPSS_decision": kp["decision_5pct"],
                "mechanical_summary": conclusion,
            }
        )
    return pd.DataFrame(rows, columns=TEST_COLUMNS), pd.DataFrame(summary)


def build_tables(train: pd.DataFrame, full: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Only descriptive statistics receive full data; all diagnostics receive train."""
    returns = train[[f"{t}_Log_Return" for t in TICKERS]].set_axis(TICKERS, axis=1)
    outliers, extremes = [], []
    for ticker in TICKERS:
        s = train[f"{ticker}_Log_Return"]
        row, mask = iqr_outliers(s, ticker)
        outliers.append(row)
        for rank, index in enumerate(s.abs().nlargest(10).index, 1):
            extremes.append(
                {
                    "ticker": ticker,
                    "scope": "train",
                    "rank_abs": rank,
                    "Date": train.loc[index, "Date"],
                    "log_return_pct": s.loc[index],
                    "absolute_log_return_pct": abs(s.loc[index]),
                    "iqr_outlier": bool(mask.loc[index]),
                }
            )
    tests, summary = stationarity_tables(train)
    return {
        "phase2_descriptive_stats": descriptive_stats(train, full),
        "phase2_return_correlation_train": returns.corr()
        .rename_axis("ticker")
        .reset_index(),
        "phase2_rolling_correlation_summary": rolling_summary(
            rolling_correlations(returns)
        ),
        "phase2_weekday_returns": weekday_returns(train),
        "phase2_outlier_summary": pd.DataFrame(outliers),
        "phase2_extreme_returns": pd.DataFrame(extremes),
        "phase2_stationarity_tests": tests,
        "phase2_stationarity_summary": summary,
    }


def leakage_checks(
    canonical: pd.DataFrame, full: pd.DataFrame, train: pd.DataFrame, test: pd.DataFrame
) -> pd.DataFrame:
    """Measured assertions plus explicitly labeled code-scope audit entries."""
    recomputed = financial_features(canonical.iloc[: len(train)])
    suffix_start = max(1, len(train) // 2)
    perturbed = canonical.copy(deep=True)
    perturbed.loc[perturbed.index[suffix_start:], CANONICAL_COLUMNS[1:]] *= 2
    perturbed_features = financial_features(perturbed)
    checks = [
        (
            "chronological_split",
            train.Date.max() < test.Date.min(),
            "max(train.Date) < min(test.Date)",
        ),
        (
            "no_date_overlap",
            not train.Date.isin(test.Date).any(),
            "Disjoint observed dates",
        ),
        (
            "canonical_row_split",
            len(train) == int(np.floor(0.9 * len(canonical))),
            "floor(0.90*N) before any NA exclusion",
        ),
        (
            "all_rows_and_original_values_preserved",
            full[CANONICAL_COLUMNS].equals(canonical),
            "Original 19 columns preserved exactly; no global drop",
        ),
        (
            "training_features_independent_of_holdout",
            train.equals(recomputed),
            "Train features equal recomputation on canonical train alone",
        ),
        (
            "no_future_features",
            full.iloc[:suffix_start].equals(perturbed_features.iloc[:suffix_start]),
            "Changing later observations leaves every earlier feature unchanged",
        ),
        (
            "backward_rolling_windows",
            train.equals(recomputed),
            "Uncentered rolling(20/60), min_periods=window; shift(1)/diff() only",
        ),
        (
            "adf_kpss_train_only",
            True,
            "Code audit: stationarity_tables(train); full/test never passed to test functions",
        ),
        (
            "acf_pacf_train_only",
            True,
            "Code audit: generate_figures ACF/PACF loops read train only",
        ),
        (
            "stl_train_only",
            True,
            "Code audit: STL(train log-price, period=5, robust=True)",
        ),
        (
            "iqr_thresholds_train_only",
            True,
            "Code audit: build_tables fits IQR bounds from train log-returns only",
        ),
        (
            "no_full_data_fitted_normalization",
            True,
            "Code audit: no scaler; descriptive Base 100 uses first observed price only",
        ),
    ]
    result = pd.DataFrame(
        [
            {"check": name, "status": "PASS" if bool(ok) else "FAIL", "details": detail}
            for name, ok, detail in checks
        ]
    )
    if (result.status != "PASS").any():
        raise EDAError(
            "Anti-leakage validation failed: "
            + ", ".join(result.loc[result.status == "FAIL", "check"])
        )
    return result


def save_csv(data: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(
        path, index=False, encoding="utf-8", date_format="%Y-%m-%d", lineterminator="\n"
    )


def date_axis(ax) -> None:
    locator = mdates.AutoDateLocator(minticks=5, maxticks=9)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.set_xlabel("Trading date")


def mark_holdout(ax, start, end) -> None:
    ax.axvline(start, color="#555555", linestyle="--", linewidth=1)
    ax.axvspan(start, end, color="#777777", alpha=0.12)
    ax.text(
        0.02,
        0.96,
        "Training period",
        transform=ax.transAxes,
        va="top",
        fontsize=9,
        bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none"},
    )
    ax.text(
        0.98,
        0.96,
        "Final holdout test period",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none"},
    )


def generate_figures(
    full: pd.DataFrame,
    train: pd.DataFrame,
    test: pd.DataFrame,
    tables: dict,
    directory: Path,
) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.18,
            "figure.facecolor": "white",
        }
    )
    paths = []

    def save(fig, name):
        fig.tight_layout()
        path = directory / f"{name}.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        paths.append(path)

    for suffix, title, unit, name in [
        ("Adj_Close", "Adjusted Close", "Adjusted USD / share", "adjusted_close"),
        ("Volume", "Trading volumes", "Million shares / session", "trading_volumes"),
        ("Log_Return", "Daily log-returns", "Daily log-return (%)", "log_returns"),
        (
            "Squared",
            "Squared daily log-returns",
            "Squared log-return (%²)",
            "squared_log_returns",
        ),
        (
            "Rolling_Vol_20D",
            "Trailing 20-session historical volatility",
            "Annualized volatility (%)",
            "rolling_volatility_20d",
        ),
    ]:
        fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
        for ax, ticker in zip(axes, TICKERS, strict=True):
            s = (
                full[f"{ticker}_Log_Return"] ** 2
                if suffix == "Squared"
                else full[f"{ticker}_{suffix}"]
            )
            if suffix == "Volume":
                s = s / 1e6
            ax.plot(full.Date, s, color=COLORS[ticker], linewidth=0.7, label=ticker)
            ax.set_ylabel(unit)
            ax.legend(loc="upper left", bbox_to_anchor=(0.01, 0.85), frameon=False)
            mark_holdout(ax, test.Date.iloc[0], full.Date.iloc[-1])
        date_axis(axes[-1])
        fig.suptitle(f"{title} — full-period descriptive visualization", y=1.01)
        save(fig, name)

    fig, ax = plt.subplots(figsize=(12, 5))
    for ticker in TICKERS:
        price = full[f"{ticker}_Adj_Close"]
        ax.plot(
            full.Date, 100 * price / price.iloc[0], label=ticker, color=COLORS[ticker]
        )
    ax.set(
        title="Normalized adjusted-price performance — full descriptive period",
        ylabel="Index (first observation = 100)",
    )
    ax.legend(loc="upper left", bbox_to_anchor=(0.01, 0.85))
    mark_holdout(ax, test.Date.iloc[0], full.Date.iloc[-1])
    date_axis(ax)
    save(fig, "normalized_prices_base100")

    returns = train[[f"{t}_Log_Return" for t in TICKERS]].set_axis(TICKERS, axis=1)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, ticker in zip(axes, TICKERS, strict=True):
        ax.hist(returns[ticker].dropna(), bins=50, color=COLORS[ticker], alpha=0.8)
        ax.set(title=ticker, xlabel="Daily log-return (%)", ylabel="Count")
    fig.suptitle("Log-return distributions — TRAIN only", y=1.02)
    save(fig, "return_histograms_train")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.boxplot([returns[t].dropna() for t in TICKERS], tick_labels=TICKERS)
    ax.set(
        title="Log-return boxplots — TRAIN only; extremes retained",
        ylabel="Daily log-return (%)",
        xlabel="Asset",
    )
    save(fig, "return_boxplots_train")

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, ticker in zip(axes, TICKERS, strict=True):
        stats.probplot(returns[ticker].dropna(), dist="norm", plot=ax)
        ax.get_lines()[0].set(color=COLORS[ticker], markersize=3, alpha=0.65)
        ax.get_lines()[1].set(color="#555555", linewidth=1.2)
        ax.set(
            title=ticker,
            xlabel="Theoretical normal quantile",
            ylabel="Ordered log-return (%)",
        )
    fig.suptitle("Normal QQ-plots — TRAIN only", y=1.02)
    save(fig, "return_qqplots_train")

    corr = returns.corr()
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(corr, cmap="BrBG", vmin=-1, vmax=1)
    ax.grid(False)
    ax.set_xticks(range(3), TICKERS)
    ax.set_yticks(range(3), TICKERS)
    ax.set(
        title="Pearson log-return correlation — TRAIN only",
        xlabel="Asset",
        ylabel="Asset",
    )
    for i, j in itertools.product(range(3), repeat=2):
        ax.text(
            j,
            i,
            f"{corr.iloc[i, j]:.3f}",
            ha="center",
            va="center",
            color="white" if corr.iloc[i, j] > 0.7 else "black",
        )
    fig.colorbar(im, ax=ax, label="Pearson correlation")
    save(fig, "return_correlation_train")

    fig, ax = plt.subplots(figsize=(12, 5))
    for pair, s in rolling_correlations(returns).items():
        ax.plot(train.Date, s, label=pair, linewidth=1)
    ax.set(
        title="Trailing 60-session log-return correlations — TRAIN only",
        ylabel="Pearson correlation",
        ylim=(-1, 1),
    )
    ax.legend(loc="lower left", ncol=3)
    date_axis(ax)
    save(fig, "rolling_correlations_60d")

    fig, ax = plt.subplots(figsize=(10, 5))
    weekday = tables["phase2_weekday_returns"]
    for offset, ticker in enumerate(TICKERS):
        sub = weekday.loc[weekday.ticker == ticker].sort_values("weekday_number")
        ax.bar(
            sub.weekday_number + (offset - 1) * 0.24,
            sub["mean"],
            width=0.24,
            label=ticker,
            color=COLORS[ticker],
        )
    ax.axhline(0, color="#555555", linewidth=0.7)
    ax.set_xticks(range(5), ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
    ax.set(
        title="Mean log-return by weekday — TRAIN exploratory description",
        ylabel="Mean daily log-return (%)",
        xlabel="Weekday",
    )
    ax.legend()
    save(fig, "weekday_returns_train")

    for ticker in TICKERS:
        for suffix, label, unit in [
            ("Adj_Close", "Adjusted Close", "USD / share"),
            ("Log_Return", "Log-return", "%"),
        ]:
            s = train[f"{ticker}_{suffix}"].dropna()
            lags = min(40, len(s) // 2 - 1)
            fig, axes = plt.subplots(1, 2, figsize=(12, 4))
            plot_acf(
                s,
                lags=lags,
                ax=axes[0],
                zero=False,
                title=f"ACF — {ticker} {label} ({unit})",
            )
            plot_pacf(
                s,
                lags=lags,
                ax=axes[1],
                zero=False,
                method="ywm",
                title=f"PACF — {ticker} {label} ({unit})",
            )
            for ax in axes:
                ax.set(xlabel="Lag (trading sessions)", ylabel="Correlation")
            fig.suptitle(
                "TRAIN only — pointwise 95% intervals; no order selected", y=1.02
            )
            save(fig, f"{ticker.lower()}_{suffix.lower()}_acf_pacf_train")
        fig, ax = plt.subplots(figsize=(9, 4))
        plot_acf(
            train[f"{ticker}_Log_Return"].dropna() ** 2, lags=40, zero=False, ax=ax
        )
        ax.set(
            title=f"{ticker} squared log-return ACF — TRAIN only",
            xlabel="Lag (trading sessions)",
            ylabel="Correlation",
        )
        save(fig, f"{ticker.lower()}_squared_returns_acf_train")
        s = train.set_index("Date")[f"{ticker}_Log_Price"]
        decomposition = STL(s, period=5, robust=True).fit()
        fig, axes = plt.subplots(4, 1, figsize=(12, 8), sharex=True)
        for ax, label, values in zip(
            axes,
            ["Observed", "Trend", "Seasonal", "Residual"],
            [s, decomposition.trend, decomposition.seasonal, decomposition.resid],
            strict=True,
        ):
            ax.plot(s.index, values, color=COLORS[ticker], linewidth=0.8)
            ax.set_ylabel(f"{label}\n(log USD)")
        date_axis(axes[-1])
        fig.suptitle(
            f"{ticker} log-price STL — TRAIN; period=5, robust=True\nExploratory trading-week hypothesis; no seasonality proof",
            y=1.02,
        )
        save(fig, f"{ticker.lower()}_log_price_stl_train")
    return paths


def markdown_table(data: pd.DataFrame) -> str:
    """Small factual tables without an optional tabulate dependency."""

    def render(value):
        if isinstance(value, (float, np.floating)):
            return f"{value:.6g}"
        if isinstance(value, pd.Timestamp):
            return value.strftime("%Y-%m-%d")
        return str(value).replace("|", "/").replace("\n", " ")

    lines = [
        "| " + " | ".join(data.columns) + " |",
        "| " + " | ".join(["---"] * len(data.columns)) + " |",
    ]
    lines.extend(
        "| " + " | ".join(map(render, row)) + " |"
        for row in data.itertuples(index=False, name=None)
    )
    return "\n".join(lines)


def warning_notes(tests: pd.DataFrame) -> str:
    """Display each warning once with its count; per-diagnostic CSV keeps full text."""
    counts = {}
    for value in tests.warnings:
        for message in value.split(" | "):
            if message:
                clean = " ".join(message.split())
                counts[clean] = counts.get(clean, 0) + 1
    return (
        "\n\n".join(
            f"- {count} diagnostic(s): {message}" for message, count in counts.items()
        )
        or "None."
    )


def write_report(
    tables: dict, full: pd.DataFrame, digest: str, figures: list[Path]
) -> None:
    """Factual reproducible report; never write the team's human interpretation."""
    desc = tables["phase2_descriptive_stats"]
    tests = tables["phase2_stationarity_tests"]
    sections = [
        (
            "Objective",
            "Create financial transformations, freeze a chronological final holdout and produce exploratory diagnostics. No forecasting model is estimated. This document records calculations; the team's human interpretation remains pending in `llm/human_analysis/phase2_interpretation.md`.",
        ),
        (
            "Input dataset",
            f"`data/processed/market_aligned.csv`: {len(full)} observations and {len(CANONICAL_COLUMNS)} original columns. SHA-256 verified against Phase 1.5 **before analysis**: `{digest}`. Original values and row order are preserved; the feature dataset has {len(full.columns)} columns.\n\n"
            + markdown_table(tables["phase2_feature_manifest"]),
        ),
        (
            "Chronological split",
            "Split computed first from canonical dates: `floor(0.90*N)` train, remaining rows test. No structural NA is removed before splitting. The first test return uses the last training price, a legitimate past observation. Holdout values are used only in explicitly descriptive full-period charts/statistics.\n\n"
            + markdown_table(tables["phase2_split_metadata"]),
        ),
        (
            "Financial transformations",
            "For each asset, P is Adjusted Close and V is volume. `Log_Price = ln(P_t)`; `Log_Return = 100*(ln(P_t)-ln(P_{t-1}))`; `Return_Pct = 100*(P_t/P_{t-1}-1)`; `Volume_Change_Pct = 100*(V_t/V_{t-1}-1)`. `Rolling_Vol_20D = 100*sqrt(252)*sample_std(Log_Return/100 over sessions t-19..t)` with ddof=1 and 20 valid observations. Windows include the current observation and use no future value. Log-return, percentage return and volume change each have one initial NA; volatility has 20 initial NAs because the first return is undefined. No imputation or global deletion occurs. Historical volatility is descriptive, not automatically a forecasting feature.\n\n"
            + markdown_table(
                pd.DataFrame(
                    [
                        {
                            "ticker": t,
                            **{d: int(full[f"{t}_{d}"].isna().sum()) for d in DERIVED},
                        }
                        for t in TICKERS
                    ]
                )
            ),
        ),
        (
            "Price dynamics",
            "Adjusted-price and Base 100 figures cover the full descriptive period and mark the final holdout. Base 100 uses only the first observed price, not fitted normalization. Trading volumes are shown in millions of shares. Model conclusions must use TRAIN diagnostics.",
        ),
        (
            "Return dynamics",
            "Daily log-return and squared-return plots are descriptive full-period charts with the test boundary. Squared returns visualize variance concentration only. Histograms, boxplots, normal QQ-plots and historical volatility are saved; distribution diagnostics use TRAIN. No normality or ARCH test is performed.",
        ),
        (
            "Descriptive statistics",
            "Sample variance/std use ddof=1. Skewness is pandas' unbiased sample skewness; kurtosis is unbiased **excess** kurtosis (normal reference 0). Full-period rows are labeled `full_descriptive` in the CSV and must not guide model selection. Counts exclude only each series' own NA.\n\n"
            + markdown_table(desc.loc[desc.scope == "train"]),
        ),
        (
            "Correlation structure",
            "Pearson correlations of contemporaneous TRAIN log-returns; correlation does not establish causality.\n\n"
            + markdown_table(tables["phase2_return_correlation_train"]),
        ),
        (
            "Rolling correlations",
            "TRAIN only; trailing 60 observed trading-session windows, minimum 60 valid paired returns, no centered windows. Summary std uses ddof=1. Descriptive analysis only; no DCC-GARCH.\n\n"
            + markdown_table(tables["phase2_rolling_correlation_summary"]),
        ),
        (
            "Weekday exploration",
            "TRAIN log-returns grouped by actual calendar weekday. Mean/median/std/count are descriptive; no inferential evidence of a weekly effect is claimed. Missing holiday sessions make period=5 different from literal weekday alignment.\n\n"
            + markdown_table(tables["phase2_weekday_returns"]),
        ),
        (
            "Extreme observations",
            "IQR bounds fitted only on TRAIN: Q1−1.5*(Q3−Q1), Q3+1.5*(Q3−Q1). Percentages divide by valid TRAIN returns. All observations retained; no winsorization or automatic correction. Top ten absolute TRAIN returns per asset are exported separately.\n\n"
            + markdown_table(tables["phase2_outlier_summary"])
            + "\n\n"
            + markdown_table(tables["phase2_extreme_returns"]),
        ),
        (
            "ACF/PACF",
            "TRAIN only: Adjusted Close and Log Return, 40 lags; PACF uses `ywm`. Squared-return ACF also uses 40 lags. Pointwise 95% intervals are not simultaneous significance bands. No p/q selection and no ARCH-LM. Log-returns represent the first difference of log-price, not the raw dollar-price difference.",
        ),
        (
            "STL decomposition",
            "TRAIN log-price, `period=5`, `robust=True`. Five trading sessions are an exploratory weekly-cycle hypothesis, not evidence of exploitable seasonality. STL smoothers are two-sided within TRAIN; components are diagnostics, never causal forecasting features. No SARIMA decision follows.",
        ),
        (
            "ADF",
            "H0: a unit root. Pre-specified constant+linear trend (`ct`) for prices/log-prices and constant (`c`) for returns. Trend accommodates possible deterministic trends without test observations or selecting terms from p-values. `autolag='AIC'`; p<0.05 mechanically rejects H0.\n\n"
            + markdown_table(
                tests.loc[
                    tests.test == "ADF",
                    [
                        "ticker",
                        "series",
                        "test_statistic",
                        "p_value",
                        "used_lag",
                        "nobs",
                        "regression",
                        "decision_5pct",
                    ],
                ]
            ),
        ),
        (
            "KPSS",
            "H0: stationarity around the specified constant/trend. Deterministic terms match ADF; `nlags='auto'`. p<0.05 mechanically rejects stationarity. Boundary p-values are censored, not exact: warnings are captured in the CSV and displayed during execution.\n\n"
            + markdown_table(
                tests.loc[
                    tests.test == "KPSS",
                    [
                        "ticker",
                        "series",
                        "test_statistic",
                        "p_value",
                        "lags",
                        "regression",
                        "decision_5pct",
                        "p_value_bound",
                    ],
                ]
            )
            + "\n\nCaptured warnings:\n\n"
            + warning_notes(tests),
        ),
        (
            "Mechanical stationarity summary",
            "`stationary_supported`: ADF rejects and KPSS does not reject stationarity. `nonstationary_supported`: ADF does not reject and KPSS rejects stationarity. Otherwise `mixed_evidence`. Non-rejection is not proof. No automatic ARIMA/VAR/VECM choice.\n\n"
            + markdown_table(tables["phase2_stationarity_summary"]),
        ),
        (
            "Limitations",
            "Vendor revisions, nonuniform trading calendars, structural breaks and finite test power can affect diagnostics. Trend specification matters. Multiple pointwise diagnostics lack multiplicity correction. Weekday differences and STL cycles are not established effects. Extremes are retained. The final holdout remains reserved for later evaluation. Future scalers, lag choices and neural-network windows must be designed using TRAIN, with rolling validation inside TRAIN where appropriate.\n\nAnti-leakage checks combine measured assertions and labeled code-scope audits:\n\n"
            + markdown_table(tables["phase2_leakage_check"])
            + "\n\nRuntime versions:\n\n"
            + markdown_table(tables["phase2_runtime_versions"]),
        ),
        (
            "Phase boundary",
            f"{len(figures)} final PNG figures and {len(tables)} CSV tables produced. Feature/train/test datasets remain local and ignored by Git. No ARIMA, SARIMA, VAR, Granger, Johansen, VECM, ARCH, GARCH, LSTM, GRU, forecasting or Diebold–Mariano computation. Stop for review before Phase 3. The team must complete the human template before requesting LLM interpretation.\n\nReproduce in the project environment:\n\n```bash\npython python/01_data_eda.py\npython -m ruff check python/01_data_eda.py tests/test_eda_stationarity.py\npython -m pytest\n```\n\nFigure inventory:\n\n"
            + "\n".join(
                f"- [`{p.name}`](../outputs/figures/phase2/{p.name})" for p in figures
            ),
        ),
    ]
    content = "# Phase 2 — EDA, Financial Transformations and Stationarity\n\n"
    content += (
        "\n\n".join(f"## {heading}\n\n{body}" for heading, body in sections) + "\n"
    )
    (ROOT / "docs/phase2_eda_stationarity.md").write_text(content, encoding="utf-8")


def main() -> int:
    try:
        canonical, digest = load_canonical(
            ROOT / "data/processed/market_aligned.csv",
            ROOT / "outputs/tables/phase1_5_processed_manifest.csv",
        )
        # Freeze canonical row/date boundary BEFORE transformations/diagnostics.
        _, _, split = chronological_split(canonical)
        full = financial_features(canonical)
        size = int(split.train_rows.iloc[0])
        train, test = full.iloc[:size].copy(), full.iloc[size:].copy()
        tables = build_tables(train, full)
        tables["phase2_split_metadata"] = split
        tables["phase2_leakage_check"] = leakage_checks(canonical, full, train, test)
        versions = {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "matplotlib": matplotlib.__version__,
            "scipy": scipy.__version__,
            "statsmodels": statsmodels.__version__,
        }
        tables["phase2_runtime_versions"] = pd.DataFrame(
            versions.items(), columns=["package", "version"]
        )
        processed = ROOT / "data/processed"
        feature_path = processed / "market_features.csv"
        for data, name in [
            (full, "market_features"),
            (train, "market_train"),
            (test, "market_test"),
        ]:
            path = processed / f"{name}.csv"
            save_csv(data, path)
            saved = pd.read_csv(
                path, float_precision="round_trip", parse_dates=["Date"]
            )
            pd.testing.assert_frame_equal(
                data.reset_index(drop=True), saved, check_exact=True
            )
        tables["phase2_feature_manifest"] = pd.DataFrame(
            [
                {
                    "file_name": feature_path.name,
                    "rows": len(full),
                    "columns": len(full.columns),
                    "first_date": full.Date.iloc[0],
                    "last_date": full.Date.iloc[-1],
                    "sha256": sha256(feature_path),
                    "derived_variable_count": len(TICKERS) * len(DERIVED),
                    "source_sha256": digest,
                    "train_sha256": sha256(processed / "market_train.csv"),
                    "test_sha256": sha256(processed / "market_test.csv"),
                    "notes": "Canonical values retained; structural NA preserved; trailing windows; no model fit",
                }
            ]
        )
        if sha256(ROOT / "data/processed/market_aligned.csv") != digest:
            raise EDAError("Canonical input changed during execution.")
        figures = generate_figures(
            full, train, test, tables, ROOT / "outputs/figures/phase2"
        )
        for name, data in tables.items():
            save_csv(data, ROOT / "outputs/tables" / f"{name}.csv")
        write_report(tables, full, digest, figures)
        print("PHASE 2 completed; no model estimated. Canonical SHA-256:", digest)
        for name in [
            "phase2_split_metadata",
            "phase2_descriptive_stats",
            "phase2_outlier_summary",
            "phase2_return_correlation_train",
            "phase2_rolling_correlation_summary",
            "phase2_stationarity_tests",
            "phase2_stationarity_summary",
            "phase2_leakage_check",
        ]:
            display = tables[name].drop(columns="warnings", errors="ignore")
            print(f"\n{name}\n{display.to_string(index=False)}", flush=True)
        print(
            "\nCaptured warnings (full text per diagnostic in CSV):\n"
            + warning_notes(tables["phase2_stationarity_tests"])
        )
        print(f"\nFigures: {len(figures)}; tables: {len(tables)}")
        return 0
    except (EDAError, OSError, ValueError, AssertionError) as exc:
        print(f"Phase 2 stopped: {exc}", file=sys.stderr, flush=True)
        print(
            "Existing outputs may belong to an earlier run; verify manifests.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
