"""ZIP packaging/integrity contracts; no downloads, model fitting or new forecasts."""

import hashlib
import importlib.util
import json
import shutil
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("submission", ROOT / "python/09e_build_submission.py")
PACK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACK)


@pytest.mark.parametrize("name", [
    "../escape.txt", "/absolute.txt", "C:/absolute.txt", "a/../escape.txt",
    "a\\windows.txt", "a//empty.txt", "./dot.txt", "a/file.txt:stream",
    ".git/config", ".venv/bin/python", "python/__pycache__/module.pyc",
    ".pytest_cache/value", ".ruff_cache/value", ".cache/weights.keras",
    ".Rproj.user/state", "report_latex/_build/main.pdf", "report_latex/main.aux",
    "report_latex/main.synctex.gz", "~$report.docx", "private/.env",
    ".env.example", "report_latex.zip", "nested/old.ZIP", "private/key.pem",
    "data/raw/.gitkeep", "dist/another.txt", "",
])
def test_unsafe_and_unwanted_paths_rejected(name):
    assert not PACK.safe_path(name)


def test_only_historical_original_snapshots_are_accepted(tmp_path):
    for relative in PACK.SNAPSHOTS + (
        "outputs/tables/phase1_raw_manifest.csv",
        "outputs/tables/phase1_5_processed_manifest.csv",
        "outputs/tables/phase2_feature_manifest.csv",
        "docs/phase9a_frozen_artifacts_manifest.json", "docs/phase9c_full_summary.json",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    assert len(PACK.check_snapshots(tmp_path)) == 7
    changed = tmp_path / PACK.SNAPSHOTS[-1]
    original = changed.read_bytes()
    changed.write_bytes(original + b"\n")
    with pytest.raises(ValueError, match="missing/divergent"):
        PACK.check_snapshots(tmp_path)
    changed.unlink()
    with pytest.raises(ValueError, match="MISSING"):
        PACK.check_snapshots(tmp_path)


def test_frozen_artifact_divergence_stops_packaging(tmp_path):
    source = tmp_path / "r/02_arima.R"
    source.parent.mkdir()
    source.write_bytes(b"# frozen fixture\n")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "phase9a_frozen_artifacts_manifest.json").write_bytes(PACK.json_bytes({
        "artifacts": [{"path": "r/02_arima.R", "sha256": PACK.digest(source),
                       "git_blob_sha256": PACK.digest(source)}],
    }))
    assert PACK.check_frozen_artifacts(tmp_path) == 1
    source.write_bytes(b"# divergent fixture\n")
    with pytest.raises(ValueError, match="frozen scientific artifact diverged"):
        PACK.check_frozen_artifacts(tmp_path)


@pytest.fixture(scope="module")
def packaged(tmp_path_factory):
    """Rebuild from a Git-free, byte-faithful copy of the real delivery payload."""
    source = tmp_path_factory.mktemp("submission-source")
    paths, revision, branch = PACK.inventory(ROOT)
    for relative in paths:
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    (source / PACK.INTERNAL_MANIFEST).write_bytes(PACK.json_bytes({
        "files": [PACK.record(source, p) for p in paths],
        "source_revision": revision, "source_branch": branch,
    }))
    # These ignored/unlisted files must never leak into a rebuilt delivery.
    for name in ("python/unlisted_secret.py", ".env", "report_latex/_build/junk.pdf", "old.zip"):
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"not a deliverable")
    result = PACK.build(source)
    return source, source / result["zip"]["path"], result


def test_real_archive_crc_payload_and_required_contents(packaged):
    source, archive, result = packaged
    internal = PACK.verify_zip(archive)
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        assert len(zipped.namelist()) == result["file_count"]
        assert zipped.read("RAPPORT_FINAL.pdf") == (ROOT / "report_latex/rapport_final_latex.pdf").read_bytes()
        for row in result["files"]:
            assert hashlib.sha256(zipped.read(row["path"])).hexdigest() == row["sha256"]
        assert "python/unlisted_secret.py" not in zipped.namelist()
        assert {n for n in zipped.namelist() if n.startswith("data/")} == set(PACK.SNAPSHOTS)
    assert len(internal["files"]) + 1 == result["file_count"]
    assert not (source / ".git").exists()
    assert result["integrity"]["extraction_all_entries"] == "PASS"
    assert result["full_scientific_status"]["section_8_3"] == "PARTIAL"
    assert result["zip"]["size_bytes"] == archive.stat().st_size
    assert archive.with_suffix(".zip.sha256").read_text().split()[0] == PACK.digest(archive)
    assert PACK.EXTERNAL_MANIFEST not in {r["path"] for r in internal["files"]}
    assert PACK.INTERNAL_MANIFEST not in {r["path"] for r in internal["files"]}


def rewritten_zip(archive, destination, *, altered=None, extra=None):
    with zipfile.ZipFile(archive) as original, zipfile.ZipFile(
        destination, "w", zipfile.ZIP_DEFLATED
    ) as output:
        for name in original.namelist():
            content = original.read(name)
            if name == altered:
                content += b"corruption"
            output.writestr(name, content)
        if extra:
            output.writestr(extra, b"unexpected")


def test_valid_crc_does_not_hide_payload_sha_corruption(packaged, tmp_path):
    _, archive, _ = packaged
    corrupted = tmp_path / "corrupted.zip"
    rewritten_zip(archive, corrupted, altered="data/raw/NVDA_raw.csv")
    with zipfile.ZipFile(corrupted) as zipped:
        assert zipped.testzip() is None
    with pytest.raises(ValueError, match="SHA/size mismatch"):
        PACK.verify_zip(corrupted)


@pytest.mark.parametrize("extra", ["../escape.txt", "unmanifested.txt"])
def test_zip_traversal_and_unmanifested_entries_fail(packaged, tmp_path, extra):
    _, archive, _ = packaged
    corrupt = tmp_path / "extra.zip"
    rewritten_zip(archive, corrupt, extra=extra)
    with pytest.raises(ValueError, match="Unsafe/forbidden|inventory differs"):
        PACK.verify_zip(corrupt)


def test_missing_required_notebook_stops_delivery():
    required = set(PACK.SNAPSHOTS + PACK.LLM_FILES + PACK.GUIDES)
    with pytest.raises(ValueError, match="Required deliverables absent"):
        PACK.required_delivery(required)


def test_secret_signature_blocks_packaging(tmp_path):
    source = tmp_path / "secret.txt"
    source.write_bytes(b"-----BEGIN " + b"PRIVATE KEY-----\nprivate material")
    with pytest.raises(ValueError, match="credential/private key"):
        PACK.scan_secrets(source)


def test_delivery_guide_matches_team_and_honest_full_status():
    guide = (ROOT / "LIVRAISON.md").read_text("utf8")
    for text in ("Nour Ben Hassine", "Nouhe Ben Khelil", "Hadir Felli", "Nouha Briki",
                 "Ahmed Dhouibi", "ING-5-J-SDIAF-B", "12 octobre 2026", "23h55",
                 "PARTIAL", "Naive", "SOURCE_REVISION", "state.json", "Git complet"):
        assert text in guide
    assert PACK.FULL_STATUS["new_full_run_during_packaging"] is False
    assert PACK.FULL_STATUS["bit_for_bit_determinism_guaranteed"] is False


def test_notebook_full_defaults_preserved():
    nb = json.loads((ROOT / PACK.NOTEBOOKS[1]).read_text("utf8"))
    source = "\n".join("".join(c["source"]) for c in nb["cells"])
    assert 'MODE = "PREFLIGHT"' in source
    assert "AUTHORIZE_FULL = False" in source
    assert 'SOURCE_REVISION = "v0.13.0-phase9b"' in source
