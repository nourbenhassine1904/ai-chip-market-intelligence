# Phase 3A: pedagogical R implementation. TRAIN only, no final forecasting.
# Run: Rscript r/02_arima.R from the repository root.

if (.Platform$OS.type == "windows") {
  # Some shells export C.UTF-8, which Windows R does not recognize.
  invisible(Sys.setlocale("LC_CTYPE", "English_United States.utf8"))
}
if (!file.exists("r/02_arima.R")) stop("Run from the repository root.")
local_library <- file.path(".cache", "R-library")
if (dir.exists(local_library)) .libPaths(c(local_library, .libPaths()))
required <- c("forecast", "tseries", "FinTS")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) {
  stop(paste0(
    "Missing R packages: ", paste(missing, collapse = ", "),
    ". No installation performed. In R run: dir.create('.cache/R-library', ",
    "recursive=TRUE, showWarnings=FALSE); install.packages(c(",
    paste(sprintf("'%s'", missing), collapse = ", "),
    "), lib='.cache/R-library', repos='https://cloud.r-project.org')"
  ))
}
versions <- data.frame(
  package = c("R", required),
  version = c(as.character(getRversion()),
              vapply(required, function(p) as.character(packageVersion(p)), character(1)))
)
print(versions, row.names = FALSE)
dir.create("outputs/tables", recursive = TRUE, showWarnings = FALSE)
dir.create("outputs/figures/phase3", recursive = TRUE, showWarnings = FALSE)
save_table <- function(x, name) {
  write.csv(x, file.path("outputs/tables", paste0("phase3_", name, ".csv")),
            row.names = FALSE, na = "", fileEncoding = "UTF-8")
}
save_table(versions, "runtime_versions_r")

allowed <- c(
  "data/processed/market_train.csv", "outputs/tables/phase2_split_metadata.csv",
  "outputs/tables/phase2_stationarity_summary.csv",
  "outputs/tables/phase2_weekday_returns.csv", "outputs/tables/phase2_leakage_check.csv"
)
reads <- character()
read_input <- function(path) {
  if (!path %in% allowed) stop(paste("Unauthorized Phase 3A input:", path))
  reads <<- c(reads, path)
  read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
}
input <- "data/processed/market_train.csv"
train <- read_input(input)
meta <- read_input("outputs/tables/phase2_split_metadata.csv")
dates <- as.Date(train$Date, format = "%Y-%m-%d")
stopifnot(nrow(meta) == 1, nrow(train) == meta$train_rows,
          !anyNA(dates), !anyDuplicated(dates), all(diff(dates) > 0),
          as.character(dates[1]) == meta$train_start,
          as.character(tail(dates, 1)) == meta$train_end,
          all(is.finite(train$NVDA_Adj_Close)), all(train$NVDA_Adj_Close > 0))
y <- log(train$NVDA_Adj_Close)
delta <- diff(y)
stopifnot(max(abs(y - train$NVDA_Log_Price)) < 1e-12,
          max(abs(delta - train$NVDA_Log_Return[-1] / 100)) < 1e-12)
phase2 <- read_input("outputs/tables/phase2_stationarity_summary.csv")
phase2 <- subset(phase2, ticker == "NVDA" & scope == "train")
stopifnot(phase2$mechanical_summary[phase2$series == "Log_Price"] == "nonstationary_supported",
          phase2$mechanical_summary[phase2$series == "Log_Return"] == "stationary_supported")
previous_guard <- read_input("outputs/tables/phase2_leakage_check.csv")
stopifnot(all(previous_guard$status == "PASS"))

# d is fixed by complementary Phase 2 tests, not chosen by auto.arima.
ndiffs_results <- data.frame(
  phase2_conclusion = "Log_Price nonstationary; first difference stationary",
  auxiliary_test = c("KPSS level (forecast default)", "KPSS trend", "ADF trend"),
  ndiffs_result = c(forecast::ndiffs(y, test = "kpss", type = "level"),
                    forecast::ndiffs(y, test = "kpss", type = "trend"),
                    forecast::ndiffs(y, test = "adf", type = "trend")),
  final_d = 1L
)
ndiffs_results$agrees_with_final_d <- ndiffs_results$ndiffs_result == 1L
save_table(ndiffs_results, "d_justification_r")
if (any(!ndiffs_results$agrees_with_final_d)) {
  warning("ndiffs disagreement retained in phase3_d_justification_r.csv; d=1 follows Phase 2.")
}

# Five sessions, not five calendar days. STL existence is not seasonal evidence.
seasonal_ts <- ts(y, frequency = 5)
ns_default <- forecast::nsdiffs(seasonal_ts, test = "seas", max.D = 1)
ns_ocsb <- forecast::nsdiffs(seasonal_ts, test = "ocsb", max.D = 1)
stl_fit <- stl(seasonal_ts, s.window = 7, t.window = 11, l.window = 7, robust = TRUE)
components <- stl_fit$time.series
strength <- max(0, 1 - var(components[, "remainder"]) /
                  var(components[, "seasonal"] + components[, "remainder"]))
ac <- as.numeric(acf(delta, lag.max = 20, plot = FALSE)$acf)[-1]
pc <- as.numeric(pacf(delta, lag.max = 20, plot = FALSE)$acf)
seasonal_ac <- ac[c(5, 10, 15, 20)]
bound <- qnorm(1 - 0.05 / (2 * 4)) / sqrt(length(delta))
weekday <- read_input("outputs/tables/phase2_weekday_returns.csv")
weekday <- subset(weekday, ticker == "NVDA" & scope == "train")
weekday_factor <- factor(as.integer(format(dates[-1], "%u")))
weekday_p <- anova(lm(delta ~ weekday_factor))$`Pr(>F)`[1]
sarima_justified <- strength > 0.64 && sum(abs(seasonal_ac) > bound) >= 3 &&
  weekday_p < 0.05 && ns_default > 0
gate <- data.frame(
  evidence = c("Phase2_STL_period_5", "returns_seasonal_acf", "Phase2_weekday_means_pct",
               "weekday_ANOVA_auxiliary_p", "R_nsdiffs_frequency_5_seas",
               "R_nsdiffs_frequency_5_ocsb", "sarima_justified"),
  result = c(strength, paste(sprintf("lag%s=%.8f", c(5, 10, 15, 20), seasonal_ac), collapse = "; "),
             paste(sprintf("%s=%.6f", weekday$weekday, weekday$mean), collapse = "; "),
             weekday_p, ns_default, ns_ocsb, sarima_justified),
  interpretation = c(
    "Robust TRAIN STL; component alone not proof. Smoothers differ slightly from Python.",
    sprintf("Bonferroni four-lag bound=%.6f; %d/4 exceed.", bound, sum(abs(seasonal_ac) > bound)),
    "Descriptive weekdays; holidays prevent equivalence to five-session periodicity.",
    "Auxiliary TRAIN mean test; heavy tails/unequal variance limit inference.",
    "forecast seasonal-strength auxiliary, frequency=5 trading sessions.",
    "OCSB seasonal-unit-root auxiliary; not a test for every seasonal mean effect.",
    "Joint evidence insufficient: no SARIMA estimated."
  )
)
save_table(gate, "seasonality_gate_r")
if (sarima_justified) stop("Seasonal evidence changed: document rationale before SARIMA estimation.")
save_table(data.frame(lag = 1:20, acf = ac, pacf = pc, scope = "train",
                      pointwise_95_bound = 1.96 / sqrt(length(delta))), "acf_pacf_numeric_r")

model_id <- function(p, d, q, drift) {
  sprintf("ARIMA(%d,%d,%d)_%s", p, d, q, if (drift) "drift" else "no_drift")
}
diagnostics <- function(res, p, q, model) {
  stopifnot(length(res) > 25, all(is.finite(res)))
  lb <- lapply(c(10, 20), function(lag) Box.test(res, lag = lag, type = "Ljung-Box", fitdf = p + q))
  jb <- tseries::jarque.bera.test(res)
  # demean=FALSE matches Python het_arch(ddof=0) on the same raw innovations.
  arch <- lapply(c(5, 10, 20), function(lag) FinTS::ArchTest(res, lags = lag, demean = FALSE))
  tests <- c(lb, list(jb), arch)
  data.frame(
    language = "R", model = model, scope = "train",
    test = c("Ljung-Box", "Ljung-Box", "Jarque-Bera", rep("ARCH-LM", 3)),
    lag = c(10, 20, 0, 5, 10, 20),
    statistic = vapply(tests, function(z) unname(z$statistic), numeric(1)),
    p_value = vapply(tests, function(z) z$p.value, numeric(1)),
    df = c(10 - p - q, 20 - p - q, 2, 5, 10, 20),
    model_df = c(p + q, p + q, 0, 0, 0, 0), nobs = length(res),
    reject_5pct = vapply(tests, function(z) z$p.value < 0.05, logical(1))
  )
}
fit_record <- function(fit, p, q, drift, source, messages = "", error = "") {
  row <- data.frame(
    language = "R", source = source, model = model_id(p, 1, q, drift),
    p = p, d = 1L, q = q, drift = drift, seasonal_order = "(0,0,0,0)", scope = "train",
    converged = FALSE, k = NA_real_, n_eff = length(y) - 1,
    log_likelihood = NA_real_, AIC = NA_real_, AICc = NA_real_, BIC = NA_real_,
    ljung_box_10 = NA_real_, ljung_box_20 = NA_real_, warnings = messages, error = error
  )
  if (!is.null(fit)) {
    row$converged <- isTRUE(fit$code == 0)
    row$k <- length(coef(fit)) + 1L
    row$log_likelihood <- as.numeric(logLik(fit))
    row$AIC <- fit$aic
    row$AICc <- fit$aicc
    row$BIC <- fit$bic
    diag <- diagnostics(as.numeric(residuals(fit))[-1], p, q, row$model)
    row$ljung_box_10 <- diag$p_value[1]
    row$ljung_box_20 <- diag$p_value[2]
  }
  row
}
specs <- data.frame(p = c(0, 0, 1, 0, 1), q = c(0, 0, 0, 1, 1),
                    drift = c(FALSE, TRUE, TRUE, TRUE, TRUE))
fits <- list()
rows <- list()
for (i in seq_len(nrow(specs))) {
  spec <- specs[i, ]
  messages <- character()
  error <- ""
  fit <- tryCatch(withCallingHandlers(
    forecast::Arima(y, order = c(spec$p, 1, spec$q), include.drift = spec$drift,
                    method = "ML", optim.control = list(maxit = 1000)),
    warning = function(w) { messages <<- c(messages, conditionMessage(w)); invokeRestart("muffleWarning") }
  ), error = function(e) { error <<- conditionMessage(e); NULL })
  row <- fit_record(fit, spec$p, spec$q, spec$drift, "manual", paste(unique(messages), collapse = " | "), error)
  rows[[i]] <- row
  fits[row$model] <- list(fit)
}
manual <- do.call(rbind, rows)

auto_messages <- character()
auto_error <- ""
auto_fit <- NULL
trace_lines <- capture.output({
  auto_fit <- tryCatch(withCallingHandlers(
    forecast::auto.arima(y, d = 1, seasonal = FALSE, stepwise = FALSE,
                         approximation = FALSE, allowdrift = TRUE,
                         max.p = 3, max.q = 3, max.order = 6, ic = "aicc",
                         method = "ML", trace = TRUE, optim.control = list(maxit = 1000)),
    warning = function(w) { auto_messages <<- c(auto_messages, conditionMessage(w)); invokeRestart("muffleWarning") }
  ), error = function(e) { auto_error <<- conditionMessage(e); NULL })
})
cat(paste(trace_lines, collapse = "\n"), "\n")
save_table(data.frame(trace_line = trace_lines), "auto_arima_trace_r")
pool <- manual
if (!is.null(auto_fit)) {
  ord <- forecast::arimaorder(auto_fit)
  auto_drift <- "drift" %in% names(coef(auto_fit))
  auto <- fit_record(auto_fit, ord[1], ord[3], auto_drift, "auto.arima",
                     paste(unique(auto_messages), collapse = " | "))
  auto$selected_by_auto <- TRUE
  if (!auto$model %in% names(fits)) {
    pool <- rbind(pool, auto[, names(manual)])
    fits[auto$model] <- list(auto_fit)
  }
} else {
  auto <- fit_record(NULL, 0, 0, FALSE, "auto.arima", paste(unique(auto_messages), collapse = " | "), auto_error)
  auto$model <- NA_character_
  auto$selected_by_auto <- FALSE
}
save_table(auto, "auto_arima_r")

valid <- subset(pool, converged & is.finite(AICc) & is.finite(BIC))
if (!nrow(valid)) { save_table(manual, "arima_manual_candidates_r"); stop("No valid R fit.") }
adequate <- subset(valid, ljung_box_10 >= 0.05 & ljung_box_20 >= 0.05)
eligible <- if (nrow(adequate)) adequate else valid
near <- subset(eligible, AICc <= min(eligible$AICc) + 2)
selected <- near[order(near$k, near$BIC, near$AICc, near$model), ][1, ]
manual$selected_candidate <- manual$model == selected$model
pool$selected_candidate <- pool$model == selected$model
save_table(manual, "arima_manual_candidates_r")
save_table(pool, "arima_selection_pool_r")
auto$selected_candidate <- !is.na(auto$model) & auto$model == selected$model
save_table(auto, "auto_arima_r")
selected_fit <- fits[[selected$model]]
res <- as.numeric(residuals(selected_fit))[-1]
diag <- diagnostics(res, selected$p, selected$q, selected$model)
save_table(diag, "arima_residual_diagnostics_r")
summary <- data.frame(
  language = "R", model = selected$model, scope = "train",
  ljung_box_10 = diag$p_value[1], ljung_box_20 = diag$p_value[2], jarque_bera = diag$p_value[3],
  arch_lm_5 = diag$p_value[4], arch_lm_10 = diag$p_value[5], arch_lm_20 = diag$p_value[6],
  residual_mean = mean(res), residual_std = sd(res),
  white_noise_mean_supported = all(diag$p_value[1:2] >= 0.05),
  normality_supported = diag$p_value[3] >= 0.05,
  arch_effect_supported = all(diag$p_value[4:6] < 0.05),
  qualification = "provisional selected mean model"
)
save_table(summary, "arima_diagnostic_summary_r")
coefficient_rows <- lapply(names(fits), function(id) {
  fit <- fits[[id]]
  if (is.null(fit)) return(NULL)
  data.frame(language = "R", model = id, term = c(names(coef(fit)), "sigma2"),
             estimate = c(unname(coef(fit)), fit$sigma2),
             standard_error = c(sqrt(diag(fit$var.coef)), NA_real_),
             selected_candidate = id == selected$model)
})
# ARIMA(0,1,0) without drift has no mean coefficients.
coefficient_rows <- Filter(Negate(is.null), coefficient_rows)
save_table(do.call(rbind, coefficient_rows), "arima_coefficients_r")
save_table(data.frame(
  language = "R", input = input, scope = "train", rows = length(y), effective_rows = length(delta),
  first_date = as.character(dates[1]), last_date = as.character(tail(dates, 1)),
  md5 = unname(tools::md5sum(input)), sum_log_price = sum(y), sum_delta_log_price = sum(delta)
), "train_manifest_r")
save_table(data.frame(
  check = c(paste0("r_", c("fit", "order_selection", "residual_diagnostics", "seasonality_gate"), "_TRAIN_only"),
            "r_all_observation_reads_allowlisted", "r_no_forecast_or_final_metrics"),
  status = "PASS",
  details = c(rep("Closed input allowlist; validated y/delta used by all stages.", 4),
              paste(reads, collapse = "; "), "Code audit: no final forecasts or evaluation metrics.")
), "holdout_guard_r")

png("outputs/figures/phase3/nvda_log_price_acf_pacf_train_r.png", width = 1500, height = 900, res = 140)
par(mfrow = c(2, 2))
forecast::Acf(y, lag.max = 40, main = "NVDA log-price ACF - TRAIN")
forecast::Pacf(y, lag.max = 40, main = "NVDA log-price PACF - TRAIN")
forecast::Acf(delta, lag.max = 40, main = "Delta log-price ACF - TRAIN")
forecast::Pacf(delta, lag.max = 40, main = "Delta log-price PACF - TRAIN")
dev.off()
png("outputs/figures/phase3/nvda_arima_checkresiduals_r.png", width = 1500, height = 1000, res = 140)
forecast::checkresiduals(selected_fit, lag = 20)
dev.off()
png("outputs/figures/phase3/nvda_arima_residuals.png", width = 1500, height = 600, res = 140)
plot(dates[-1], res, type = "l", xlab = "Date", ylab = "Log-price innovation",
     main = paste("NVDA", selected$model, "- TRAIN residuals"))
abline(h = 0, col = "gray50")
dev.off()
png("outputs/figures/phase3/nvda_arima_residual_acf.png", width = 1200, height = 600, res = 140)
forecast::Acf(res, lag.max = 40, main = paste("Residual ACF -", selected$model, "- TRAIN"))
dev.off()
png("outputs/figures/phase3/nvda_arima_residual_qqplot.png", width = 900, height = 800, res = 140)
qqnorm(res, main = paste("Normal QQ -", selected$model, "- TRAIN"))
qqline(res, col = "steelblue")
dev.off()
png("outputs/figures/phase3/nvda_arima_squared_residual_acf.png", width = 1200, height = 600, res = 140)
forecast::Acf(res^2, lag.max = 40, main = paste("Squared residual ACF -", selected$model, "- TRAIN"))
dev.off()
print(pool, row.names = FALSE)
print(diag, row.names = FALSE)
cat("Provisional selected mean model:", selected$model, "\n")
cat("No forecasting or final evaluation performed. Run Python --summarize for shared tables.\n")
