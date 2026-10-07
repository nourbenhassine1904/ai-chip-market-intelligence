"""Offline Phase 4 tests: synthetic observations and generated metadata only."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from statsmodels.tsa.api import VAR

SCRIPT = Path(__file__).resolve().parents[1] / "python/03_var_vecm.py"
SPEC = importlib.util.spec_from_file_location("var_vecm", SCRIPT)
phase4 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(phase4)


@pytest.fixture
def synthetic():
    rng = np.random.default_rng(281)
    n = 350
    dates = pd.bdate_range("2020-01-02", periods=n)
    frame = pd.DataFrame({"Date": dates.strftime("%Y-%m-%d")})
    for a in phase4.ASSETS:
        levels = 3 + np.cumsum(rng.normal(0.001, 0.02, n))
        frame[f"{a}_Adj_Close"] = np.exp(levels)
        frame[f"{a}_Log_Price"] = levels
        frame[f"{a}_Log_Return"] = np.r_[np.nan, 100 * np.diff(levels)]
    protocol = SimpleNamespace(
        expected_rows=n,
        first_date=frame.Date.iloc[0],
        last_date=frame.Date.iloc[-1],
        max_var_lag=10,
        serial_gate_1=20,
        serial_gate_2=30,
        bic_tie_units=2,
        johansen_level_lags=3,
        johansen_sensitivity_lags="2;4",
        alpha=0.05,
    )
    return frame, protocol


def test_chronology_and_expected_variables(synthetic):
    frame, protocol = synthetic
    dates = phase4.validate_frame(frame, protocol)
    assert dates.is_monotonic_increasing and not dates.duplicated().any()
    assert phase4.RETURNS == [f"{a}_Log_Return" for a in phase4.ASSETS]
    assert phase4.LEVELS == [f"{a}_Log_Price" for a in phase4.ASSETS]


@pytest.mark.parametrize(
    "fault",
    ["order", "duplicate", "missing_column", "return_na", "zero_price", "wrong_return"],
)
def test_rejects_invalid_inputs(synthetic, fault):
    frame, protocol = synthetic
    if fault == "order":
        frame = frame.iloc[::-1]
    elif fault == "duplicate":
        frame.loc[5, "Date"] = frame.loc[4, "Date"]
    elif fault == "missing_column":
        frame = frame.drop(columns=[phase4.LEVELS[0]])
    elif fault == "return_na":
        frame.loc[10, phase4.RETURNS[0]] = np.nan
    elif fault == "zero_price":
        frame.loc[10, "NVDA_Adj_Close"] = 0
    else:
        frame.loc[10, phase4.RETURNS[0]] += 1
    with pytest.raises(ValueError):
        phase4.validate_frame(frame, protocol)


def test_returns_are_backward_only_and_future_perturbation(synthetic):
    frame, protocol = synthetic
    changed = frame.copy()
    for a in phase4.ASSETS:
        level = changed[f"{a}_Log_Price"].to_numpy(copy=True)
        level[200:] += 0.5
        changed[f"{a}_Log_Price"] = level
        changed[f"{a}_Adj_Close"] = np.exp(level)
        changed[f"{a}_Log_Return"] = np.r_[np.nan, 100 * np.diff(level)]
    phase4.validate_frame(changed, protocol)
    np.testing.assert_array_equal(
        frame[phase4.RETURNS].iloc[:200], changed[phase4.RETURNS].iloc[:200]
    )
    for a in phase4.ASSETS:
        np.testing.assert_allclose(
            frame[f"{a}_Log_Return"].iloc[1:], 100 * np.diff(frame[f"{a}_Log_Price"])
        )


@pytest.mark.parametrize(
    "path",
    [
        "data/processed/market_test.csv",
        "data/processed/market_aligned.csv",
        "../market_train.csv",
    ],
)
def test_holdout_access_forbidden_before_open(tmp_path, monkeypatch, path):
    def forbidden(*args, **kwargs):
        pytest.fail("Filesystem read attempted for unauthorized input")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    with pytest.raises(ValueError, match="Unauthorized"):
        phase4.read_observations(tmp_path, path, [])


def test_stability_companion_conventions():
    stable = np.array([[[0.8, 0.0], [0.0, -0.3]]])
    explosive = np.array([[[1.01, 0.0], [0.0, 0.3]]])
    assert phase4.is_stable(stable)
    assert not phase4.is_stable(explosive)
    assert not phase4.is_stable(np.array([[[1.0]]]))
    # AR(2) companion polynomial lambda^2-.5*lambda-.2=0.
    roots = phase4.companion_eigenvalues(np.array([[[0.5]], [[0.2]]]))
    np.testing.assert_allclose(np.sort(roots), np.sort(np.roots([1, -0.5, -0.2])))
    with pytest.raises(ValueError):
        phase4.companion_eigenvalues(np.array([[[np.nan]]]))


def test_lag_selection_bounded_and_reproducible(synthetic):
    frame, protocol = synthetic
    returns = frame[phase4.RETURNS].iloc[1:].to_numpy()
    first, fit = phase4.lag_selection(returns, protocol)
    second, repeated = phase4.lag_selection(returns, protocol)
    pd.testing.assert_frame_equal(first, second)
    np.testing.assert_array_equal(fit.params, repeated.params)
    assert first.lag.tolist() == list(range(1, 11))
    assert first.ic_nobs.nunique() == 1
    assert first.ic_nobs.iloc[0] == len(returns) - 10
    assert first.selected.sum() == 1 and 1 <= fit.k_ar <= 10
    assert (first.estimation_nobs == len(returns) - first.lag).all()


def test_selection_requires_diagnostics_before_ic_and_parsimony():
    table = pd.DataFrame(
        {
            "lag": [1, 2, 3, 4],
            "estimable": [True] * 4,
            "stable": [True, False, True, True],
            "serial_adequate": [False, True, True, True],
            "bic": [0.0, 1.0, 2.001, 2.0],
            "hqic": [0.0] * 4,
            "aic": [0.0] * 4,
            "ic_nobs": [1000] * 4,
        }
    )
    protocol = SimpleNamespace(bic_tie_units=2)
    assert phase4.choose_lag(table, protocol) == 3
    table["serial_adequate"] = False
    assert phase4.choose_lag(table, protocol) == 1  # flagged provisional fallback
    table["stable"] = False
    with pytest.raises(ValueError, match="No estimable stable"):
        phase4.choose_lag(table, protocol)


def test_six_conditional_granger_tests_match_equation_wald(synthetic):
    frame, _ = synthetic
    fit = VAR(frame[phase4.RETURNS].iloc[1:].to_numpy()).fit(2)
    table = phase4.granger_table(fit)
    assert len(table) == 6 and not table[["cause", "effect"]].duplicated().any()
    assert (table.cause != table.effect).all() and table.df.eq(2).all()
    assert {
        "cause",
        "effect",
        "test_statistic",
        "df",
        "p_value",
        "decision_5pct",
    }.issubset(table.columns)
    # AMD -> NVDA: retain all system regressors, restrict AMD's two lag coefficients.
    indices = [2, 5]
    b = fit.params[indices, 0]
    covariance = (
        np.linalg.inv(fit.endog_lagged.T @ fit.endog_lagged)[np.ix_(indices, indices)]
        * fit.sigma_u[0, 0]
    )
    expected = b @ np.linalg.solve(covariance, b)
    actual = table.loc[(table.cause == "AMD") & (table.effect == "NVDA")].iloc[0]
    assert actual.test_statistic == pytest.approx(expected)
    assert (table.p_value_holm >= table.p_value).all()


def test_johansen_uses_log_levels_and_correct_lag_convention(synthetic, monkeypatch):
    frame, protocol = synthetic
    original = phase4.coint_johansen
    calls = []

    def spy(values, det_order, k_ar_diff):
        np.testing.assert_array_equal(values, frame[phase4.LEVELS].to_numpy())
        calls.append((det_order, k_ar_diff))
        return original(values, det_order, k_ar_diff)

    monkeypatch.setattr(phase4, "coint_johansen", spy)
    table = phase4.johansen_table(frame[phase4.LEVELS].to_numpy(), protocol)
    assert calls == [(0, 2), (0, 1), (0, 3)]
    assert table.null_rank_at_most.tolist() == [0, 1, 2] * 3
    assert (table.effective_nobs == len(frame) - table.level_lags).all()
    assert table.input_variables.eq(";".join(phase4.LEVELS)).all()


def test_rank_is_sequential_not_count_of_rejections():
    assert phase4.sequential_rank([5, 20, 10], [10, 15, 5]) == 0
    assert phase4.sequential_rank([11, 14, 10], [10, 15, 5]) == 1
    assert phase4.sequential_rank([11, 16, 6], [10, 15, 5]) == 3


@pytest.mark.parametrize("rank", [0, 3, -1, 4, None])
def test_vecm_invalid_rank_never_constructed(synthetic, monkeypatch, rank):
    frame, protocol = synthetic

    def forbidden(*args, **kwargs):
        pytest.fail("VECM constructor invoked for invalid rank")

    monkeypatch.setattr(phase4, "VECM", forbidden)
    with pytest.raises(ValueError, match="rank 1 or 2"):
        phase4.fit_vecm(frame[phase4.LEVELS].to_numpy(), rank, protocol)


def test_vecm_shared_gate_and_positive_configuration(synthetic, monkeypatch):
    frame, protocol = synthetic
    assert phase4.shared_vecm_decision(0, 0) == (
        0,
        False,
        "no cointegration supported; VECM not justified",
    )
    assert phase4.shared_vecm_decision(1, 0)[1] is False
    assert phase4.shared_vecm_decision(3, 3)[1] is False
    assert phase4.shared_vecm_decision(1, 1)[1] is True
    with pytest.raises(ValueError, match="between zero and three"):
        phase4.shared_vecm_decision(-1, -1)
    with pytest.raises(ValueError, match="between zero and three"):
        phase4.shared_vecm_decision(4, 4)
    seen = {}

    class FakeVECM:
        def __init__(self, values, **kwargs):
            seen.update(kwargs)
            np.testing.assert_array_equal(values, frame[phase4.LEVELS].to_numpy())

        def fit(self):
            return "fitted"

    monkeypatch.setattr(phase4, "VECM", FakeVECM)
    assert phase4.fit_vecm(frame[phase4.LEVELS].to_numpy(), 1, protocol) == "fitted"
    assert seen == {"k_ar_diff": 2, "coint_rank": 1, "deterministic": "co"}


def test_r_python_provenance_and_actual_output_contract():
    # Generated tables, never market observations; detects stale/misaligned metadata.
    root = SCRIPT.parents[1]
    protocol = pd.read_csv(root / phase4.PROTOCOL).iloc[0]
    r = phase4.language_table("train_manifest", "r", protocol)
    p = phase4.language_table("train_manifest", "python", protocol)
    for field in [
        "rows",
        "return_rows",
        "first_date",
        "last_date",
        "train_md5",
        "protocol_md5",
        "variables",
    ]:
        assert r[field].iloc[0] == p[field].iloc[0]
    assert not r.holdout_read.any() and not p.holdout_read.any()
    for language in ["r", "python"]:
        table = phase4.language_table("granger_causality", language, protocol)
        assert len(table) == 6
        assert table.language.eq("R" if language == "r" else "Python").all()
    guard = pd.read_csv(root / "outputs/tables/phase4_holdout_guard.csv")
    assert guard.status.eq("PASS").all()
    decision = pd.read_csv(root / "outputs/tables/phase4_vecm_decision.csv").iloc[0]
    if not decision.vecm_justified:
        for name in ["alpha", "beta", "diagnostics"]:
            assert not list((root / "outputs/tables").glob(f"phase4_vecm_{name}*.csv"))


def test_metadata_reader_rejects_stale_protocol(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "python").mkdir()
    (tmp_path / "outputs/tables").mkdir(parents=True)
    (tmp_path / phase4.PROTOCOL).write_text("fixed\n", encoding="utf8")
    (tmp_path / "python/03_var_vecm.py").write_text("script\n", encoding="utf8")
    pd.DataFrame(
        [
            {
                "language": "Python",
                "scope": phase4.SCOPE,
                "train_md5": "train",
                "protocol_md5": "stale",
                "implementation_md5": "stale",
            }
        ]
    ).to_csv(tmp_path / "outputs/tables/phase4_train_manifest_python.csv", index=False)
    with pytest.raises(ValueError, match="Stale or mismatched"):
        phase4.language_table(
            "train_manifest", "python", SimpleNamespace(train_md5="train"), tmp_path
        )
