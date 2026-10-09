"""Isolation/provenance safety tests; no scientific subprocess or market-data parse."""

import ast
import importlib.util
import json
import subprocess
from pathlib import Path

import nbformat
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "full_reproduction", ROOT / "python/09c_full_reproduction.py"
)
FULL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FULL)


@pytest.fixture
def workspace(tmp_path):
    reference, sandbox = tmp_path / "reference", tmp_path / "sandbox"
    reference.mkdir()
    sandbox.mkdir()
    workflow = object.__new__(FULL.Workflow)
    workflow.reference_root, workflow.sandbox_root = FULL.isolated_roots(
        reference, sandbox
    )
    workflow.source_revision = "fixture"
    workflow.rscript = "Rscript"
    workflow.python = sandbox / ".venv/Scripts/python.exe"
    (reference / "protected.txt").write_bytes(b"frozen")
    FULL.save(
        sandbox,
        FULL.STATE,
        {
            "reference_root": str(reference.resolve()),
            "sandbox_root": str(sandbox.resolve()),
            "source_revision": "fixture",
            "protected_files": {"protected.txt": FULL.sha(reference / "protected.txt")},
            "snapshots": {},
            "full_started": False,
        },
    )
    (sandbox / "outputs/tables").mkdir(parents=True)
    return workflow


def test_notebook_valid_syntax_and_safe_default():
    notebook = nbformat.read(
        ROOT / "notebooks/AI_Chip_Market_Intelligence_FULL.ipynb", as_version=4
    )
    nbformat.validate(notebook)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            ast.parse(cell.source)
            assert not cell.outputs and cell.execution_count is None
    sources = "\n".join(c.source for c in notebook.cells)
    assert 'MODE = "PREFLIGHT"' in sources
    assert "execute_full(authorize_full=AUTHORIZE_FULL" in sources
    assert "AUTHORIZE_FULL = False" in sources


def test_authentic_command_plan_and_order():
    inventory = FULL.inspect_commands(ROOT)
    names = {r["path"] for r in inventory}
    assert len([n for n in names if n.startswith("r/")]) == 5
    assert FULL.STEPS[0][1] == "python/01_data_preparation.py"
    assert FULL.STEPS[1][1] == "python/01_data_eda.py"
    assert FULL.STEPS[-2][1] == "python/05_lstm_gru.py"
    assert FULL.STEPS[-1] == ("evaluation", "python/06_evaluation.py", ())
    for stage in ("arima", "validation", "var", "garch"):
        commands = [r for r in FULL.STEPS if r[0] == stage]
        assert commands[-1][2] == ("--summarize",)
        assert any(r[1].endswith(".R") for r in commands[:-1])
    assert not any(
        f in ("--higher", "--vecm") for _, _, flags in FULL.STEPS for f in flags
    )


@pytest.mark.parametrize("nested", ["same", "child", "parent"])
def test_reference_isolation_rejects_overlap(tmp_path, nested):
    reference = tmp_path / "reference"
    sandbox = (
        reference
        if nested == "same"
        else reference / "child"
        if nested == "child"
        else tmp_path
    )
    with pytest.raises(FULL.ReproductionError, match="distinct"):
        FULL.isolated_roots(reference, sandbox)


@pytest.mark.parametrize("relative", ["../outside", "/outside"])
def test_write_path_rejects_escape(workspace, relative):
    with pytest.raises(FULL.ReproductionError):
        FULL.save(workspace.sandbox_root, relative, {"bad": True})


def test_write_path_rejects_reference_redirect(workspace):
    target = workspace.sandbox_root / "redirect"
    try:
        target.symlink_to(workspace.reference_root, target_is_directory=True)
    except OSError:
        if __import__("os").name != "nt":
            raise
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(target), str(workspace.reference_root)],
            check=True,
            capture_output=True,
        )
    with pytest.raises(FULL.ReproductionError, match="Redirected"):
        FULL.save(workspace.sandbox_root, "redirect/science.json", {})
    assert not (workspace.reference_root / "science.json").exists()


def test_snapshot_hashing_never_parses_holdout(tmp_path, monkeypatch):
    path = tmp_path / "market_test.csv"
    path.write_bytes(b"not even a CSV; hash integrity only")
    monkeypatch.setattr(FULL, "rows", lambda *_: pytest.fail("Holdout parsed"))
    expected = {"market_test.csv": FULL.sha(path)}
    assert FULL.require_snapshots(tmp_path, expected)[0]["status"] == "PASS"
    path.write_bytes(b"divergent")
    with pytest.raises(FULL.ReproductionError, match="missing/divergent"):
        FULL.require_snapshots(tmp_path, expected)
    path.unlink()
    assert FULL.snapshot_checks(tmp_path, expected)[0]["status"] == "MISSING"


def test_no_existing_directory_overwrite(workspace):
    with pytest.raises(FULL.ReproductionError, match="overwrite"):
        workspace.prepare()


def test_protected_reference_tampering_stops(workspace):
    assert workspace.verify_reference() == 1
    (workspace.reference_root / "protected.txt").write_bytes(b"changed")
    with pytest.raises(FULL.ReproductionError, match="Protected"):
        workspace.verify_reference()


def test_sandbox_owner_tampering_stops(workspace):
    state = workspace.state()
    state["reference_root"] = "wrong-root"
    FULL.save(workspace.sandbox_root, FULL.STATE, state)
    with pytest.raises(FULL.ReproductionError, match="ownership"):
        workspace.state()


@pytest.mark.parametrize(
    "name",
    [
        "outputs/tables/phase7_final_predictions.csv",
        "outputs/tables/phase7_runtime_audit.json",
        ".cache/phase7/protocol_gate.json",
    ],
)
def test_old_phase7_active_evidence_rejected(workspace, name):
    path = workspace.sandbox_root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("historical", encoding="utf8")
    with pytest.raises(FULL.ReproductionError, match="Old Phase 7"):
        workspace.assert_phase7_empty()


def test_archiving_only_sandbox_preserves_bytes(workspace, monkeypatch):
    state = workspace.state()
    state["full_started"] = True
    FULL.save(workspace.sandbox_root, FULL.STATE, state)
    monkeypatch.chdir(workspace.sandbox_root)
    path = workspace.sandbox_root / "outputs/tables/phase7_final_predictions.csv"
    path.write_bytes(b"historical predictions")
    expected = FULL.sha(path)
    records = workspace.archive_outputs()
    assert records == [
        {"path": "outputs/tables/phase7_final_predictions.csv", "sha256": expected}
    ]
    assert not path.exists()
    assert (
        FULL.sha(
            workspace.sandbox_root
            / ".cache/phase9c/historical_outputs/outputs/tables/phase7_final_predictions.csv"
        )
        == expected
    )
    workspace.assert_phase7_empty()
    assert workspace.verify_reference() == 1


def test_archiving_refused_in_preflight(workspace):
    with pytest.raises(FULL.ReproductionError, match="explicit FULL"):
        workspace.archive_outputs()


def test_phase7_cannot_prepare_before_training(workspace, monkeypatch):
    monkeypatch.setattr(
        workspace, "probe", lambda *_: pytest.fail("Command before training")
    )
    with pytest.raises(FULL.ReproductionError, match="genuine Phase 6"):
        workspace.prepare_phase7()


def test_full_needs_explicit_mode_and_sandbox_cwd(workspace, monkeypatch):
    monkeypatch.setattr(workspace, "preflight", lambda: pytest.fail("No implicit FULL"))
    with pytest.raises(FULL.ReproductionError, match="explicit"):
        workspace.execute_full()
    with pytest.raises(FULL.ReproductionError, match="cwd"):
        workspace.execute_full(authorize_full=True)


def test_failed_preflight_cannot_execute_commands(workspace, monkeypatch):
    monkeypatch.chdir(workspace.sandbox_root)
    monkeypatch.setattr(workspace, "preflight", lambda: {"status": "FAIL"})
    monkeypatch.setattr(
        workspace, "probe", lambda *_: pytest.fail("Scientific subprocess on FAIL")
    )
    with pytest.raises(FULL.ReproductionError, match="PASS preflight"):
        workspace.execute_full(authorize_full=True)


def test_preflight_executes_only_environment_probes(workspace, monkeypatch):
    monkeypatch.setattr(FULL, "check_protocols", lambda _: {})
    monkeypatch.setattr(FULL, "inspect_commands", lambda _: [])
    monkeypatch.setattr(FULL, "check_llm", lambda _: {"claims": 35})
    monkeypatch.setattr(workspace, "environment", lambda: {"python": "fixture"})
    monkeypatch.setattr(
        workspace, "archive_outputs", lambda: pytest.fail("PREFLIGHT archived science")
    )
    monkeypatch.setattr(
        workspace, "execute_full", lambda **_: pytest.fail("PREFLIGHT executed FULL")
    )
    result = workspace.preflight()
    assert result["status"] == "PASS"
    assert result["full_status"] == "PARTIAL"
    assert not result["estimation"] and not result["test_observations_parsed"]


def test_protocol_incoherence_stops_before_git(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "outputs/tables").mkdir(parents=True)
    for name in ("phase6_protocol.json", "phase7_final_evaluation_protocol.json"):
        original = json.loads((ROOT / "docs" / name).read_text(encoding="utf8"))
        if name == "phase6_protocol.json":
            original["seed"] = 43
        (tmp_path / "docs" / name).write_text(json.dumps(original), encoding="utf8")
    (tmp_path / FULL.SNAPSHOT_AUDIT).write_bytes(
        (ROOT / FULL.SNAPSHOT_AUDIT).read_bytes()
    )
    with pytest.raises(FULL.ReproductionError, match="Incoherent"):
        FULL.check_protocols(tmp_path)


def test_changed_neural_lock_cannot_reach_holdout(workspace):
    name = "outputs/tables/phase6_locked_lstm.csv"
    for root, epochs in ((workspace.reference_root, 38), (workspace.sandbox_root, 39)):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"configuration,lookback,units,dropout,median_best_epoch\nC,60,64,0.2,{epochs}\n",
            encoding="utf8",
        )
    with pytest.raises(FULL.ReproductionError, match="TRAIN lock differs"):
        workspace.verify_locks("neural")


def test_no_automatic_installation():
    tree = ast.parse(
        (ROOT / "python/09c_full_reproduction.py").read_text(encoding="utf8")
    )
    strings = [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]
    assert "install" not in strings
    assert "install.packages" not in "\n".join(strings)
    assert "--summarize" not in FULL.STEPS[-1][2]


@pytest.mark.parametrize(
    "arguments",
    [
        ["-c", "print('arbitrary command')"],
        ["python/04_garch.py"],
        ["python/05_lstm_gru.py"],
        ["python/06_evaluation.py"],
    ],
)
def test_closed_command_allowlist_in_preflight(workspace, monkeypatch, arguments):
    monkeypatch.setattr(
        FULL.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("Unapproved subprocess"),
    )
    with pytest.raises(FULL.ReproductionError, match="closed"):
        workspace.probe("unapproved", [workspace.python, *arguments])


@pytest.fixture
def committed_gate_workspace(tmp_path):
    directory = tmp_path / "gate-workspace"
    (directory / "docs").mkdir(parents=True)
    for name in (FULL.PROTOCOL, FULL.PROTOCOL_MD):
        (directory / name).write_bytes((ROOT / name).read_bytes())
    (directory / ".gitignore").write_text(".cache/\n", encoding="utf8")

    def command(*args):
        return subprocess.run(
            ["git", "-C", str(directory), *args], check=True, capture_output=True
        )

    command("init")
    command("add", ".")
    command(
        "-c",
        "user.name=Gate fixture",
        "-c",
        "user.email=fixture@localhost",
        "commit",
        "-m",
        "docs: predeclare final holdout evaluation protocol",
    )
    module_spec = importlib.util.spec_from_file_location(
        "authentic_evaluator_gate_test", ROOT / "python/06_evaluation.py"
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return directory, module


def test_authentic_verifier_creates_genuine_new_gate(committed_gate_workspace):
    directory, evaluator = committed_gate_workspace
    assert not (directory / ".cache/phase7/protocol_gate.json").exists()
    gate = evaluator.verify_protocol_commit(root=directory)
    assert (
        gate["working_tree_clean_verified"] and not gate["test_read_before_this_gate"]
    )
    assert gate["protocol_hashes"][FULL.PROTOCOL] == FULL.sha(directory / FULL.PROTOCOL)
    assert gate["verified_utc"]
    assert (
        json.loads(
            (directory / ".cache/phase7/protocol_gate.json").read_text(encoding="utf8")
        )
        == gate
    )
    assert not (directory / "data").exists()


def test_authentic_verifier_refuses_dirty_new_gate(committed_gate_workspace):
    directory, evaluator = committed_gate_workspace
    (directory / "untracked.txt").write_text("dirty", encoding="utf8")
    with pytest.raises(ValueError, match="clean working tree"):
        evaluator.verify_protocol_commit(root=directory)
    assert not (directory / ".cache/phase7/protocol_gate.json").exists()


def test_authentic_verifier_refuses_changed_protocol(committed_gate_workspace):
    directory, evaluator = committed_gate_workspace
    path = directory / FULL.PROTOCOL
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="predeclared"):
        evaluator.verify_protocol_commit(root=directory)


def test_real_reference_protocol_and_llm_contracts():
    assert (
        FULL.check_protocols(ROOT)["protocol_commit"]
        == "1e5ad76c6834f4e24fee825c894261597c94c917"
    )
    assert FULL.check_llm(ROOT)["claims"] == 35
