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
