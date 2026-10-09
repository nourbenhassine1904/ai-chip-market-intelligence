"""Phase 9A delivery/provenance contracts; no historical pipeline execution."""

import ast
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import nbformat
import pytest

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/AI_Chip_Market_Intelligence.ipynb"
NB = nbformat.read(NOTEBOOK, as_version=4)
SPEC = importlib.util.spec_from_file_location("review", ROOT / "python/phase9a_review.py")
REVIEW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REVIEW)


def test_notebook_schema_syntax_sections_and_no_machine_paths():
    nbformat.validate(NB)
    text = "\n".join(c.source for c in NB.cells)
    for section in ["Introduction", "Data", "EDA", "ARIMA", "VAR / Granger / Johansen",
                    "GARCH", "LSTM / GRU", "Final Evaluation", "LLM", "Conclusion"]:
        assert f"## {section}" in text
    assert not re.search(r"[A-Za-z]:[\\/]", text)
    assert not re.search(r"\\\\[A-Za-z0-9_-]+\\", text)
    imports = set()
    for cell in NB.cells:
        if cell.cell_type != "code":
            continue
        tree = ast.parse(cell.source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(x.name.split(".")[0] for x in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"fit", "download", "to_csv", "savefig", "write_text", "run"}
        assert cell.execution_count is None and cell.outputs == []
    assert not imports.intersection({"tensorflow", "statsmodels", "yfinance", "arch", "sklearn", "subprocess"})


@pytest.mark.parametrize("kind", ["tables", "figures", "texts"])
def test_all_notebook_sources_exist_and_are_manifested(kind):
    records = {r["path"] for r in REVIEW.frozen_records()}
    for relative in NB.metadata.phase9a[kind]:
        assert relative in records
        assert (ROOT / relative).is_file()
        REVIEW.published(relative)


def test_metadata_covers_executable_table_figure_references():
    tables, figures = set(), set()
    for cell in NB.cells:
        if cell.cell_type != "code":
            continue
        for node in ast.walk(ast.parse(cell.source)):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in {"table", "show_figure", "published"}
                    and node.args and isinstance(node.args[0], ast.Constant)):
                value = node.args[0].value
                if node.func.id == "table":
                    tables.add(f"outputs/tables/{value}.csv")
                elif node.func.id == "show_figure":
                    figures.add(value)
    assert tables <= set(NB.metadata.phase9a.tables)
    assert figures == set(NB.metadata.phase9a.figures)


def test_frozen_science_exact_bytes_and_manifest_matches_base_git_tree():
    result = REVIEW.verify_frozen(portable=True)
    assert result.status.eq("PASS").all(), result[result.status != "PASS"]
    manifest = json.loads((ROOT / REVIEW.MANIFEST).read_text(encoding="utf8"))
    assert manifest["base_commit"] == subprocess.check_output(
        ["git", "rev-parse", "v0.11.0-phase8^{commit}"], cwd=ROOT).decode().strip()
    names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only",
                                     manifest["base_commit"]], cwd=ROOT).decode().splitlines()
    expected = {p for p in names if p.split("/")[0] in
                {"docs", "llm", "outputs", "python", "r"} and not p.endswith(".gitkeep")}
    assert {r["path"] for r in manifest["artifacts"]} == expected
    assert not result.path.duplicated().any()
    changed = set(subprocess.check_output(
        ["git", "diff", "--name-only", manifest["base_commit"], "--"],
        cwd=ROOT).decode().splitlines())
    assert not expected.intersection(changed)
    # Independently check every portable digest against the archived Git blob.
    records = manifest["artifacts"]
    queries = "\n".join(f"{manifest['base_commit']}:{r['path']}" for r in records) + "\n"
    raw = subprocess.run(["git", "cat-file", "--batch"], input=queries.encode(),
                         cwd=ROOT, check=True, capture_output=True).stdout
    cursor = 0
    for record in records:
        end = raw.index(b"\n", cursor)
        _, kind, size = raw[cursor:end].split()
        assert kind == b"blob"
        cursor = end + 1
        blob = raw[cursor:cursor + int(size)]
        assert hashlib.sha256(blob).hexdigest() == record["git_blob_sha256"]
        cursor += int(size) + 1


def test_manifest_detects_missing_and_changed_bytes(tmp_path):
    directory = tmp_path / "docs"
    directory.mkdir()
    source = tmp_path / "example.csv"
    source.write_bytes(b"a\n1\n")
    blob = hashlib.sha256(source.read_bytes()).hexdigest()
    (directory / "phase9a_frozen_artifacts_manifest.json").write_text(json.dumps({
        "artifacts": [{"path": "example.csv", "sha256": blob, "git_blob_sha256": blob}]}))
    assert REVIEW.verify_frozen(tmp_path).status.eq("PASS").all()
    source.write_bytes(b"a\n2\n")
    assert REVIEW.verify_frozen(tmp_path).status.eq("FAIL").all()
    with pytest.raises(ValueError, match="checksum"):
        REVIEW.published("example.csv", tmp_path)
    source.unlink()
    assert REVIEW.verify_frozen(tmp_path).status.eq("FAIL").all()


def test_metric_provenance_and_arithmetic_from_frozen_predictions():
    replay = REVIEW.metric_replay()
    assert replay.status.eq("PASS").all()
    assert len(replay) == 10
    assert replay.n_forecasts.eq(211).all()
    assert NB.metadata.phase9a.metrics_source == "outputs/tables/phase7_final_predictions.csv"
    assert REVIEW.table("phase7_final_model_recommendation").iloc[0].final_recommended_price_model == "Naive"


def test_guides_modes_rstudio_and_real_commands():
    for relative in ["README.md", "docs/team_setup_windows.md", "docs/reproduction_guide.md",
                     "docs/phase9a_repository_audit.md", "docs/final_requirements_checklist.md",
                     "docs/final_figure_selection.md", "docs/phase9a_reproducibility.md"]:
        assert (ROOT / relative).is_file()
    guide = (ROOT / "docs/reproduction_guide.md").read_text(encoding="utf8")
    assert "Mode A" in guide and "FAST" in guide and "Mode B" in guide and "FULL" in guide
    assert "not run during Phase 9A" in guide
    assert "Using RStudio with this repository" in (ROOT / "docs/team_setup_windows.md").read_text(encoding="utf8")
    for script, flag in re.findall(r"(?:python|Rscript) ((?:python|r)/[\w./]+)(?: (--[\w-]+))?", guide):
        assert (ROOT / script).is_file(), script
        if flag:
            assert flag in (ROOT / script).read_text(encoding="utf8"), (script, flag)


def test_schema_cli_is_independent_of_changed_sandbox_outputs(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["phase9a_review.py", "--structure"])
    monkeypatch.setattr(REVIEW, "verify_dataset_structure", lambda: None)

    def forbidden(*args, **kwargs):
        raise AssertionError("A standalone schema check must not verify regenerated output hashes")

    monkeypatch.setattr(REVIEW, "verify_frozen", forbidden)
    assert REVIEW.main() == 0


def test_document_links_and_figure_selection_exist():
    docs = [ROOT / "README.md", *ROOT.glob("docs/*9a*.md"),
            ROOT / "docs/final_figure_selection.md", ROOT / "docs/final_requirements_checklist.md",
            ROOT / "docs/reproduction_guide.md", ROOT / "docs/team_setup_windows.md"]
    for doc in docs:
        for relative in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf8")):
            if "://" in relative or relative.startswith("#"):
                continue
            assert (doc.parent / relative.split("#")[0]).exists(), (doc, relative)
    selection = (ROOT / "docs/final_figure_selection.md").read_text(encoding="utf8")
    for relative in re.findall(r"`(outputs/(?:figures|tables)/[^`]+)`", selection):
        assert (ROOT / relative).is_file()


def test_real_execution_evidence_when_available():
    path = ROOT / "outputs/tables/phase9a_notebook_execution_audit.csv"
    assert path.is_file()
    audit = REVIEW.pd.read_csv(path)
    assert audit.columns.tolist() == ["check", "status", "detail"]
    for check in ["frozen_before", "FAST_execution", "FAST_guards", "clean_copy_FAST", "frozen_after"]:
        selected = audit[audit.check == check]
        assert len(selected) == 1 and selected.iloc[0].status == "PASS", audit.to_string()
