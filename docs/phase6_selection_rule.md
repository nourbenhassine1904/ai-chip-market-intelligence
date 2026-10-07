# Phase 6 — Predeclared training and selection rule

Written before any Phase 6 network fit or inspection of validation scores.
The fixed settings are archived in `phase6_protocol.json`.

- Read only official TRAIN. Keep the five requested features and remove only
  the leading 20 rows with unavailable historical features. Verify trailing
  volatility and backward returns using TRAIN alone.
- For N usable rows, boundaries are floor(7N/10), floor(8N/10), floor(9N/10),
  N. The three expanding TRAIN prefixes precede three contiguous outer
  validation blocks. All indices are zero-based, ends exclusive.
- Every input ends at origin t; every target is exactly t+1 through t+10.
  Training targets remain in the permitted training region. Outer validation
  origins run from block_start-1 through block_end-11 inclusive, daily. Keep
  only complete ten-output windows: h5 and h10 share the same origins, as do
  all architectures/configurations and the naive benchmark. Consequently h5
  targets stop five observations before the block end; h10 reaches its end.
- Fit separate StandardScaler X/y on the outer-fold TRAIN prefix only, never
  outer validation. Use one scalar y normalization shared across ten outputs.
  Both architectures and all candidates use the same fold scalers.
- To prevent future outer-validation labels selecting weights at an earlier
  origin, reserve the final 10% of each fold TRAIN for chronological inner
  early stopping. Optimization targets end before floor(.9*train_rows);
  early-stopping targets are entirely in the remaining TRAIN tail. Purge
  windows whose ten targets straddle this inner boundary. Scalers may use
  this tail because it is part of fold TRAIN, but never outer validation.
  This inner tail is a stopping device, not an independently scored test.
  There are still exactly 18 main fits; no additional fold refits are run.
- Fit exactly A/B/C for each of LSTM/GRU in each of three folds, seed 42
  reset before each fit, batch 32, Adam .001, MSE, at most 100 epochs,
  patience 10, restore the minimum inner-validation-loss weights. No shuffle,
  stateful recurrence, feature search, extra architecture or adaptive grid.
- A failed fit is recorded with its exception and cannot qualify. Do not
  silently substitute another configuration. Nonfinite losses/forecasts stop
  a run. Selection requires all three successful, leakage-free fold fits.
- Main score is the equal-weight mean of six fold/horizon RMSE ratios to the
  matched naive baseline. Smaller is preferable. Scores within absolute
  0.001 are practically tied; then use mean MAE ratio (same tolerance), fewer
  parameters, shorter lookback, and finally configuration label for stability.
  The tolerance is fixed before results; neither pooled USD RMSE nor the
  historical Phase 3B score replaces this primary selection criterion.
- Keep a locked LSTM and a locked GRU even when both lose to naive. Report
  negative improvements. Compare models only on matching internal origins.
  Pool squared/absolute errors for summary USD metrics; retain unweighted
  fold ratios separately. Overlapping horizons are not independent samples.
- After locking, refit each selected architecture once on all usable TRAIN
  windows, with full-TRAIN X/y scalers and a fixed integer number of epochs:
  median of its three one-based best epochs. No early stopping at refit.
  Save the two refit models/scalers locally in ignored `.cache/phase6`.
- Produce endpoint h1..h10 forecasts from the last TRAIN window, plus naive.
  Exponentiation is a point forecast without lognormal bias correction;
  it is not automatically a conditional mean in USD. No future observations,
  final test metrics, final DM, Prophet, hybrid or other phase is used.
- Run on CPU with deterministic TensorFlow operations requested and fixed
  thread counts. Record versions, device, seeds, histories, errors and times;
  do not promise identical bits across different hardware/software stacks.
