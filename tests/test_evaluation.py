"""Offline Phase 7 tests: synthetic observations and immutable forecast artifacts."""

import ast
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from scipy import stats
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "evaluation", ROOT / "python/06_evaluation.py"
)
phase = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(phase)


@pytest.fixture
def observations():
    rng = np.random.default_rng(7)
    frame = pd.DataFrame(
        {"Date": pd.bdate_range("2018-01-02", periods=2200).strftime("%Y-%m-%d")}
    )
    for asset in ["NVDA", "AMD", "SOXX"]:
        levels = 3 + np.cumsum(rng.normal(0.001, 0.02, len(frame)))
        frame[f"{asset}_Adj_Close"] = np.exp(levels)
        frame[f"{asset}_Log_Price"] = levels
        frame[f"{asset}_Log_Return"] = np.r_[np.nan, np.diff(levels) * 100]
    frame["NVDA_Rolling_Vol_20D"] = frame.NVDA_Log_Return.rolling(20).std() * np.sqrt(
        252
    )
    for i in range(34 - len(frame.columns)):
        frame[f"unused_{i}"] = 1.0
    return frame


def synthetic_protocol(frame, train_rows=1980):
    p = phase.load_protocol()
    p.update(
        train_first_date=frame.Date.iloc[0],
        train_last_date=frame.Date.iloc[train_rows - 1],
        test_first_date=frame.Date.iloc[train_rows],
        test_last_date=frame.Date.iloc[-1],
    )
    return p


def test_protocol_exists_committed_unchanged_and_precedes_result_commit():
    p = phase.load_protocol()
    commits = (
        phase.git(
            "log",
            "--format=%H",
            "--fixed-strings",
            "--grep=" + p["protocol_commit_subject"],
        )
        .decode()
        .splitlines()
    )
    assert commits
    protocol_commit = commits[-1]
    for path in [phase.PROTOCOL, phase.PROTOCOL_MD]:
        assert (ROOT / path).read_bytes() == phase.git(
            "show", f"{protocol_commit}:{path}"
        )
    results = (
        phase.git(
            "log",
            "--format=%H",
            "--fixed-strings",
            "--grep=feat: add final holdout model evaluation",
        )
        .decode()
        .splitlines()
    )
    for result in results:
        phase.git("merge-base", "--is-ancestor", protocol_commit, result)
        assert result != protocol_commit


def test_test_access_requires_protocol_and_train_freeze(tmp_path):
    # Guard must reject before trying to open even a nonexistent test file.
    for gate, ready in [
        (None, False),
        ({"working_tree_clean_verified": True}, False),
        (None, True),
    ]:
        events = []
        with pytest.raises(ValueError, match="TEST forbidden"):
            phase.read_observations(phase.TEST, events, gate, ready, tmp_path)
        assert events == []


def test_expected_holdout_shape_and_boundary(observations):
    p = synthetic_protocol(observations)
    combined = phase.validate_split(
        observations.iloc[:1980], observations.iloc[1980:], p
    )
    assert combined.shape == (2200, 34)
    assert len(combined.iloc[1980:]) == 220


@pytest.mark.parametrize(
    "fault", ["size", "schema", "date", "duplicate", "future_return", "centered_vol"]
)
def test_invalid_split_or_lookahead_stops(observations, fault):
    p = synthetic_protocol(observations)
    train, test = observations.iloc[:1980].copy(), observations.iloc[1980:].copy()
    if fault == "size":
        test = test.iloc[:-1]
    elif fault == "schema":
        test = test.rename(columns={"unused_0": "wrong"})
    elif fault == "date":
        test.iloc[0, 0] = "1900-01-01"
    elif fault == "duplicate":
        test.iloc[1, 0] = test.iloc[0, 0]
    elif fault == "future_return":
        test["NVDA_Log_Return"] = test.NVDA_Log_Return.shift(-1)
    else:
        test["NVDA_Rolling_Vol_20D"] = test.NVDA_Log_Return.rolling(
            20, center=True
        ).std() * np.sqrt(252)
    with pytest.raises(ValueError):
        phase.validate_split(train, test, p)


def test_211_common_origins_h5_h10_alignment(observations):
    grid = phase.origin_grid(observations.Date, 1980)
    assert len(grid) == 211
    assert grid.origin_index.tolist() == list(range(1979, 2190))
    for h in [5, 10]:
        assert (grid[f"target_index_h{h}"] == grid.origin_index + h).all()
        assert (
            grid[f"target_date_h{h}"].tolist()
            == observations.Date.iloc[grid.origin_index + h].tolist()
        )
    assert grid.target_date_h10.iloc[-1] == observations.Date.iloc[-1]
    assert grid.target_date_h5.iloc[-1] == observations.Date.iloc[-6]
    with pytest.raises(ValueError, match="origin"):
        phase.origin_grid(observations.Date.iloc[:-1], 1980)


def test_var_percent_returns_reconstructed_cumulatively():
    returns = np.ones((10, 3))
    returns[:, 1:] = 1000  # Other assets must not enter the reconstruction.
    result = phase.returns_to_log_price(np.log(100), returns)
    np.testing.assert_allclose(np.exp(result), 100 * np.exp(np.arange(1, 11) / 100))
    with pytest.raises(ValueError):
        phase.returns_to_log_price(1, returns[:9])


class FrozenARIMA:
    def __init__(self):
        self.params = np.array([0.1, 0.2])
        self.append_calls = []

    def append(self, values, *, refit):
        assert refit is False
        self.append_calls.append(values)
        return self

    def get_forecast(self, steps):
        mean = np.repeat(3.0, steps)
        return SimpleNamespace(
            predicted_mean=mean, conf_int=lambda alpha: np.c_[mean - 0.5, mean + 0.5]
        )


class FrozenNetwork:
    def __init__(self):
        self.weights = [np.ones((5, 10))]
        self.inputs = []

    def get_weights(self):
        return self.weights

    def __call__(self, x, *, training):
        assert training is False
        self.inputs.append(x.copy())
        return SimpleNamespace(numpy=lambda: np.zeros((1, 10)))


def test_arima_append_without_refit_and_coefficient_check():
    arima = FrozenARIMA()
    before = arima.params.copy()
    phase.frozen_arima_update(arima, 3.2)
    assert arima.append_calls == [[3.2]]
    np.testing.assert_array_equal(before, arima.params)

    class BadARIMA(FrozenARIMA):
        def append(self, values, *, refit):
            self.params += 1
            return self

    with pytest.raises(ValueError, match="coefficients changed"):
        phase.frozen_arima_update(BadARIMA(), 3)


@pytest.fixture
def panel(observations):
    frame = observations.iloc[:91].copy()
    grid = phase.origin_grid(frame.Date, 80, expected=2)
    sx = StandardScaler().fit(frame[phase.FEATURES].iloc[20:80].to_numpy())
    sy = StandardScaler().fit(frame.NVDA_Log_Price.iloc[20:80].to_numpy()[:, None])
    arima = FrozenARIMA()
    var = SimpleNamespace(
        params=np.zeros((28, 3)), forecast=lambda values, steps: np.zeros((steps, 3))
    )
    networks = {"LSTM C": FrozenNetwork(), "GRU C": FrozenNetwork()}
    table, _costs, frozen = phase.generate_forecasts(
        frame, grid, arima, var, networks, sx, sy
    )
    p = phase.load_protocol()
    p.update(first_origin_index=79, expected_common_origins=2)
    return table, p, frame, frozen, arima, networks


def test_panel_same_origins_actuals_naive_correct_and_weights_frozen(panel):
    table, p, frame, frozen, arima, networks = panel
    phase.validate_prediction_panel(table, p)
    assert all(frozen.values())
    assert len(table) == 20
    assert arima.append_calls == [[frame.NVDA_Log_Price.iloc[80]]]
    naive = table.loc[table.model.eq("Naive")]
    np.testing.assert_array_equal(
        naive.forecast_price, frame.NVDA_Adj_Close.iloc[naive.origin_index]
    )
    for h in [5, 10]:
        assert (
            table.loc[table.horizon.eq(h)]
            .groupby("origin_index")
            .actual_price.nunique()
            .eq(1)
            .all()
        )
    for model in networks.values():
        assert len(model.inputs) == 2
        assert model.inputs[0].shape == (1, 60, 5)
        np.testing.assert_array_equal(model.weights[0], np.ones((5, 10)))


@pytest.mark.parametrize(
    "fault", ["origin", "actual", "target", "future", "garch", "missing"]
)
def test_panel_rejects_alignment_and_scope_faults(panel, fault):
    table, p, *_ = panel
    table = table.copy()
    if fault == "origin":
        table.loc[table.horizon.eq(5), "origin_index"] += 1
    elif fault == "actual":
        table.loc[0, "actual_price"] += 1
    elif fault == "target":
        table.loc[0, "target_index"] += 1
    elif fault == "future":
        table.loc[0, "max_feature_source_date"] = "2099-01-01"
    elif fault == "garch":
        table.loc[0, "model"] = "GARCH"
    else:
        table = table.iloc[:-1]
    with pytest.raises(ValueError):
        phase.validate_prediction_panel(table, p)


def test_train_only_scalers_and_future_perturbation(observations):
    m = phase.phase6_module()
    x, y = (
        observations[phase.FEATURES].iloc[20:].to_numpy(),
        observations.NVDA_Log_Price.iloc[20:].to_numpy(),
    )
    sx, sy = m.fit_scalers(x, y, 1960)
    changed_x, changed_y = x.copy(), y.copy()
    changed_x[1960:] += 1e6
    changed_y[1960:] += 1e6
    sx2, sy2 = m.fit_scalers(changed_x, changed_y, 1960)
    np.testing.assert_array_equal(sx.mean_, sx2.mean_)
    np.testing.assert_array_equal(sy.scale_, sy2.scale_)
    assert sx.n_samples_seen_ == sy.n_samples_seen_ == 1960
    future = observations.copy()
    future.loc[2001:, phase.FEATURES] += 1e6
    a, b = FrozenNetwork(), FrozenNetwork()
    before = phase.weights_hash(a)
    fa = phase.neural_forecast(a, phase.observed_prefix(observations, 2000), sx, sy)
    fb = phase.neural_forecast(b, phase.observed_prefix(future, 2000), sx, sy)
    np.testing.assert_array_equal(a.inputs[0], b.inputs[0])
    np.testing.assert_array_equal(fa, fb)
    assert phase.weights_hash(a) == before
    assert (
        phase.observed_prefix(future, 2000).Date.max() == observations.Date.iloc[2000]
    )


def test_metrics_exact_and_garch_excluded(panel):
    table, *_ = panel
    result = phase.final_metrics(table)
    group = table.loc[table.model.eq("Naive") & table.horizon.eq(5)]
    row = result.loc[result.model.eq("Naive") & result.horizon.eq(5)].iloc[0]
    errors = group.forecast_price.to_numpy() - group.actual_price.to_numpy()
    assert row.MSE == pytest.approx(np.mean(errors**2))
    assert row.RMSE == pytest.approx(np.sqrt(np.mean(errors**2)))
    assert row.MAE == pytest.approx(np.mean(np.abs(errors)))
    assert row.MAPE == pytest.approx(100 * np.mean(np.abs(errors) / group.actual_price))
    assert "GARCH" not in result.model.tolist()
    assert result.n_forecasts.eq(2).all()


@pytest.mark.parametrize("h", [5, 10])
def test_dm_zero_difference_and_sign(h):
    a = np.arange(1.0, 212.0)
    zero = phase.diebold_mariano(a, a, h)
    assert zero["dm_statistic"] == 0 and zero["p_value"] == 1
    assert zero["status"] == "degenerate_identical_observed_losses"
    better = phase.diebold_mariano(a, a * 2, h)
    worse = phase.diebold_mariano(a * 2, a, h)
    assert better["dm_statistic"] < 0 < worse["dm_statistic"]
    assert better["p_value"] == pytest.approx(worse["p_value"])
    assert phase.diebold_mariano(a + 1, a, h)["status"].startswith("undefined")


@pytest.mark.parametrize("h", [5, 10])
def test_dm_hac_h_minus_one_and_hln_against_independent_matrix(h):
    rng = np.random.default_rng(42)
    a, b = rng.exponential(4, 211), rng.exponential(7, 211)
    d = a - b
    u = d - d.mean()
    # Independent quadratic-form Bartlett covariance, including both triangles.
    distances = np.abs(np.arange(len(d))[:, None] - np.arange(len(d))[None, :])
    weights = np.maximum(0, 1 - distances / h)
    lrv = u @ weights @ u / len(d)
    hln = np.sqrt((len(d) + 1 - 2 * h + h * (h - 1) / len(d)) / len(d))
    expected = d.mean() / np.sqrt(lrv / len(d)) * hln
    result = phase.diebold_mariano(a, b, h)
    assert result["hac_lag"] == h - 1
    assert result["long_run_variance"] == pytest.approx(lrv)
    assert result["dm_statistic"] == pytest.approx(expected)
    assert result["p_value"] == pytest.approx(2 * stats.t.sf(abs(expected), 210))


def test_holm_four_comparisons_separate_per_horizon():
    rng = np.random.default_rng(7)
    rows = []
    for h in [5, 10]:
        baseline = rng.exponential(20, 211)
        for i, name in enumerate(phase.MODELS):
            losses = (
                baseline if i == 0 else baseline * (1 + i / 100) + rng.normal(0, 1, 211)
            )
            rows.extend(
                {"model": name, "horizon": h, "origin_index": j, "squared_error": loss}
                for j, loss in enumerate(losses)
            )
    dm = phase.dm_table(pd.DataFrame(rows), phase.load_protocol())
    assert len(dm) == 10
    for h in [5, 10]:
        group = dm.loc[dm.horizon.eq(h) & dm.model_b.eq("Naive")]
        assert len(group) == 4
        np.testing.assert_allclose(
            group.p_value_holm_if_applicable,
            multipletests(group.p_value, method="holm")[1],
        )
    assert dm.loc[dm.model_b.eq("LSTM C"), "p_value_holm_if_applicable"].isna().all()


def test_frozen_csv_tampering_rejected_and_overwrite_forbidden(panel, tmp_path):
    table, p, *_ = panel
    (tmp_path / "docs").mkdir()
    (tmp_path / phase.PROTOCOL).write_text(json.dumps(p), encoding="utf8")
    digest = phase.freeze_predictions(table, {}, tmp_path)
    reloaded, actual = phase.load_frozen_predictions(tmp_path)
    assert actual == digest
    pd.testing.assert_frame_equal(reloaded, table, check_dtype=False)
    with pytest.raises(ValueError, match="overwrite"):
        phase.freeze_predictions(table, {}, tmp_path)
    with (tmp_path / phase.PREDICTIONS).open("ab") as file:
        file.write(b"\n")
    with pytest.raises(ValueError, match="SHA256"):
        phase.load_frozen_predictions(tmp_path)


def recommendation_fixture():
    metrics, tests = [], []
    for name in phase.MODELS:
        for h in [5, 10]:
            metrics.append({"model": name, "horizon": h, "RMSE": 10.0, "MAE": 8.0})
            if name != "Naive":
                tests.append(
                    {
                        "model_a": name,
                        "model_b": "Naive",
                        "horizon": h,
                        "mean_loss_diff": -1.0,
                        "p_value_holm_if_applicable": 0.001,
                        "status": "defined",
                    }
                )
    return pd.DataFrame(metrics), pd.DataFrame(tests)


@pytest.mark.parametrize(
    "fault", ["none", "unsupported", "worse_mae", "worse_horizon", "undefined"]
)
def test_recommendation_predeclared_gates(fault):
    metrics, dm = recommendation_fixture()
    chosen = metrics.model.eq("VAR(9)")
    metrics.loc[chosen, "RMSE"] = 9.0
    metrics.loc[chosen, "MAE"] = 7.0
    if fault == "unsupported":
        dm.loc[dm.model_a.eq("VAR(9)"), "p_value_holm_if_applicable"] = 0.2
    elif fault == "worse_mae":
        metrics.loc[chosen & metrics.horizon.eq(5), "MAE"] = 9.0
    elif fault == "worse_horizon":
        metrics.loc[chosen & metrics.horizon.eq(10), "RMSE"] = 11.0
    elif fault == "undefined":
        dm.loc[dm.model_a.eq("VAR(9)") & dm.horizon.eq(10), "status"] = (
            "undefined_nonpositive_long_run_variance"
        )
    result, _ = phase.recommendation(metrics, dm, phase.load_protocol())
    assert result["final_recommended_price_model"] == (
        "VAR(9)" if fault == "none" else "Naive"
    )


def test_recommendation_tie_uses_predeclared_parsimony():
    metrics, dm = recommendation_fixture()
    metrics.loc[metrics.model.ne("Naive"), "RMSE"] = 9.0
    metrics.loc[metrics.model.ne("Naive"), "MAE"] = 7.0
    result, _ = phase.recommendation(metrics, dm, phase.load_protocol())
    assert result["final_recommended_price_model"] == "ARIMA(2,1,2)"


def test_published_manifest_and_frozen_panel_provenance():
    table, digest = phase.load_frozen_predictions()
    manifest = pd.read_csv(ROOT / "outputs/tables/phase7_holdout_manifest.csv").iloc[0]
    p = phase.load_protocol()
    assert len(table) == 2110
    assert manifest.test_rows == 220 and manifest.columns == 34
    assert manifest.test_first_date == "2025-11-17"
    assert manifest.test_last_date == "2026-10-02"
    assert manifest.test_sha256 == p["historical_test_sha256"]
    assert manifest.train_sha256 == p["train_sha256"]
    runtime = json.loads((ROOT / phase.RUNTIME_AUDIT).read_text(encoding="utf8"))
    assert manifest.implementation_sha256 == phase.sha(
        runtime["forecast_implementation_source"].encode("utf8")
    )
    assert table.implementation_sha256.eq(manifest.implementation_sha256).all()
    assert len(digest) == 64
    grid = pd.read_csv(ROOT / "outputs/tables/phase7_evaluation_origins.csv")
    assert len(grid) == 211
    assert grid.origin_date.iloc[0] == "2025-11-14"
    for h in [5, 10]:
        base = table.loc[table.model.eq("Naive") & table.horizon.eq(h)]
        assert base.origin_date.tolist() == grid.origin_date.tolist()
        assert base.target_date.tolist() == grid[f"target_date_h{h}"].tolist()


def test_published_metrics_dm_coverage_reproducible_from_frozen_predictions():
    table, digest = phase.load_frozen_predictions()
    for expected, name in [
        (phase.final_metrics(table), "final_metrics"),
        (phase.dm_table(table, phase.load_protocol()), "diebold_mariano"),
        (phase.interval_coverage(table), "arima_interval_coverage"),
    ]:
        stored = pd.read_csv(
            ROOT / f"outputs/tables/phase7_{name}.csv", float_precision="round_trip"
        )
        pd.testing.assert_frame_equal(
            expected, stored[expected.columns], check_exact=True
        )
        assert stored.predictions_sha256.eq(digest).all()


def test_published_audit_order_cache_and_eight_figures():
    audit = pd.read_csv(ROOT / "outputs/tables/phase7_holdout_evaluation_audit.csv")
    assert len(audit) == 16 and audit.status.eq("PASS").all()
    events = pd.read_csv(ROOT / "outputs/tables/phase7_access_events.csv")
    assert events.event.tolist() == [
        "train_access",
        "models_frozen",
        "test_access",
        "predictions_frozen",
        "metrics_started",
    ]
    times = pd.to_datetime(events.utc)
    assert times.is_monotonic_increasing
    assert times.iloc[2] < times.iloc[3] < times.iloc[4]
    manifest = pd.read_csv(ROOT / "outputs/tables/phase7_holdout_manifest.csv").iloc[0]
    committed = pd.Timestamp(
        phase.git("show", "-s", "--format=%cI", manifest.protocol_commit)
        .decode()
        .strip()
    )
    assert committed < pd.Timestamp(manifest.protocol_gate_verified_utc) < times.iloc[2]
    fits = pd.read_csv(ROOT / "outputs/tables/phase7_model_fit_log.csv")
    neural = fits.loc[fits.model.isin(["LSTM C", "GRU C"])]
    assert (
        neural["mode"]
        .isin(["loaded_from_phase6_cache", "reconstructed_from_locked_specification"])
        .all()
    )
    assert neural.epochs.tolist() == [38, 36]
    assert neural.parameters.tolist() == [18570, 14282]
    assert len(list((ROOT / "outputs/figures/phase7").glob("*.png"))) == 8


def test_summarize_cannot_read_observations_or_fit_models(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Summary must not read observations or fit models")

    for name in [
        "read_observations",
        "fit_classical",
        "prepare_neural",
        "phase6_module",
        "generate_forecasts",
    ]:
        monkeypatch.setattr(phase, name, forbidden)
    original_exists, original_read_text = Path.exists, Path.read_text

    def cache_absent(path):
        return (
            False
            if path == phase.CACHE / "protocol_gate.json"
            else original_exists(path)
        )

    def no_ignored_audit_cache(path, *args, **kwargs):
        if phase.CACHE in path.parents:
            raise AssertionError("Replay must work without the ignored Phase 7 cache")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", cache_absent)
    monkeypatch.setattr(Path, "read_text", no_ignored_audit_cache)
    # Capture derivatives in memory; don't overwrite repository artifacts in tests.
    saved = {}
    monkeypatch.setattr(
        phase,
        "save_table",
        lambda rows, name, *args, **kwargs: saved.update({name: pd.DataFrame(rows)}),
    )
    monkeypatch.setattr(phase, "figures", lambda *args: None)
    phase.summarize()
    assert len(saved["final_metrics"]) == 10
    assert len(saved["diebold_mariano"]) == 10
    assert saved["holdout_evaluation_audit"].status.eq("PASS").all()


def test_original_protocol_gate_replays_without_ignored_cache(tmp_path, monkeypatch):
    runtime = json.loads((ROOT / phase.RUNTIME_AUDIT).read_text(encoding="utf8"))
    for relative in [phase.PROTOCOL, phase.PROTOCOL_MD, phase.RUNTIME_AUDIT]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    original_git = phase.git

    def repository_git(*args, **kwargs):
        assert args[0] != "status", (
            "Replaying an existing gate must not create a new one"
        )
        return original_git(*args)

    monkeypatch.setattr(phase, "git", repository_git)
    gate = phase.verify_protocol_commit(tmp_path)
    assert gate == runtime["protocol_gate"]
    assert not (tmp_path / ".cache/phase7/protocol_gate.json").exists()


def test_forecast_logic_unchanged_by_replay_portability_fix():
    runtime = json.loads((ROOT / phase.RUNTIME_AUDIT).read_text(encoding="utf8"))
    before = ast.parse(runtime["forecast_implementation_source"])
    after = ast.parse((ROOT / "python/06_evaluation.py").read_text(encoding="utf8"))
    names = [
        "validate_features",
        "validate_split",
        "origin_grid",
        "observed_prefix",
        "returns_to_log_price",
        "frozen_arima_update",
        "prepare_neural",
        "fit_classical",
        "neural_forecast",
        "generate_forecasts",
        "validate_prediction_panel",
        "final_metrics",
        "diebold_mariano",
        "dm_table",
        "recommendation",
    ]

    def functions(tree):
        return {
            node.name: ast.dump(node)
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name in names
        }

    assert functions(before) == functions(after)
