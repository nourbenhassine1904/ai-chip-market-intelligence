# Reproduction guide

Published results are the frozen Phases 1–8 artifacts. Phase 9A provides a
read-only scientific narrative, executable consistency checks, and exact commands.
Displaying a historical CSV is not a full reestimation. Newly generated research
outputs must stay separate and must not replace the historical final evaluation.

## Mode A — REVIEW / FAST

From a checkout containing the Phase 9A files, activate `.venv` as described
in [team_setup_windows.md](team_setup_windows.md). No Yahoo access, market CSVs,
R, neural weights or GPU are needed. Execute:

```powershell
python python/phase9a_review.py --portable
python python/09a_execute_notebook.py --clean-copy
Import-Csv outputs/tables/phase9a_notebook_execution_audit.csv | Format-Table -AutoSize
python -m ruff check .
python -m pytest
```

The notebook displays verified historical tables/PNGs, plots the archived loss
curves, verifies common prediction origins, and checks four metric formulas
against archived forecasts and published metrics. It does not read data/, run
an analysis script, fit a model, recalculate DM or select a replacement model.
The executor additionally denies network/process/model imports and repository
writes inside the kernel. Only new audit evidence and ignored executed notebooks
are written by the outer executor. It compares all 305 scientific hashes before
and after. `--clean-copy` executes again without data/, .git or ignored model caches;
this is a clean-checkout simulation, not a remote GitHub download.
This evidence covers review and arithmetic checks, not the full end-to-end
notebook required by section 8.3.

Open the notebook in a compatible editor with `.venv` selected, or use the
nbclient command above. No separate Jupyter server package is required for nbclient.

## Mode B — FULL REPRODUCTION: isolate first

FULL was **not run during Phase 9A**. The command recipe below is for explicit
future reproduction, not an automatic notebook mode. It may take minutes or much
longer on another CPU; never rerun deep learning merely to test the notebook.

Set these variables while in the untouched reference repository. Create a new
clone in a new sibling directory; do not move or delete the reference checkout:

```powershell
$Reference = (Get-Location).Path
$Revision = git rev-parse HEAD
$Sandbox = Join-Path (Split-Path $Reference -Parent) 'ai-chip-reproduction'
if (Test-Path -LiteralPath $Sandbox) { throw 'Choose a new empty sandbox path.' }
git clone --no-hardlinks --no-local $Reference $Sandbox
git -C $Sandbox checkout --detach $Revision
Set-Location -LiteralPath $Sandbox
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip check
$env:LC_ALL = 'English_United States.utf8'
```

`--no-local --no-hardlinks` makes independent Git storage. Selecting `$Revision`
preserves the source revision regardless of its branch name or publication state.
Confirm that it contains the Phase 9A files. Ensure the path is short enough for
Windows installations. Keep `$Reference` pointing to the original checkout for
every historical comparison.

## Reconstruct data, with a divergence gate

**Original snapshot route:** copy the seven original CSVs into this sandbox,
preserving filenames and bytes, then run the checks below. Raw names are
`NVDA_raw.csv`, `AMD_raw.csv`, `SOXX_raw.csv`; processed names are
`market_aligned.csv`, `market_features.csv`, `market_train.csv`, `market_test.csv`.
No archive or download URL for these exact snapshots is supplied in the repository.
To rebuild missing processed data from original raw bytes, skip acquisition and
run preparation followed by EDA, comparing historical hashes at each stage.

**New Yahoo download route:** all following commands execute in the sandbox:

```powershell
python python/00_data_acquisition.py
if ($LASTEXITCODE -ne 0) { throw 'Acquisition failed; inspect partial files and audits.' }
python python/01_data_preparation.py
if ($LASTEXITCODE -ne 0) { throw 'Preparation failed.' }
python python/phase9a_review.py --structure
if ($LASTEXITCODE -ne 0) { throw 'Canonical schema invalid.' }
python python/01_data_eda.py
if ($LASTEXITCODE -ne 0) { throw 'EDA/split failed.' }
python python/phase9a_review.py --data --historical-root $Reference
if ($LASTEXITCODE -ne 0) { throw 'Historical snapshot differs or is missing. Stop strict FULL reproduction.' }
```

Acquisition writes new manifests in the sandbox, so compare data to manifests
from `$Reference`, **not** only to the freshly generated manifest. A matching
new acquisition manifest merely describes the new download. SHA comparison uses
exact saved bytes, never normalized text. Historical checks cover raw, canonical,
features, TRAIN and TEST. Date/schema consistency alone cannot prove identical data.

Yahoo historical revisions, package CSV formatting and precision changes can all
cause mismatch. Record expected/actual hashes, preserve new outputs separately,
and stop claiming strict reproduction. Do not amend historical protocols to accept
new hashes, retune on the old holdout, or update official final metrics.
Acquisition/preparation/EDA overwrite their tables and EDA's technical report
**only in the sandbox**. They have no output-directory flags.

## Classical model commands

Run only after all historical data hashes match. These are the actual CLI names:

```powershell
python python/02_arima.py
Rscript r/02_arima.R
python python/02_arima.py --compare-r
python python/02_arima.py --summarize
python python/02b_arima_validation.py
Rscript r/02b_arima_validation.R
python python/02b_arima_validation.py --summarize
python python/03_var_vecm.py
Rscript r/03_var_vecm.R
python python/03_var_vecm.py --summarize
python python/04_garch.py
Rscript r/04_garch.R
python python/04_garch.py --summarize
```

Check `$LASTEXITCODE` after each command and stop on errors. `--compare-r` is
the historical optional optimizer sensitivity, not a new tuning grid. ARIMA
rolling validation is substantially slower than identification/VAR. GARCH fits
two fixed distributions per language. `--vecm` and `--higher` exist but are
excluded from this recipe because the published rank/order gates are closed.
No SARIMA or Prophet is forced. R dependencies and RStudio operation are in
[Using RStudio with this repository](team_setup_windows.md#using-rstudio-with-this-repository).
RStudio sources the same sandbox files from the repository root.

## Deep learning and historical evaluation boundary

The authentic training command is:

```powershell
python python/05_lstm_gru.py
```

It performs the original bounded TRAIN-only 18 fits and two refits, writes
Phase 6 tables/figures and ignored `.cache/phase6/` weights/scalers, and can be
CPU-expensive. It does not run in Phase 9A. All seeds, configurations and temporal
folds are in `docs/phase6_protocol.json`; no new candidates may be selected.
Numerically identical models across TensorFlow builds/CPUs are not guaranteed.

The authentic Phase 7 CLI offers:

```powershell
python python/06_evaluation.py --summarize
```

In the sandbox, this replays derivatives from **historical frozen predictions**
without reading TEST or fitting, and overwrites sandbox Phase 7 derived outputs.
It is not a fresh neural evaluation. The no-option command
`python python/06_evaluation.py` would fit locked TRAIN classical specifications,
load verified caches or reconstruct the two locked neural fits, then forecast TEST.
It **refuses to run on a final checkout with existing frozen predictions**.
Phase 9A does not remove that gate or prescribe deleting the historical predictions.

A strict new Phase 7 evaluation is therefore **not an immediately runnable FULL
recipe from the final checkout**: it additionally needs an explicitly prepared
separate evaluation run area, exact snapshot/protocol bytes, committed predeclared
protocol provenance, preserved historical evidence and validated caches or openly
identified reconstructed weights. This important remaining limitation is PARTIAL,
not silently bypassed. Regenerated caches have different file/provenance hashes,
and the Phase 7 loader may reconstruct locked fits. A changed neural realization
must not be described as the original frozen model. This work is outside Phase 9A.

The historical evaluation remains definitive for the study. Its metrics/DM come
from `phase7_final_predictions.csv`, identified by `phase7_prediction_freeze.csv`.
The same 211 origins/horizon and observed prefixes are frozen; GARCH is separate
volatility analysis. The consumed final holdout must never become a tuning set.

## Minimal plan for section 8.3 FULL reproduction

**Proposal only: not implemented, executed or demonstrated by this review.**
Section 8.3, as supplied by the user, requires an RMarkdown/Jupyter notebook
reproducing the entire study on a clean machine with the listed packages.
The current FAST notebook and manual commands do not demonstrate this capability;
compliance remains PARTIAL until the full notebook actually executes successfully.

### Orchestrator and isolation

Recommend a separate proposed `notebooks/AI_Chip_Market_Intelligence_FULL.ipynb`.
It would reuse the existing model scripts, invoke them in order, stop on nonzero
exit, capture stdout/stderr and elapsed time, and display **new run** outputs.
This file does not currently exist. Adding a truly orchestrated FULL mode to the
current notebook is possible, but requires the same workspace/gate handling plus
an explicit mode choice and separate tests: the FAST executor intentionally
blocks model imports, subprocesses and market-data reads. A separate notebook
is the smaller extension that leaves the demonstrated FAST path unchanged.

Use an independent clone/run workspace at a recorded source commit. Retain an
immutable reference copy of all frozen Phase 1–8 outputs, protocols, final
forecasts, official LLM response and Naive recommendation, and compare reference
hashes before/after. Archive the workspace's initial historical output copies
before regeneration. Scripts lack an output-directory option, so their repository
root and working directory must resolve inside the new workspace. Regenerated
tables/figures/logs must never replace reference files. Do not run on main or use
the reference checkout as the output destination.

### Prerequisites and ordered work

| Step | Minimal implementation | Evidence / stop condition |
| --- | --- | --- |
| 1. Inputs | Supply the original three raw snapshots as an archive with historical SHA256 references. Rebuild canonical/features/TRAIN/TEST with `python/01_data_preparation.py` and `python/01_data_eda.py`. Alternatively run `python/00_data_acquisition.py` with the existing fixed dates in isolation. | Compare all seven data hashes to the untouched historical manifests. Stop strict reproduction on a revised Yahoo download or changed serialization; do not amend frozen input hashes. A new acquisition manifest alone proves only the new download's self-consistency. |
| 2. Packages | Prepare Python 3.12.3, R 4.5.2, base/development requirements, nbformat/nbclient/ipykernel, and forecast, tseries, FinTS, vars, urca, rugarch. Record versions and prepare reproduction constraints from the recorded stack because current requirements do not pin it all. | Manual installation in the new environment, import/package checks, pip check, selected source commit and environment report. No installation is performed by this corrective review. |
| 3. TRAIN pipeline | Orchestrate restoration/acquisition, preparation, EDA, ARIMA identification/sensitivity and rolling validation, VAR/Granger/Johansen, GARCH, and LSTM/GRU in the authentic command order above, including R before each shared Python summary. | Genuine command logs and regenerated outputs from each stage. Keep the bounded original grid, seed and rules; respect closed SARIMA/VECM/higher-GARCH gates. Stop on failed checks or inconsistent locks rather than retuning. |
| 4. CPU learning | Run TensorFlow 2.21.0 on native Windows CPU with original features, windows, scalers, folds, 18 fits and two refits. | Actual loss histories, device/seed/epochs and measured runtime. No GPU required; no blanket bit-for-bit promise across machines or library versions. |
| 5. Final evaluation | Prepare a new Phase 7 run area as described below and invoke the authentic no-option `python/06_evaluation.py`. | New forecasts, common origins, frozen parameters, four metrics, DM and fresh provenance. A historical `--summarize` replay is insufficient. Stop on historical data/lock mismatch; never change thresholds based on scores. |
| 6. LLM and delivery | Load the unchanged official prompt/response, facts, team comparison and 35-claim audit; rerun source/provenance checks against the reference and render run outputs in the FULL notebook. | Preserve official LLM bytes. Reproducing the documentary analysis is distinct from generating another response; the unknown original model/version/time prevents a promise of identical generation. Save executed notebook, logs and comparisons. |

New-run findings cannot change the official final Naive recommendation. Report
differences as reproduction findings; never promote a holdout-selected challenger
or replace published scores.

### Explicit missing Phase 7 preparation

`python/06_evaluation.py` refuses existing frozen predictions. Its
`verify_protocol_commit` requires exact protocol bytes and committed protocol
history; without historical runtime evidence, it also requires a clean working
tree to create a **new** pre-access gate. Calling it in the final checkout cannot
therefore demonstrate FULL.

The future orchestrator must archive copied Phase 7 outputs outside active
run-output paths and prepare an initially empty Phase 7 output area **only in
the independent run workspace**, while preserving the reference artifacts.
Retain original Git history and the unchanged predeclared protocol; create a
documented local checkpoint of the prepared TRAIN-stage workspace and verify a
clean working tree before evaluation. Do not copy historical `.cache/phase7/`
gates or `phase7_runtime_audit.json` into the active evaluation area to pass off
the old pre-access evidence as a new gate. No checkpoint, archive movement or
evaluation action is performed in this review.

The existing loader checks original Phase 6 weight/scaler/provenance hashes.
Restored original caches must match those references. Newly trained cache files
may differ and trigger reconstruction of the locked networks; record that mode
and additional CPU time. Do not call reconstructed weights identical to the
original frozen realization. Keep protocol/cache checks enabled and stop on
inconsistent locks/provenance instead of modifying historical models or protocols.
Distinguish genuine reestimation from historical cache replay in the evidence.

### Duration and acceptance criteria

Phase 6 recorded about **20.14 minutes** of CPU fitting on the original stack,
excluding preprocessing, scoring, figures and other phases (source:
[Phase 6 computational cost](phase6_lstm_gru.md#computational-cost)). ARIMA rolling
validation, Python/R installation, acquisition and possible Phase 7 neural
reconstruction add time. Reserve a longer uninterrupted CPU session and measure
each stage; no universal total runtime has been established.

Mark section 8.3 PASS only after the FULL notebook runs top to bottom on a clean
machine/environment without the author's preinstalled `.venv`, data, R library
or model caches, using the documented snapshot/package prerequisites. Retain
revision, environment, input hashes, commands/exit codes, training logs, executed
notebook, generated prediction panel/metrics and output comparisons. Declare
numerical comparison tolerances before execution and record differences. Verify
all reference scientific hashes and the official response remain unchanged.
A guarded stop is an honest failed/partial reproduction, not PASS. No FULL
acceptance run has been performed in this corrective review.

## Phase inputs, outputs and cost

| Phase | Inputs | Authentic scripts | Outputs in sandbox | Cost / caveat |
| --- | --- | --- | --- | --- |
| 1 | Yahoo, protocol dates/assets | `python/00_data_acquisition.py` | raw CSVs, three Phase 1 audit/manifest CSVs | Network; revisions possible |
| 1.5 | raw + Phase 1 manifest | `python/01_data_preparation.py` | `market_aligned.csv`, alignment audit/manifest | Structural validation, no model |
| 2 | canonical + manifest | `python/01_data_eda.py` | features/TRAIN/TEST, Phase 2 tables/figures/report | EDA; writes docs too |
| 3A | TRAIN + Phase 2 evidence | `python/02_arima.py`, `r/02_arima.R` | `phase3_*`, figures phase3 | Fits, diagnostics, optional optimizer sensitivity |
| 3B | TRAIN + candidate/protocol CSVs | `python/02b_arima_validation.py`, `r/02b_arima_validation.R` | `phase3b_*`, lock, docs/report | Many rolling fits; slow |
| 4 | TRAIN + `phase4_protocol.csv` | `python/03_var_vecm.py`, `r/03_var_vecm.R` | `phase4_*`, IRF/FEVD, VECM decision | Rank zero gate |
| 5 | TRAIN + protocol/selection rule | `python/04_garch.py`, `r/04_garch.R` | `phase5_*`, volatility figures | Fixed variance models; price scores excluded |
| 6 | TRAIN + protocol/selection rule | `python/05_lstm_gru.py` | `phase6_*`, loss/forecast figures, ignored weights | CPU-heavy bounded original fits |
| 7 | frozen predictions + runtime audit (replay) | `python/06_evaluation.py --summarize` | derivatives/DM/recommendation/PNGs | Replay, not new TEST forecasting |
| 8 | facts, official prompt/response, baselines | no LLM-generation CLI | comparison/audit already committed | Documentary audit; model metadata unavailable |
| 9A | published artifacts + SHA manifest | notebook, `python/09a_execute_notebook.py` | FAST execution audit + ignored executed notebooks | No models/data/network in kernel |

All scientific scripts/tests and outputs were inventoried in
[phase9a_repository_audit.md](phase9a_repository_audit.md). Phase 9B writes the
15–25-page report; it does not authorize new holdout selection or repaired scores.
