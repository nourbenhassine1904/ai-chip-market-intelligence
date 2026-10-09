"""Guarded Phase 9C orchestration. PREFLIGHT never fits or parses market observations.

FULL is an explicit, separate operation in an independently owned Git clone.
Scientific implementations and their CLI options are never modified here.
"""

import argparse
import ast
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = "v0.13.0-phase9b"
STATE = ".cache/phase9c/state.json"
PROTOCOL = "docs/phase7_final_evaluation_protocol.json"
PROTOCOL_MD = "docs/phase7_final_evaluation_protocol.md"
SNAPSHOT_AUDIT = "outputs/tables/phase9a_data_checksum_audit.csv"
LLM = "llm/responses/phase8_official_llm_response.md"
R_PACKAGES = ("forecast", "tseries", "FinTS", "vars", "urca", "rugarch")
PY_PACKAGES = (
    "pandas",
    "numpy",
    "matplotlib",
    "scipy",
    "statsmodels",
    "arch",
    "pmdarima",
    "yfinance",
    "scikit-learn",
    "tensorflow",
    "nbformat",
    "nbclient",
    "ipykernel",
)
STEPS = (
    ("preparation", "python/01_data_preparation.py", ()),
    ("eda", "python/01_data_eda.py", ()),
    ("arima", "python/02_arima.py", ()),
    ("arima", "r/02_arima.R", ()),
    ("arima", "python/02_arima.py", ("--compare-r",)),
    ("arima", "python/02_arima.py", ("--summarize",)),
    ("validation", "python/02b_arima_validation.py", ()),
    ("validation", "r/02b_arima_validation.R", ()),
    ("validation", "python/02b_arima_validation.py", ("--summarize",)),
    ("var", "python/03_var_vecm.py", ()),
    ("var", "r/03_var_vecm.R", ()),
    ("var", "python/03_var_vecm.py", ("--summarize",)),
    ("garch", "python/04_garch.py", ()),
    ("garch", "r/04_garch.R", ()),
    ("garch", "python/04_garch.py", ("--summarize",)),
    ("neural", "python/05_lstm_gru.py", ()),
    ("evaluation", "python/06_evaluation.py", ()),
)


class ReproductionError(RuntimeError):
    """Visible stop; never substitute historical results for a failed new run."""


PYTHON_PROBE = (
    "import sys,json,platform,importlib.metadata as m; import tensorflow as tf; "
    "print(json.dumps({'python':platform.python_version(),'prefix':sys.prefix,"
    "'packages':{n:m.version(n) for n in " + repr(PY_PACKAGES) + "},"
    "'devices':[d.device_type for d in tf.config.list_physical_devices()]}))"
)
R_PROBE = "p <- c(" + ",".join('"' + n + '"' for n in R_PACKAGES) + "); "
R_PROBE += "cat(R.version.string, '\\n'); for (x in p) { if (!requireNamespace(x, quietly=TRUE)) stop(paste('Missing',x)); cat(x, as.character(packageVersion(x)), '\\n') }"
R_PARSE = "for (f in list.files('r', pattern='[.]R$', full.names=TRUE)) { parse(f); cat(f, '\\n') }"
GATE_PROBE = (
    "import importlib.util,json; from pathlib import Path; "
    "s=importlib.util.spec_from_file_location('evaluation','python/06_evaluation.py'); "
    "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
    "print(json.dumps(m.verify_protocol_commit(root=Path.cwd())))"
)
CHECKPOINT_ADD = [
    "git",
    "add",
    "--",
    "outputs",
    "docs",
    "python/09c_full_reproduction.py",
    "notebooks/AI_Chip_Market_Intelligence_FULL.ipynb",
]
CHECKPOINT_COMMIT = [
    "git",
    "-c",
    "user.name=Reproduction workspace",
    "-c",
    "user.email=reproduction@localhost",
    "commit",
    "-m",
    "chore: checkpoint isolated TRAIN reproduction before TEST",
]


def sha(path):
    """Hash bytes only; in particular never parse TEST observations in PREFLIGHT."""
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], stderr=subprocess.PIPE
    )


def isolated_roots(reference, sandbox):
    reference, sandbox = Path(reference).resolve(), Path(sandbox).resolve()
    if (
        reference == sandbox
        or reference in sandbox.parents
        or sandbox in reference.parents
    ):
        raise ReproductionError(
            "Reference and sandbox must be distinct, non-nested roots"
        )
    return reference, sandbox


def contained(root, relative):
    """Reject traversal, symlinks and Windows junctions redirecting a destination."""
    root = Path(root).resolve()
    path = root / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ReproductionError("Absolute/traversing destination forbidden")
    if path.resolve() != path.absolute() or (
        path.resolve() != root and root not in path.resolve().parents
    ):
        raise ReproductionError("Redirected destination forbidden")
    return path


def save(root, relative, data):
    path = contained(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf8"
    )


def snapshot_expectations(reference):
    records = rows(reference / SNAPSHOT_AUDIT)
    expected_paths = {f"data/raw/{a}_raw.csv" for a in ("NVDA", "AMD", "SOXX")}
    expected_paths |= {
        f"data/processed/market_{n}.csv"
        for n in ("aligned", "features", "train", "test")
    }
    if len(records) != 7 or {r["path"] for r in records} != expected_paths:
        raise ReproductionError("Historical seven-snapshot manifest is incoherent")
    return {r["path"]: r["expected_sha256"] for r in records}


def snapshot_checks(root, expected):
    result = []
    for relative, digest in expected.items():
        path = contained(root, relative)
        actual = sha(path) if path.is_file() else "MISSING"
        result.append(
            {
                "path": relative,
                "expected_sha256": digest,
                "actual_sha256": actual,
                "status": "PASS"
                if actual == digest
                else "MISSING"
                if actual == "MISSING"
                else "DIVERGENT",
            }
        )
    return result


def require_snapshots(root, expected):
    result = snapshot_checks(root, expected)
    if any(r["status"] != "PASS" for r in result):
        raise ReproductionError(
            "STOP strict reproduction: missing/divergent historical snapshot"
        )
    return result


def inspect_commands(root):
    """Parse all Python sources without importing them; inspect all R sources."""
    inventory = []
    for folder, suffix in (("python", ".py"), ("r", ".R")):
        for path in sorted((root / folder).glob("*" + suffix)):
            text = path.read_text(encoding="utf8")
            tree = ast.parse(text, filename=str(path)) if suffix == ".py" else None
            options = set()
            if tree:
                for node in ast.walk(tree):
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "add_argument"
                    ):
                        options.update(
                            a.value
                            for a in node.args
                            if isinstance(a, ast.Constant)
                            and isinstance(a.value, str)
                            and a.value.startswith("--")
                        )
            inventory.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": sha(path),
                    "lines": len(text.splitlines()),
                    "options": sorted(options),
                    "placeholder": path.name == "01_data_eda.R",
                }
            )
    by_name = {r["path"]: r for r in inventory}
    for _, name, flags in STEPS + (
        ("acquisition", "python/00_data_acquisition.py", ()),
    ):
        if name not in by_name or any(f not in by_name[name]["options"] for f in flags):
            raise ReproductionError(
                "Missing authentic script or invented CLI option: " + name
            )
    evaluation = (root / "python/06_evaluation.py").read_text(encoding="utf8")
    tree = ast.parse(evaluation)
    run = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run"
    )
    calls = [
        n.func.id
        for n in ast.walk(run)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    ]
    if (
        "verify_protocol_commit" not in evaluation
        or "models_ready=True" not in evaluation
        or "prepare_neural" not in evaluation
    ):
        raise ReproductionError("Phase 7 freeze/gate contract missing")
    if not all(
        name in calls
        for name in (
            "verify_protocol_commit",
            "prepare_neural",
            "read_observations",
            "freeze_predictions",
        )
    ):
        raise ReproductionError("Phase 7 authentic orchestration incomplete")
    return inventory


def check_protocols(root):
    p6 = json.loads((root / "docs/phase6_protocol.json").read_text(encoding="utf8"))
    p7 = json.loads((root / PROTOCOL).read_text(encoding="utf8"))
    expected = snapshot_expectations(root)
    if (
        p6["seed"] != 42
        or p6["framework_version"] != "2.21.0"
        or p6["device"] != "CPU"
        or p6["architectures"] != ["LSTM", "GRU"]
        or p6["fold_cut_tenths"] != [7, 8, 9, 10]
        or list(p6["configurations"]) != ["A", "B", "C"]
        or p6["shuffle"]
        or p6["train_sha256"] != expected["data/processed/market_train.csv"]
        or p7["train_sha256"] != p6["train_sha256"]
        or p7["historical_test_sha256"] != expected["data/processed/market_test.csv"]
        or p7["neural"]["seed"] != 42
        or p7["neural"]["LSTM_epochs"] != 38
        or p7["neural"]["GRU_epochs"] != 36
        or p7["retuning"]
        or p7["refit_after_test_access"]
        or p7["recommendation"]["fallback"] != "Naive"
    ):
        raise ReproductionError("Incoherent original protocols")
    commits = (
        git(
            root,
            "log",
            "--format=%H",
            "--fixed-strings",
            "--grep=" + p7["protocol_commit_subject"],
        )
        .decode()
        .splitlines()
    )
    if not commits:
        raise ReproductionError("Missing predeclared protocol history")
    commit = commits[-1]
    for name in (PROTOCOL, PROTOCOL_MD):
        if (root / name).read_bytes() != git(root, "show", f"{commit}:{name}"):
            raise ReproductionError(
                "Protocol differs from its original predeclared commit"
            )
    return {
        "protocol_commit": commit,
        "phase6_sha256": sha(root / "docs/phase6_protocol.json"),
        "phase7_sha256": sha(root / PROTOCOL),
        "phase7_md_sha256": sha(root / PROTOCOL_MD),
    }


def check_llm(root):
    if (
        sha(root / LLM)
        != "eecb0de3e0dd8e152e93db70ff71f9dad87024b7b2f3e1bee1ede05225f6f3b4"
    ):
        raise ReproductionError("Official LLM response changed")
    claims = rows(root / "llm/human_analysis/phase8_hallucination_audit.csv")
    if (
        len(claims) != 35
        or len({r["claim_id"] for r in claims}) != 35
        or any(
            r["issue_type"] != "supported" or r["supported_by_project"] != "TRUE"
            for r in claims
        )
    ):
        raise ReproductionError("Historical 35-claim LLM audit inconsistent")
    response = (root / LLM).read_text(encoding="utf8")
    for claim in claims:
        if " ".join(claim["llm_claim"].split()) not in " ".join(response.split()):
            raise ReproductionError(
                "Audit claim absent from historical response: " + claim["claim_id"]
            )
        for source in claim["source"].split("; "):
            if not contained(root, source.split("#", 1)[0]).is_file():
                raise ReproductionError("Historical LLM source missing: " + source)
    return {
        "response_sha256": sha(root / LLM),
        "claims": 35,
        "scope": "historical documentary audit, no new generation",
    }


class Workflow:
    def __init__(
        self, reference_root, sandbox_root, source_revision=BASE, rscript=None
    ):
        self.reference_root, self.sandbox_root = isolated_roots(
            reference_root, sandbox_root
        )
        self.source_revision = (
            git(self.reference_root, "rev-parse", source_revision + "^{commit}")
            .decode()
            .strip()
        )
        self.rscript = str(
            Path(rscript or shutil.which("Rscript") or "Rscript").absolute()
        )
        self.python = (
            self.sandbox_root
            / ".venv"
            / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )

    def state(self):
        path = contained(self.sandbox_root, STATE)
        state = json.loads(path.read_text(encoding="utf8"))
        if any(
            state[k] != str(v)
            for k, v in (
                ("reference_root", self.reference_root),
                ("sandbox_root", self.sandbox_root),
                ("source_revision", self.source_revision),
            )
        ):
            raise ReproductionError("Sandbox ownership/revision mismatch")
        return state

    def verify_reference(self):
        state = self.state()
        protected = state["protected_files"]
        for name, digest in protected.items():
            if sha(contained(self.reference_root, name)) != digest:
                raise ReproductionError("Protected reference changed: " + name)
        require_snapshots(self.reference_root, state["snapshots"])
        return len(protected)

    def command_env(self):
        env = os.environ.copy()
        env.update(
            PYTHONDONTWRITEBYTECODE="1",
            PYTHONNOUSERSITE="1",
            CUDA_VISIBLE_DEVICES="-1",
            MPLCONFIGDIR=str(contained(self.sandbox_root, ".cache/matplotlib")),
            R_LIBS_USER=str(contained(self.sandbox_root, ".cache/R-library")),
            TMP=str(contained(self.sandbox_root, ".cache/phase9c/tmp")),
            TEMP=str(contained(self.sandbox_root, ".cache/phase9c/tmp")),
            IPYTHONDIR=str(contained(self.sandbox_root, ".cache/phase9c/ipython")),
            JUPYTER_RUNTIME_DIR=str(
                contained(self.sandbox_root, ".cache/phase9c/jupyter")
            ),
        )
        env.pop("PYTHONPATH", None)
        env.pop("R_LIBS", None)
        for name in (
            ".cache/phase9c/tmp",
            ".cache/phase9c/ipython",
            ".cache/phase9c/jupyter",
            ".cache/matplotlib",
        ):
            contained(self.sandbox_root, name).mkdir(parents=True, exist_ok=True)
        return env

    def probe(self, label, command, timeout=180):
        state = self.state()
        command = list(map(str, command))
        environment_commands = [
            [str(self.python), "-c", PYTHON_PROBE],
            [str(self.python), "-m", "pip", "check"],
            [self.rscript, "-e", R_PROBE],
            [self.rscript, "-e", R_PARSE],
        ]
        scientific_commands = [
            [self.rscript if name.endswith(".R") else str(self.python), name, *flags]
            for _, name, flags in STEPS
        ]
        scientific_commands.append([str(self.python), "python/00_data_acquisition.py"])
        phase7_commands = [
            CHECKPOINT_ADD,
            CHECKPOINT_COMMIT,
            [str(self.python), "-c", GATE_PROBE],
        ]
        allowed = (
            command in environment_commands
            or state["full_started"]
            and command in scientific_commands
            or state.get("phase6_completed")
            and command in phase7_commands
        )
        if not allowed:
            raise ReproductionError(
                "Command outside the closed orchestration allowlist"
            )
        if command in scientific_commands:
            contained(self.sandbox_root, command[1])
        if any(
            str(self.reference_root).casefold() in value.casefold() for value in command
        ):
            raise ReproductionError("Command references protected reference_root")
        started = time.perf_counter()
        result = subprocess.run(
            list(map(str, command)),
            cwd=self.sandbox_root,
            env=self.command_env(),
            capture_output=True,
            text=True,
            encoding="utf8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        record = {
            "command": list(map(str, command)),
            "cwd": str(self.sandbox_root),
            "exit_code": result.returncode,
            "elapsed_seconds": time.perf_counter() - started,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        save(self.sandbox_root, f".cache/phase9c/logs/{label}.json", record)
        if result.returncode:
            raise ReproductionError(
                f"Command failed ({label}): {result.stderr[-2000:]}"
            )
        return result.stdout

    def prepare(self, *, copy_environment=False):
        if self.sandbox_root.exists():
            raise ReproductionError("Refuse to overwrite an existing sandbox")
        expected = snapshot_expectations(self.reference_root)
        allowed_new = {
            "python/09c_full_reproduction.py",
            "tests/test_full_reproduction.py",
            "notebooks/AI_Chip_Market_Intelligence_FULL.ipynb",
            "docs/phase9c_full_reproduction.md",
            "docs/phase9c_preflight_audit.md",
        }
        changed = set(
            git(self.reference_root, "diff", "--name-only", self.source_revision, "--")
            .decode()
            .splitlines()
        )
        if changed - allowed_new:
            raise ReproductionError(
                "Tracked reference differs from selected source revision"
            )
        require_snapshots(self.reference_root, expected)
        check_protocols(self.reference_root)
        frozen = json.loads(
            (
                self.reference_root / "docs/phase9a_frozen_artifacts_manifest.json"
            ).read_text(encoding="utf8")
        )["artifacts"]
        for r in frozen:
            if sha(self.reference_root / r["path"]) not in (
                r["sha256"],
                r["git_blob_sha256"],
            ):
                raise ReproductionError(
                    "Frozen scientific manifest mismatch: " + r["path"]
                )
        names = (
            git(
                self.reference_root,
                "ls-tree",
                "-r",
                "--name-only",
                "-z",
                self.source_revision,
            )
            .decode()
            .split("\0")
        )
        protected = {n: sha(contained(self.reference_root, n)) for n in names if n}
        subprocess.run(
            [
                "git",
                "clone",
                "--no-local",
                "--no-hardlinks",
                str(self.reference_root),
                str(self.sandbox_root),
            ],
            check=True,
            capture_output=True,
        )
        git(self.sandbox_root, "checkout", "--detach", self.source_revision)
        cache = contained(self.sandbox_root, ".cache/phase9c")
        cache.mkdir(parents=True)
        (cache / ".gitignore").write_text("*\n", encoding="utf8")
        state = {
            "reference_root": str(self.reference_root),
            "sandbox_root": str(self.sandbox_root),
            "source_revision": self.source_revision,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "protected_files": protected,
            "snapshots": expected,
            "full_started": False,
        }
        save(self.sandbox_root, STATE, state)
        for name in expected:
            destination = contained(self.sandbox_root, name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(contained(self.reference_root, name), destination)
        # Copy only the new orchestrator/notebook; no model cache or old gate is copied.
        for name in (
            "python/09c_full_reproduction.py",
            "notebooks/AI_Chip_Market_Intelligence_FULL.ipynb",
            "docs/phase9c_full_reproduction.md",
            "docs/phase9c_preflight_audit.md",
        ):
            if contained(self.reference_root, name).is_file():
                shutil.copyfile(
                    contained(self.reference_root, name),
                    contained(self.sandbox_root, name),
                )
        if copy_environment:
            self.copy_environment()
        self.verify_reference()
        return state

    def copy_environment(self):
        """Explicit copy of installed packages into a new venv; no pip/network/install."""
        self.state()
        if self.python.parent.parent.exists():
            raise ReproductionError("Refuse to overwrite an existing environment")
        source = contained(
            self.reference_root,
            ".venv/Lib/site-packages"
            if os.name == "nt"
            else f".venv/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages",
        )
        if not source.is_dir():
            raise ReproductionError(
                "Installed reference environment unavailable; prepare packages manually"
            )
        subprocess.run(
            [sys.executable, "-m", "venv", str(self.python.parent.parent)],
            check=True,
            env=self.command_env(),
            cwd=self.sandbox_root,
        )
        destination = self.python.parent.parent / source.relative_to(
            self.reference_root / ".venv"
        )
        shutil.copytree(
            source,
            destination,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        for path in destination.glob("*.pth"):
            if (
                str(self.reference_root).casefold()
                in path.read_text(encoding="utf8").casefold()
            ):
                raise ReproductionError(
                    "Environment .pth redirects to the reference checkout"
                )
        library = contained(self.reference_root, ".cache/R-library")
        if library.is_dir():
            shutil.copytree(library, contained(self.sandbox_root, ".cache/R-library"))
        save(
            self.sandbox_root,
            ".cache/phase9c/environment_copy.json",
            {
                "route": "explicit local package copy, not a fresh-machine installation",
                "source_python": sys.executable,
                "destination_python": str(self.python),
                "network": False,
            },
        )

    def environment(self):
        if not self.python.is_file() or not Path(self.rscript).is_file():
            raise ReproductionError(
                "Missing isolated Python or Rscript; install manually, no automatic installation"
            )
        info = json.loads(
            self.probe(
                "python_environment", [self.python, "-c", PYTHON_PROBE]
            ).splitlines()[-1]
        )
        if (
            not info["python"].startswith("3.12.")
            or info["packages"]["tensorflow"] != "2.21.0"
            or "CPU" not in info["devices"]
        ):
            raise ReproductionError("Python 3.12 / TensorFlow 2.21.0 / CPU required")
        if Path(info["prefix"]).resolve() != self.python.parent.parent.resolve():
            raise ReproductionError("Interpreter escapes the isolated environment")
        self.probe("pip_check", [self.python, "-m", "pip", "check"])
        info["r"] = self.probe("r_environment", [self.rscript, "-e", R_PROBE])
        info["r_parsed_sources"] = self.probe("r_parse", [self.rscript, "-e", R_PARSE])
        return info

    def copy_r_library(self, source_library):
        """Explicit dependency restoration into this owned sandbox, never installation."""
        if self.state()["full_started"]:
            raise ReproductionError("Cannot change environment after FULL starts")
        source = Path(source_library).resolve()
        destination = contained(self.sandbox_root, ".cache/R-library")
        if (
            not source.is_dir()
            or source == destination
            or destination in source.parents
            or source in destination.parents
        ):
            raise ReproductionError("Invalid distinct R library source")
        shutil.copytree(source, destination, dirs_exist_ok=True)
        save(
            self.sandbox_root,
            ".cache/phase9c/r_library_copy.json",
            {
                "source": str(source),
                "destination": str(destination),
                "route": "explicit installed-package copy",
                "network": False,
            },
        )

    def preflight(self):
        state = self.state()
        audit = {
            "mode": "PREFLIGHT",
            "status": "FAIL",
            "full_status": "PARTIAL",
            "estimation": False,
            "test_observations_parsed": False,
            "snapshot_integrity_hashing_only": True,
            "reference_root": str(self.reference_root),
            "sandbox_root": str(self.sandbox_root),
            "source_revision": self.source_revision,
        }
        try:
            audit["protected_file_count"] = self.verify_reference()
            audit["snapshots_reference"] = snapshot_checks(
                self.reference_root, state["snapshots"]
            )
            audit["snapshots_sandbox"] = snapshot_checks(
                self.sandbox_root, state["snapshots"]
            )
            require_snapshots(self.reference_root, state["snapshots"])
            require_snapshots(self.sandbox_root, state["snapshots"])
            audit["protocols"] = check_protocols(self.sandbox_root)
            inventory = inspect_commands(self.sandbox_root)
            for r in inventory:
                if (
                    r["path"] in state["protected_files"]
                    and sha(self.reference_root / r["path"]) != r["sha256"]
                ):
                    raise ReproductionError(
                        "Scientific source differs in sandbox: " + r["path"]
                    )
            for name in state["protected_files"]:
                if (
                    name.startswith("docs/")
                    and any(
                        token in name
                        for token in (
                            "protocol",
                            "selection_rule",
                            "validation_candidates",
                        )
                    )
                    and sha(contained(self.sandbox_root, name))
                    != sha(contained(self.reference_root, name))
                ):
                    raise ReproductionError("Sandbox protocol/rule changed: " + name)
            save(self.sandbox_root, ".cache/phase9c/source_inventory.json", inventory)
            audit["environment"] = self.environment()
            audit["llm"] = check_llm(self.sandbox_root)
            # Historical forecasts are allowed only before FULL's archival operation.
            audit["phase7_historical_outputs_present"] = (
                self.sandbox_root / "outputs/tables/phase7_final_predictions.csv"
            ).exists()
            audit["phase7_action_required"] = (
                "archive copied historical outputs; checkpoint TRAIN results; genuine fresh gate"
            )
            if state["full_started"]:
                raise ReproductionError(
                    "This sandbox already started FULL; select a new run, no silent resume"
                )
            self.verify_reference()
            audit["status"] = "PASS"
        except (
            ReproductionError,
            OSError,
            ValueError,
            subprocess.SubprocessError,
            KeyError,
        ) as exc:
            audit["error"] = f"{type(exc).__name__}: {exc}"
        save(self.sandbox_root, ".cache/phase9c/preflight.json", audit)
        return audit

    def archive_outputs(self):
        """FULL only: preserve copied outputs outside active paths, never touch reference."""
        if (
            not self.state()["full_started"]
            or Path.cwd().resolve() != self.sandbox_root
        ):
            raise ReproductionError("Archival requires explicit FULL in sandbox_root")
        destination = contained(self.sandbox_root, ".cache/phase9c/historical_outputs")
        if destination.exists():
            raise ReproductionError("Historical archive already exists")
        records = []
        tables = contained(self.sandbox_root, "outputs/tables")
        paths = [
            p
            for p in tables.iterdir()
            if p.is_file()
            and any(p.name.startswith(f"phase{n}_") for n in (3, "3b", 4, 5, 6, 7))
        ]
        paths += [
            p
            for n in (3, "3b", 4, 5, 6, 7)
            for p in contained(self.sandbox_root, f"outputs/figures/phase{n}").rglob(
                "*"
            )
            if p.is_file()
        ]
        for path in paths:
            relative = path.relative_to(self.sandbox_root).as_posix()
            path = contained(self.sandbox_root, relative)
            target = contained(
                self.sandbox_root, ".cache/phase9c/historical_outputs/" + relative
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            digest = sha(path)
            shutil.move(str(path), target)
            if sha(target) != digest:
                raise ReproductionError("Archive byte mismatch")
            records.append({"path": relative, "sha256": digest})
        save(
            self.sandbox_root,
            ".cache/phase9c/historical_outputs/manifest.json",
            records,
        )
        self.verify_reference()
        return records

    def assert_phase7_empty(self):
        self.state()
        if list(contained(self.sandbox_root, "outputs/tables").glob("phase7_*")):
            raise ReproductionError("Old Phase 7 outputs present in active area")
        cache = contained(self.sandbox_root, ".cache/phase7")
        if cache.exists() and any(cache.iterdir()):
            raise ReproductionError("Old Phase 7 cache/gate present")

    def verify_locks(self, stage):
        specifications = {
            "validation": [
                ("phase3b_locked_arima_model.csv", ("model", "order", "drift"))
            ],
            "var": [
                (
                    "phase4_r_python_summary.csv",
                    ("selected_lag", "johansen_rank", "vecm_justified"),
                )
            ],
            "garch": [
                (
                    "phase5_locked_garch_model.csv",
                    ("locked_garch_specification", "distribution", "p", "q"),
                )
            ],
            "neural": [
                (
                    f"phase6_locked_{a}.csv",
                    (
                        "configuration",
                        "lookback",
                        "units",
                        "dropout",
                        "median_best_epoch",
                    ),
                )
                for a in ("lstm", "gru")
            ],
        }
        for name, fields in specifications.get(stage, []):
            historical = rows(self.reference_root / "outputs/tables" / name)
            actual = rows(contained(self.sandbox_root, "outputs/tables/" + name))

            def projected(records, fields=fields):
                # Numeric strings 38 and 38.0 describe the same fixed epoch.
                return [
                    {
                        f: float(r[f])
                        if f
                        in (
                            "lookback",
                            "units",
                            "dropout",
                            "median_best_epoch",
                            "selected_lag",
                            "johansen_rank",
                            "p",
                            "q",
                        )
                        else r[f]
                        for f in fields
                    }
                    for r in records
                ]

            if projected(actual) != projected(historical):
                raise ReproductionError("STOP: regenerated TRAIN lock differs: " + name)

    def prepare_phase7(self):
        if not self.state().get("phase6_completed"):
            raise ReproductionError(
                "Phase 7 forbidden before genuine Phase 6 completion"
            )
        self.assert_phase7_empty()
        self.verify_locks("neural")
        check_protocols(self.sandbox_root)
        # Authentic verifier: no custom gate JSON and no TEST/model call.
        self.probe("checkpoint_add", CHECKPOINT_ADD)
        self.probe("checkpoint_commit", CHECKPOINT_COMMIT)
        if git(self.sandbox_root, "status", "--porcelain").strip():
            raise ReproductionError("Phase 7 requires a clean checkpoint")
        gate = json.loads(
            self.probe(
                "fresh_protocol_gate", [self.python, "-c", GATE_PROBE]
            ).splitlines()[-1]
        )
        if (
            not gate["working_tree_clean_verified"]
            or gate["test_read_before_this_gate"]
        ):
            raise ReproductionError("Invalid genuine pre-access gate")
        save(self.sandbox_root, ".cache/phase9c/fresh_gate_evidence.json", gate)
        return gate

    def execute_full(self, *, authorize_full=False, controlled_download=False):
        if not authorize_full or Path.cwd().resolve() != self.sandbox_root:
            raise ReproductionError(
                "FULL needs explicit authorization and cwd=sandbox_root"
            )
        audit = self.preflight()
        if audit["status"] != "PASS":
            raise ReproductionError("FULL requires a fresh PASS preflight")
        state = self.state()
        state["full_started"] = True
        save(self.sandbox_root, STATE, state)
        try:
            self.archive_outputs()
            self.assert_phase7_empty()
            if controlled_download:
                self.probe(
                    "acquisition_download",
                    [self.python, "python/00_data_acquisition.py"],
                    timeout=None,
                )
                require_snapshots(
                    self.sandbox_root,
                    {
                        n: h
                        for n, h in state["snapshots"].items()
                        if n.startswith("data/raw/")
                    },
                )
            else:
                save(
                    self.sandbox_root,
                    ".cache/phase9c/acquisition_restore.json",
                    {
                        "route": "original snapshots, no Yahoo download; historical acquisition retained",
                        "snapshots": require_snapshots(
                            self.sandbox_root, state["snapshots"]
                        ),
                    },
                )
            for index, (stage, script, flags) in enumerate(STEPS):
                if stage == "evaluation":
                    self.prepare_phase7()
                self.probe(
                    f"{index:02d}_{stage}_{Path(script).stem}_{'_'.join(flags)}",
                    [
                        self.rscript if script.endswith(".R") else self.python,
                        script,
                        *flags,
                    ],
                    timeout=None,
                )
                if index == 0:
                    require_snapshots(
                        self.sandbox_root,
                        {
                            n: h
                            for n, h in state["snapshots"].items()
                            if "raw/" in n or "aligned" in n
                        },
                    )
                if stage == "eda":
                    require_snapshots(self.sandbox_root, state["snapshots"])
                if index == len(STEPS) - 1 or STEPS[index + 1][0] != stage:
                    self.verify_locks(stage)
                if stage == "neural":
                    training = rows(
                        contained(
                            self.sandbox_root, "outputs/tables/phase6_training_runs.csv"
                        )
                    )
                    refits = rows(
                        contained(
                            self.sandbox_root,
                            "outputs/tables/phase6_full_train_refits.csv",
                        )
                    )
                    if (
                        len(training) != 18
                        or len(refits) != 2
                        or any(r["status"] != "PASS" for r in training + refits)
                    ):
                        raise ReproductionError(
                            "Incomplete authentic Phase 6 training/refits"
                        )
                    state["phase6_completed"] = True
                    save(self.sandbox_root, STATE, state)
                self.verify_reference()
            check_llm(self.sandbox_root)
            result = self.compare_outputs()
            save(self.sandbox_root, ".cache/phase9c/full_result.json", result)
            return result
        except Exception as exc:
            save(
                self.sandbox_root,
                ".cache/phase9c/full_failure.json",
                {
                    "status": "STOP",
                    "full_compliance": "PARTIAL",
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )
            raise
        finally:
            self.verify_reference()

    def compare_outputs(self):
        """Report byte/numeric differences; never bless a different realization."""
        comparisons = []
        archive = contained(
            self.sandbox_root, ".cache/phase9c/historical_outputs/manifest.json"
        )
        for record in json.loads(archive.read_text(encoding="utf8")):
            path = contained(self.sandbox_root, record["path"])
            actual = sha(path) if path.is_file() else "MISSING"
            comparisons.append(
                {
                    "path": record["path"],
                    "historical_sha256": record["sha256"],
                    "new_sha256": actual,
                    "identical_bytes": actual == record["sha256"],
                }
            )
        metrics_path = contained(
            self.sandbox_root, "outputs/tables/phase7_final_metrics.csv"
        )
        historical = rows(
            self.reference_root / "outputs/tables/phase7_final_metrics.csv"
        )
        new = rows(metrics_path)
        numeric = []
        old = {(r["model"], r["horizon"]): r for r in historical}
        for r in new:
            key = r["model"], r["horizon"]
            for metric in ("MSE", "RMSE", "MAE", "MAPE"):
                difference = float(r[metric]) - float(old[key][metric])
                numeric.append(
                    {
                        "model": key[0],
                        "horizon": key[1],
                        "metric": metric,
                        "difference": difference,
                        "within_descriptive_tolerance": abs(difference) <= 1e-6,
                    }
                )
        runtime = json.loads(
            contained(
                self.sandbox_root, "outputs/tables/phase7_runtime_audit.json"
            ).read_text(encoding="utf8")
        )
        if not all(runtime["frozen"].values()):
            raise ReproductionError("New runtime reports mutable parameters")
        fit_log = rows(
            contained(self.sandbox_root, "outputs/tables/phase7_model_fit_log.csv")
        )
        return {
            "status": "PIPELINE_EXECUTED",
            "full_compliance": "PARTIAL_PENDING_CLEAN_MACHINE_REVIEW",
            "byte_comparisons": comparisons,
            "metric_differences": numeric,
            "descriptive_absolute_tolerance": 1e-6,
            "neural_provenance": [
                r for r in fit_log if r["model"] in ("LSTM C", "GRU C")
            ],
            "reference_protected_files": self.verify_reference(),
            "official_recommendation": "Naive unchanged",
        }

    def execute_preflight_notebook(self):
        """Run canonical safe-default notebook with an ephemeral isolated kernel."""
        import nbformat
        from jupyter_client import KernelManager
        from jupyter_client.kernelspec import KernelSpecManager
        from nbclient import NotebookClient

        self.state()
        self.verify_reference()
        source = contained(
            self.reference_root, "notebooks/AI_Chip_Market_Intelligence_FULL.ipynb"
        )
        notebook = nbformat.read(source, as_version=4)
        nbformat.validate(notebook)
        code_cells = [c for c in notebook.cells if c.cell_type == "code"]
        trees = [ast.parse(c.source) for c in code_cells]
        defaults = {
            n.targets[0].id: n.value.value
            for n in trees[0].body
            if isinstance(n, ast.Assign)
            and isinstance(n.targets[0], ast.Name)
            and isinstance(n.value, ast.Constant)
        }
        if defaults.get("MODE") != "PREFLIGHT" or any(
            defaults.get(k) is not False
            for k in (
                "AUTHORIZE_FULL",
                "PREPARE",
                "COPY_ENVIRONMENT",
                "CONTROLLED_DOWNLOAD",
            )
        ):
            raise ReproductionError("Notebook must retain safe PREFLIGHT defaults")
        kernel_root = contained(self.sandbox_root, ".cache/phase9c/kernels")
        environment = self.command_env()
        kernel_environment = {
            k: environment[k]
            for k in (
                "PYTHONDONTWRITEBYTECODE",
                "PYTHONNOUSERSITE",
                "CUDA_VISIBLE_DEVICES",
                "MPLCONFIGDIR",
                "R_LIBS_USER",
                "TMP",
                "TEMP",
                "IPYTHONDIR",
                "JUPYTER_RUNTIME_DIR",
            )
        }
        kernel_environment.update(
            AI_CHIP_REFERENCE_ROOT=str(self.reference_root),
            AI_CHIP_SANDBOX_ROOT=str(self.sandbox_root),
            AI_CHIP_RSCRIPT=self.rscript,
        )
        save(
            self.sandbox_root,
            ".cache/phase9c/kernels/phase9c/kernel.json",
            {
                "argv": [
                    str(self.python),
                    "-m",
                    "ipykernel_launcher",
                    "-f",
                    "{connection_file}",
                ],
                "display_name": "Phase 9C isolated PREFLIGHT",
                "language": "python",
                "env": kernel_environment,
            },
        )
        manager = KernelManager(
            kernel_name="phase9c",
            connection_file=str(
                contained(self.sandbox_root, ".cache/phase9c/kernel_connection.json")
            ),
            kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernel_root)]),
        )
        client = NotebookClient(
            notebook,
            timeout=300,
            km=manager,
            allow_errors=False,
            resources={"metadata": {"path": str(self.sandbox_root)}},
        )
        client.execute(cleanup_kc=True)
        if manager.has_kernel or any(c.execution_count is None for c in code_cells):
            raise ReproductionError("Notebook kernel cleanup/execution incomplete")
        destination = contained(
            self.sandbox_root,
            ".cache/phase9c/AI_Chip_Market_Intelligence_FULL.preflight.ipynb",
        )
        nbformat.write(notebook, destination)
        evidence = {
            "status": "PASS",
            "mode": "PREFLIGHT",
            "code_cells": len(code_cells),
            "kernel_executable": str(self.python),
            "kernel_shutdown": True,
            "full_executed": False,
            "source_notebook_sha256": sha(source),
            "orchestrator_sha256": sha(Path(__file__)),
            "protected_files_unchanged": self.verify_reference(),
            "executed_notebook": str(destination),
        }
        save(self.sandbox_root, ".cache/phase9c/notebook_execution.json", evidence)
        return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-root", required=True)
    parser.add_argument("--sandbox-root", required=True)
    parser.add_argument("--source-revision", default=BASE)
    parser.add_argument("--rscript", default=shutil.which("Rscript"))
    parser.add_argument("--mode", choices=("PREFLIGHT", "FULL"), default="PREFLIGHT")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--copy-environment", action="store_true")
    parser.add_argument(
        "--copy-r-library",
        help="Explicit installed R library source; copied only in PREFLIGHT",
    )
    parser.add_argument("--authorize-full", action="store_true")
    parser.add_argument(
        "--execute-notebook",
        action="store_true",
        help="Validate the safe-default notebook in PREFLIGHT only",
    )
    parser.add_argument("--controlled-download", action="store_true")
    args = parser.parse_args()
    workflow = Workflow(
        args.reference_root, args.sandbox_root, args.source_revision, args.rscript
    )
    if args.copy_environment and not args.prepare:
        parser.error("--copy-environment requires --prepare")
    if args.mode == "PREFLIGHT" and (args.authorize_full or args.controlled_download):
        parser.error("PREFLIGHT cannot request scientific execution or downloading")
    if args.execute_notebook and args.mode != "PREFLIGHT":
        parser.error("Notebook validation is PREFLIGHT only")
    if args.prepare:
        if args.mode != "PREFLIGHT":
            parser.error("Prepare separately in PREFLIGHT before FULL")
        workflow.prepare(copy_environment=args.copy_environment)
    if args.copy_r_library:
        if args.mode != "PREFLIGHT":
            parser.error("Copy dependencies separately in PREFLIGHT")
        workflow.copy_r_library(args.copy_r_library)
    result = (
        workflow.preflight()
        if args.mode == "PREFLIGHT"
        else workflow.execute_full(
            authorize_full=args.authorize_full,
            controlled_download=args.controlled_download,
        )
    )
    if args.execute_notebook and result["status"] == "PASS":
        result["notebook_execution"] = workflow.execute_preflight_notebook()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] in ("PASS", "PIPELINE_EXECUTED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
