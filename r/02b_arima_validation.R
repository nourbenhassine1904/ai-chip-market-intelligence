# Phase 3B: run from repository root. No final test input or full-TRAIN refit.
if (.Platform$OS.type == "windows") {
  invisible(Sys.setlocale("LC_CTYPE", "English_United States.utf8"))
}
if (!file.exists("r/02b_arima_validation.R")) stop("Run from repository root.")
local_library <- file.path(".cache", "R-library")
if (dir.exists(local_library)) .libPaths(c(local_library, .libPaths()))
if (!requireNamespace("forecast", quietly = TRUE)) {
  stop("forecast missing; install explicitly in R before running this script.")
}
options(digits = 17)
scope <- "TRAIN_only_internal_rolling_origin"
input <- "data/processed/market_train.csv"
protocol_path <- "docs/phase3b_validation_protocol.csv"
candidates_path <- "docs/phase3b_validation_candidates.csv"
protocol <- read.csv(protocol_path, stringsAsFactors = FALSE)
candidates <- read.csv(candidates_path, stringsAsFactors = FALSE)
stopifnot(nrow(protocol) == 1)
reads <- character()
read_observations <- function(path) {
  if (!identical(path, input)) stop("Unauthorized market input.")
  expected <- paste0(normalizePath(".", winslash = "/"), "/", input)
  if (normalizePath(path, winslash = "/") != expected) stop("Redirected TRAIN path.")
  reads <<- c(reads, path)
  read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
}
if (unname(tools::md5sum(input)) != protocol$train_md5) stop("Frozen TRAIN MD5 mismatch.")
train <- read_observations(input)
dates <- as.Date(train$Date, format = "%Y-%m-%d")
prices <- train$NVDA_Adj_Close
stopifnot(nrow(train) == protocol$expected_rows,
          !anyNA(dates), !anyDuplicated(dates), all(diff(dates) > 0),
          as.character(dates[1]) == protocol$first_date,
          as.character(tail(dates, 1)) == protocol$last_date,
          all(is.finite(prices)), all(prices > 0))
y <- log(prices)
horizons <- c(protocol$horizon_1, protocol$horizon_2)
# origin_index and target_index are exported zero-based, matching Python.
indices <- seq.int(protocol$initial_size - 1L, length(y) - max(horizons) - 1L,
                   by = protocol$origin_step)
origins <- do.call(rbind, lapply(indices, function(origin) {
  data.frame(origin_index = origin, train_size = origin + 1L,
             origin_date = as.character(dates[origin + 1L]), horizon = horizons,
             target_index = origin + horizons,
             target_date = as.character(dates[origin + horizons + 1L]))
}))
forecasts <- list()
fit_rows <- list()
for (number in seq_along(indices)) {
  origin <- indices[number]
  history <- y[seq_len(origin + 1L)]
  for (j in seq_len(nrow(candidates))) {
    spec <- candidates[j, ]
    prediction <- rep(NA_real_, max(horizons))
    price_prediction <- prediction
    converged <- FALSE
    usable <- FALSE
    messages <- character()
    error <- ""
    method <- ""
    tryCatch(withCallingHandlers({
      if (spec$model == "Naive") {
        prediction <- rep(tail(history, 1), max(horizons))
        converged <- TRUE
        method <- "analytic last observation"
      } else if (spec$model == "RW_drift") {
        prediction <- tail(history, 1) + seq_len(max(horizons)) * mean(diff(history))
        converged <- TRUE
        method <- "analytic ML drift"
      } else {
        fit <- forecast::Arima(history, order = c(spec$p, spec$d, spec$q),
                               include.drift = spec$drift, method = "ML",
                               optim.control = list(maxit = protocol$maxiter))
        converged <- !is.null(fit$code) && fit$code == 0
        prediction <- as.numeric(forecast::forecast(fit, h = max(horizons))$mean)
        method <- "forecast::Arima ML/default start"
      }
      price_prediction <- exp(prediction)
      if (spec$model == "Naive") price_prediction[] <- prices[origin + 1L]
      if (length(prediction) != max(horizons) || any(!is.finite(price_prediction)) ||
          any(price_prediction <= 0)) stop("Invalid forecast/back-transformation.")
      usable <- converged
    }, warning = function(w) {
      messages <<- c(messages, conditionMessage(w))
      invokeRestart("muffleWarning")
    }), error = function(e) { error <<- conditionMessage(e) })
    fit_rows[[length(fit_rows) + 1L]] <- data.frame(
      language = "R", implementation = "forecast/analytic baselines", validation_scope = scope,
      model = spec$model, origin_index = origin, origin_date = as.character(dates[origin + 1L]),
      train_size = length(history), fit_last_index = origin, converged = converged,
      usable = usable, method = method, warnings = paste(unique(messages), collapse = " | "), error = error
    )
    for (h in horizons) {
      forecasts[[length(forecasts) + 1L]] <- data.frame(
        language = "R", implementation = "forecast/analytic baselines", validation_scope = scope,
        model = spec$model, origin_index = origin, train_size = length(history),
        origin_date = as.character(dates[origin + 1L]), horizon = h,
        target_index = origin + h, target_date = as.character(dates[origin + h + 1L]),
        converged = converged, usable = usable, actual_price = prices[origin + h + 1L],
        actual_log = y[origin + h + 1L], forecast_log = if (usable) prediction[h] else NA_real_,
        forecast_price = if (usable) price_prediction[h] else NA_real_
      )
    }
  }
  cat(sprintf("R origin %d/%d completed\n", number, length(indices)))
  flush.console()
}
forecasts <- do.call(rbind, forecasts)
fits <- do.call(rbind, fit_rows)
dir.create("outputs/tables", recursive = TRUE, showWarnings = FALSE)
save_table <- function(table, name) {
  write.csv(table, file.path("outputs/tables", paste0("phase3b_", name, ".csv")),
            row.names = FALSE, na = "", fileEncoding = "UTF-8")
}
checks <- c(
  only_market_train_observations_read = identical(reads, input),
  no_market_test_read = identical(reads, input),
  no_holdout_dates_used = max(origins$target_date) <= tail(train$Date, 1),
  no_full_data_refit = all(fits$train_size < nrow(train)),
  validation_origins_inside_TRAIN = all(origins$origin_index >= 0 & origins$target_index < nrow(train)),
  forecasts_use_past_information_only = all(fits$fit_last_index == fits$origin_index & fits$train_size == fits$origin_index + 1L),
  correct_horizon_alignment = all(origins$target_index == origins$origin_index + origins$horizon),
  no_random_shuffle = all(diff(origins$origin_index) >= 0) && all(diff(dates) > 0),
  no_ordinary_K_fold = all(origins$train_size == origins$origin_index + 1L),
  all_models_same_origin_target_grid = all(vapply(candidates$model, function(model_name) {
    grid <- forecasts[forecasts$model == model_name, names(origins)]
    rownames(grid) <- NULL
    identical(grid, origins)
  }, logical(1))),
  dates_match_observed_TRAIN_indices = all(origins$origin_date == as.character(dates[origins$origin_index + 1L])) &&
    all(origins$target_date == as.character(dates[origins$target_index + 1L]))
)
guard <- data.frame(language = "R", check = names(checks), status = ifelse(checks, "PASS", "FAIL"),
                    details = "Measured prefix/grid assertion plus code audit of closed reader and expanding loop")
save_table(guard, "holdout_guard_r")
if (!all(checks)) stop("FAIL in R holdout guard; STOP.")
metric_rows <- list()
for (model in candidates$model) {
  for (h in horizons) {
    # Avoid subset() masking the loop variable `model` with its data column.
    group <- forecasts[forecasts$model == model & forecasts$horizon == h, ]
    stopifnot(nrow(group) == length(indices))
    good <- subset(group, usable)
    err <- good$forecast_price - good$actual_price
    log_err <- good$forecast_log - good$actual_log
    metric_rows[[length(metric_rows) + 1L]] <- data.frame(
      language = "R", implementation = "forecast/analytic baselines", validation_scope = scope,
      model = model, horizon = h, n_origins = nrow(group), n_forecasts = nrow(good),
      failed_fits = nrow(group) - nrow(good), nonconverged_fits = sum(!group$converged),
      evaluation_sample = "available converged origins; incomplete candidates cannot lock",
      MSE = if (length(err)) mean(err^2) else NA_real_,
      RMSE = if (length(err)) sqrt(mean(err^2)) else NA_real_,
      MAE = if (length(err)) mean(abs(err)) else NA_real_,
      MAPE = if (length(err)) 100 * mean(abs(err) / good$actual_price) else NA_real_,
      log_MAE = if (length(err)) mean(abs(log_err)) else NA_real_,
      log_RMSE = if (length(err)) sqrt(mean(log_err^2)) else NA_real_
    )
  }
}
metrics <- do.call(rbind, metric_rows)
save_table(origins, "origins_r")
save_table(forecasts, "forecasts_r")
save_table(fits, "fit_log_r")
save_table(metrics, "validation_metrics_r")
manifest <- data.frame(
  language = "R", rows = nrow(train), first_date = train$Date[1], last_date = tail(train$Date, 1),
  train_md5 = unname(tools::md5sum(input)), protocol_md5 = unname(tools::md5sum(protocol_path)),
  candidates_md5 = unname(tools::md5sum(candidates_path)), initial_size = protocol$initial_size,
  origin_step = protocol$origin_step, n_origins = length(indices), R_version = as.character(getRversion()),
  forecast_version = as.character(utils::packageVersion("forecast"))
)
save_table(manifest, "manifest_r")
print(metrics, row.names = FALSE)
cat("R validation completed. Generate common reports/lock without refitting:\n",
    "python python/02b_arima_validation.py --summarize\n")
