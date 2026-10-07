# Phase 4. Run from repository root; only frozen TRAIN observations are read.
if (.Platform$OS.type == 'windows') {
  invisible(Sys.setlocale('LC_CTYPE', 'English_United States.utf8'))
}
if (!file.exists('r/03_var_vecm.R')) stop('Run from repository root.')
if (dir.exists('.cache/R-library')) .libPaths(c('.cache/R-library', .libPaths()))
required <- c('vars', 'urca')
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) stop(paste0('Missing packages; no automatic installation. Run in R: ',
  'install.packages(c(', paste(sprintf("'%s'", missing), collapse=', '), '))'))
options(digits = 17)
protocol_path <- 'docs/phase4_protocol.csv'
protocol <- read.csv(protocol_path, stringsAsFactors = FALSE)
stopifnot(nrow(protocol) == 1, protocol$max_var_lag == 10,
          protocol$johansen_level_lags >= 2, protocol$serial_gate_1 == 20,
          protocol$serial_gate_2 == 30, protocol$cholesky_order == 'NVDA;AMD;SOXX')
input <- 'data/processed/market_train.csv'
assets <- c('NVDA', 'AMD', 'SOXX')
return_columns <- paste0(assets, '_Log_Return')
level_columns <- paste0(assets, '_Log_Price')
scope <- 'TRAIN_only_no_final_evaluation'
reads <- character()
read_observations <- function(path) {
  if (!identical(path, input)) stop('Unauthorized market input.')
  expected <- paste0(normalizePath('.', winslash='/'), '/', input)
  if (normalizePath(path, winslash='/') != expected) stop('Redirected TRAIN path.')
  if (unname(tools::md5sum(path)) != protocol$train_md5) stop('Frozen TRAIN MD5 mismatch.')
  reads <<- c(reads, path)
  read.csv(path, stringsAsFactors=FALSE, check.names=FALSE)
}
# MD5 is measured independently in base R; SHA reference comes from frozen protocol.
train <- read_observations(input)
stopifnot(all(c('Date', return_columns, level_columns, paste0(assets, '_Adj_Close')) %in% names(train)))
dates <- as.Date(train$Date, format='%Y-%m-%d')
stopifnot(nrow(train) == protocol$expected_rows, !anyNA(dates), !anyDuplicated(dates),
          all(diff(dates) > 0), as.character(dates[1]) == protocol$first_date,
          as.character(tail(dates, 1)) == protocol$last_date)
for (asset in assets) {
  prices <- train[[paste0(asset, '_Adj_Close')]]
  levels <- train[[paste0(asset, '_Log_Price')]]
  returns <- train[[paste0(asset, '_Log_Return')]]
  stopifnot(all(is.finite(prices)), all(prices > 0), all(is.finite(levels)),
            is.na(returns[1]), all(is.finite(returns[-1])),
            max(abs(levels - log(prices))) < 1e-12,
            max(abs(returns[-1] - 100 * diff(levels))) < 1e-10)
}
y <- as.matrix(train[-1, return_columns]); colnames(y) <- assets
x <- as.matrix(train[, level_columns]); colnames(x) <- assets
meta <- data.frame(language='R', scope=scope, train_md5=protocol$train_md5,
                   protocol_md5=unname(tools::md5sum(protocol_path)),
                   implementation_md5=unname(tools::md5sum('r/03_var_vecm.R')))
save_table <- function(table, name) {
  dir.create('outputs/tables', recursive=TRUE, showWarnings=FALSE)
  for (field in names(meta)) table[[field]] <- meta[[field]]
  write.csv(table, paste0('outputs/tables/phase4_', name, '_r.csv'), row.names=FALSE,
            na='', fileEncoding='UTF-8')
}
guard_names <- c('market_train.csv only', 'market_test.csv not read',
                 'chronological order preserved', 'frozen TRAIN fingerprint',
                 'no future information', paste(c('lag selection', 'Granger', 'Johansen',
                 'VECM', 'IRF', 'FEVD'), 'TRAIN only'), 'no final evaluation')
stopifnot(identical(reads, input))
save_table(data.frame(check=guard_names, status='PASS',
  evidence_type=c(rep('runtime assertion', 5), rep('code scope audit', 7)),
  details=c(rep('Frozen TRAIN chronology, MD5 and backward transformations validated', 5),
            rep('Only TRAIN arrays enter functions; conditional gates apply; no evaluation', 7))),
  'holdout_guard')
save_table(data.frame(rows=nrow(train), return_rows=nrow(y), first_date=protocol$first_date,
  last_date=protocol$last_date, sha256_reference=protocol$train_sha256,
  sha256_verified=NA, md5_verified=TRUE, variables=paste(c(return_columns, level_columns), collapse=';'),
  observation_reads=paste(reads, collapse=';'), holdout_read=FALSE), 'train_manifest')
save_table(data.frame(package=c('R', required), version=c(as.character(getRversion()),
  vapply(required, function(p) as.character(packageVersion(p)), character(1)))), 'runtime_versions')

johansen <- function(k) urca::ca.jo(x, type='trace', ecdet='none', K=k, spec='transitory')
if ('--vecm' %in% commandArgs(trailingOnly=TRUE)) {
  decision <- read.csv('outputs/tables/phase4_vecm_decision.csv', stringsAsFactors=FALSE)
  rank <- decision$cointegration_rank
  stopifnot(nrow(decision) == 1, isTRUE(decision$vecm_justified), rank %in% c(1, 2),
            decision$protocol_md5 == meta$protocol_md5, decision$train_md5 == meta$train_md5)
  jo <- johansen(protocol$johansen_level_lags)
  fitted <- urca::cajorls(jo, r=rank)
  beta <- fitted$beta
  alpha <- t(coef(fitted$rlm)[seq_len(rank), , drop=FALSE])
  for (name in c('alpha', 'beta')) {
    matrix <- get(name)
    table <- expand.grid(variable=assets, relation=seq_len(rank), stringsAsFactors=FALSE)
    table$coefficient <- as.vector(matrix)
    table$rank <- rank
    table$deterministic <- 'unrestricted constant outside beta'
    save_table(table, paste0('vecm_', name))
  }
  representation <- vars::vec2var(jo, r=rank)
  # vars::serial.test(vec2var) uses K^2*h df, unlike rank-adjusted VECM df in Python.
  # Retain native diagnostics with explicit degrees of freedom.
  diagnostics <- do.call(rbind, lapply(c(10, 20, 30), function(h) {
    test <- vars::serial.test(representation, lags.pt=h, type='PT.adjusted')$serial
    data.frame(test='adjusted Portmanteau (native vec2var df)', horizon=h,
      test_statistic=as.numeric(test$statistic), df=as.numeric(test$parameter), p_value=as.numeric(test$p.value))
  }))
  test <- vars::normality.test(representation, multivariate=TRUE)$jb.mul$JB
  diagnostics <- rbind(diagnostics, data.frame(test='multivariate Jarque-Bera', horizon=NA,
    test_statistic=as.numeric(test$statistic), df=as.numeric(test$parameter), p_value=as.numeric(test$p.value)))
  diagnostics$rank <- rank
  save_table(diagnostics, 'vecm_diagnostics')
  cat('R conditional VECM PASS: rank=', rank, '\n')
} else {
  ic <- vars::VARselect(y, lag.max=protocol$max_var_lag, type='const')$criteria
  fits <- lapply(seq_len(protocol$max_var_lag), function(p) vars::VAR(y, p=p, type='const'))
  lags <- do.call(rbind, lapply(seq_along(fits), function(p) {
    fit <- fits[[p]]
    roots <- vars::roots(fit, modulus=TRUE)
    p20 <- as.numeric(vars::serial.test(fit, lags.pt=protocol$serial_gate_1, type='PT.adjusted')$serial$p.value)
    p30 <- as.numeric(vars::serial.test(fit, lags.pt=protocol$serial_gate_2, type='PT.adjusted')$serial$p.value)
    data.frame(lag=p, aic=ic['AIC(n)', p], bic=ic['SC(n)', p], hqic=ic['HQ(n)', p], fpe=ic['FPE(n)', p],
      ic_nobs=nrow(y)-protocol$max_var_lag, estimation_nobs=fit$obs,
      estimable=all(is.finite(unlist(lapply(fit$varresult, coef)))), stable=all(roots < 1),
      max_companion_modulus=max(roots), serial_p20=p20, serial_p30=p30,
      serial_adequate=min(p20, p30) >= protocol$alpha)
  }))
  pool <- subset(lags, estimable & stable)
  if (!nrow(pool)) stop('No estimable stable VAR in fixed grid.')
  adequate <- subset(pool, serial_adequate)
  if (nrow(adequate)) pool <- adequate
  tied <- subset(pool, (bic-min(pool$bic))*ic_nobs <= protocol$bic_tie_units)
  selected <- tied$lag[order(tied$lag, tied$bic, tied$hqic, tied$aic)][1]
  lags$selected <- lags$lag == selected
  for (criterion in c('aic', 'bic', 'hqic', 'fpe')) {
    lags[[paste0(criterion, '_proposed')]] <- lags$lag == lags$lag[which.min(lags[[criterion]])]
  }
  save_table(lags, 'var_lag_selection')
  fit <- fits[[selected]]
  chosen <- subset(lags, selected)
  roots <- vars::roots(fit, modulus=FALSE)
  save_table(data.frame(root_index=seq_along(roots), companion_real=Re(roots), companion_imag=Im(roots),
    companion_modulus=Mod(roots), inverse_characteristic_modulus=1/Mod(roots),
    stable=all(Mod(roots) < 1), lag=selected), 'var_stability')
  serial <- do.call(rbind, lapply(c(5, 10, 20, 30), function(h) {
    if (h <= selected) return(data.frame(horizon=h, test_statistic=NA, df=NA, p_value=NA,
      decision_5pct='not_applicable_h_le_p'))
    test <- vars::serial.test(fit, lags.pt=h, type='PT.adjusted')$serial
    data.frame(horizon=h, test_statistic=as.numeric(test$statistic), df=as.numeric(test$parameter),
      p_value=as.numeric(test$p.value), decision_5pct=if (test$p.value < .05) 'reject_serial_null' else 'fail_to_reject_serial_null')
  }))
  serial$lag <- selected; serial$test <- 'adjusted Portmanteau'
  save_table(serial, 'var_residual_serial_correlation')
  normal <- vars::normality.test(fit, multivariate=TRUE)$jb.mul$JB
  save_table(data.frame(test='multivariate Jarque-Bera', test_statistic=as.numeric(normal$statistic),
    df=as.numeric(normal$parameter), p_value=as.numeric(normal$p.value), lag=selected,
    decision_5pct=if (normal$p.value < .05) 'reject_normality' else 'fail_to_reject_normality'), 'var_residual_normality')
  granger <- do.call(rbind, lapply(assets, function(cause) do.call(rbind, lapply(setdiff(assets, cause), function(effect) {
    # Equation-level conditional Wald: vars::causality(cause) instead pools all other equations.
    equation <- fit$varresult[[effect]]
    terms <- paste0(cause, '.l', seq_len(selected))
    b <- coef(equation)[terms]; covariance <- vcov(equation)[terms, terms, drop=FALSE]
    statistic <- as.numeric(t(b) %*% solve(covariance, b))
    p <- pchisq(statistic, df=selected, lower.tail=FALSE)
    data.frame(cause=cause, effect=effect, test_statistic=statistic, df=selected, p_value=p,
      decision_5pct=if (p < .05) 'reject_H0' else 'fail_to_reject_H0')
  }))))
  granger$p_value_holm <- p.adjust(granger$p_value, method='holm')
  granger$reject_holm_5pct <- granger$p_value_holm < .05
  granger$lag <- selected; granger$test <- 'conditional equation Wald chi-square'
  save_table(granger, 'granger_causality')
  ks <- c(protocol$johansen_level_lags, as.integer(strsplit(protocol$johansen_sensitivity_lags, ';', fixed=TRUE)[[1]]))
  trace <- do.call(rbind, lapply(ks, function(k) {
    jo <- johansen(k)
    statistics <- rev(jo@teststat); critical <- jo@cval[3:1, , drop=FALSE]
    first_nonreject <- which(statistics <= critical[, '5pct'])
    rank <- if (length(first_nonreject)) first_nonreject[1]-1L else 3L
    data.frame(specification=if (k == protocol$johansen_level_lags) 'main' else 'sensitivity',
      level_lags=k, k_ar_diff=k-1, deterministic='ecdet=none; unrestricted constant in differenced equations',
      input_variables=paste(level_columns, collapse=';'), nobs_levels=nrow(x), effective_nobs=nrow(x)-k,
      null_rank_at_most=0:2, trace_statistic=statistics, critical_10pct=critical[, '10pct'],
      critical_5pct=critical[, '5pct'], critical_1pct=critical[, '1pct'],
      reject_5pct=statistics > critical[, '5pct'], selected_rank=rank,
      critical_table='urca native Osterwald-Lenum table; ecdet=none')
  }))
  save_table(trace, 'johansen_trace')
  residuals <- as.data.frame(resid(fit)); residuals$Date <- as.character(dates[-seq_len(selected+1)])
  save_table(residuals, 'var_residuals')
  coefficients <- do.call(rbind, lapply(assets, function(asset) {
    equation <- summary(fit$varresult[[asset]])$coefficients
    data.frame(lag=selected, nobs=fit$obs, response=asset, term=rownames(equation),
               coefficient=equation[, 1], std_error=equation[, 2])
  }))
  save_table(coefficients, 'var_coefficients')
  dynamic_ok <- isTRUE(chosen$stable) && isTRUE(chosen$serial_adequate)
  save_table(data.frame(stable=chosen$stable, serial_adequate=chosen$serial_adequate,
    irf_fevd_permitted=dynamic_ok, lag=selected), 'var_dynamic_decision')
  if (dynamic_ok) {
    horizon <- protocol$irf_horizon
    irf <- vars::irf(fit, impulse=assets, response=assets, n.ahead=horizon,
                     ortho=TRUE, cumulative=FALSE, boot=TRUE, runs=500, seed=2026, ci=.95)
    table <- do.call(rbind, lapply(assets, function(shock) do.call(rbind, lapply(assets, function(effect) {
      data.frame(shock=shock, response=effect, horizon=0:horizon, irf=irf$irf[[shock]][, effect],
        lower_95=irf$Lower[[shock]][, effect], upper_95=irf$Upper[[shock]][, effect],
        order=paste(assets, collapse=';'), interval_method='residual bootstrap percentile, 500 draws, seed 2026')
    }))))
    save_table(table, 'var_irf')
    fevd <- vars::fevd(fit, n.ahead=horizon)
    stopifnot(all(vapply(fevd, function(m) max(abs(rowSums(m)-1)) < 1e-10, logical(1))))
    table <- do.call(rbind, lapply(assets, function(effect) do.call(rbind, lapply(assets, function(shock) {
      data.frame(response=effect, shock=shock, horizon=seq_len(horizon),
        variance_share_pct=100*fevd[[effect]][, shock], order=paste(assets, collapse=';'))
    }))))
    save_table(table, 'var_fevd')
  }
  cat('R PASS: VAR(', selected, '); stable=', chosen$stable,
      '; serial adequate=', chosen$serial_adequate, '\n', sep='')
}
