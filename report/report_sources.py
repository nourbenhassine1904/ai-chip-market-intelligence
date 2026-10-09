"""Read archived evidence for Phase 9B; never estimate or write scientific outputs."""

import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LLM_RESPONSE = "llm/responses/phase8_official_llm_response.md"
LLM_RESPONSE_SHA256 = "eecb0de3e0dd8e152e93db70ff71f9dad87024b7b2f3e1bee1ede05225f6f3b4"


def llm_section_b():
    """Exact original UTF-8 section, including its heading and final newline."""
    data = (ROOT / LLM_RESPONSE).read_bytes()
    if hashlib.sha256(data).hexdigest() != LLM_RESPONSE_SHA256:
        raise ValueError("Official LLM response checksum changed")
    start = data.index(b"B. VULGARISATION\n")
    end = data.index(b"C. SIMULATED INVESTMENT INTERPRETATION\n", start)
    return data[start:end].decode("utf8")


def read_csv(name):
    path = name if "/" in name else f"outputs/tables/{name}.csv"
    with (ROOT / path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def fr(value, digits=3):
    return f"{float(value):.{digits}f}".replace(".", ",")


def significant(value):
    return f"{float(value):.6g}".replace(".", ",")


def markdown_table(headers, rows):
    return "\n".join(
        ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
        + ["| " + " | ".join(map(str, row)) + " |" for row in rows]
    )


def tables():
    """Display only sourced cells; derived counts are explicit in traceability."""
    result = {}
    split = read_csv("phase2_split_metadata")[0]
    canonical = read_csv("phase1_5_processed_manifest")[0]
    result["data"] = (
        ["Ensemble", "Séances", "Début", "Fin"],
        [["Canonique", canonical["rows"], canonical["first_date"], canonical["last_date"]],
         ["TRAIN", split["train_rows"], split["train_start"], split["train_end"]],
         ["TEST", split["test_rows"], split["test_start"], split["test_end"]]],
        ["outputs/tables/phase1_5_processed_manifest.csv", "outputs/tables/phase2_split_metadata.csv"],
    )
    descriptive = [r for r in read_csv("phase2_descriptive_stats")
                   if r["scope"] == "train" and r["series"] == "Log_Return"]
    result["descriptive"] = (
        ["Actif", "n", "Moyenne %", "Écart-type %", "Kurtosis exc."],
        [[r["ticker"], r["count"], fr(r["mean"]), fr(r["standard_deviation"]), fr(r["kurtosis"])]
         for r in descriptive], ["outputs/tables/phase2_descriptive_stats.csv"],
    )
    summary = read_csv("phase2_stationarity_summary")
    result["stationarity"] = (
        ["Série", "Actifs", "ADF", "KPSS", "Lecture conjointe"],
        [[series, "NVDA, AMD, SOXX", "Non rejet" if series != "Log_Return" else "Rejet",
          "Rejet" if series != "Log_Return" else "Non rejet",
          "Non-stationnarité soutenue" if series != "Log_Return" else "Stationnarité soutenue"]
         for series in ["Adj_Close", "Log_Price", "Log_Return"]],
        ["outputs/tables/phase2_stationarity_summary.csv"],
    )
    for r in summary:
        expected = "stationary_supported" if r["series"] == "Log_Return" else "nonstationary_supported"
        if r["mechanical_summary"] != expected:
            raise ValueError("The report's categorical stationarity summary no longer matches evidence")
    granger = read_csv("phase4_granger_causality_comparison")
    if not all(r["decision_agrees"] == "True" for r in granger):
        raise ValueError("Cross-language Granger disagreement")
    result["granger"] = (
        ["Prédicteur → cible", "p brute", "p Holm", "À 5 % après Holm"],
        [[r["cause"] + " → " + r["effect"], fr(r["p_value_r"], 6),
          fr(r["p_value_holm_r"], 6), "Soutenu" if r["reject_holm_5pct_r"] == "True" else "Non soutenu"]
         for r in granger], ["outputs/tables/phase4_granger_causality_comparison.csv"],
    )
    garch = read_csv("phase5_garch_model_comparison")
    persistence = read_csv("phase5_garch_persistence")
    for r in garch:
        match = next(p for p in persistence if (p["language"], p["model"]) == (r["language"], r["model"]))
        if match["persistence"] != r["persistence"] or match["half_life_sessions"] != r["half_life_sessions"]:
            raise ValueError("Persistence sources differ")
    result["garch"] = (
        ["Langue / loi", "ω", "α", "β", "α+β", "Demi-vie"],
        [[r["language"] + " / " + r["distribution"], fr(r["omega"], 4), fr(r["alpha1"], 4),
          fr(r["beta1"], 4), fr(r["persistence"], 4), fr(r["half_life_sessions"], 2)] for r in garch],
        ["outputs/tables/phase5_garch_model_comparison.csv", "outputs/tables/phase5_garch_persistence.csv"],
    )
    metrics = read_csv("phase7_final_metrics")
    order = {name: i for i, name in enumerate(["Naive", "ARIMA(2,1,2)", "VAR(9)", "LSTM C", "GRU C"])}
    metrics.sort(key=lambda r: (int(r["horizon"]), order[r["model"]]))
    result["final_metrics"] = (
        ["Modèle", "h", "MSE USD²", "RMSE USD", "MAE USD", "MAPE %"],
        [[r["model"], r["horizon"], *[fr(r[c]) for c in ["MSE", "RMSE", "MAE", "MAPE"]]] for r in metrics],
        ["outputs/tables/phase7_final_metrics.csv"],
    )
    dm = [r for r in read_csv("phase7_diebold_mariano") if r["model_b"] == "Naive"]
    result["dm"] = (
        ["A contre Naive", "h", "p brute", "p Holm", "Conclusion"],
        [[r["model_a"], r["horizon"], significant(r["p_value"]),
          significant(r["p_value_holm_if_applicable"]),
          "Naive" if r["decision_5pct"] == "reject_equal_accuracy" else "Non rejet"] for r in dm],
        ["outputs/tables/phase7_diebold_mariano.csv"],
    )
    audit = read_csv("llm/human_analysis/phase8_hallucination_audit.csv")
    counts = Counter(r["claim_id"][0] for r in audit)
    supported = Counter(r["claim_id"][0] for r in audit if r["issue_type"] == "supported")
    result["llm"] = (
        ["Section", "Affirmations", "Supported", "Autres catégories détectées"],
        [[key, str(counts[key]), str(supported[key]), str(counts[key] - supported[key])]
         for key in "ABCD"] + [["Total", str(len(audit)), str(sum(supported.values())),
                                  str(len(audit) - sum(supported.values()))]],
        ["llm/human_analysis/phase8_hallucination_audit.csv"],
    )
    costs = read_csv("phase7_model_tradeoffs")
    result["costs"] = (
        ["Modèle", "Fit s", "Prévision s", "Paramètres", "Interprétabilité"],
        [[r["model"], fr(r["training_cost"]), fr(r["prediction_cost"]), r["parameters_if_available"],
          {"high": "Haute", "medium": "Moyenne", "low": "Faible"}[r["interpretability"]]] for r in costs],
        ["outputs/tables/phase7_model_tradeoffs.csv"],
    )
    return result


def traceability():
    records = []

    def add(section, claim, sources, comment):
        records.append({"claim_id": f"9B-{len(records)+1:03d}", "section": section,
                        "claim": claim, "source_file": "; ".join(sources),
                        "verification_status": "VERIFIED_SOURCE", "comment": comment})

    sections = {"data": "2", "descriptive": "3", "stationarity": "3", "granger": "5", "garch": "6",
                "final_metrics": "8", "dm": "8", "llm": "9", "costs": "10"}
    for name, (headers, rows, sources) in tables().items():
        for row in rows:
            add(sections[name], "| " + " | ".join(row) + " |", sources,
                f"Table {name}; columns: {'; '.join(headers)}; exact archived cells/explicit counts, display rounding only.")
    selections = [
        ("2", "Canonical shape", "phase1_5_processed_manifest", {}, ["rows", "columns", "first_date", "last_date"]),
        ("3", "NVDA ADF/KPSS evidence", "phase2_stationarity_tests", {"ticker": "NVDA"},
         ["series", "test", "p_value", "p_value_bound", "regression", "decision_5pct"]),
        ("3", "TRAIN return correlation", "phase2_return_correlation_train", {}, ["ticker", "NVDA", "AMD", "SOXX"]),
        ("3", "Retained outliers", "phase2_outlier_summary", {}, ["ticker", "scope", "outlier_count"]),
        ("4", "ARIMA selected diagnostics R", "phase3_arima_residual_diagnostics_r", {},
         ["model", "test", "lag", "p_value", "statistic"]),
        ("4", "ARIMA selected diagnostics Python", "phase3_arima_residual_diagnostics_python", {},
         ["model", "test", "lag", "p_value", "statistic"]),
        ("4", "Phase 3B Naive lock with diagnostic warning", "phase3b_locked_arima_model", {},
         ["model", "order", "drift", "status", "phase3a_note"]),
        ("4", "Phase 3B forecast coverage", "phase3b_arima_validation_metrics", {"horizon": "5"},
         ["language", "model", "n_forecasts", "failed_fits"]),
        ("5", "VAR and Johansen summary", "phase4_r_python_summary", {},
         ["language", "aic_proposed_lag", "bic_proposed_lag", "selected_lag", "max_companion_modulus",
          "serial_p20", "serial_p30", "johansen_rank", "vecm_justified"]),
        ("5", "Johansen main specification", "phase4_johansen_rank_comparison", {"level_lags": "3"},
         ["null_rank_at_most", "trace_statistic_r", "critical_5pct_r", "critical_5pct_python",
          "selected_rank_r", "selected_rank_python"]),
        ("5", "FEVD NVDA h20", "phase4_var_fevd", {"response": "NVDA", "horizon": "20", "language": "R"},
         ["response", "shock", "horizon", "variance_share_pct", "order"]),
        ("6", "Normal versus Student-t", "phase5_garch_model_comparison", {},
         ["language", "distribution", "AIC", "BIC", "tail_quantile_rmse", "shape_df_if_applicable"]),
        ("6", "ARCH before GARCH", "phase5_arch_lm_pre_garch", {}, ["language", "lag", "p_value"]),
        ("6", "ARCH/LB after GARCH", "phase5_garch_standardized_residual_diagnostics", {},
         ["language", "model", "test", "lag", "p_value", "p_value_holm_variance", "reject_for_gate"]),
        ("6", "h10 daily innovation sigma", "phase5_volatility_forecast_train_end", {"horizon": "10"},
         ["language", "model", "origin_date", "forecast_variance", "forecast_sigma", "locked"]),
        ("7", "LSTM C lock", "phase6_locked_lstm", {},
         ["model", "configuration", "lookback", "units", "dropout", "trainable_parameters", "average_RMSE_ratio", "seed"]),
        ("7", "GRU C lock", "phase6_locked_gru", {},
         ["model", "configuration", "lookback", "units", "dropout", "trainable_parameters", "average_RMSE_ratio", "seed"]),
        ("7", "Internal neural losses", "phase6_validation_metrics_summary", {},
         ["model", "configuration", "horizon", "n_forecasts", "RMSE", "MAE"]),
        ("7", "CPU refits", "phase6_full_train_refits", {},
         ["model", "train_rows", "refit_epochs", "training_seconds", "early_stopping"]),
        ("8", "ARIMA interval width/coverage", "phase7_arima_interval_coverage", {},
         ["horizon", "95pct_coverage", "mean_interval_width", "nominal_coverage"]),
        ("8", "Recommendation eligibility", "phase7_recommendation_checks", {},
         ["model", "average_RMSE_ratio", "average_MAE_ratio", "eligible_challenger", "Holm_DM_improvement_supported"]),
        ("8", "Official final Naive recommendation", "phase7_final_model_recommendation", {},
         ["final_recommended_price_model", "rule", "reason"]),
    ]
    for section, label, name, filters, columns in selections:
        selected = [r for r in read_csv(name) if all(r[k] == v for k, v in filters.items())]
        if not selected:
            raise ValueError(f"Empty trace selection: {name}, {filters}")
        for row in selected:
            values = {c: row[c] for c in columns}
            add(section, label + ": " + json.dumps(values, ensure_ascii=False),
                [f"outputs/tables/{name}.csv"],
                "Exact source strings; filters=" + json.dumps(filters) + "; no scientific recomputation.")
    seconds = sum(float(r["training_seconds"]) for r in read_csv("phase6_training_runs"))
    seconds += sum(float(r["training_seconds"]) for r in read_csv("phase6_full_train_refits"))
    add("7", f"CPU fit total = {fr(seconds)} seconds; {fr(seconds/60, 2)} minutes",
        ["outputs/tables/phase6_training_runs.csv", "outputs/tables/phase6_full_train_refits.csv"],
        "Arithmetic sum of measured archived wall times, no new fit; excludes other pipeline stages.")
    for section, claim, name in [
        ("4", "59 rolling origins; initial 1386, step 10; rule requires complete coverage and >=1% RMSE/MAE gain in both languages/horizons", "docs/phase3b_arima_validation.md"),
        ("5", "VAR(1) fails serial diagnostics; only lags 9/10 pass; rank zero closes VECM; Cholesky order NVDA AMD SOXX", "docs/phase4_var_vecm.md"),
        ("7", "Five features; direct Dense(10); fold TRAIN scalers; inner TRAIN stopping; nine purged windows; config A/B/C", "docs/phase6_lstm_gru.md"),
        ("8", "220 holdout rows; 211 common origins; parameters frozen; h5/h10 observed sessions; no holdout retuning", "docs/phase7_final_evaluation.md"),
        ("9", "AI-assisted team-reviewed baselines, no independent blinded human control; exact generation metadata unavailable", "docs/phase8_llm_analysis.md"),
        ("10", "FAST verified archived outputs; FULL section 8.3 remains PARTIAL, not executed", "docs/phase9a_reproducibility.md"),
        ("10", "Proposed isolated FULL notebook, original snapshots/packages/CPU/clean Phase 7 gate and preserved LLM", "docs/reproduction_guide.md"),
    ]:
        add(section, claim, [name], "Documentary cross-check of protocol/method/limitation; not a numerical test.")
    section_b = llm_section_b()
    add("Annexe E", "Original LLM section B reproduced verbatim; SHA256="
        + hashlib.sha256(section_b.encode("utf8")).hexdigest(), [LLM_RESPONSE],
        "Exact source section, including heading and newline; whole response SHA256=" + LLM_RESPONSE_SHA256
        + "; provided section 5 requirement; no independent review of the official specifications PDF.")
    add("6", "March 2020 volatility episode placed in documented coronavirus/financial-conditions context",
        ["outputs/tables/phase5_conditional_volatility.csv", "outputs/figures/phase5/phase5_conditional_volatility.png"],
        "Descriptive date concordance only, no causal attribution or event-study test. Primary context verified: "
        "Federal Reserve FOMC statement 2020-03-15, "
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20200315a.htm (consulted 2026-10-09).")
    return records


def trace_csv():
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=["claim_id", "section", "claim", "source_file",
                                               "verification_status", "comment"], lineterminator="\n")
    writer.writeheader()
    writer.writerows(traceability())
    return handle.getvalue()
