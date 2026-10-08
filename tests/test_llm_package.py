"""Read-only Phase 8B evidence and audit checks; never run historical analyses."""

import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "llm/prompts"
MANIFEST = json.loads(
    (PROMPTS / "phase8_source_manifest.json").read_text(encoding="utf-8")
)
RESPONSE_COMMIT = "67d60efba09c05ec571cd6907014e08ada9a2cd6"
RESPONSE_SHA256 = "eecb0de3e0dd8e152e93db70ff71f9dad87024b7b2f3e1bee1ede05225f6f3b4"
RESPONSE_PATH = "llm/responses/phase8_official_llm_response.md"
ALLOWED_PHASE8B_CHANGES = {
    "docs/phase8_llm_analysis.md",
    "llm/human_analysis/phase8_human_vs_llm_comparison.md",
    "llm/human_analysis/phase8_hallucination_audit.csv",
    "tests/test_llm_package.py",
}
OUTPUT_HEADINGS = [
    "A. MODEL HYPOTHESES FROM STATISTICAL RESULTS",
    "B. VULGARISATION",
    "C. SIMULATED INVESTMENT INTERPRETATION",
    "D. CRITICAL REVIEW",
]
ISSUE_TYPES = {
    "supported",
    "invented_number",
    "causal_overclaim",
    "pvalue_misinterpretation",
    "oversimplification",
    "unsupported_financial_claim",
    "other",
}
NUMERIC_CHECKS = [
    {
        "line": 6,
        "source": "outputs/tables/phase3_arima_residual_diagnostics_r.csv",
        "where": {"test": "ARCH-LM", "lag": "5"},
        "column": "p_value",
        "format": "g6",
        "latex": True,
    },
    {
        "line": 6,
        "source": "outputs/tables/phase3_arima_residual_diagnostics_r.csv",
        "where": {"test": "ARCH-LM", "lag": "10"},
        "column": "p_value",
        "format": "g6",
        "latex": True,
    },
    {
        "line": 6,
        "source": "outputs/tables/phase3_arima_residual_diagnostics_r.csv",
        "where": {"test": "ARCH-LM", "lag": "20"},
        "column": "p_value",
        "format": "g6",
        "latex": True,
    },
    {
        "line": 7,
        "source": "outputs/tables/phase3b_arima_validation_metrics.csv",
        "where": {"language": "R", "model": "Naive", "horizon": "5"},
        "column": "n_origins",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 8,
        "source": "outputs/tables/phase2_return_correlation_train.csv",
        "where": {"ticker": "NVDA"},
        "column": "SOXX",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 8,
        "source": "outputs/tables/phase4_r_python_summary.csv",
        "where": {"language": "R"},
        "column": "aic_proposed_lag",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 8,
        "source": "outputs/tables/phase4_r_python_summary.csv",
        "where": {"language": "R"},
        "column": "selected_lag",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 8,
        "source": "outputs/tables/phase4_r_python_summary.csv",
        "where": {"language": "R"},
        "column": "max_companion_modulus",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 9,
        "source": "outputs/tables/phase4_granger_causality_comparison.csv",
        "where": {"cause": "SOXX", "effect": "NVDA"},
        "column": "p_value_holm_r",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 9,
        "source": "outputs/tables/phase4_granger_causality_comparison.csv",
        "where": {"cause": "SOXX", "effect": "AMD"},
        "column": "p_value_holm_r",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 11,
        "source": "outputs/tables/phase5_garch_model_comparison.csv",
        "where": {"language": "R", "distribution": "Normal"},
        "column": "persistence",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 11,
        "source": "outputs/tables/phase5_garch_model_comparison.csv",
        "where": {"language": "R", "distribution": "Student-t"},
        "column": "persistence",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 11,
        "source": "outputs/tables/phase5_garch_model_comparison.csv",
        "where": {"language": "Python", "distribution": "Normal"},
        "column": "persistence",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 11,
        "source": "outputs/tables/phase5_garch_model_comparison.csv",
        "where": {"language": "Python", "distribution": "Student-t"},
        "column": "persistence",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 21,
        "source": "outputs/tables/phase5_volatility_forecast_train_end.csv",
        "where": {"language": "R", "model": "GARCH(1,1)_Normal", "horizon": "10"},
        "column": "forecast_sigma",
        "format": "f2",
        "latex": False,
    },
    {
        "line": 21,
        "source": "outputs/tables/phase5_volatility_forecast_train_end.csv",
        "where": {"language": "Python", "model": "GARCH(1,1)_Normal", "horizon": "10"},
        "column": "forecast_sigma",
        "format": "f2",
        "latex": False,
    },
    {
        "line": 21,
        "source": "outputs/tables/phase5_volatility_forecast_train_end.csv",
        "where": {"language": "R", "model": "GARCH(1,1)_Normal", "horizon": "10"},
        "column": "origin_date",
        "format": "date_fr",
        "latex": False,
    },
    {
        "line": 23,
        "source": "outputs/tables/phase7_final_metrics.csv",
        "where": {"model": "Naive", "horizon": "5"},
        "column": "RMSE",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 23,
        "source": "outputs/tables/phase7_final_metrics.csv",
        "where": {"model": "Naive", "horizon": "5"},
        "column": "MAE",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 23,
        "source": "outputs/tables/phase7_final_metrics.csv",
        "where": {"model": "Naive", "horizon": "10"},
        "column": "RMSE",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 23,
        "source": "outputs/tables/phase7_final_metrics.csv",
        "where": {"model": "Naive", "horizon": "10"},
        "column": "MAE",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 24,
        "source": "outputs/tables/phase7_holdout_manifest.csv",
        "where": {},
        "column": "common_origins",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 28,
        "source": "outputs/tables/phase7_final_metrics.csv",
        "where": {"model": "Naive", "horizon": "5"},
        "column": "RMSE",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 28,
        "source": "outputs/tables/phase7_final_metrics.csv",
        "where": {"model": "Naive", "horizon": "10"},
        "column": "RMSE",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 28,
        "source": "outputs/tables/phase7_final_metrics.csv",
        "where": {"model": "ARIMA(2,1,2)", "horizon": "10"},
        "column": "RMSE",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 28,
        "source": "outputs/tables/phase7_diebold_mariano.csv",
        "where": {"model_a": "ARIMA(2,1,2)", "model_b": "Naive", "horizon": "10"},
        "column": "p_value",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 29,
        "source": "outputs/tables/phase5_volatility_forecast_train_end.csv",
        "where": {"language": "R", "model": "GARCH(1,1)_Normal", "horizon": "10"},
        "column": "forecast_sigma",
        "format": "f2",
        "latex": False,
    },
    {
        "line": 29,
        "source": "outputs/tables/phase5_volatility_forecast_train_end.csv",
        "where": {"language": "Python", "model": "GARCH(1,1)_Normal", "horizon": "10"},
        "column": "forecast_sigma",
        "format": "f2",
        "latex": False,
    },
    {
        "line": 34,
        "source": "outputs/tables/phase7_holdout_manifest.csv",
        "where": {},
        "column": "common_origins",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 35,
        "source": "outputs/tables/phase2_return_correlation_train.csv",
        "where": {"ticker": "NVDA"},
        "column": "SOXX",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 35,
        "source": "outputs/tables/phase4_var_fevd.csv",
        "where": {
            "language": "R",
            "response": "NVDA",
            "shock": "SOXX",
            "horizon": "20",
        },
        "column": "variance_share_pct",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 39,
        "source": "outputs/tables/phase7_diebold_mariano.csv",
        "where": {"model_a": "LSTM C", "model_b": "Naive", "horizon": "5"},
        "column": "p_value_holm_if_applicable",
        "format": "g6",
        "latex": True,
    },
    {
        "line": 39,
        "source": "outputs/tables/phase7_diebold_mariano.csv",
        "where": {"model_a": "GRU C", "model_b": "Naive", "horizon": "5"},
        "column": "p_value_holm_if_applicable",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 39,
        "source": "outputs/tables/phase7_diebold_mariano.csv",
        "where": {"model_a": "GRU C", "model_b": "Naive", "horizon": "10"},
        "column": "p_value_holm_if_applicable",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 39,
        "source": "outputs/tables/phase7_diebold_mariano.csv",
        "where": {"model_a": "LSTM C", "model_b": "Naive", "horizon": "10"},
        "column": "p_value_holm_if_applicable",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 39,
        "source": "outputs/tables/phase7_diebold_mariano.csv",
        "where": {"model_a": "GRU C", "model_b": "LSTM C", "horizon": "5"},
        "column": "p_value",
        "format": "g6",
        "latex": True,
    },
    {
        "line": 39,
        "source": "outputs/tables/phase7_diebold_mariano.csv",
        "where": {"model_a": "GRU C", "model_b": "LSTM C", "horizon": "10"},
        "column": "p_value",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 40,
        "source": "outputs/tables/phase7_final_metrics.csv",
        "where": {"model": "Naive", "horizon": "10"},
        "column": "RMSE",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 40,
        "source": "outputs/tables/phase7_final_metrics.csv",
        "where": {"model": "ARIMA(2,1,2)", "horizon": "10"},
        "column": "RMSE",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 43,
        "source": "outputs/tables/phase5_garch_model_comparison.csv",
        "where": {"language": "R", "distribution": "Student-t"},
        "column": "shape_df_if_applicable",
        "format": "f2",
        "latex": False,
    },
    {
        "line": 43,
        "source": "outputs/tables/phase5_garch_model_comparison.csv",
        "where": {"language": "Python", "distribution": "Student-t"},
        "column": "shape_df_if_applicable",
        "format": "f2",
        "latex": False,
    },
    {
        "line": 44,
        "source": "outputs/tables/phase7_arima_interval_coverage.csv",
        "where": {"horizon": "5"},
        "column": "95pct_coverage",
        "format": "percent",
        "latex": False,
    },
    {
        "line": 44,
        "source": "outputs/tables/phase7_arima_interval_coverage.csv",
        "where": {"horizon": "5"},
        "column": "nominal_coverage",
        "format": "percent",
        "latex": False,
    },
    {
        "line": 44,
        "source": "outputs/tables/phase7_arima_interval_coverage.csv",
        "where": {"horizon": "5"},
        "column": "mean_interval_width",
        "format": "g6",
        "latex": False,
    },
    {
        "line": 44,
        "source": "outputs/tables/phase7_arima_interval_coverage.csv",
        "where": {"horizon": "10"},
        "column": "95pct_coverage",
        "format": "percent",
        "latex": False,
    },
    {
        "line": 44,
        "source": "outputs/tables/phase7_arima_interval_coverage.csv",
        "where": {"horizon": "10"},
        "column": "nominal_coverage",
        "format": "percent",
        "latex": False,
    },
    {
        "line": 44,
        "source": "outputs/tables/phase7_arima_interval_coverage.csv",
        "where": {"horizon": "10"},
        "column": "mean_interval_width",
        "format": "g6",
        "latex": False,
    },
]

QUESTIONS = [
    "Where do the baseline interpretation and LLM agree?",
    "Where do they disagree?",
    "Did the LLM invent any statistics?",
    "Did the LLM overstate Granger causality?",
    "Did the LLM misuse non-significant p-values?",
    "Did the LLM oversimplify stationarity or cointegration?",
    "Did the LLM correctly separate price forecasting from volatility forecasting?",
    "Did the LLM understand why Naive was finally recommended?",
    "Was the simulated investment interpretation appropriately cautious?",
    "What useful insight did the LLM add?",
    "What did the team interpret better than the LLM?",
    "Final critical assessment of the LLM",
]
AUDIT_HEADER = [
    "claim_id",
    "llm_claim",
    "supported_by_project",
    "source",
    "issue_type",
    "severity",
    "team_comment",
]


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def display(value):
    if not value:
        return "NA"
    if re.fullmatch(
        r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", value
    ):
        return format(float(value), ".6g")
    return value.replace("|", r"\|").replace("\n", " ")


def source_table(spec):
    # Only existing output summaries are read, never market observations or models.
    assert spec["source"].startswith("outputs/tables/")
    with (ROOT / spec["source"]).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    selected = [r for r in rows if all(r[k] in v for k, v in spec["where"].items())]
    assert len(selected) == spec["expected_rows"]
    columns = spec["columns"]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    lines += [
        "| " + " | ".join(display(row[c]) for c in columns) + " |" for row in selected
    ]
    return (
        "<!-- table: "
        + spec["id"]
        + " -->\nSource: \x60"
        + spec["source"]
        + "\x60.\n\n"
        + "\n".join(lines)
        + "\n<!-- endtable: "
        + spec["id"]
        + " -->"
    )


@pytest.mark.parametrize("spec", MANIFEST["tables"], ids=lambda s: s["id"])
def test_each_numeric_table_matches_existing_csv(spec):
    assert source_table(spec) in read("llm/prompts/phase8_project_facts.md")


def test_prompt_embeds_complete_facts_and_disclaimer():
    prompt = read("llm/prompts/phase8_official_llm_prompt.md")
    facts = read("llm/prompts/phase8_project_facts.md").strip()
    embedded = prompt.split("<!-- BEGIN PROJECT FACTS -->\n", 1)[1].split(
        "\n<!-- END PROJECT FACTS -->", 1
    )[0]
    assert embedded == facts
    assert read("llm/prompts/phase8_investment_disclaimer.md").strip() in prompt
    for phrase in [
        "Do not invent statistics, p-values, confidence intervals, causal claims,\nmodel results or economic explanations not supported by the supplied facts.",
        "If a requested conclusion is not supported by the supplied information,\nstate that it cannot be concluded.",
        "A. MODEL HYPOTHESES FROM STATISTICAL RESULTS",
        "B. VULGARISATION",
        "C. SIMULATED INVESTMENT INTERPRETATION",
        "D. CRITICAL REVIEW",
        "EXACTLY four sections",
        "p > 0.05",
        "team-reviewed baseline interpretations produced during model development",
    ]:
        assert phrase in prompt


def git_output(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def audit_rows():
    with (ROOT / "llm/human_analysis/phase8_hallucination_audit.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == AUDIT_HEADER
        return list(reader)


def test_official_response_is_complete_and_byte_identical():
    actual = (ROOT / RESPONSE_PATH).read_bytes()
    assert hashlib.sha256(actual).hexdigest() == RESPONSE_SHA256
    assert actual == git_output("show", f"{RESPONSE_COMMIT}:{RESPONSE_PATH}")
    assert "Paste the complete, unedited" not in actual.decode("utf-8")
    text = actual.decode("utf-8")
    headings = re.findall(r"^(?:#{1,6} )?([A-Z]\. .+)$", text, re.MULTILINE)
    assert headings == OUTPUT_HEADINGS
    parts = re.split(r"^(?:#{1,6} )?[A-Z]\. .+$", text, flags=re.MULTILINE)
    assert len(parts) == 5
    assert all(len(body.strip()) > 100 for body in parts[1:])


def test_comparison_preserves_twelve_sections_with_analysis():
    text = read("llm/human_analysis/phase8_human_vs_llm_comparison.md")
    headings = re.findall(r"^## (.+)$", text, re.MULTILINE)
    assert headings == [f"{i}. {q}" for i, q in enumerate(QUESTIONS, 1)]
    parts = re.split(r"^## .+$", text, flags=re.MULTILINE)
    assert all(len(part.strip()) > 250 for part in parts[1:])
    assert (
        "team-reviewed baseline interpretations produced during model development"
        in text
    )
    assert "Aucune hallucination numérique" in text


def test_audit_rows_are_valid_quoted_sourced_and_cover_all_sections():
    rows = audit_rows()
    assert 20 <= len(rows) <= 35
    assert len({r["claim_id"] for r in rows}) == len(rows)
    assert {r["claim_id"][0] for r in rows} == set("ABCD")
    response = read(RESPONSE_PATH)
    for row in rows:
        assert all(value is not None and value.strip() for value in row.values())
        assert re.fullmatch(r"[ABCD][0-9]{2}", row["claim_id"])
        claim = row["llm_claim"].replace("\r\n", "\n")
        assert claim in response  # Verbatim apart from platform CSV line endings.
        section = row["claim_id"][0]
        body = response.split(OUTPUT_HEADINGS["ABCD".index(section)], 1)[1]
        if section != "D":
            body = body.split(OUTPUT_HEADINGS["ABCD".index(section) + 1], 1)[0]
        assert claim in body
        assert row["issue_type"] in ISSUE_TYPES
        assert len(row["team_comment"]) > 30
        for reference in row["source"].split("; "):
            relative = reference.split("#", 1)[0]
            assert relative.startswith(("outputs/tables/", "docs/", "llm/"))
            assert ".." not in Path(relative).parts
            assert (ROOT / relative).is_file()
        if row["issue_type"] == "supported":
            assert row["supported_by_project"] == "TRUE"
            assert row["severity"] == "none"
        else:
            assert row["supported_by_project"] in {"FALSE", "partial"}
            assert row["severity"] in {"low", "medium", "high"}
            assert row["source"] and row["team_comment"]


def test_documented_audit_counts_match_csv():
    rows = audit_rows()
    counts = Counter(r["issue_type"] for r in rows)
    for relative in [
        "docs/phase8_llm_analysis.md",
        "llm/human_analysis/phase8_human_vs_llm_comparison.md",
    ]:
        text = read(relative)
        for issue in ISSUE_TYPES:
            assert f"| {issue} | {counts[issue]} |" in text
        assert str(len(rows)) in text


@pytest.mark.parametrize("check", NUMERIC_CHECKS)
def test_reported_numbers_match_contextual_source_cells(check):
    # Presentation/unit checks only: no fit, forecast, statistical test or holdout read.
    with (ROOT / check["source"]).open(encoding="utf-8", newline="") as stream:
        rows = [
            r
            for r in csv.DictReader(stream)
            if all(r[k] == v for k, v in check["where"].items())
        ]
    assert len(rows) == 1
    value = rows[0][check["column"]]
    mode = check["format"]
    if mode == "date_fr":
        rendered = "/".join(reversed(value.split("-")))
    elif mode == "percent":
        rendered = f"{100 * float(value):.0f} %"
    else:
        rendered = format(float(value), ".2f" if mode == "f2" else ".6g")
    if check["latex"]:
        mantissa, exponent = rendered.split("e")
        rendered = mantissa + r"\times10^{" + str(int(exponent)) + "}"
    line = read(RESPONSE_PATH).splitlines()[check["line"] - 1]
    assert rendered in line


@pytest.mark.parametrize(
    "relative,digest", MANIFEST["source_sha256_normalized_lf"].items()
)
def test_frozen_source_summaries_and_baselines(relative, digest):
    assert hashlib.sha256(read(relative).encode("utf-8")).hexdigest() == digest


def test_phase1_to_7_tracked_files_unchanged_from_phase7():
    base = MANIFEST["source_base_commit"]
    original = set(
        git_output("ls-tree", "-r", "--name-only", base).decode().splitlines()
    )
    changed = set(
        git_output("diff", "--no-renames", "--name-only", base, "--")
        .decode()
        .splitlines()
    )
    assert not original.intersection(changed)
    assert (
        git_output("rev-parse", MANIFEST["source_base_tag"] + "^{commit}")
        .decode()
        .strip()
        == base
    )


def test_phase8b_changes_only_authorized_files():
    changed = set(
        git_output("diff", "--no-renames", "--name-only", RESPONSE_COMMIT, "--")
        .decode()
        .splitlines()
    )
    assert changed <= ALLOWED_PHASE8B_CHANGES
    assert not git_output("diff", RESPONSE_COMMIT, "--", RESPONSE_PATH)


def test_phase8b_scientific_honesty_and_disclaimer():
    doc = read("docs/phase8_llm_analysis.md")
    for phrase in [
        "Phase 8B",
        "not an independent human analysis",
        "No holdout",
        "The LLM response was generated only after the statistical analyses and final holdout evaluation had been completed.",
        "retrospective",
        "unavailable",
        RESPONSE_SHA256,
        RESPONSE_COMMIT,
    ]:
        assert phrase in doc
    assert "Pending manual generation" not in doc
    assert "**Pending.**" not in doc
    facts = read("llm/prompts/phase8_project_facts.md")
    for phrase in [
        "SARIMA gate is FALSE",
        "VECM gate is FALSE",
        "GARCH(1,1) Normal",
        "211",
        "Naive",
        "underflow",
        "Cholesky",
        "not proof",
        "not measured",
    ]:
        assert phrase in facts
    disclaimer = read("llm/prompts/phase8_investment_disclaimer.md")
    for phrase in [
        "academic exercise",
        "simulated",
        "not personalized financial advice",
        "No future performance is guaranteed",
    ]:
        assert phrase in disclaimer
