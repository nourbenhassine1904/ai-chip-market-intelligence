"""Read-only checks for the Phase 8A package; never import analysis runners."""

import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "llm/prompts"
MANIFEST = json.loads(
    (PROMPTS / "phase8_source_manifest.json").read_text(encoding="utf-8")
)
RESPONSE = (
    "# Official LLM Response\n\n> Paste the complete, unedited LLM response here.\n"
)
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


def test_response_comparison_and_audit_are_unfilled():
    assert read("llm/responses/phase8_official_llm_response.md") == RESPONSE
    expected = "# Phase 8 — Human/Team Baseline vs LLM Comparison\n\n"
    expected += "\n\n".join(f"## {i}. {q}" for i, q in enumerate(QUESTIONS, 1)) + "\n"
    assert read("llm/human_analysis/phase8_human_vs_llm_comparison.md") == expected
    with (ROOT / "llm/human_analysis/phase8_hallucination_audit.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        assert list(csv.reader(stream)) == [AUDIT_HEADER]


@pytest.mark.parametrize(
    "relative,digest", MANIFEST["source_sha256_normalized_lf"].items()
)
def test_frozen_source_summaries_and_baselines(relative, digest):
    assert hashlib.sha256(read(relative).encode("utf-8")).hexdigest() == digest


def test_phase1_to_7_tracked_files_unchanged_from_phase7():
    # Includes committed, staged and unstaged changes to every pre-existing tracked file.
    base = MANIFEST["source_base_commit"]
    changed = subprocess.check_output(
        ["git", "diff", "--name-status", "--diff-filter=DMRTUXB", base, "--"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    )
    assert changed == ""
    assert (
        subprocess.check_output(
            ["git", "rev-parse", MANIFEST["source_base_tag"] + "^{commit}"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
        ).strip()
        == base
    )


def test_phase8a_status_and_scientific_limits():
    doc = read("docs/phase8_llm_analysis.md")
    for phrase in [
        "Phase 8A",
        "not yet generated",
        "not an independent human analysis",
        "No holdout",
        "was generated only after",
    ]:
        assert phrase in doc
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
