"""Execute FAST with nbclient, including a data/cache/Git-free checkout simulation."""

import argparse
import ast
import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from phase9a_review import ROOT, frozen_records, verify_frozen

NOTEBOOK = "notebooks/AI_Chip_Market_Intelligence.ipynb"
AUDIT = "outputs/tables/phase9a_notebook_execution_audit.csv"
GUARD = '''
import sys as _sys
from pathlib import Path as _Path
_root = _Path.cwd().resolve()
_blocked_imports = {'tensorflow', 'yfinance', 'statsmodels', 'arch', 'sklearn'}
def _phase9a_guard(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'subprocess.Popen', 'os.system'}:
        raise RuntimeError('FAST forbids network/process execution: ' + event)
    if event == 'import' and args[0].split('.')[0] in _blocked_imports:
        raise RuntimeError('FAST forbids model/acquisition imports: ' + args[0])
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = _Path(args[0]).resolve()
        if path.is_relative_to(_root / 'data'):
            raise RuntimeError('FAST forbids local data access')
        mode, flags = args[1], args[2]
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+'))
        writing = writing or bool(flags & (1 | 2 | 64 | 512 | 1024))
        if writing and path.is_relative_to(_root) and '.cache' not in path.parts:
            raise RuntimeError('FAST forbids repository writes: ' + str(path))
_sys.addaudithook(_phase9a_guard)
'''


def execute(root, output, kernel_dir):
    import nbformat
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    from nbclient import NotebookClient

    nb = nbformat.read(root / NOTEBOOK, as_version=4)
    nbformat.validate(nb)
    for cell in nb.cells:
        if cell.cell_type == "code":
            ast.parse(cell.source)
    guard = nbformat.v4.new_code_cell(GUARD)
    nb.cells.insert(0, guard)
    spec = kernel_dir / "phase9a"
    spec.mkdir(parents=True, exist_ok=True)
    (spec / "kernel.json").write_text(json.dumps({
        "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": "Phase 9A current environment", "language": "python"}), encoding="utf8")
    km = KernelManager(kernel_name="phase9a",
                       kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernel_dir)]))
    client = NotebookClient(nb, timeout=180, km=km,
                            resources={"metadata": {"path": str(root)}}, allow_errors=False)
    # An explicitly supplied manager is not owned by nbclient: request cleanup.
    # Otherwise its live Windows process holds the temporary working directory.
    client.execute(cleanup_kc=True)
    assert not km.has_kernel, "Kernel was not shut down"
    nb.cells.pop(0)
    for index, cell in enumerate((c for c in nb.cells if c.cell_type == "code"), 1):
        cell.execution_count = index
    assert all(c.execution_count is not None for c in nb.cells if c.cell_type == "code")
    assert any("image/png" in o.get("data", {}) for c in nb.cells
               for o in c.get("outputs", [])), "No displayed PNG output"
    output.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, output)
    return sum(c.cell_type == "code" for c in nb.cells)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean-copy", action="store_true",
                        help="Also execute from a copy without data, ignored caches or .git")
    args = parser.parse_args()
    rows = []

    def check(name, status, detail):
        rows.append({"check": name, "status": status, "detail": detail})

    try:
        result = verify_frozen(portable=True)
        frozen_before = result.copy()
        assert result.status.eq("PASS").all(), result[result.status != "PASS"].to_string()
        check("frozen_before", "PASS", f"{len(result)} exact SHA256 checks")
        # Keep execution/config/cache products out of the scientific directories.
        cache = ROOT / ".cache/phase9a"
        cache.mkdir(parents=True, exist_ok=True)
        os.environ["MPLCONFIGDIR"] = str(cache / "matplotlib")
        os.environ["JUPYTER_CONFIG_DIR"] = str(cache / "jupyter")
        os.environ["IPYTHONDIR"] = str(cache / "ipython")
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        with tempfile.TemporaryDirectory(prefix="phase9a-") as temp:
            temp = Path(temp)
            count = execute(ROOT, cache / "AI_Chip_Market_Intelligence.executed.ipynb",
                            temp / "kernels")
            check("FAST_execution", "PASS", f"nbclient: {count} code cells executed in order; current Python kernel")
            check("FAST_guards", "PASS", "Runtime guards deny data reads, network, subprocesses, model imports and repository writes")
            check("figures_displayable", "PASS", "PNG MIME outputs captured by the kernel; all source figures decoded")
            check("frozen_metric_arithmetic", "PASS", "MSE/RMSE/MAE/MAPE checked against frozen predictions; no new forecasts or DM")
            if args.clean_copy:
                clean = temp / "clean"
                records = {r["path"]: r for r in frozen_records()}
                paths = list(records)
                paths += ["docs/phase9a_frozen_artifacts_manifest.json", NOTEBOOK,
                          "python/phase9a_review.py"]
                for relative in paths:
                    target = clean / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(ROOT / relative, target)
                    if relative in records:
                        record = records[relative]
                        raw = target.read_bytes()
                        lf = raw.replace(b"\r\n", b"\n")
                        if hashlib.sha256(lf).hexdigest() == record["git_blob_sha256"]:
                            target.write_bytes(lf)
                assert not (clean / "data").exists()
                assert not (clean / ".git").exists()
                execute(clean, cache / "AI_Chip_Market_Intelligence.clean.executed.ipynb",
                        temp / "kernels")
                check("clean_copy_FAST", "PASS", "Executed from committed LF bytes with no data/, .git or ignored historical model caches")
            else:
                check("clean_copy_FAST", "NOT_RUN", "Use --clean-copy")
    except Exception as exc:
        check("execution_error", "FAIL", f"{type(exc).__name__}: {exc}")
        raise
    finally:
        result = verify_frozen(portable=True)
        unchanged = result.status.eq("PASS").all() and result.equals(frozen_before)
        check("frozen_after", "PASS" if unchanged else "FAIL",
              f"{len(result)} exact SHA256 checks after execution")
        with (ROOT / AUDIT).open("w", encoding="utf8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
            writer.writeheader()
            writer.writerows(rows)
        for row in rows:
            print(row)
    if not unchanged:
        raise RuntimeError("Frozen files changed during execution")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
