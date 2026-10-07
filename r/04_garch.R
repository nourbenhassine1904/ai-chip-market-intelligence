# Phase 5: independent two-stage ARMA mean / symmetric GARCH variance, TRAIN only.
if (.Platform$OS.type == 'windows') invisible(Sys.setlocale('LC_CTYPE', 'English_United States.utf8'))
if (!file.exists('r/04_garch.R')) stop('Run from repository root.')
if (dir.exists('.cache/R-library')) .libPaths(c('.cache/R-library', .libPaths()))
required <- c('rugarch', 'FinTS')
missing <- required[!vapply(required, requireNamespace, logical(1), quietly=TRUE)]
if (length(missing)) stop(paste0('Missing packages. No automatic installation. In R run: install.packages(c(',
  paste(sprintf("'%s'", missing), collapse=', '), '))'))
options(digits=17)
protocol_path <- 'docs/phase5_protocol.csv'
rule_path <- 'docs/phase5_selection_rule.md'
protocol <- read.csv(protocol_path, stringsAsFactors=FALSE)
stopifnot(nrow(protocol)==1, protocol$return_variable=='NVDA_Log_Return',
          protocol$forecast_horizon==10, protocol$mean_burn==0)
input <- 'data/processed/market_train.csv'
scope <- 'TRAIN_only_volatility_no_final_evaluation'
reads <- character()
read_observations <- function(path) {
  if (!identical(path, input)) stop('Unauthorized market input.')
  expected <- paste0(normalizePath('.', winslash='/'), '/', input)
  if (normalizePath(path, winslash='/') != expected) stop('Redirected TRAIN path.')
  if (unname(tools::md5sum(path)) != protocol$train_md5) stop('Frozen TRAIN MD5 mismatch.')
  reads <<- c(reads, path)
  read.csv(path, stringsAsFactors=FALSE, check.names=FALSE)
}
train <- read_observations(input)
stopifnot(all(c('Date', 'NVDA_Log_Return', 'NVDA_Log_Price', 'NVDA_Adj_Close') %in% names(train)))
dates <- as.Date(train$Date, format='%Y-%m-%d')
stopifnot(nrow(train)==protocol$expected_rows, !anyNA(dates), !anyDuplicated(dates),
          all(diff(dates)>0), as.character(dates[1])==protocol$first_date,
          as.character(tail(dates,1))==protocol$last_date,
          all(is.finite(train$NVDA_Adj_Close)), all(train$NVDA_Adj_Close>0),
          all(is.finite(train$NVDA_Log_Price)), is.na(train$NVDA_Log_Return[1]),
          all(is.finite(train$NVDA_Log_Return[-1])),
          max(abs(log(train$NVDA_Adj_Close)-train$NVDA_Log_Price))<1e-12,
          max(abs(100*diff(train$NVDA_Log_Price)-train$NVDA_Log_Return[-1]))<1e-10)
returns <- train$NVDA_Log_Return[-1]
meta <- data.frame(language='R', scope=scope, train_md5=protocol$train_md5,
  protocol_md5=unname(tools::md5sum(protocol_path)), selection_rule_md5=unname(tools::md5sum(rule_path)),
  implementation_md5=unname(tools::md5sum('r/04_garch.R')))
save_table <- function(table, name) {
  dir.create('outputs/tables', recursive=TRUE, showWarnings=FALSE)
  for (field in names(meta)) table[[field]] <- meta[[field]]
  write.csv(table, paste0('outputs/tables/phase5_', name, '_r.csv'), row.names=FALSE,
            na='', fileEncoding='UTF-8')
}
guard_names <- c('market_train.csv only', 'market_test.csv not read', 'chronological order preserved',
  'backward percentage log-returns', 'mean filtering TRAIN only', 'ARCH-LM TRAIN only', 'GARCH fit TRAIN only',
  'distribution comparison TRAIN only', 'standardized residual diagnostics TRAIN only',
  'volatility forecast from TRAIN endpoint only', 'no realized holdout volatility read',
  'no final RMSE/MAE/MAPE', 'no final DM')
stopifnot(identical(reads, input))
save_table(data.frame(check=guard_names, status='PASS', evidence=c(
  rep('runtime input/dates/transformation assertion',4),
  rep('code scope audit: TRAIN arrays only; no realized future targets',9))), 'holdout_guard')
save_table(data.frame(rows=nrow(train), return_rows=length(returns), first_date=protocol$first_date,
  last_date=protocol$last_date, return_first_date=as.character(dates[2]), variable='NVDA_Log_Return',
  unit='daily percentage log-return', sha256_reference=protocol$train_sha256,
  sha256_verified=NA, md5_verified=TRUE, observation_reads=paste(reads, collapse=';')), 'train_manifest')
# Reuse actual historical diagnostics; do not refit any Phase 3A model.
for (language in c('r','python')) {
  previous <- read.csv(paste0('outputs/tables/phase3_arima_residual_diagnostics_', language, '.csv'))
  evidence <- subset(previous, scope=='train' & test %in% c('ARCH-LM', 'Jarque-Bera'))
  stopifnot(nrow(evidence)==4, all(evidence$p_value<.05))
}

messages <- character()
mean_fit <- withCallingHandlers(stats::arima(returns, order=c(1,0,1), include.mean=TRUE,
  method='ML', transform.pars=TRUE, optim.control=list(maxit=protocol$maxiter, reltol=1e-10)),
  warning=function(w) {messages <<- c(messages, conditionMessage(w)); invokeRestart('muffleWarning')})
innovations <- as.numeric(residuals(mean_fit))
stopifnot(length(innovations)==length(returns), all(is.finite(innovations)))
lb <- lapply(c(10,20), function(h) Box.test(innovations, lag=h, type='Ljung-Box', fitdf=2))
mu <- coef(mean_fit)['intercept']; phi <- coef(mean_fit)['ar1']; theta <- coef(mean_fit)['ma1']
mean_table <- data.frame(mean_model='ARMA(1,1)_with_mean', mean_mu=unname(mu), ar1=unname(phi), ma1=unname(theta),
  recursion_intercept=unname((1-phi)*mu), innovation_variance=mean_fit$sigma2, nobs=length(returns),
  additional_burn=0, converged=mean_fit$code==0, loglik=as.numeric(logLik(mean_fit)),
  AIC=AIC(mean_fit), BIC=BIC(mean_fit), ljung_box_p10=lb[[1]]$p.value, ljung_box_p20=lb[[2]]$p.value,
  mean_adequate_5pct=all(vapply(lb, function(z) z$p.value>=.05, logical(1))), warnings=paste(unique(messages),collapse=' | '))
save_table(mean_table, 'mean_filter')
save_table(data.frame(Date=as.character(dates[-1]), NVDA_Log_Return=returns, innovation=innovations), 'mean_innovations')
arch_tests <- function(residuals, model='mean_filter') {
  do.call(rbind, lapply(c(5,10,20), function(h) {
    test <- FinTS::ArchTest(residuals, lags=h, demean=FALSE)
    data.frame(model=model, test='ARCH-LM', lag=h, statistic=as.numeric(test$statistic),
      p_value=as.numeric(test$p.value), df=h, model_df=0, nobs=length(residuals), reject_5pct=test$p.value<.05)
  }))
}
pre <- arch_tests(innovations)
save_table(pre, 'arch_lm_pre_garch')
if (!isTRUE(mean_table$converged) || min(mean_table$ljung_box_p10,mean_table$ljung_box_p20)<protocol$mean_strong_failure_p) {
  stop('STOP before GARCH: common mean filter fails convergence or strong serial diagnostic.')
}
if (sum(pre$p_value<protocol$alpha)<protocol$arch_required_rejections) stop('STOP before GARCH: insufficient ARCH evidence.')

post_diagnostics <- function(z, model) {
  rows <- list()
  for (series in c('z','z_squared')) {
    values <- if (series=='z') z else z^2
    for (h in c(10,20)) {
      test <- Box.test(values, lag=h, type='Ljung-Box', fitdf=2)
      rows[[length(rows)+1]] <- data.frame(model=model, series=series, test='Ljung-Box', lag=h,
        statistic=as.numeric(test$statistic), p_value=test$p.value, df=h-2, model_df=2, nobs=length(z),
        reject_5pct=test$p.value<.05)
    }
  }
  arch_rows <- arch_tests(z,model); arch_rows$series <- 'z'
  table <- rbind(do.call(rbind,rows), arch_rows[,names(rows[[1]])])
  variance <- table$test=='ARCH-LM' | table$series=='z_squared'
  table$diagnostic_family <- ifelse(variance,'variance','mean')
  table$p_value_holm_variance <- NA_real_
  table$p_value_holm_variance[variance] <- p.adjust(table$p_value[variance],method='holm')
  table$reject_for_gate <- ifelse(variance,table$p_value_holm_variance<.05,table$p_value<.05)
  table
}

higher <- '--higher' %in% commandArgs(trailingOnly=TRUE)
if (higher) {
  gate <- read.csv('outputs/tables/phase5_higher_order_gate.csv',stringsAsFactors=FALSE)
  stopifnot(nrow(gate)==1, isTRUE(gate$higher_order_justified),
            gate$protocol_md5==meta$protocol_md5,gate$selection_rule_md5==meta$selection_rule_md5)
  specs <- data.frame(p=c(2,1),q=c(1,2),distribution=gate$baseline_distribution)
} else specs <- data.frame(p=1,q=1,distribution=c('Normal','Student-t'))
models <- list(); diagnostics <- list(); volatility <- list(); forecasts <- list()
set.seed(protocol$seed)
for (index in seq_len(nrow(specs))) {
  choice <- specs[index,]; p <- choice$p; q <- choice$q; distribution <- choice$distribution
  model <- sprintf('GARCH(%d,%d)_%s',p,q,distribution)
  spec <- rugarch::ugarchspec(variance.model=list(model='sGARCH',garchOrder=c(p,q)),
    mean.model=list(armaOrder=c(0,0),include.mean=FALSE,archm=FALSE),
    distribution.model=if (distribution=='Normal') 'norm' else 'std')
  messages <- character()
  fit <- withCallingHandlers(rugarch::ugarchfit(spec=spec,data=innovations,out.sample=0,
    solver='solnp',solver.control=list(tol=1e-8,outer.iter=1000,inner.iter=2000),
    fit.control=list(stationarity=1,scale=0,rec.init='all')),
    warning=function(w) {messages <<- c(messages,conditionMessage(w));invokeRestart('muffleWarning')})
  parameters <- rugarch::coef(fit)
  omega <- unname(parameters['omega'])
  alpha <- unname(parameters[paste0('alpha',seq_len(p))]); beta <- unname(parameters[paste0('beta',seq_len(q))])
  shape <- if (distribution=='Student-t') unname(parameters['shape']) else NA_real_
  persistence <- sum(alpha)+sum(beta)
  sigma <- as.numeric(rugarch::sigma(fit))
  stopifnot(length(sigma)==length(innovations),all(is.finite(sigma)),all(sigma>0))
  z <- innovations/sigma
  diag <- post_diagnostics(z,model)
  probabilities <- c(.01,.02,.05,.95,.98,.99)
  theoretical <- if (distribution=='Normal') qnorm(probabilities) else qt(probabilities,df=shape)*sqrt((shape-2)/shape)
  tail_rmse <- sqrt(mean((as.numeric(quantile(z,probabilities,type=7))-theoretical)^2))
  ll <- as.numeric(rugarch::likelihood(fit)); n <- length(innovations); k <- length(parameters)
  valid <- rugarch::convergence(fit)==0 && all(is.finite(parameters)) && is.finite(ll) &&
    omega>0 && all(alpha>=0) && all(beta>=0) && (distribution=='Normal' || shape>2)
  stationary <- valid && persistence>=0 && persistence<1
  variance <- if (stationary) omega/(1-persistence) else NA_real_
  half_life <- if (stationary && persistence>0 && p==1 && q==1) log(.5)/log(persistence) else NA_real_
  mean_rejections <- sum(diag$reject_for_gate[diag$diagnostic_family=='mean'])
  variance_rejections <- sum(diag$reject_for_gate[diag$diagnostic_family=='variance'])
  native_ic <- rugarch::infocriteria(fit)
  models[[index]] <- data.frame(model=model,distribution=distribution,p=p,q=q,
    converged=rugarch::convergence(fit)==0,convergence_code=rugarch::convergence(fit),
    loglik=ll,AIC=-2*ll+2*k,BIC=-2*ll+log(n)*k,AIC_per_observation=as.numeric(native_ic[1]),
    BIC_per_observation=as.numeric(native_ic[2]),omega=omega,alpha1=alpha[1],alpha2=if(p==2)alpha[2] else 0,
    beta1=beta[1],beta2=if(q==2)beta[2] else 0,persistence=persistence,shape_df_if_applicable=shape,
    variance_stationary=stationary,unconditional_variance=variance,half_life_sessions=half_life,nobs=n,
    variance_parameter_count=k,tail_quantile_rmse=tail_rmse,mean_rejections=mean_rejections,
    variance_rejections=variance_rejections,backcast=mean(innovations^2),
    initialization='native rec.init=all; full innovation second moment',solver='solnp',
    variance_mean='Zero; no mean re-estimation',power=2,asymmetric_order=0,
    warnings=paste(unique(messages),collapse=' | '),valid=valid,
    diagnostically_adequate=valid && stationary && mean_rejections==0 && variance_rejections==0)
  diagnostics[[index]] <- diag
  volatility[[index]] <- data.frame(Date=as.character(dates[-1]),model=model,NVDA_Log_Return=returns,
    innovation=innovations,conditional_sigma=sigma,standardized_residual=z)
  forecast <- rugarch::ugarchforecast(fit,n.ahead=protocol$forecast_horizon,n.roll=0)
  predicted_sigma <- as.numeric(rugarch::sigma(forecast))
  stopifnot(length(predicted_sigma)==10,all(is.finite(predicted_sigma)),all(predicted_sigma>0))
  expected_next <- omega + sum(alpha*tail(innovations,p)[p:1]^2) + sum(beta*tail(sigma,q)[q:1]^2)
  stopifnot(abs(predicted_sigma[1]^2-expected_next)<1e-7)
  forecasts[[index]] <- data.frame(model=model,horizon=1:10,origin_date=protocol$last_date,
    forecast_variance=predicted_sigma^2,forecast_sigma=predicted_sigma,
    annualized_sigma_if_reported=predicted_sigma*sqrt(protocol$annualization_sessions),
    variance_unit='percentage_points_squared',sigma_unit='daily_percent',
    forecast_target='innovation variance, not ARMA return forecast-error variance')
}
suffix <- if (higher) 'higher' else 'baseline'
save_table(do.call(rbind,models),paste0('models_',suffix))
save_table(do.call(rbind,diagnostics),paste0('diagnostics_',suffix))
save_table(do.call(rbind,volatility),paste0('volatility_',suffix))
save_table(do.call(rbind,forecasts),paste0('forecasts_',suffix))
save_table(data.frame(package=c('R',required),version=c(as.character(getRversion()),
  vapply(required,function(p)as.character(packageVersion(p)),character(1)))),'runtime_versions')
cat('R PASS: mean gate and ARCH gate passed;',length(models),suffix,'GARCH fits\n')
print(do.call(rbind,models)[,c('model','converged','AIC','BIC','persistence','mean_rejections','variance_rejections')],row.names=FALSE)
