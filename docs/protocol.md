# AI-Chip Market Intelligence — Experimental Protocol

## Assets

- NVDA
- AMD
- SOXX

## Main forecasting target

NVIDIA (NVDA)

## Data source

Yahoo Finance

## Study period

2018-01-01 to 2026-10-02

## Frequency

Daily trading observations

## Main market variable

Adjusted Close

## Planned derived variables

- log-price
- log-return
- percentage return
- volume change
- simple realized volatility if justified

## Train/Test protocol

- 90% training
- 10% testing
- chronological split only
- no random split

## Forecast horizons

- h = 5 trading days
- h = 10 trading days

## Baseline

Naive / random-walk benchmark

## Scientific rules

- No data leakage.
- Never fit a scaler on test data.
- Preserve chronological order.
- Set random seeds when relevant.
- Do not force SARIMA without evidence of seasonality.
- Do not estimate a VECM unless cointegration is demonstrated.
- Do not interpret Granger causality as real-world causal proof.
- Do not justify GARCH without volatility diagnostics / ARCH evidence.
- Do not select a model only because it has a lower AIC.
- Diagnose residuals for every classical model.
- Compare models out-of-sample.
- Report failures and limitations honestly.
- Never invent statistical results.
- Human statistical interpretation must be written before requesting LLM interpretation.
