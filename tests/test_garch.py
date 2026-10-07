"""Offline Phase 5 tests; synthetic observations and generated metadata only."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "python/04_garch.py"
SPEC = importlib.util.spec_from_file_location("garch_phase", SCRIPT)
garch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(garch)


@pytest.fixture
def synthetic():
    rng = np.random.default_rng(521)
    n = 500
    dates = pd.bdate_range("2020-01-02", periods=n)
    level = 3 + np.cumsum(rng.normal(0.001, 0.02, n))
    frame = pd.DataFrame(
        {
            "Date": dates.strftime("%Y-%m-%d"),
            "NVDA_Adj_Close": np.exp(level),
            "NVDA_Log_Price": level,
            "NVDA_Log_Return": np.r_[np.nan, 100 * np.diff(level)],
        }
    )
    protocol = SimpleNamespace(
        expected_rows=n,
        first_date=frame.Date.iloc[0],
        last_date=frame.Date.iloc[-1],
        mean_strong_failure_p=0.01,
        alpha=0.05,
        arch_required_rejections=2,
        maxiter=2000,
        forecast_horizon=10,
        annualization_sessions=252,
        student_ic_improvement=10.0,
        train_md5="synthetic",
        train_sha256="synthetic",
    )
    return frame, protocol


def test_train_variable_chronology_and_initial_na(synthetic):
    frame, protocol = synthetic
    dates = garch.validate_frame(frame, protocol)
    assert dates.is_monotonic_increasing and dates.is_unique
    assert garch.RETURN == "NVDA_Log_Return"
    assert frame[garch.RETURN].isna().sum() == 1


@pytest.mark.parametrize(
    "fault",
    ["order", "duplicate", "missing_return", "extra_na", "zero_price", "future_return"],
)
def test_invalid_input_rejected(synthetic, fault):
    frame, protocol = synthetic
    if fault == "order":
        frame = frame.iloc[::-1]
    elif fault == "duplicate":
        frame.loc[3, "Date"] = frame.loc[2, "Date"]
    elif fault == "missing_return":
        frame = frame.drop(columns=[garch.RETURN])
    elif fault == "extra_na":
        frame.loc[100, garch.RETURN] = np.nan
    elif fault == "zero_price":
        frame.loc[100, "NVDA_Adj_Close"] = 0
    else:
        frame[garch.RETURN] = frame[garch.RETURN].shift(-1)
    with pytest.raises(ValueError):
        garch.validate_frame(frame, protocol)


@pytest.mark.parametrize(
    "relative",
    [
        "data/processed/market_test.csv",
        "data/processed/market_aligned.csv",
        "../market_train.csv",
    ],
)
def test_holdout_forbidden_before_open(tmp_path, monkeypatch, relative):
    def forbidden(*args, **kwargs):
        pytest.fail("Unauthorized observation file opened")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    with pytest.raises(ValueError, match="Unauthorized"):
        garch.read_observations(tmp_path, relative, [])


def test_backward_returns_future_perturbation(synthetic):
    frame, protocol = synthetic
    changed = frame.copy()
    changed.loc[300:, "NVDA_Log_Price"] += 0.5
    changed["NVDA_Adj_Close"] = np.exp(changed.NVDA_Log_Price)
    changed[garch.RETURN] = np.r_[np.nan, 100 * np.diff(changed.NVDA_Log_Price)]
    garch.validate_frame(changed, protocol)
    np.testing.assert_array_equal(
        frame[garch.RETURN].iloc[:300], changed[garch.RETURN].iloc[:300]
    )


def test_mean_filter_alignment_and_constant_convention(synthetic):
    frame, protocol = synthetic
    returns = frame[garch.RETURN].iloc[1:].to_numpy()
    residuals, row = garch.fit_mean(returns, protocol)
    assert len(residuals) == len(returns) == row["nobs"]
    assert np.isfinite(residuals).all() and row["additional_burn"] == 0
    assert row["recursion_intercept"] == pytest.approx(
        (1 - row["ar1"]) * row["mean_mu"]
    )
    assert residuals[0] == pytest.approx(returns[0] - row["mean_mu"])
    repeated, _ = garch.fit_mean(returns, protocol)
    np.testing.assert_array_equal(residuals, repeated)


def test_arch_lm_matches_auxiliary_regression_and_detects_arch():
    rng = np.random.default_rng(5)
    innovations = np.zeros(2500)
    for i in range(1, len(innovations)):
        innovations[i] = rng.normal() * np.sqrt(0.2 + 0.7 * innovations[i - 1] ** 2)
    innovations = innovations[500:]
    table = garch.arch_tests(innovations)
    assert table.lag.tolist() == [5, 10, 20] and table.p_value.lt(0.01).all()
    square = innovations**2
    h = 5
    design = np.column_stack(
        [np.ones(len(square) - h), *[square[h - j : -j] for j in range(1, h + 1)]]
    )
    target = square[h:]
    fitted = design @ np.linalg.lstsq(design, target, rcond=None)[0]
    expected = len(target) * (
        1 - np.sum((target - fitted) ** 2) / np.sum((target - target.mean()) ** 2)
    )
    assert table.iloc[0].statistic == pytest.approx(expected)


@pytest.mark.parametrize("failure", ["mean", "arch"])
def test_pipeline_stops_before_any_garch_on_failed_prerequisite(
    synthetic, monkeypatch, failure
):
    frame, protocol = synthetic
    dates = pd.to_datetime(frame.Date)
    mean = {"converged": True, "ljung_box_p10": 0.2, "ljung_box_p20": 0.3}
    if failure == "mean":
        mean["ljung_box_p10"] = 0.001
    pre = pd.DataFrame({"p_value": [0.001] * 3 if failure == "mean" else [0.5] * 3})
    monkeypatch.setattr(
        garch, "load_train", lambda: (frame, dates, protocol, [garch.TRAIN])
    )
    monkeypatch.setattr(
        garch, "metadata", lambda *args, **kwargs: {"language": "Python"}
    )
    monkeypatch.setattr(garch, "historical_motivation", lambda *args: None)
    monkeypatch.setattr(garch, "save", lambda *args: None)
    monkeypatch.setattr(
        garch, "fit_mean", lambda *args: (frame[garch.RETURN].iloc[1:].to_numpy(), mean)
    )
    monkeypatch.setattr(garch, "arch_tests", lambda *args: pre)

    def forbidden(*args, **kwargs):
        pytest.fail("GARCH fitted before prerequisite gate passed")

    monkeypatch.setattr(garch, "fit_variance", forbidden)
    with pytest.raises(ValueError, match="STOP before GARCH"):
        garch.run_python()


def test_persistence_long_run_and_half_life():
    persistence, stationary, variance, half_life = garch.persistence_measures(
        0.05, [0.1], [0.85]
    )
    assert stationary and persistence == pytest.approx(0.95)
    assert variance == pytest.approx(1.0)
    assert half_life == pytest.approx(np.log(0.5) / np.log(0.95))
    for alpha, beta in [(0.1, 0.9), (0.2, 0.9), (-0.1, 0.5)]:
        _, stationary, variance, half_life = garch.persistence_measures(
            0.1, [alpha], [beta]
        )
        assert not stationary and np.isnan(variance) and np.isnan(half_life)
    _, stationary, variance, half_life = garch.persistence_measures(
        0.1, [0.1, 0.1], [0.7]
    )
    assert (
        stationary and np.isfinite(variance) and np.isnan(half_life)
    )  # no false AR(1) half-life


def test_standardized_residuals_and_invalid_sigma():
    np.testing.assert_allclose(garch.standardized([2, -6, 0], [2, 3, 4]), [1, -2, 0])
    for sigma in [[1, 0, 1], [1, -1, 1], [1, np.nan, 1], [1, 2]]:
        with pytest.raises(ValueError):
            garch.standardized([2, -6, 0], sigma)


def test_student_quantiles_have_unit_variance_scaling():
    from scipy import stats

    probabilities = np.array([0.01, 0.5, 0.99])
    expected = stats.t.ppf(probabilities, df=6) * np.sqrt(4 / 6)
    np.testing.assert_array_equal(
        garch.theoretical_quantiles(probabilities, "Student-t", 6), expected
    )
    with pytest.raises(ValueError, match="df>2"):
        garch.theoretical_quantiles(probabilities, "Student-t", 2)


def test_post_diagnostics_families_df_and_multiplicity():
    z = np.random.default_rng(4).normal(size=1000)
    table = garch.post_diagnostics(z, "synthetic")
    assert len(table) == 7
    variance = table.diagnostic_family.eq("variance")
    assert variance.sum() == 5
    assert (
        table.loc[variance, "p_value_holm_variance"]
        .ge(table.loc[variance, "p_value"])
        .all()
    )
    assert table.loc[~variance, "p_value_holm_variance"].isna().all()
    lb = table.loc[table.test.eq("Ljung-Box")]
    assert (lb.df == lb.lag - 2).all()


def test_higher_gate_requires_variance_evidence_not_mean_correlation():
    table = pd.DataFrame(
        {
            "test": ["ARCH-LM", "Ljung-Box", "Ljung-Box"],
            "series": ["z", "z_squared", "z"],
            "reject_for_gate": [False, False, True],
        }
    )
    assert garch.higher_order_gate(table)["higher_order_justified"] is False
    table.loc[0, "reject_for_gate"] = True
    assert garch.higher_order_gate(table)["garch11_arch_remaining"] is True
    table.loc[0, "reject_for_gate"] = False
    table.loc[1, "reject_for_gate"] = True
    gate = garch.higher_order_gate(table)
    assert (
        gate["higher_order_justified"] and gate["squared_residual_dependence_remaining"]
    )


def model_fixture():
    rows = []
    for language in ["R", "Python"]:
        for distribution in ["Normal", "Student-t"]:
            student = distribution == "Student-t"
            rows.append(
                {
                    "language": language,
                    "model": garch.model_id(1, 1, distribution),
                    "distribution": distribution,
                    "p": 1,
                    "q": 1,
                    "valid": True,
                    "variance_stationary": True,
                    "diagnostically_adequate": True,
                    "AIC": 800.0 if student else 1000.0,
                    "BIC": 830.0 if student else 1020.0,
                    "tail_quantile_rmse": 0.1 if student else 0.2,
                    "mean_rejections": 0,
                    "variance_rejections": 0,
                }
            )
    return pd.DataFrame(rows)


def test_selection_cannot_use_ic_alone_or_hide_language_disagreement():
    table = model_fixture()
    protocol = SimpleNamespace(student_ic_improvement=10)
    assert garch.choose_baseline(table, protocol)[0] == "GARCH(1,1)_Student-t"
    table.loc[
        table.language.eq("R") & table.distribution.eq("Student-t"),
        "tail_quantile_rmse",
    ] = 0.21
    assert garch.choose_baseline(table, protocol)[0] == "GARCH(1,1)_Normal"
    table["valid"] = False
    table["diagnostically_adequate"] = False
    with pytest.raises(ValueError, match="No converged stationary"):
        garch.choose_baseline(table, protocol)


def test_forecast_exact_horizon_recursion_and_no_future_information():
    eps = np.array([1.0, -2.0, 3.0])
    sigma = np.array([2.0, 2.0, 2.0])
    forecast = garch.forecast_variance_from_history(0.1, [0.1], [0.8], eps, sigma)
    assert len(forecast) == 10
    assert forecast[0] == pytest.approx(0.1 + 0.1 * 9 + 0.8 * 4)
    np.testing.assert_allclose(forecast[1:], 0.1 + 0.9 * forecast[:-1])
    full = np.r_[eps, 1000.0, -1000.0]
    np.testing.assert_array_equal(
        forecast,
        garch.forecast_variance_from_history(0.1, [0.1], [0.8], full[:3], sigma),
    )
    with pytest.raises(ValueError):
        garch.forecast_variance_from_history(0.1, [0.1], [0.8], eps, sigma, horizon=11)


@pytest.mark.parametrize("distribution", ["Normal", "Student-t"])
def test_real_synthetic_garch_forecast_matches_recursion(synthetic, distribution):
    frame, protocol = synthetic
    row, diagnostics, sigma, z, forecast = garch.fit_variance(
        frame[garch.RETURN].iloc[1:].to_numpy(), distribution, protocol
    )
    assert row["converged"] and row["valid"]
    assert len(sigma) == len(z) == len(frame) - 1
    np.testing.assert_allclose(z * sigma, frame[garch.RETURN].iloc[1:])
    assert len(forecast) == 10 and (forecast > 0).all() and len(diagnostics) == 7
    assert row["variance_mean"] == "Zero; no mean re-estimation"


def test_metadata_determinism_and_stale_outputs(tmp_path):
    for folder in ["docs", "python", "outputs/tables"]:
        (tmp_path / folder).mkdir(parents=True)
    (tmp_path / garch.PROTOCOL).write_text("protocol\n", encoding="utf8")
    (tmp_path / garch.RULE).write_text("rule\n", encoding="utf8")
    (tmp_path / "python/04_garch.py").write_text("script\n", encoding="utf8")
    protocol = SimpleNamespace(train_md5="train")
    first = garch.metadata(protocol, root=tmp_path)
    assert first == garch.metadata(protocol, root=tmp_path)
    pd.DataFrame([first]).to_csv(
        tmp_path / "outputs/tables/phase5_train_manifest_python.csv", index=False
    )
    garch.language_table("train_manifest", "python", protocol, tmp_path)
    (tmp_path / garch.RULE).write_text("changed rule\n", encoding="utf8")
    with pytest.raises(ValueError, match="Stale or mismatched"):
        garch.language_table("train_manifest", "python", protocol, tmp_path)


def test_published_r_python_metadata_units_dates_and_closed_gate():
    root = SCRIPT.parents[1]
    protocol = pd.read_csv(root / garch.PROTOCOL).iloc[0]
    tables = [
        garch.language_table("train_manifest", language, protocol)
        for language in ["r", "python"]
    ]
    for field in [
        "rows",
        "return_rows",
        "first_date",
        "last_date",
        "return_first_date",
        "variable",
        "train_md5",
    ]:
        assert tables[0][field].iloc[0] == tables[1][field].iloc[0]
    forecasts = pd.read_csv(
        root / "outputs/tables/phase5_volatility_forecast_train_end.csv"
    )
    for _, group in forecasts.groupby(["language", "model"]):
        assert group.horizon.tolist() == list(range(1, 11))
        assert group.origin_date.eq(protocol.last_date).all()
        np.testing.assert_allclose(group.forecast_sigma**2, group.forecast_variance)
        np.testing.assert_allclose(
            group.annualized_sigma_if_reported, group.forecast_sigma * np.sqrt(252)
        )
    guard = pd.read_csv(root / "outputs/tables/phase5_holdout_guard.csv")
    assert guard.status.eq("PASS").all()
    gate = pd.read_csv(root / "outputs/tables/phase5_higher_order_gate.csv").iloc[0]
    if not gate.higher_order_justified:
        assert not list((root / "outputs/tables").glob("phase5_models_higher_*.csv"))
    volatility = pd.read_csv(root / "outputs/tables/phase5_conditional_volatility.csv")
    for _, group in volatility.groupby("language"):
        assert len(group) == 1980 and group.Date.is_monotonic_increasing
        assert (
            group.iloc[0][["conditional_sigma_normal", "conditional_sigma_student_t"]]
            .isna()
            .all()
        )
        assert (
            group.iloc[1:][["conditional_sigma_normal", "conditional_sigma_student_t"]]
            .gt(0)
            .all()
            .all()
        )
