# Decision Log

## D001 — Asset selection

Decision:  
Use NVDA, AMD and SOXX.

Reason:  
The project requires a multidimensional financial setting and the three
assets provide company-level and sector-level information.

Status:  
Accepted

---

## D002 — Main forecasting target

Decision:  
Use NVDA as the principal forecasting target.

Status:  
Accepted

---

## D003 — Data split

Decision:  
90% train / 10% test, chronological.

Status:  
Accepted

---

## D004 — Conditional models

Decision:  
SARIMA, VECM and advanced GARCH variants will only be retained when
statistical diagnostics justify them.

Status:  
Accepted

---

## D005 — Canonical data acquisition

Decision:

Python/yfinance is the canonical acquisition pipeline.
R will later consume the same validated dataset.

Reason:

Avoid divergent datasets between languages and team members.

Status:

Accepted

---

## D006 — Raw market data and Git

Decision:

Raw downloaded market data is kept locally and excluded from Git.

Reason:

The repository stores reproducible acquisition code instead of
duplicating generated raw files.

Status:

Accepted

---

## D007 — Canonical aligned dataset

Decision:

Use one aligned wide-format dataset built from NVDA, AMD and SOXX
as the common input for downstream analyses.

Reason:

Ensure all team members and both Python/R pipelines work from
the same trading dates and the same validated market observations.

Status:

Accepted

---

## D008 — Alignment strategy

Decision:

Align NVDA, AMD and SOXX using the intersection of observed
trading dates.

Reason:

Avoid artificial calendar rows and avoid imputing market observations.

Status:

Accepted

---

## D009 — Reference historical price

Decision:
Use Adjusted Close as the main historical price series
for log-price and return transformations.

Reason:
Adjusted Close provides a historically comparable price series
after relevant corporate-action adjustments.

Status:
Accepted

---

## D010 — Final holdout policy

Decision:
Reserve the last 10% of observations as a strictly chronological
final test set.

Reason:
Prevent temporal information leakage and preserve a genuine
out-of-sample evaluation period.

Status:
Accepted

---

## D011 — Diagnostic scope

Decision:
Use the training period for diagnostics that influence model selection.

Reason:
The final test set must not influence transformation or model choices.

Status:
Accepted
