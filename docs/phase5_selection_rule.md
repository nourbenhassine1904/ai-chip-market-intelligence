# Phase 5 — Predeclared fitting and selection rule

Written before computing the Phase 5 mean-filter and GARCH results.
The numeric settings are in `phase5_protocol.csv`. Observations are TRAIN only.

- Use ARMA(1,1) with unconditional mean mu on percentage log-returns in both
  languages. Keep all 1979 return innovations, with zero additional burn.
  In recursion form the intercept is `(1-phi)*mu`. Estimate the mean first,
  freeze its innovations, and fit zero-mean symmetric GARCH separately.
- Mean Ljung–Box at 10/20 uses fitdf=2. Stop before GARCH if the mean fit
  fails convergence or either p-value is below 0.01; flag intermediate
  0.01–0.05 evidence. Pre-GARCH ARCH-LM at 5/10/20 uses ddof=0/demean=FALSE.
  Require at least two p-values below 0.05, otherwise stop before GARCH.
- Baselines are only GARCH(1,1) Normal and standardized Student-t (df>2).
  Python uses native arch backcasting (first 75 innovations, decay .94) and
  SLSQP; R uses rugarch rec.init='all', scale=0, stationarity=1 and solnp.
  These independent native initializations are retained, not cross-seeded.
- Require convergence, finite likelihood/volatilities, omega>0, all ARCH/GARCH
  coefficients nonnegative and sum<1 for a stationary admissible fit.
- Post-GARCH Ljung–Box uses fitdf=2 for z and z-squared, at 10/20.
  These are approximate diagnostic reference distributions after fitting.
  Post ARCH-LM uses ddof=0 at 5/10/20. Use Holm correction across the five
  variance diagnostics (three ARCH-LM and two squared Ljung–Box tests),
  within each model/language. Keep raw p-values and raw decisions visible.
  Mean adequacy requires both raw z Ljung–Box p-values >=.05; variance
  adequacy requires all five Holm p-values >=.05.
- Compare total likelihood IC on the same observations, with k=3/4 variance
  parameters for Normal/Student-t; report R's per-observation IC separately.
  First-stage mean parameters are common and excluded from conditional
  second-stage IC; these are not joint ARMA-GARCH likelihood criteria.
- Student-t is preferred only if both languages give a valid stationary fit,
  its total AIC and BIC improve by at least 10 over Normal, its tail-quantile
  RMSE improves, and it has no more rejected mean or adjusted variance tests.
  Tail RMSE uses probabilities .01,.02,.05,.95,.98,.99 against the fitted
  unit-variance innovation distribution. This is an in-sample descriptive
  comparison, not a calibrated goodness-of-fit test or holdout score.
  Prefer diagnostically adequate candidates; otherwise retain a clearly
  provisional baseline for the higher-order gate, not a validated lock.
- Open the higher-order gate only when the selected valid GARCH(1,1) has
  Holm-significant ARCH or squared-residual dependence in either language.
  Mean correlation alone cannot open it. If open, fit at most (2,1) and
  (1,2) with the selected baseline distribution. Do not add asymmetry terms.
  Retain a higher order only if adequate in both languages and it improves
  total AIC and BIC by at least 2 in both. Within 2 BIC units prefer fewer
  variance parameters. If none restores adequacy, document the remaining
  limitation without expanding the grid or claiming a validated model.
- Lock a shared specification only when diagnostics pass in both languages;
  native parameter differences remain visible. Never label it best final model.
- Ten-step forecasts start exclusively from the last TRAIN innovation and
  filtered variance. Forecast innovation variance, not multi-step ARMA return
  forecast-error variance. Historical sigma uses parameters estimated on all
  TRAIN and must not be treated as a real-time out-of-sample feature.
