# AI-Chip Market Intelligence

Multivariate Forecasting, Dynamic Interdependencies and Volatility Risk Analysis of NVIDIA, AMD and the Semiconductor Market

Current project status: **Phase 1 — Data Acquisition & Audit**.
See [`docs/phase1_data_acquisition.md`](docs/phase1_data_acquisition.md) for execution and audit details.

## Context

Mini-project for the course **Séries Temporelles pour Data Science & IA**  
TEK-UP University  
Academic Year 2026/2027

## Objective

This project will study three related questions: forecasting NVIDIA (NVDA) market values, examining dynamic interdependencies among NVDA, AMD and the semiconductor sector, and analyzing volatility and market risk. The work will compare suitable methods using a documented, chronological out-of-sample evaluation.

## Assets

- **NVDA** — NVIDIA
- **AMD** — Advanced Micro Devices
- **SOXX** — semiconductor sector ETF

## Planned methodology

The planned roadmap is data preparation, exploratory analysis, stationarity analysis, a baseline, ARIMA/SARIMA if justified, VAR, Granger causality, cointegration, VECM if justified, ARCH/GARCH, LSTM, GRU, out-of-sample evaluation, and critical LLM analysis.

The presence of a method in the roadmap does not imply that it will automatically be retained. Each model must be statistically justified.

## Repository structure

- `data/` — placeholders for raw and processed local data; market data is not committed.
- `python/` — canonical data acquisition and future analysis scripts; `r/` — future analysis placeholders.
- `notebooks/` — guidance for future notebooks.
- `outputs/` — locations for selected final figures and tables.
- `llm/` — human analysis, prompts and responses for the later critical analysis phase.
- `report/` — report planning and documentation.
- `docs/` — protocol, data dictionary, decisions and team workflow.

## Reproducibility

- Use a strict chronological 90% training / 10% test split; do not shuffle observations.
- Set fixed random seeds whenever a stochastic method is used.
- Record package versions used for each analysis.
- Use paths relative to the repository root; do not use absolute local file paths.
- Preserve downloaded raw data and do not modify it manually. Generated or downloaded data stays out of Git.
- Raw data stays local; Phase 1 audit tables and SHA-256 manifests document actual acquisition runs.

## Collaboration workflow

Keep `main` stable. Each substantial task should use a dedicated branch, be pushed to GitHub, and be proposed through a pull request to `main`. Another team member reviews the changes before merge. See [`docs/team_workflow.md`](docs/team_workflow.md) for commands and commit conventions.

## Initial environment

Create a local environment and install the base dependencies:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
```
