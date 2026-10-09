"""Read-only provenance checks and summaries of published artifacts (no fitting)."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "docs/phase9a_frozen_artifacts_manifest.json"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen_records(root=ROOT):
    return json.loads((root / MANIFEST).read_text(encoding="utf8"))["artifacts"]


def verify_frozen(root=ROOT, *, portable=False):
    """Local strict bytes; portable also accepts exact committed Git blob bytes."""
    rows = []
    for record in frozen_records(root):
        path = root / record["path"]
        actual = digest(path) if path.is_file() else "MISSING"
        accepted = {record["sha256"]}
        if portable:
            accepted.add(record["git_blob_sha256"])
        rows.append({"path": record["path"], "status": "PASS" if actual in accepted
                     else "FAIL", "actual_sha256": actual,
                     "representation": "capture" if actual == record["sha256"]
                     else "git_blob" if actual == record["git_blob_sha256"] else "divergent"})
    return pd.DataFrame(rows)


def published(relative, root=ROOT):
    """Require an explicitly manifested source before reading any CSV/text/image."""
    records = {r["path"]: r for r in frozen_records(root)}
    if relative not in records:
        raise ValueError(f"Source is not in the frozen manifest: {relative}")
    path = root / relative
    if digest(path) not in {records[relative]["sha256"],
                            records[relative]["git_blob_sha256"]}:
        raise ValueError(f"Frozen source checksum mismatch: {relative}")
    return path


def table(name, root=ROOT):
    return pd.read_csv(published(f"outputs/tables/{name}.csv", root),
                       float_precision="round_trip")


def metric_replay(root=ROOT):
    """Arithmetic verification of frozen predictions, never new holdout forecasts."""
    predictions = table("phase7_final_predictions", root)
    metrics = table("phase7_final_metrics", root)
    protocol = json.loads(published("docs/phase7_final_evaluation_protocol.json", root)
                          .read_text(encoding="utf8"))
    expected_hash = table("phase7_prediction_freeze", root).iloc[0].predictions_sha256
    assert digest(published("outputs/tables/phase7_final_predictions.csv", root)) == expected_hash
    assert set(predictions.model) == set(protocol["models"])
    assert set(predictions.horizon) == set(protocol["horizons"])
    assert not predictions.duplicated(["model", "horizon", "origin_date"]).any()
    assert (predictions.target_index - predictions.origin_index == predictions.horizon).all()
    assert (predictions.max_feature_source_date <= predictions.origin_date).all()
    assert (predictions.origin_date < predictions.target_date).all()
    reference = None
    result = []
    for (model, horizon), group in predictions.groupby(["model", "horizon"]):
        group = group.sort_values("origin_date")
        panel = group[["origin_date", "origin_index"]].reset_index(drop=True)
        assert len(group) == protocol["expected_common_origins"]
        if reference is None:
            reference = panel
        pd.testing.assert_frame_equal(panel, reference)
        same_h = predictions[predictions.horizon == horizon]
        assert same_h.groupby("origin_date").actual_price.nunique().eq(1).all()
        assert same_h.groupby("origin_date").target_date.nunique().eq(1).all()
        actual, forecast = group.actual_price.to_numpy(), group.forecast_price.to_numpy()
        assert np.isfinite(actual).all() and (actual > 0).all()
        assert np.isfinite(forecast).all()
        error = forecast - actual
        np.testing.assert_allclose(error, group.error, rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(error**2, group.squared_error, rtol=1e-12, atol=1e-12)
        values = {"MSE": np.mean(error**2), "RMSE": np.sqrt(np.mean(error**2)),
                  "MAE": np.mean(np.abs(error)), "MAPE": 100*np.mean(np.abs(error/actual))}
        original = metrics[(metrics.model == model) & (metrics.horizon == horizon)]
        assert len(original) == 1
        assert original.iloc[0].predictions_sha256 == expected_hash
        assert original.iloc[0].n_forecasts == len(group)
        for name, value in values.items():
            np.testing.assert_allclose(value, original.iloc[0][name], rtol=1e-12, atol=1e-12)
        result.append({"model": model, "horizon": horizon, "n_forecasts": len(group),
                       **values, "source": "phase7_final_predictions.csv", "status": "PASS"})
    return pd.DataFrame(result)


def verify_local_data(root=ROOT, historical_root=None):
    """Hash optional data against historical manifests; missing is explicit, no writes."""
    source = historical_root or root
    raw = table("phase1_raw_manifest", source)
    canonical = table("phase1_5_processed_manifest", source).iloc[0]
    features = table("phase2_feature_manifest", source).iloc[0]
    expected = [(f"data/raw/{r.file_name}", r.sha256) for r in raw.itertuples()]
    expected += [("data/processed/market_aligned.csv", canonical.sha256),
                 ("data/processed/market_features.csv", features.sha256),
                 ("data/processed/market_train.csv", features.train_sha256),
                 ("data/processed/market_test.csv", features.test_sha256)]
    rows = []
    for relative, sha in expected:
        path = root / relative
        actual = digest(path) if path.exists() else "MISSING"
        rows.append({"path": relative, "expected_sha256": sha, "actual_sha256": actual,
                     "status": "MISSING" if actual == "MISSING" else
                     "PASS" if actual == sha else "DIVERGENT"})
    return pd.DataFrame(rows)


def verify_dataset_structure(root=ROOT):
    """Check schema/chronology/split without estimating anything or reading TEST values."""
    path = root / "data/processed/market_aligned.csv"
    data = pd.read_csv(path, parse_dates=["Date"], float_precision="round_trip")
    expected = ["Date"] + [f"{ticker}_{field}" for ticker in ["NVDA", "AMD", "SOXX"]
                           for field in ["Open", "High", "Low", "Close", "Adj_Close", "Volume"]]
    assert list(data.columns) == expected
    assert data.Date.is_monotonic_increasing and data.Date.is_unique
    assert not data.isna().any().any()
    assert np.isfinite(data.drop(columns="Date").to_numpy()).all()
    assert (data[[f"{t}_Adj_Close" for t in ["NVDA", "AMD", "SOXX"]]] > 0).all().all()
    print(f"Canonical structure PASS: {data.shape}; {data.Date.min().date()} to {data.Date.max().date()}")
    print(f"Chronological split boundary: floor(0.90*N)={int(.9*len(data))}; no shuffle")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", action="store_true", help="Audit optional local data")
    parser.add_argument("--structure", action="store_true", help="Check canonical schema")
    parser.add_argument("--portable", action="store_true",
                        help="Accept exact Git blob bytes as well as captured Windows bytes")
    parser.add_argument("--historical-root", type=Path,
                        help="Original untouched repository when auditing an isolated rerun")
    args = parser.parse_args()
    if args.structure:
        verify_dataset_structure()
        if not args.data:
            return 0
    if args.data:
        result = verify_local_data(historical_root=args.historical_root)
        print(result.to_string(index=False))
        return 1 if result.status.isin(["MISSING", "DIVERGENT"]).any() else 0
    result = verify_frozen(portable=args.portable)
    print(result.groupby(["status", "representation"]).size().to_string())
    return 1 if (result.status != "PASS").any() else 0


if __name__ == "__main__":
    raise SystemExit(main())
