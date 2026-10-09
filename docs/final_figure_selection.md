# Figures and tables selected for the Phase 9B report

Selection from existing versioned artifacts only: **15 PNGs and four tables**.
No statistical result is generated. Final page constraints may require combining
panels or moving secondary diagnostics to appendices. Figure captions must state
TRAIN/full-descriptive/final scope, units and historical provenance.
PNG figures are not newly estimated by Phase 9A; the notebook's redraw of CSV
loss histories is explicitly identified as a display of archived data.

| Exact path | Source phase | Interpretation | Scientific message | Planned report section |
| --- | --- | --- | --- | --- |
| `outputs/figures/phase2/normalized_prices_base100.png` | 2 | Relative trajectories, all assets, descriptive holdout marked. | Market context; not fitted scaling. | Data / EDA |
| `outputs/figures/phase2/log_returns.png` | 2 | Variable amplitude and volatility clustering. | Returns and regimes, no economic event attribution. | EDA |
| `outputs/figures/phase2/nvda_adj_close_acf_pacf_train.png` | 2 | Persistent level dependence. | Motivates stationarity diagnostics before modeling. | Stationarity |
| `outputs/figures/phase2/nvda_log_return_acf_pacf_train.png` | 2 | Dependence after log differencing. | Supports d=1 investigation; pointwise bands. | Stationarity / ARIMA |
| `outputs/tables/phase2_stationarity_summary.csv` | 2 | ADF/KPSS combined mechanical outcomes. | Nonstationary levels, stationary returns within specifications. | Stationarity |
| `outputs/figures/phase3/nvda_arima_checkresiduals_r.png` | 3A | R mean residual diagnostics. | Adequacy is separate from IC or predictive gain. | ARIMA diagnostics |
| `outputs/figures/phase3b/phase3b_rmse_by_model_h10.png` | 3B | Internal rolling validation. | Complexity does not satisfy the complete Naive replacement rule. | Temporal validation |
| `outputs/tables/phase4_granger_causality_comparison.csv` | 4 | Raw/Holm conditional tests in R/Python. | Predictive information is not real-world causation. | VAR / Granger |
| `outputs/figures/phase4/phase4_var_irf.png` | 4 | Orthogonal innovation responses. | Exploratory Cholesky-dependent dynamics. | VAR dynamics |
| `outputs/figures/phase4/phase4_var_fevd.png` | 4 | Innovation contributions to error variance. | Multivariate information can matter without a price-score gain. | VAR dynamics |
| `outputs/figures/phase5/phase5_conditional_volatility.png` | 5 | Retrospective TRAIN sigma paths. | Persistent conditional risk, daily percent, not price direction. | GARCH |
| `outputs/figures/phase5/phase5_squared_standardized_residual_acf.png` | 5 | Postfit squared-residual dependence. | No detected ARCH at tested lags is not proof of iid. | GARCH diagnostics |
| `outputs/figures/phase6/phase6_lstm_loss_curve.png` | 6 | Locked C/fold 3 training and inner-stop losses. | Early stopping, not holdout or external-fold score. | Deep learning |
| `outputs/figures/phase6/phase6_gru_loss_curve.png` | 6 | Comparable GRU loss history. | Architecture cost/overfitting warning with one seed. | Deep learning |
| `outputs/figures/phase7/phase7_rmse_comparison_h5.png` | 7 | Matched final price RMSE, h5. | Naive versus classical/neural observed performance. | Final evaluation |
| `outputs/figures/phase7/phase7_rmse_comparison_h10.png` | 7 | Matched final price RMSE, h10. | Isolated ARIMA RMSE lead does not override selection policy. | Final evaluation |
| `outputs/figures/phase7/phase7_actual_vs_forecasts_h10.png` | 7 | Historical target-aligned forecast paths. | Retain neural negative results and observed errors. | Final evaluation |
| `outputs/tables/phase7_diebold_mariano.csv` | 7 | Published paired loss inference. | Distinguish raw/Holm and non-rejection/equivalence. | Statistical comparison |
| `llm/human_analysis/phase8_hallucination_audit.csv` | 8B | 35 grouped sourced claims, severity/issue fields. | No detected numerical hallucination in checked claims; limited audit. | LLM critique |

Use `outputs/tables/phase7_final_metrics.csv` as the numeric source accompanying
the RMSE panels, and `outputs/tables/phase7_final_model_recommendation.csv` for
the final Naive recommendation. No new DM/LLM chart is fabricated: their existing
tables are more informative and preserve the source evidence.
