"""Source, rendered-document and frozen-artifact checks; no scientific execution."""

import csv
import hashlib
import importlib.util
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[1]
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
SOURCE = ROOT / "report/rapport_final.md"
DOCX = ROOT / "report/rapport_final.docx"
PDF = ROOT / "report/rapport_final.pdf"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def sources():
    spec = importlib.util.spec_from_file_location("report_sources", ROOT / "report/report_sources.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def document():
    with ZipFile(DOCX) as archive:
        return ET.fromstring(archive.read("word/document.xml"))


def read_csv(relative):
    with (ROOT / relative).open(encoding="utf8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_deliverables_and_ten_chapters():
    for relative in ["report/rapport_final.md", "report/rapport_final.docx", "report/rapport_final.pdf",
                     "report/README.md", "report/preparation_soutenance.md",
                     "docs/phase9b_report_audit.md", "docs/phase9b_results_traceability.csv"]:
        assert (ROOT / relative).stat().st_size > 0
    text = SOURCE.read_text(encoding="utf8")
    chapters = re.findall(r"^# (\d+) ", text, flags=re.MULTILINE)
    assert chapters == [str(i) for i in range(1, 11)]
    assert "2026/2027" in text and "TEK-UP" in text
    assert "[noms et identifiants à compléter]" in text
    assert "[nom à compléter]" in text
    assert "Date de remise : [à compléter]" in text


@pytest.mark.parametrize("table_name", ["data", "descriptive", "stationarity", "granger", "garch",
                                       "final_metrics", "dm", "llm", "costs"])
def test_markdown_and_word_tables_match_archived_sources(table_name, sources, document):
    tables = sources.tables()
    headers, rows, _ = tables[table_name]
    expected = sources.markdown_table(headers, rows)
    text = SOURCE.read_text(encoding="utf8")
    match = re.search(rf"<!-- table: {table_name} -->\s*(.*?)\s*<!-- endtable: {table_name} -->",
                      text, flags=re.DOTALL)
    assert match is not None and match[1] == expected
    word_tables = document.findall(".//w:body/w:tbl", NS)
    assert len(word_tables) == 9
    table = word_tables[list(tables).index(table_name)]
    actual = [["".join(t.text or "" for t in cell.findall(".//w:t", NS))
               for cell in row.findall("w:tc", NS)] for row in table.findall("w:tr", NS)]
    assert actual == [headers, *rows]


def test_final_metric_panel_and_naive_recommendation(document):
    metrics = read_csv("outputs/tables/phase7_final_metrics.csv")
    assert len(metrics) == 10
    assert {(r["model"], int(r["horizon"])) for r in metrics} == {
        (model, h) for model in ["Naive", "ARIMA(2,1,2)", "VAR(9)", "LSTM C", "GRU C"] for h in [5, 10]}
    word_text = " ".join(t.text or "" for t in document.findall(".//w:t", NS))
    for row in metrics:
        for key in ["MSE", "RMSE", "MAE", "MAPE"]:
            assert f"{float(row[key]):.3f}".replace(".", ",") in word_text
    recommendation = read_csv("outputs/tables/phase7_final_model_recommendation.csv")[0]
    assert recommendation["final_recommended_price_model"] == "Naive"
    text = SOURCE.read_text(encoding="utf8")
    assert "Naive constitue la recommandation finale de prix" in text
    assert "Holm" in text and "non-rejet" in text
    assert "léger avantage de RMSE à dix séances" in text


def test_figures_exist_selected_and_embedded_without_modification():
    text = SOURCE.read_text(encoding="utf8")
    paths = [(SOURCE.parent / p).resolve() for p in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)]
    assert len(paths) == len(set(paths)) == 15
    assert all(p.is_file() and p.is_relative_to(ROOT / "outputs/figures") for p in paths)
    selection = (ROOT / "docs/final_figure_selection.md").read_text(encoding="utf8")
    assert all(p.relative_to(ROOT).as_posix() in selection for p in paths)
    with ZipFile(DOCX) as archive:
        images = [archive.read(p) for p in archive.namelist() if p.startswith("word/media/") and not p.endswith("/")]
    assert len(images) == 15
    assert {hashlib.sha256(data).hexdigest() for data in images} == {digest(p) for p in paths}


def test_key_prose_quantities_match_archived_cells(sources, document):
    source_text = SOURCE.read_text(encoding="utf8")
    word_text = " ".join(t.text or "" for t in document.findall(".//w:t", NS))
    checks = [
        ("phase4_r_python_summary", {}, "max_companion_modulus", 6),
        ("phase4_johansen_rank_comparison", {"level_lags": "3", "null_rank_at_most": "0"}, "trace_statistic_r", 6),
        ("phase6_locked_lstm", {}, "average_RMSE_ratio", 6),
        ("phase6_locked_gru", {}, "average_RMSE_ratio", 6),
        ("phase7_recommendation_checks", {"model": "ARIMA(2,1,2)"}, "average_RMSE_ratio", 9),
        ("phase7_arima_interval_coverage", {"horizon": "5"}, "mean_interval_width", 6),
        ("phase7_arima_interval_coverage", {"horizon": "10"}, "mean_interval_width", 6),
    ]
    for name, filters, field, decimals in checks:
        row = next(r for r in sources.read_csv(name) if all(r[k] == v for k, v in filters.items()))
        expected = sources.fr(row[field], decimals)
        assert expected in source_text and expected in word_text, (name, field, expected)
    for name in ["phase6_locked_lstm", "phase6_locked_gru"]:
        parameters = sources.read_csv(name)[0]["trainable_parameters"]
        assert parameters in source_text and parameters in word_text


def test_exact_internal_references_exist():
    for relative in ["report/rapport_final.md", "report/preparation_soutenance.md"]:
        text = (ROOT / relative).read_text(encoding="utf8")
        for path in re.findall(r"`((?:outputs/|docs/|llm/|notebooks/|python/|r/)[^`]+)`", text):
            if "*" not in path:
                assert (ROOT / path).is_file(), path
    text = SOURCE.read_text(encoding="utf8")
    refs = re.findall(r"^\[R(\d+)\] ", text, re.MULTILINE)
    assert refs == [str(i) for i in range(1, 18)]


def test_llm_annex_e_is_exact_original_section_b(sources, document):
    original = sources.llm_section_b()
    text = SOURCE.read_text(encoding="utf8")
    match = re.search(r"<!-- llm-section-b:start -->\n(.*?)<!-- llm-section-b:end -->", text, re.DOTALL)
    assert match is not None and match[1] == original
    paragraphs = ["".join(t.text or "" for t in p.findall(".//w:t", NS))
                  for p in document.findall("w:body/w:p", NS)]
    first = paragraphs.index("B. VULGARISATION")
    original_lines = original.splitlines()
    assert paragraphs[first:first + len(original_lines)] == original_lines
    assert "Texte du LLM reproduit fidèlement" in text
    assert "Annexe E Explication vulgarisée originale du LLM" in text
    assert sources.LLM_RESPONSE_SHA256 == digest(ROOT / sources.LLM_RESPONSE)


def test_stationarity_asset_list_and_documentary_scope(sources):
    rows = sources.tables()["stationarity"][1]
    assert all(row[1].split(", ") == ["NVDA", "AMD", "SOXX"] for row in rows)
    text = SOURCE.read_text(encoding="utf8")
    assert "Le PDF officiel du cahier des charges n’était pas intégré au dépôt lors de l’audit automatisé" in text
    assert "Aucune vérification indépendante exhaustive du PDF officiel n’est revendiquée" in text
    assert "ne démontre ni causalité ni effet d’annonce" in text
    assert "[R17]" in text


def test_traceability_is_current_and_sources_exist(sources):
    path = ROOT / "docs/phase9b_results_traceability.csv"
    assert path.read_text(encoding="utf8") == sources.trace_csv()
    rows = read_csv(path.relative_to(ROOT).as_posix())
    assert len(rows) > 100
    assert list(rows[0]) == ["claim_id", "section", "claim", "source_file", "verification_status", "comment"]
    assert len({r["claim_id"] for r in rows}) == len(rows)
    for row in rows:
        assert row["verification_status"] == "VERIFIED_SOURCE"
        assert all((ROOT / p).is_file() for p in row["source_file"].split("; "))


def test_llm_scope_and_full_limitation_are_explicit():
    text = SOURCE.read_text(encoding="utf8")
    audit = read_csv("llm/human_analysis/phase8_hallucination_audit.csv")
    assert len(audit) == 35 and all(r["issue_type"] == "supported" for r in audit)
    for fragment in ["35 affirmations", "indépendante aveugle", "métadonnées", "FULL", "PARTIAL",
                     "machine vierge", "snapshots", "TensorFlow CPU", "clone isolé",
                     "prédictions préexistantes", "réponse LLM officielle", "durée totale FULL"]:
        assert fragment in text, fragment
    assert "FULL n’a pas été démontré" in text
    assert "ne constitue pas un livrable scientifique obligatoire manquant" in text
    questions = re.findall(r"^\d+\. \*\*", (ROOT / "report/preparation_soutenance.md").read_text(encoding="utf8"), re.MULTILINE)
    assert len(questions) == 15


def test_historical_science_and_phase9a_notebook_preserved():
    for manifest in ["docs/phase9a_frozen_artifacts_manifest.json", "docs/phase9b_frozen_references.json"]:
        records = json.loads((ROOT / manifest).read_text(encoding="utf8"))["artifacts"]
        assert len(records) == (305 if "phase9a" in manifest else 2)
        for record in records:
            assert digest(ROOT / record["path"]) in {record["sha256"], record["git_blob_sha256"]}, record["path"]
    response = ROOT / "llm/responses/phase8_official_llm_response.md"
    assert digest(response) == "eecb0de3e0dd8e152e93db70ff71f9dad87024b7b2f3e1bee1ede05225f6f3b4"


def test_available_local_snapshots_preserved():
    records = read_csv("outputs/tables/phase9a_data_checksum_audit.csv")
    assert len(records) == 7
    available = [r for r in records if (ROOT / r["path"]).is_file()]
    if not available:
        pytest.skip("Local snapshots are intentionally excluded from a normal clone")
    for record in available:
        assert digest(ROOT / record["path"]) == record["expected_sha256"], record["path"]


def test_real_pagination_and_render_fingerprints():
    audit = json.loads((ROOT / "docs/phase9b_render_audit.json").read_text(encoding="utf-8-sig"))
    actual_pdf_pages = len(re.findall(rb"/Type\s*/Page\b", PDF.read_bytes()))
    with ZipFile(DOCX) as archive:
        app = ET.fromstring(archive.read("docProps/app.xml"))
    word_pages = int(app.find("{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Pages").text)
    assert actual_pdf_pages == word_pages == audit["total_pages"]
    assert 15 <= audit["body_pages_excluding_annexes"] <= 25
    assert 15 <= audit["pages_excluding_annexes"] <= 25
    assert audit["pages_excluding_annexes"] == audit["annex_start_page"] - 1
    assert audit["body_pages_excluding_annexes"] == audit["annex_start_page"] - audit["body_start_page"]
    assert audit["visual_review"] == "PASS"
    for key, path in [("markdown_sha256", SOURCE), ("docx_sha256", DOCX), ("pdf_sha256", PDF)]:
        assert audit[key] == digest(path)
    assert len(audit["reviewed_pdf_pages"]) == actual_pdf_pages


def test_word_editable_equations_and_page_format(document):
    equations = document.findall(".//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath")
    assert len(equations) == 4
    section = document.find("w:body/w:sectPr", NS)
    size = section.find("w:pgSz", NS)
    assert int(size.get("{" + W + "}w")) == 11906
    assert int(size.get("{" + W + "}h")) == 16838
    margins = section.find("w:pgMar", NS)
    assert all(int(margins.get("{" + W + "}" + side)) == 1417 for side in ["left", "right", "top", "bottom"])
    assert document.find(".//w:instrText", NS) is not None
