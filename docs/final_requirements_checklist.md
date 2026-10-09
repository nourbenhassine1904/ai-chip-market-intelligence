# Final requirements checklist

The official specification PDF was not available in the repository or the supplied
attachment resources. This is a **documentary audit limitation**, not a missing
scientific deliverable requested by the professor. The original audit used the
Phase 9A task list; this correction also incorporates the section 8.3 requirement
provided by the user: an RMarkdown or Jupyter notebook reproducing the entire
study end to end on a clean machine with the listed packages. The complete PDF
has not been independently read, so other clauses cannot be certified from it.

PASS means evidence exists for the stated item, not universal model adequacy.
PARTIAL identifies incomplete compliance or supporting reproducibility/provenance
checks; MISSING includes the report intentionally deferred to Phase 9B.
**Totals: 29 PASS, 3 PARTIAL, 1 MISSING — 33 reviewed checks.** These counts include
supporting checks and are not a count of independently verified PDF clauses.

| Requirement | Status | Real evidence / file | Remaining action |
| --- | --- | --- | --- |
| Financial data ≥5 years | PASS | `outputs/tables/phase1_asset_audit.csv`: Observed 2018-01-02–2026-10-02; 2200 rows. | None. |
| Documented source | PASS | `docs/phase1_data_acquisition.md`: Yahoo/yfinance arguments, dates and versions. | None. |
| Derived indicators | PASS | `docs/data_dictionary.md`: 15 backward log/return/volume/volatility features. | None. |
| Cleaning and audit | PASS | `outputs/tables/phase1_5_alignment_audit.csv`: Intersection, NA/duplicates/OHLC checks, no imputation. | None. |
| Suitable temporal objects | PASS | `python/01_data_eda.py`: Dated pandas frames; Date/ordered vectors and forecast ts conversion in r/02_arima.R. | Explain observed-session indexing in report. |
| EDA | PASS | `docs/phase2_eda_stationarity.md`: 24 published Phase 2 figures and descriptive tables. | Select compact set for report. |
| ACF/PACF | PASS | `outputs/figures/phase2/nvda_log_return_acf_pacf_train.png`: TRAIN diagnostics; level/return plots for three assets. | None. |
| ADF/KPSS | PASS | `outputs/tables/phase2_stationarity_tests.csv`: Specified deterministic terms, warning/decision columns. | Retain test caveats. |
| ARIMA / conditional SARIMA | PASS | `outputs/tables/phase3_seasonality_gate.csv`: ARIMA identified; SARIMA not justified, gate documented. | Do not force SARIMA. |
| Classical diagnostics | PASS | `outputs/tables/phase3_arima_diagnostic_summary.csv`: Residual serial, normality, ARCH diagnostics and warnings. | Retain unfavorable diagnostics. |
| VAR | PASS | `outputs/tables/phase4_var_lag_selection_comparison.csv`: Both languages retain stable VAR(9). | None. |
| Granger | PASS | `outputs/tables/phase4_granger_causality_comparison.csv`: Conditional tests, raw/Holm, language comparison. | No economic causality claim. |
| Johansen | PASS | `outputs/tables/phase4_johansen_rank_comparison.csv`: Rank zero in both languages. | Retain specification conventions. |
| VECM if justified | PASS | `outputs/tables/phase4_vecm_decision.csv`: Rank zero explicitly closes VECM gate. | No VECM required under this condition. |
| ARCH-LM prerequisite | PASS | `outputs/tables/phase5_arch_lm_pre_garch.csv`: Rejections on mean innovations precede variance fits. | None. |
| GARCH | PASS | `outputs/tables/phase5_garch_model_comparison.csv`: Normal/Student-t, diagnostics, persistence, shared lock. | Distinguish variance from price; no held-out volatility score. |
| LSTM | PASS | `outputs/tables/phase6_locked_lstm.csv`: Bounded temporal search and C lock. | Retain negative result. |
| GRU | PASS | `outputs/tables/phase6_locked_gru.csv`: Matched temporal search and C lock. | Retain negative result. |
| Sliding windows | PASS | `python/05_lstm_gru.py`: make_windows asserts past input and ten-target block. | None. |
| Leak-free scaling | PASS | `outputs/tables/phase6_scaler_audit.csv`: X/y fit within each TRAIN prefix; no TEST fitting. | None. |
| Loss curves | PASS | `outputs/tables/phase6_loss_history.csv`: Actual epoch loss/val_loss and both archived curves. | Distinguish inner early-stop loss from outer validation. |
| Temporal validation | PASS | `outputs/tables/phase6_temporal_folds.csv`: Expanding folds; also Phase 3B rolling origins. | None. |
| Naive comparison | PASS | `outputs/tables/phase7_recommendation_checks.csv`: Same benchmark, matched origins, predeclared fallback. | None. |
| Horizons 5 and 10 | PASS | `outputs/tables/phase7_evaluation_origins.csv`: 211 common observed-session origins per horizon. | None. |
| MSE/RMSE/MAE/MAPE | PASS | `outputs/tables/phase7_final_metrics.csv`: Sourced metrics, verified arithmetic on frozen predictions. | Never relabel replay as new holdout run. |
| Diebold–Mariano | PASS | `outputs/tables/phase7_diebold_mariano.csv`: HAC/HLN, two-sided/raw/Holm and scope recorded. | Non-rejection does not prove equality. |
| Complete LLM section | PASS | `docs/phase8_llm_analysis.md`: Official A/B/C/D prompt and unchanged response, simulated investment disclaimer. | Retain missing generation metadata. |
| Critical LLM comparison | PASS | `llm/human_analysis/phase8_human_vs_llm_comparison.md`: Completed comparison plus 35-claim sourced audit. | Independence of human-only baselines not attested. |
| Classic R and Python code | PASS | `r/04_garch.R`: Four real R model scripts and nine real Python pipeline scripts. | R EDA placeholder is not counted as implemented code. |
| Section 8.3 — end-to-end RMarkdown/Jupyter notebook | PARTIAL | `notebooks/AI_Chip_Market_Intelligence.ipynb`: 52 FAST code cells executed successfully in the reference and data/cache/Git-free contexts; `outputs/tables/phase9a_notebook_execution_audit.csv` documents review of frozen outputs, not end-to-end model execution. | Implement a separate FULL notebook or a genuinely orchestrated isolated mode, provide verified input snapshots and listed package versions, prepare the Phase 7 run area, and execute the entire chain on a clean machine with saved logs/provenance. See the minimal plan in `docs/reproduction_guide.md`. |
| Strict FULL data/runtime readiness (supporting check) | PARTIAL | `docs/reproduction_guide.md`: Authentic isolated command recipe exists; original snapshots/caches are not distributed and the final checkout retains the Phase 7 immutable-prediction gate. | Package or restore original inputs, reject divergent downloads for strict reproduction, record Python/R versions, validate CPU execution and archive new run outputs separately; demonstrate all stages rather than only `--summarize`. |
| LLM generation provenance | PARTIAL | `docs/phase8_llm_analysis.md`: Response preserved; exact model/version/time unknown. | Record only if independently supplied. |
| Final 15–25-page report | MISSING | `report/README.md`: Only planning placeholder; intentionally deferred. | Phase 9B, no new modeling. |

Scientific conclusions, protocols and official LLM response stay frozen. Conditional
SARIMA/VECM omissions count as justified completion, not secretly fitted models.
No test, number or independent reviewer is invented to make the checklist pass.
Notebook status must match the actual execution CSV, not a planned execution.
