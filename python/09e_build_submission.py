"""Package frozen university deliverables; never download, fit or evaluate models."""

import argparse
import ast
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = "AI_Chip_Market_Intelligence_Remise_2026.zip"
INTERNAL_MANIFEST = "MANIFESTE_LIVRAISON.json"
EXTERNAL_MANIFEST = "docs/final_submission_manifest.json"
EXTERNAL_AUDIT = "docs/final_submission_audit.md"
SCIENTIFIC_REVISION = "v0.15.0-phase9d"
SNAPSHOTS = (
    "data/raw/NVDA_raw.csv", "data/raw/AMD_raw.csv", "data/raw/SOXX_raw.csv",
    "data/processed/market_aligned.csv", "data/processed/market_features.csv",
    "data/processed/market_train.csv", "data/processed/market_test.csv",
)
NOTEBOOKS = (
    "notebooks/AI_Chip_Market_Intelligence.ipynb",
    "notebooks/AI_Chip_Market_Intelligence_FULL.ipynb",
)
LLM_FILES = (
    "llm/prompts/phase8_official_llm_prompt.md",
    "llm/responses/phase8_official_llm_response.md",
    "llm/human_analysis/phase8_human_vs_llm_comparison.md",
    "llm/human_analysis/phase8_hallucination_audit.csv",
)
GUIDES = (
    "LIVRAISON.md", "README.md", "docs/reproduction_guide.md",
    "docs/team_setup_windows.md", "docs/final_requirements_checklist.md",
    "docs/protocol.md", "docs/data_dictionary.md", "docs/decisions.md",
    "docs/phase9c_full_execution_audit.md", "docs/phase9c_full_summary.json",
    "docs/phase9d_latex_report.md", "report_latex/README.md",
)
ROOT_FILES = {
    "README.md", "LIVRAISON.md", "requirements.txt", "requirements-dev.txt",
    "ai-chip-market-intelligence.Rproj", ".gitignore", ".gitattributes",
}
FOLDERS = {"python", "r", "tests", "notebooks", "docs", "llm", "report", "report_latex"}
NEW_FILES = {"LIVRAISON.md", "python/09e_build_submission.py", "tests/test_final_submission.py"}
FORBIDDEN_PARTS = {
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
    ".ruff_cache", ".mypy_cache", ".Rproj.user", ".cache", "_build",
    ".ipynb_checkpoints", ".aws", ".codex", ".agents", "dist",
}
FORBIDDEN_SUFFIXES = {
    ".zip", ".pyc", ".pyo", ".aux", ".log", ".toc", ".out", ".bbl",
    ".blg", ".fls", ".fdb_latexmk", ".synctex", ".gz", ".tmp", ".temp",
    ".pem", ".key", ".p12", ".pfx",
}
SECRET_PATTERN = re.compile(
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    rb"\bAKIA[0-9A-Z]{16}\b|\bgh[pousr]_[A-Za-z0-9]{30,}\b|"
    rb"\bgithub_pat_[A-Za-z0-9_]{40,}\b|\bsk-(?:proj-)?[A-Za-z0-9_-]{40,}\b"
)
FULL_STATUS = {
    "prepared_sandbox_runner": "PIPELINE_EXECUTED",
    "clean_machine": "PARTIAL",
    "full_notebook_top_to_bottom": "PARTIAL",
    "section_8_3": "PARTIAL",
    "new_full_run_during_packaging": False,
    "final_recommendation": "Naive",
    "bit_for_bit_determinism_guaranteed": False,
    "evidence": "docs/phase9c_full_summary.json",
}


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf8")


def safe_path(relative):
    """Reject traversal, Windows drives/streams, UNC, duplicate separators and caches."""
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        return False
    path = PurePosixPath(relative)
    if path.is_absolute() or any(p in {"", ".", ".."} for p in relative.split("/")):
        return False
    if any(p.lower() in {x.lower() for x in FORBIDDEN_PARTS} for p in path.parts):
        return False
    if any(p.lower().startswith(".env") or p.startswith("~$") for p in path.parts):
        return False
    return path.suffix.lower() not in FORBIDDEN_SUFFIXES and path.name not in {
        ".gitkeep", ".Rhistory", ".RData", ".Ruserdata", "Thumbs.db", "Desktop.ini",
    }


def source_path(root, relative):
    path = root / relative
    if not safe_path(relative) or path.is_symlink() or not path.is_file():
        raise ValueError(f"Missing or unsafe delivery source: {relative}")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Source escapes repository: {relative}")
    if any(p.is_symlink() for p in path.parents if p != root.parent):
        raise ValueError(f"Symbolic source directory: {relative}")
    return path


def historical_snapshots(root):
    """Use original frozen CSV manifests, corroborated by 9C3; no updated hashes."""
    def rows(relative):
        with (root / relative).open(encoding="utf8", newline="") as handle:
            return list(csv.DictReader(handle))

    tables = "outputs/tables/"
    raw = rows(tables + "phase1_raw_manifest.csv")
    canonical = rows(tables + "phase1_5_processed_manifest.csv")[0]
    features = rows(tables + "phase2_feature_manifest.csv")[0]
    expected = {"data/raw/" + row["file_name"]: row["sha256"] for row in raw}
    expected.update({
        "data/processed/market_aligned.csv": canonical["sha256"],
        "data/processed/market_features.csv": features["sha256"],
        "data/processed/market_train.csv": features["train_sha256"],
        "data/processed/market_test.csv": features["test_sha256"],
    })
    if set(expected) != set(SNAPSHOTS):
        raise ValueError("Historical manifests do not identify exactly seven snapshots")
    frozen = json.loads((root / "docs/phase9a_frozen_artifacts_manifest.json").read_text("utf8"))
    records = {r["path"]: r for r in frozen["artifacts"]}
    for name in ("phase1_raw_manifest", "phase1_5_processed_manifest", "phase2_feature_manifest"):
        relative = tables + name + ".csv"
        record = records[relative]
        if digest(root / relative) not in {record["sha256"], record["git_blob_sha256"]}:
            raise ValueError(f"Historical data manifest diverged: {relative}")
    summary = json.loads((root / "docs/phase9c_full_summary.json").read_text("utf8"))
    corroborated = {r["path"]: r["expected"] for r in summary["protection"]["snapshots"]}
    if corroborated != expected:
        raise ValueError("9C3 and original snapshot fingerprints disagree")
    if summary["full_status"] != FULL_STATUS["prepared_sandbox_runner"]:
        raise ValueError("Unexpected historical FULL execution status")
    return expected


def check_snapshots(root):
    result = []
    for relative, expected in historical_snapshots(root).items():
        path = root / relative
        actual = digest(path) if path.is_file() else "MISSING"
        row = {"path": relative, "expected_sha256": expected,
               "sha256": actual, "status": "PASS" if actual == expected else "FAIL"}
        result.append(row)
    failures = [r for r in result if r["status"] != "PASS"]
    if failures:
        raise ValueError("STOP: missing/divergent original snapshots: " + json.dumps(failures))
    return result


def check_frozen_artifacts(root):
    manifest = json.loads((root / "docs/phase9a_frozen_artifacts_manifest.json").read_text("utf8"))
    for row in manifest["artifacts"]:
        path = source_path(root, row["path"])
        if digest(path) not in {row["sha256"], row["git_blob_sha256"]}:
            raise ValueError(f"STOP: frozen scientific artifact diverged: {row['path']}")
    return len(manifest["artifacts"])


def inventory(root):
    """Allowlisted Git files plus three new packaging files and seven local snapshots."""
    if (root / ".git").exists():
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip()
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=root).decode().strip()
        tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
        candidates = set(tracked) | NEW_FILES
    else:
        packaged = json.loads((root / INTERNAL_MANIFEST).read_text("utf8"))
        revision, branch = packaged["source_revision"], packaged["source_branch"]
        candidates = {r["path"] for r in packaged["files"]} - {"RAPPORT_FINAL.pdf"}
    selected = set(SNAPSHOTS)
    for relative in candidates:
        if not safe_path(relative) or relative in {EXTERNAL_MANIFEST, EXTERNAL_AUDIT}:
            continue
        parts = PurePosixPath(relative).parts
        if (relative in ROOT_FILES or parts[0] in FOLDERS
                or parts[:2] in {("outputs", "tables"), ("outputs", "figures")}):
            selected.add(relative)
    for relative in selected:
        source_path(root, relative)
    return sorted(selected), revision, branch


def record(root, relative):
    path = source_path(root, relative)
    return {"path": relative, "size_bytes": path.stat().st_size, "sha256": digest(path)}


def required_delivery(paths):
    names = set(paths)
    required = set(SNAPSHOTS + NOTEBOOKS + LLM_FILES + GUIDES) | {
        "RAPPORT_FINAL.pdf", "report_latex/rapport_final_latex.pdf",
        "report_latex/main.tex", "report_latex/metadata.tex", "report_latex/references.bib",
        "requirements.txt", "requirements-dev.txt", "python/09e_build_submission.py",
        "tests/test_final_submission.py", "python/phase9a_review.py",
        "python/09a_execute_notebook.py", "python/09c_full_reproduction.py",
        "outputs/tables/phase7_final_predictions.csv",
        "outputs/tables/phase7_final_model_recommendation.csv",
    }
    required.update("python/" + n + ".py" for n in (
        "00_data_acquisition", "01_data_preparation", "01_data_eda", "02_arima",
        "02b_arima_validation", "03_var_vecm", "04_garch", "05_lstm_gru", "06_evaluation",
    ))
    required.update("r/" + n + ".R" for n in (
        "01_data_eda", "02_arima", "02b_arima_validation", "03_var_vecm", "04_garch",
    ))
    missing = sorted(required - names)
    if missing:
        raise ValueError(f"Required deliverables absent: {missing}")
    for prefix, suffix in (("python/", ".py"), ("r/", ".R"), ("outputs/figures/", ".png")):
        if not any(p.startswith(prefix) and p.endswith(suffix) for p in names):
            raise ValueError(f"Missing scientific files: {prefix}*{suffix}")


def scan_secrets(path):
    if (path.suffix.lower() in {".md", ".txt", ".py", ".r", ".json", ".ipynb", ".csv", ".tex"}
            and SECRET_PATTERN.search(path.read_bytes())):
        raise ValueError(f"Potential credential/private key in delivery: {path.name}")


def validate_notebooks(root):
    result = []
    for relative in NOTEBOOKS:
        notebook = json.loads((root / relative).read_text("utf8"))
        if notebook.get("nbformat") != 4 or not isinstance(notebook.get("cells"), list):
            raise ValueError(f"Invalid notebook structure: {relative}")
        code = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        for cell in code:
            ast.parse("".join(cell["source"]))
        result.append({"path": relative, "status": "PASS_JSON_AND_PYTHON_SYNTAX",
                       "code_cells": len(code), "sha256": digest(root / relative)})
    return result


def verify_zip(archive):
    """Read the real ZIP, test CRC and exact payload hashes; never extract unsafe names."""
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
        if len(names) != len(set(names)) or len(names) != len({n.casefold() for n in names}):
            raise ValueError("Duplicate or case-colliding ZIP paths")
        if any(not safe_path(n) for n in names):
            raise ValueError("Unsafe/forbidden ZIP entry")
        if any((i.external_attr >> 16) & 0o170000 == 0o120000 for i in zipped.infolist()):
            raise ValueError("Symbolic link in ZIP")
        if zipped.testzip() is not None:
            raise ValueError("ZIP CRC failure")
        manifest = json.loads(zipped.read(INTERNAL_MANIFEST))
        records = manifest["files"]
        expected = {r["path"] for r in records} | {INTERNAL_MANIFEST}
        if set(names) != expected or len(records) != len(expected) - 1:
            raise ValueError("ZIP inventory differs from manifest")
        required_delivery(names)
        for row in records:
            content = zipped.read(row["path"])
            if len(content) != row["size_bytes"] or hashlib.sha256(content).hexdigest() != row["sha256"]:
                raise ValueError(f"ZIP payload SHA/size mismatch: {row['path']}")
            if (PurePosixPath(row["path"]).suffix.lower() in {
                ".md", ".txt", ".py", ".r", ".json", ".ipynb", ".csv", ".tex"
            } and SECRET_PATTERN.search(content)):
                raise ValueError(f"Potential credential/private key in ZIP: {row['path']}")
        snapshots = manifest["snapshots"]
        if {r["path"] for r in snapshots} != set(SNAPSHOTS) or len(snapshots) != 7:
            raise ValueError("ZIP snapshot inventory must contain exactly seven original CSVs")
        for row in snapshots:
            if hashlib.sha256(zipped.read(row["path"])).hexdigest() != row["expected_sha256"]:
                raise ValueError(f"ZIP snapshot differs from historical SHA256: {row['path']}")
        pdf = zipped.read("report_latex/rapport_final_latex.pdf")
        if not pdf.startswith(b"%PDF-") or b"%%EOF" not in pdf[-1024:]:
            raise ValueError("Final PDF has invalid header/trailer")
        if zipped.read("RAPPORT_FINAL.pdf") != pdf:
            raise ValueError("Root PDF is not an exact copy")
    return manifest


def run_fast(extracted, scratch):
    """Use FAST's guarded executor directly so its historical audit CSV is not written."""
    code = """
import importlib.util, json, sys
from pathlib import Path
root, scratch = map(Path, sys.argv[1:])
sys.path.insert(0, str(root / 'python'))
import phase9a_review as review
checks = review.verify_frozen(root, portable=True)
assert checks.status.eq('PASS').all(), checks[checks.status != 'PASS'].to_string()
data = review.verify_local_data(root)
assert data.status.eq('PASS').all(), data[data.status != 'PASS'].to_string()
metrics = review.metric_replay(root)
spec = importlib.util.spec_from_file_location('fast_executor', root / 'python/09a_execute_notebook.py')
executor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(executor)
count = executor.execute(root, scratch / 'FAST.executed.ipynb', scratch / 'kernels')
print(json.dumps({'status': 'PASS', 'frozen_files': len(checks), 'snapshots': len(data),
                  'metric_rows': len(metrics), 'executed_code_cells': count,
                  'new_forecasts': False, 'model_training': False}))
"""
    env = os.environ.copy()
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "MPLCONFIGDIR": str(scratch / "matplotlib"),
                "IPYTHONDIR": str(scratch / "ipython"), "JUPYTER_CONFIG_DIR": str(scratch / "jupyter")})
    process = subprocess.run([sys.executable, "-B", "-c", code, str(extracted), str(scratch)],
                             cwd=extracted, env=env, capture_output=True, text=True,
                             timeout=600, check=False)
    if process.returncode:
        raise RuntimeError("Extracted FAST failed: " + process.stdout[-2000:] + process.stderr[-4000:])
    result = json.loads(process.stdout.strip().splitlines()[-1])
    result["scope"] = "Extracted ZIP, current installed environment; not a clean-machine FULL proof"
    return result


def build(root=ROOT, output=None, *, execute_fast=False):
    root = Path(root).resolve()
    output = Path(output or root / "dist" / ARCHIVE).resolve()
    if not output.is_relative_to(root / "dist") or output.suffix.lower() != ".zip":
        raise ValueError("Archive must be a ZIP under the selected root's dist/")
    snapshots = check_snapshots(root)  # Mandatory STOP before any staging on mismatch.
    frozen_count = check_frozen_artifacts(root)
    paths, revision, branch = inventory(root)
    before = {r["path"]: r for r in (record(root, p) for p in paths)}
    notebooks = validate_notebooks(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    built_at = datetime.now(timezone.utc).isoformat()
    with tempfile.TemporaryDirectory(prefix="phase9e-", dir=output.parent) as temp:
        temp = Path(temp)
        staging, extracted, scratch = temp / "staging", temp / "extracted", temp / "checks"
        for relative in paths:
            source = source_path(root, relative)
            scan_secrets(source)
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        shutil.copyfile(staging / "report_latex/rapport_final_latex.pdf", staging / "RAPPORT_FINAL.pdf")
        payload = [record(staging, p) for p in sorted(paths + ["RAPPORT_FINAL.pdf"])]
        required_delivery([r["path"] for r in payload])
        for relative in paths:
            if record(staging, relative) != before[relative]:
                raise ValueError(f"Source/staging bytes changed: {relative}")
        internal = {
            "schema_version": 1, "source_revision": revision, "source_branch": branch,
            "scientific_revision": SCIENTIFIC_REVISION, "built_at_utc": built_at,
            "source_capture": "Working-tree bytes at the source revision, including new packaging/documentation; all captured by per-file SHA256.",
            "files": payload, "snapshots": snapshots, "notebooks": notebooks,
            "historical_frozen_artifacts_verified": frozen_count,
            "full_scientific_status": FULL_STATUS,
            "hash_scope": "All payload files; MANIFESTE_LIVRAISON.json excludes itself.",
            "external_evidence": "ZIP size/hash and post-build audit are outside the ZIP; no circular hash.",
            "excluded_post_build_documents": [EXTERNAL_MANIFEST, EXTERNAL_AUDIT],
            "selection": "Allowlisted tracked files plus packaging files and exactly seven original CSV snapshots",
        }
        (staging / INTERNAL_MANIFEST).write_bytes(json_bytes(internal))
        entries = sorted([r["path"] for r in payload] + [INTERNAL_MANIFEST])
        candidate = temp / "candidate.zip"
        with zipfile.ZipFile(candidate, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
            for relative in entries:
                zipped.write(staging / relative, relative)
        verify_zip(candidate)
        with zipfile.ZipFile(candidate) as zipped:
            zipped.extractall(extracted)  # Names/symlinks checked before extraction.
        for relative in entries:
            if digest(extracted / relative) != digest(staging / relative):
                raise ValueError(f"Extraction mismatch: {relative}")
        check_snapshots(extracted)
        validate_notebooks(extracted)
        fast = run_fast(extracted, scratch) if execute_fast else {"status": "NOT_RUN"}
        for relative in entries:
            if digest(extracted / relative) != digest(staging / relative):
                raise ValueError(f"FAST modified delivered file: {relative}")
        for relative in paths:
            if record(root, relative) != before[relative]:
                raise ValueError(f"Packaging modified source: {relative}")
        complete_records = [record(staging, p) for p in entries]
        # A failed verification never replaces a previous successful archive.
        candidate.replace(output)
    zip_hash = digest(output)
    sidecar = output.with_suffix(".zip.sha256")
    sidecar.write_text(f"{zip_hash}  {output.name}\n", encoding="ascii")
    sizes = {}
    for row in complete_records:
        folder = row["path"].split("/")[0] if "/" in row["path"] else "(racine)"
        sizes[folder] = sizes.get(folder, 0) + row["size_bytes"]
    size = output.stat().st_size
    result = {
        **internal, "files": complete_records, "file_count": len(complete_records),
        "hash_scope": "All ZIP entries, including the internal manifest; this external manifest is not embedded.",
        "zip": {"path": output.relative_to(root).as_posix(), "size_bytes": size,
                "size_mb_decimal": size / 1_000_000, "size_mib": size / 1_048_576,
                "sha256_file": sidecar.relative_to(root).as_posix()},
        "directory_sizes_bytes": dict(sorted(sizes.items(), key=lambda x: -x[1])),
        "pdf": {"status": "PASS_EXACT_SOURCE_COPY_AND_PDF_HEADER_TRAILER",
                "path": "report_latex/rapport_final_latex.pdf",
                "sha256": before["report_latex/rapport_final_latex.pdf"]["sha256"],
                "root_copy": "RAPPORT_FINAL.pdf", "prism_verification": "NOT_ATTESTED"},
        "integrity": {"crc": "PASS", "all_payload_sha256": "PASS", "relative_paths": "PASS",
                      "required_deliverables": "PASS", "secret_signature_scan": "PASS",
                      "exclusions": "PASS", "extraction_all_entries": "PASS",
                      "source_files_unchanged": "PASS", "extracted_files_after_fast": "PASS"},
        "fast": fast,
        "email_attachment": {
            "reference_budget_bytes": 25_000_000, "base64_estimated_bytes": 4 * ((size + 2) // 3),
            "exceeds_reference_budget_after_base64": 4 * ((size + 2) // 3) > 25_000_000,
            "risk": "Provider dependent; MIME/base64 adds about one third plus headers.",
            "external_share_created": False, "email_sent": False,
        },
    }
    (root / EXTERNAL_MANIFEST).write_bytes(json_bytes(result))
    print(json.dumps({"archive": str(output), "size_bytes": size, "size_mb_decimal": size / 1e6,
                      "file_count": result["file_count"], "sha256": zip_hash, "fast": fast}, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-fast", action="store_true", help="Run guarded FAST in the extracted copy")
    parser.add_argument("--verify", type=Path, help="Verify an existing ZIP without building")
    args = parser.parse_args()
    try:
        if args.verify:
            manifest = verify_zip(args.verify)
            print(f"PASS: CRC, paths, required files and {len(manifest['files'])} payload SHA256")
        else:
            build(args.root, args.output, execute_fast=args.run_fast)
    except (ValueError, RuntimeError, OSError, zipfile.BadZipFile) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
