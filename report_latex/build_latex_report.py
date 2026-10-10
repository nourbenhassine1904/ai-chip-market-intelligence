"""Compile the separate LaTeX report; never write the historical report."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from prepare_assets import check_assets, refresh_assets

PROJECT = Path(__file__).resolve().parent
BUILD = PROJECT / "_build"
OUTPUT = PROJECT / "rapport_final_latex.pdf"


def tex_environment():
    """Keep PATH directories only, avoiding malformed host file entries in MiKTeX."""
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join(
        entry
        for entry in environment.get("PATH", "").split(os.pathsep)
        if Path(entry.strip('"')).is_dir()
    )
    return environment


def command(command_args, label):
    result = subprocess.run(
        command_args,
        cwd=PROJECT,
        env=tex_environment(),
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    (BUILD / f"{label}.stdout.txt").write_text(result.stdout, encoding="utf8")
    (BUILD / f"{label}.stderr.txt").write_text(result.stderr, encoding="utf8")
    if result.returncode:
        print(result.stdout[-6000:])
        print(result.stderr[-2000:])
        raise RuntimeError(
            f"{label} failed with exit code {result.returncode}; see {BUILD}"
        )
    return {"command": command_args, "exit_code": result.returncode, "log": label}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-assets", action="store_true")
    parser.add_argument("--engine", default="pdflatex")
    args = parser.parse_args()
    if args.refresh_assets:
        refresh_assets()
    else:
        check_assets()
    compiler = shutil.which(args.engine)
    bibtex = shutil.which("bibtex")
    if compiler is None or bibtex is None:
        raise RuntimeError(
            "Install/configure a TeX distribution exposing pdflatex and bibtex; no automatic installation"
        )
    BUILD.mkdir(exist_ok=True)
    version = subprocess.run(
        [compiler, "--version"],
        env=tex_environment(),
        capture_output=True,
        text=True,
        errors="replace",
        check=True,
    ).stdout
    flags = ["--disable-installer"] if "MiKTeX" in version else []
    latex = [
        compiler,
        *flags,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        "-no-shell-escape",
        "-output-directory=" + str(BUILD),
        "main.tex",
    ]
    logs = [command(latex, "latex-pass-1")]
    logs.append(command([bibtex, "_build/main"], "bibtex"))
    logs.extend(command(latex, f"latex-pass-{i}") for i in (2, 3))
    log = (BUILD / "main.log").read_text(encoding="utf8", errors="replace")
    fatal_markers = (
        "There were undefined references",
        "There were undefined citations",
        "Citation ",
        "LaTeX Warning: Reference ",
        "Missing character:",
        "Label(s) may have changed",
    )
    remaining = [
        line
        for line in log.splitlines()
        if any(marker in line for marker in fatal_markers)
    ]
    if remaining:
        raise RuntimeError(
            "Unresolved references/glyphs after final pass: " + "\n".join(remaining)
        )
    # Copy only after a successful compilation; never overwrite report/rapport_final.pdf.
    shutil.copyfile(BUILD / "main.pdf", OUTPUT)
    audit = {
        "status": "COMPILED",
        "engine_version": version,
        "commands": logs,
        "output": str(OUTPUT),
        "automatic_package_installation": False,
        "shell_escape": False,
        "overfull_boxes": [line for line in log.splitlines() if "Overfull" in line],
        "visual_review": "PENDING",
    }
    (BUILD / "compile_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf8"
    )
    print("Compiled:", OUTPUT)
    print("Overfull boxes:", len(audit["overfull_boxes"]))


if __name__ == "__main__":
    main()
