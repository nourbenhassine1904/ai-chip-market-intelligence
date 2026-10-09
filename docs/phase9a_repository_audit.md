# Phase 9A — Repository audit

Audit baseline: `cdfb4e1649bff7cd583936f06dcb74c79f1f2a30`, `v0.11.0-phase8`, branch
`feature/final-deliverables`, initial working tree clean. This baseline is the
Phase 8 merge on main from which Phase 9A started; it does not describe the
current HEAD or publication state. Select a delivery revision containing the
Phase 9A files as explained in [team_setup_windows.md](team_setup_windows.md).

## Scope and organization

Read README, ignore/attributes, base/dev requirements, protocol, decisions,
data dictionary, all Phase 1–8 technical documents, and inventory of every
Python/R/test source. No AGENTS.md was found in the repository. No official
requirements PDF was found among repository files or the supplied attachment
resources; the checklist uses the user's enumerated requirements and the section
8.3 end-to-end notebook requirement subsequently supplied by the user, without
claiming access to the full PDF. The absent PDF limits documentary verification;
it is not itself a required scientific deliverable.

`data/` holds ignored local raw/processed CSVs; only placeholders are committed.
`python/` contains nine historical executable scripts. `r/` contains four real
model scripts plus the EDA placeholder. `tests/` contains ten historical test
modules. `notebooks/` previously contained only a README. `outputs/` holds
published tables and PNGs. `docs/` preserves protocols, rules, phase reports
and decisions. `llm/` holds facts/prompt, the official response, interpretations,
comparison and hallucination audit. `report/README.md` is a planning placeholder.
The RStudio project `ai-chip-market-intelligence.Rproj` already exists.

## Real script inventory

| Path | Lines inspected | Actual options |
| --- | ---: | --- |
| `python/00_data_acquisition.py` | 322 | No CLI options |
| `python/01_data_eda.py` | 1089 | No CLI options |
| `python/01_data_preparation.py` | 448 | No CLI options |
| `python/02_arima.py` | 797 | --summarize, --compare-r |
| `python/02b_arima_validation.py` | 977 | --summarize |
| `python/03_var_vecm.py` | 866 | --summarize, --vecm |
| `python/04_garch.py` | 1156 | --summarize, --higher |
| `python/05_lstm_gru.py` | 1003 | No CLI options |
| `python/06_evaluation.py` | 1258 | --summarize |
| `r/01_data_eda.R` | 7 | No CLI options |
| `r/02_arima.R` | 294 | No CLI options |
| `r/02b_arima_validation.R` | 175 | No CLI options |
| `r/03_var_vecm.R` | 211 | --vecm |
| `r/04_garch.R` | 192 | --higher |

`r/01_data_eda.R` is a seven-line future-responsibility placeholder, not executable
EDA. Base R and `forecast`, `tseries`, `FinTS`, `vars`, `urca`, `rugarch` are the
actual R dependencies; scripts prepend `.cache/R-library` when it exists.
No script installs packages. jsonlite is present locally but is not required
by these R model scripts. Forecast imports ts methods; code also uses base Date
and ordered vectors/matrices. Python uses dated pandas frames/indices.

New Phase 9A utilities: `python/phase9a_review.py` (read-only SHA/data/schema/metric
checks) and `python/09a_execute_notebook.py` (nbclient FAST execution/audit).
Detailed function/import/write-call inventories are recorded in
[`phase9a_repository_inventory.json`](../outputs/tables/phase9a_repository_inventory.json).
That file also names every prior technical document and its headings.

## Pipeline

Yahoo → raw audit/manifest → intersection-aligned canonical data → backward
features → chronological TRAIN/TEST → TRAIN EDA/stationarity → ARIMA
identification/internal validation → VAR/Granger/Johansen → ARCH/GARCH →
LSTM/GRU temporal validation → predeclared frozen-model holdout evaluation →
official LLM response and documentary comparison → FAST delivery checks.
See [reproduction_guide.md](reproduction_guide.md) for inputs, outputs, genuine
commands, cost and isolated execution.

## Published artifact inventory

Historical tables by prefix: `{'phase1': 5, 'phase2': 12, 'phase3': 34, 'phase3b': 17, 'phase4': 40, 'phase5': 36, 'phase6': 19, 'phase7': 18}`.
PNG figures by directory: `{'phase2': 24, 'phase3': 12, 'phase3b': 6, 'phase4': 6, 'phase5': 7, 'phase6': 7, 'phase7': 8}`.
Total: 181 historical table/evidence files and
70 PNGs. Phase 8's 35-claim audit is under llm/,
not outputs/tables. The table inventory includes the Phase 7 runtime JSON.
The frozen manifest names all 305 protected scientific/code/doc files,
including official response and protocols. Ten preexisting test source hashes
are retained separately as baseline references.

The scientific main findings are sourced in the notebook and phase reports:
Naive remains the locked/final recommended price benchmark; VAR(9) is stable;
Johansen rank zero closes VECM; the conservative GARCH Normal lock does not
establish Gaussian tail adequacy; neural configurations C lose to Naive.

## Verified Python runtime

| Package | Observed installed version |
| --- | --- |
| python | 3.12.3 |
| pandas | 3.0.6 |
| numpy | 2.5.3 |
| matplotlib | 3.11.2 |
| scipy | 1.18.1 |
| statsmodels | 0.15.0 |
| arch | 8.0.0 |
| pmdarima | 2.1.1 |
| yfinance | 1.7.0 |
| scikit-learn | 1.9.1 |
| tensorflow | 2.21.0 |
| nbformat | 5.11.1 |
| nbclient | 0.11.0 |
| ipykernel | 7.4.0 |
| pytest | 9.1.1 |
| ruff | 0.16.10 |

TensorFlow device query was executed: CPU only, no GPU. Rscript reports R 4.5.2;
read-only package checks found forecast 9.0.2, tseries 0.10.63, FinTS 0.4.9,
vars 1.6.1, urca 1.3.4 and rugarch 1.5.6. Initial pip check passed. Development
notebook packages were absent, then installed with explicit approval; configured
index failures (notebook/debugpy) were resolved using the necessary three
packages from PyPI. No server notebook dependency is required.

## Reproducibility problems and missing deliverables

- README was stuck at Phase 2 and described R/notebooks as future placeholders;
  Phase 9A updates it and adds the principal notebook.
- A clean clone has no market CSVs or neural weights. FAST requires neither.
  The original seven CSVs exist locally and can be checked, but no original
  snapshot distribution archive is committed. Acquisition may retrieve revisions.
- Most Python dependencies and all R dependencies are unpinned. Version records
  exist, but there is no lockfile/renv lock or portable historical snapshot bundle.
- Deep Windows paths, locale `C.UTF-8`, local R library and CPU numerical details
  affect installation/execution; documented without changing the environment policy.
- Git text conversion produced 164 checkout-vs-blob differences in the original
  315-entry inventory (including tests). These are baseline representation
  differences, not Phase 9A scientific mutations. Local verification stays strict;
  portable review accepts only the exact captured hash or exact committed blob
  hash and never silently normalizes a changed source. Historical raw data hashes
  remain exact-byte checks. Phase 7 CSVs already enforce LF.
- Scripts write directly to scientific output directories; EDA and Phase 3B also
  write reports. Isolation is mandatory for regeneration. No output-dir CLI exists.
- Final evaluation deliberately refuses to overwrite frozen predictions. FULL
  classical/neural recipes are documented, but a new strict Phase 7 forecast run
  needs a separately prepared area/provenance and is not automatically runnable
  from the final checkout. A summary replay is not a reestimation.
- Two historical Phase 8 tests used an open-ended working-tree diff. Their
  historical assertions now end at `v0.11.0-phase8`; the new Phase 9A suite verifies
  current frozen science. Only test scope changes, no statistical logic/results.
- Old phase-boundary prose includes intentionally unanswered-template statements
  written before later development. Those historical reports remain unedited;
  the current notebook and Phase 8 document explain the completed chronology.
- LLM model/version/generation metadata and independent human-review provenance
  remain unavailable. Do not infer them or call baselines blinded/human-only.
- The successful FAST notebook run does not demonstrate the section 8.3
  end-to-end requirement. Notebook compliance and FULL data/runtime readiness
  remain PARTIAL; the minimal untested implementation plan is in the reproduction guide.
- The official PDF is unavailable, limiting documentary review rather than
  constituting a missing scientific deliverable. The 15–25-page final report
  is deferred to Phase 9B. The corrected checklist has 29 PASS, 3 PARTIAL and
  1 MISSING across 33 checks.

Validation evidence and remaining work are in
[phase9a_reproducibility.md](phase9a_reproducibility.md). No FULL model run or new
Yahoo download was performed in this phase.
