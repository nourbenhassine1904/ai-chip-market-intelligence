# Team setup — Windows PowerShell

Use one repository for Python, notebooks and RStudio. Published scientific
results are already tracked; downloading data or training is unnecessary for
review. Read [the reproduction guide](reproduction_guide.md) before any pipeline run.

## A. Clone and choose the delivered revision

In PowerShell, choose a short writable parent directory (especially for TensorFlow):

```powershell
git clone https://github.com/nourbenhassine1904/ai-chip-market-intelligence.git
Set-Location ai-chip-market-intelligence
git status --short
git tag --list v0.11.0-phase8
```

Phase 9A is a **local** commit on `feature/final-deliverables`, not pushed by this
task. A remote clone currently contains Phase 8, not necessarily this notebook.
Use a team-supplied repository copy/bundle containing the local Phase 9A commit,
or its revision once subsequently shared by the owner. `v0.11.0-phase8` is the
scientific baseline and does not contain Phase 9A additions. Do not claim the
unpublished notebook is already available on GitHub.

## B–E. Python, R and dependencies

```powershell
py -3.12 --version
Rscript --version
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip check
python -c "import sys, tensorflow as tf; print(sys.version); print(tf.__version__); print(tf.config.list_physical_devices())"
```

Run installations manually; scripts do not install packages. If the `py` launcher
is absent, first confirm `python --version` is 3.12, then use `python -m venv .venv`.
If activation is blocked by local execution policy, use
`.\.venv\Scripts\python.exe` for each Python command instead of changing global policy.
If Rscript is not on PATH, call its installed executable, for example
`& 'C:\Program Files\R\R-4.5.2\bin\Rscript.exe' --version`.

Observed scientific stack and current check: **Python 3.12.3, TensorFlow 2.21.0,
Windows native CPU, R 4.5.2**. Historical detailed versions are in
`outputs/tables/phase6_runtime_versions.csv` and `phase7_runtime_versions.csv`.
Most base requirements are not pinned: installing today does not lock the entire
historical stack. Check versions and compare manifests before claiming replication.

`requirements-dev.txt` declares nbformat, nbclient and ipykernel, plus Ruff/pytest.
The FAST executor launches the **current Python executable** as its kernel and
does not register a user-wide kernel. An editor can select `.venv` directly.
The configured index initially lacked `debugpy`; if that happens, use the same
manual installation with the official public index:

```powershell
python -m pip install --index-url https://pypi.org/simple -r requirements-dev.txt
```

## Windows paths and CPU TensorFlow

A deeply nested OneDrive checkout can exceed the path limits of package installers
or other applications. Prefer a new clone in a short directory, rather than moving
the scientific checkout during an audit. An administrator may enable
`HKLM\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled=1` or the
Enable Win32 long paths policy. Applications also need long-path support;
the registry setting is not a universal fix. Review the
[Microsoft path documentation](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation).
No registry change is made by this project.

TensorFlow 2.21.0 is checked locally rather than inferred from current web defaults.
Use CPU; no GPU or CUDA is required. Native Windows GPU support after TF 2.10
is not the supported pip route described by the
[TensorFlow installation guide](https://www.tensorflow.org/install/pip).
GPU-unavailable/oneDNN informational messages alone do not mean the run failed.
Fixed seeds and requested deterministic ops improve reproducibility but do not
promise bit-for-bit identity across machines, versions or numerical libraries.

## F–H. Local data and chronological TRAIN/TEST

`data/raw/` and `data/processed/` contain only `.gitkeep` in a clean clone.
The existing published manifests are evidence, not market data downloads.
Choose one route in an **isolated reproduction clone**, not the reference checkout:

1. Obtain the original seven CSV snapshots from a team member, preserve bytes,
   place them in their original relative paths, and verify against the historical
   manifests. No snapshot archive is currently versioned or remotely supplied.
2. Run authentic acquisition/preparation/EDA scripts in the isolated clone,
   accepting Yahoo revision risk. The exact commands and historical checksum
   comparison are in [reproduction_guide.md](reproduction_guide.md).

In the reference checkout, read-only verification commands are:

```powershell
python python/phase9a_review.py --portable
python python/phase9a_review.py --data
python python/phase9a_review.py --structure
```

`--data` reports MISSING or DIVERGENT and returns nonzero for either. FAST still
works when local data are missing. `--structure` requires `market_aligned.csv`;
it checks the real 19-column schema, dates, finite values and positive adjusted
prices. The existing Phase 2 script produces the 34-column features and chronological
split: historically 2200 total, 1980 TRAIN through 2025-11-14, 220 TEST starting
2025-11-17 (source: `outputs/tables/phase2_split_metadata.csv`). No shuffle or fill.

## I. Classical Python and R runs

The complete ordered commands are in the reproduction guide. Use them only in
the isolated clone because their outputs can overwrite tables, figures and docs.
Python acquisition/preparation/EDA are canonical. Real R model scripts are
`r/02_arima.R`, `r/02b_arima_validation.R`, `r/03_var_vecm.R`, `r/04_garch.R`.
`r/01_data_eda.R` is an unimplemented historical placeholder, not an R EDA pipeline.
Do not force `--vecm` or `--higher`: published gates are closed.

## Using RStudio with this repository

Open `ai-chip-market-intelligence.Rproj` in the **same** repository folder.
For reproduction, open the Rproj in the isolated clone. The committed Rproj
already exists; no second repository is needed for RStudio.

In the RStudio Console, confirm root and dependencies:

```r
getwd()
stopifnot(file.exists("r/02_arima.R"), file.exists("data/processed/market_train.csv"))
dir.create(".cache/R-library", recursive=TRUE, showWarnings=FALSE)
.libPaths(c(".cache/R-library", .libPaths()))
packages <- c("forecast", "tseries", "FinTS", "vars", "urca", "rugarch")
missing <- packages[!vapply(packages, requireNamespace, logical(1), quietly=TRUE)]
missing
# Only if missing packages are listed, install them manually:
if (length(missing)) install.packages(missing, lib=".cache/R-library", repos="https://cloud.r-project.org")
```

In the isolated clone, execute from the root:

```r
source("r/02_arima.R")
source("r/02b_arima_validation.R")
source("r/03_var_vecm.R")
source("r/04_garch.R")
```

The Python summary commands must follow the matching R runs, as documented in
the reproduction guide. R writes language-specific CSVs under `outputs/tables/`;
Python summaries combine R/Python and produce shared figures. Open these CSVs
in RStudio and view PNGs under `outputs/figures/phase3`, `phase3b`, `phase4`, `phase5`.
Classical scripts use base Date/numeric arrays and package-specific temporal
objects; Phase 6 deep learning remains Python. No R model implementation changes.

## J–K. Open the notebook and published results

Open `notebooks/AI_Chip_Market_Intelligence.ipynb` in a Jupyter-capable editor
(for example VS Code with the Jupyter extension) and choose the `.venv` interpreter.
Use Run All in FAST. A notebook server UI is not installed by the declared
development requirements; nbclient execution needs no server:

```powershell
python python/09a_execute_notebook.py --clean-copy
Import-Csv outputs/tables/phase9a_notebook_execution_audit.csv | Format-Table -AutoSize
python -m ruff check .
python -m pytest
```

The executed notebooks go to ignored `.cache/phase9a/`, not historical outputs.
Read the phase links in README and `llm/human_analysis/phase8_human_vs_llm_comparison.md`.
Tables and figures are **published historical results**. FAST arithmetic checks
are **newly reproduced verifications**, not model reestimation.

## L. Troubleshooting

| Symptom | Diagnosis and action |
| --- | --- |
| Missing local CSV | Expected on a clone; FAST needs none. Restore snapshots or rebuild in isolation. |
| Historical SHA mismatch | Preserve both manifests and report divergence. Do not label data identical or replace official outputs. |
| Frozen source mismatch in FAST | Stop; inspect the manifest and Git diff. Never regenerate the manifest to bless changed results. |
| Wrong kernel/import missing | Select `.venv`; manually install development requirements, run pip check. |
| R locale warnings `C.UTF-8` | In PowerShell before Rscript: `$env:LC_ALL = 'English_United States.utf8'`. |
| Missing R package | Install the displayed packages manually in `.cache/R-library`; inspect `.libPaths()`. |
| Existing Phase 7 predictions | Intentional immutable-file gate; use the isolated replay route, do not delete predictions in the reference checkout. |
| TRAIN hash rejected after Yahoo reload | Expected strict protocol protection; stop FULL scientific replication and record revised data separately. |
| Long installation paths | Prefer a short new clone; consult administrator for long-path policy. |
| Native Windows GPU unavailable | CPU is the declared environment. |
