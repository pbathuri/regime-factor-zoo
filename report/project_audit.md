# RegimeFactorZoo — Project Audit

*Snapshot as of 2026-07-26. Written before reading Baba-Yara's "In Search of
Sparsity" working paper in depth and before Phases 4-5 begin.*

Purpose of this document: a single place that records what has actually been
built, validated, and proven so far — as opposed to what's planned. Every
number below was produced by code in this repo, not copied from a paper.

---

## Status at a glance

| Phase | What it answers | Status | Key result |
|---|---|---|---|
| 0 — Data layer | Can we get trustworthy CRSP/Compustat/OSAP data, dual-sourced? | ✅ Done | WRDS primary + Ken French/yfinance fallback; dual-source FF3 agrees to <1bp |
| 1 — FF3 from scratch | Can we rebuild Mkt-RF/SMB/HML from raw prices + fundamentals? | ✅ Done, validated | SMB corr 0.976, HML corr 0.965 vs Ken French (726 months, 1964-2024) |
| 2 — Fama-MacBeth | Is factor risk actually *priced* in the cross-section? | ✅ Done | HML priced (t=2.20), SMB not (t=0.96), MKT significant but wrong sign (t=-2.07) |
| 3 — Factor zoo (OSAP) | Do individual firm characteristics predict returns? | ✅ Done | 8 of 9 OSAP characteristics significant, `BM` t=6.07 |
| 4 — Sparse selection | Of many correlated characteristics, which carry independent information? | ⬜ Not started | This is Baba-Yara's actual method |
| 5 — Regime-stability split | Does the sparse selection change across VIX regimes? | ⬜ Not started | Original contribution |
| 6 — Memo + outreach | Package results, email Baba-Yara | ⬜ Not started | |

---

## Phase 0 — Data layer

**Goal:** trustworthy, dual-sourced raw data so results don't depend on one
vendor being right.

- **Primary:** WRDS (CRSP monthly/daily, Compustat annual/quarterly, CRSP-Compustat
  link table, `ff.factors_monthly`) via `src/data/wrds_pull_*.py`.
- **Fallback:** Ken French Data Library + `yfinance`, for reviewers without WRDS
  credentials — `src/data/download_factors.py`.
- **Validation:** WRDS-sourced FF3 vs. Ken French published FF3 agree to <1bp
  (commit `bf5bc50`).

**Raw pulls on disk** (`data/pulls/`, gitignored — not in the repo, regenerable
via `make wrds-data` / `make public-data`):

| File | Size | Contents |
|---|---|---|
| `crsp_monthly.parquet` | 73M | Monthly CRSP prices/returns/shares, common shares, NYSE/AMEX/NASDAQ |
| `crsp_daily.parquet` | 545M | Daily CRSP |
| `compustat_annual.parquet` | 43M | Annual fundamentals |
| `compustat_quarterly.parquet` | 95M | Quarterly fundamentals |
| `crsp_compustat_link.parquet` | 832K | permno ↔ gvkey link table |
| `ff3_monthly_wrds.parquet` | 40M | Trusted Mkt-RF/SMB/HML/RF from WRDS |
| `25_portfolios_5x5_vw.parquet` | 272K | Ken French 25 test-asset portfolios |
| `data/pulls/osap/` | 2.3G | Open Source Asset Pricing (Chen & Zimmermann) — 209-characteristic panel |

---

## Phase 1 — Fama-French 3-factor model, from scratch

**Goal:** rebuild Mkt-RF, SMB, HML from raw CRSP prices + Compustat fundamentals
— not download Ken French's finished series — to prove the mechanics are
understood, not just imported.

**Pipeline** (full line-by-line writeup: [`learning/pipeline_walkthrough.md`](../learning/pipeline_walkthrough.md)):

1. Market Equity (ME) from CRSP price × shares outstanding, with the
   negative-price (bid-ask midpoint) convention fixed.
2. Book Equity (BE) via the Davis-Fama-French (2000) fallback-ladder formula
   from Compustat `seq`/`ceq`/`pstk`/`at`/`lt`, positive-BE filter applied.
3. CRSP ↔ Compustat identity bridge via the link table, with link-validity-window
   filtering.
4. Book-to-Market with look-ahead-safe timing: fiscal-year-*Y* book equity paired
   with **December-*Y*** market equity, portfolios formed the following **June**
   (6-month gap = no using a 10-K before it was filed).
5. NYSE-only breakpoints (median size split, 30th/70th percentile B/M split) —
   NASDAQ excluded from breakpoint calculation to avoid a size-only sort.
6. 2×3 sort → 6 value-weighted portfolios → SMB and HML.

**Validation:** SMB corr = **0.976**, HML corr = **0.965** vs. Ken French's
published series, 726 overlapping months (1964-2024). The ~3% gap from 1.00 is
attributable to convention differences (frozen vs. drifting value weights,
delisting screens, breakpoint timing) — not error.

**Sanity checks:** Apple Dec-2023 ME = $2.98T (correct); Apple FY2023 BE =
$62.7B (correct); Apple B/M ≈ 0.02 (expensive growth stock, correct); highest
B/M names are distressed micro-caps (correct).

**Code:** `notebooks/5_path_a_phase1_data_construction.ipynb` (Sections 1-10).

---

## Phase 2 — Fama-MacBeth (1973): is factor risk priced?

**Goal:** Phase 1 proved the factors *exist*. Phase 2 asks whether *bearing*
their risk is *rewarded* — do assets more exposed to a factor earn more, on
average, across the cross-section?

**Method** (two-pass, Fama & MacBeth 1973, *JPE*):

- **Pass 1 (time-series, once):** for each of the 25 Ken-French size/B-M test
  portfolios, regress its excess returns on `[Mkt-RF, SMB, HML]` over the full
  726-month history → a 25×3 beta matrix. Sanity check passed: small-value
  portfolios show visibly higher SMB and HML betas than big-growth.
- **Pass 2 (cross-sectional, every month):** for each of 726 months, regress
  that month's 25 excess returns on the (fixed) Pass-1 betas → that month's
  λ (price of risk) for each factor. Produces a 726-row time series of λ's.
- **Inference:** Newey-West (1987) HAC standard errors on the average λ per
  factor (`maxlags=6`) — not a naive mean/std t-test, since monthly λ's are
  autocorrelated.

**Result:**

| Factor | Mean λ (monthly) | Newey-West SE | t-stat | p-value | N |
|---|---:|---:|---:|---:|---:|
| MKT | -0.006199 | 0.002992 | -2.072 | 0.038 | 726 |
| SMB | 0.001189 | 0.001240 | 0.958 | 0.338 | 726 |
| HML | 0.003299 | 0.001502 | 2.196 | 0.028 | 726 |

**Interpretation:** HML is priced (positive, significant) — the value premium
shows up as a genuine compensated risk in this sample. SMB is not
distinguishable from zero. MKT is statistically significant but with the
theoretically "wrong" sign — a real, flagged empirical anomaly (not a bug),
consistent with the well-documented difficulty of estimating a reliable
market risk premium via Fama-MacBeth over this sample period.

**Code:** Pass 1/Pass 2 built and executed in
`notebooks/5_path_a_phase1_data_construction.ipynb` (see note under Known
Issues below re: notebook naming).

---

## Phase 3 — Factor zoo: individual-characteristic predictive power (OSAP)

**Goal:** move from portfolio-level factor exposure (Phase 2) to firm-level,
continuous-characteristic predictive power — the direct empirical bridge to
Baba-Yara's paper, which starts from exactly this kind of evidence across many
signals before applying sparse selection.

**Data:** Open Source Asset Pricing (Chen & Zimmermann) firm-characteristic
panel, pulled via Google Drive/`gdown`, read selectively from a 2.2GB zip
without full extraction. 9 candidate characteristics selected (10th candidate,
`Size`, dropped — not present in the actual data release despite being
documented; Phase 1's own ME serves as the size measure instead):

`BM`, `Mom12m`, `OperProf`, `AssetGrowth`, `Accruals`, `InvestPPEInv`,
`NetDebtFinance`, `CashProd`, `BetaTailRisk`

**Pipeline:**

1. Lag characteristics one month forward (`target_month = date + 1 month`) —
   a characteristic observed at *t* predicts the return realized at *t+1*.
2. Join to CRSP returns on `(permno, month)`, inner join (both characteristic
   and realized return must exist).
3. Convert to excess return (`ret - rf`), consistent with Chen & Zimmermann's
   own convention (raw returns first, excess derived explicitly).
4. Winsorize both the characteristic and excess return at the 1st/99th
   percentile **within each month** — individual-stock returns are far noisier
   than the value-weighted portfolio returns used in Phase 1/2, and a handful
   of extreme observations can otherwise dominate a month's cross-sectional
   regression.
5. Monthly cross-sectional (Fama-MacBeth-style) regression of excess return on
   the characteristic, one month at a time, with a minimum-N-per-month guard
   (30 firms) to exclude statistically meaningless small-sample months.
6. Newey-West test on the resulting λ time series — same machinery as Phase 2,
   reapplied.

Steps 1-6 were generalized into one reusable function
(`run_characteristic_fm(panel, char_col, min_n, maxlags)`) and run once per
characteristic — the same "loop over units → one regression per unit → stack
into a table" pattern used in Pass 1/Pass 2, at one more level of abstraction.

**Result** (738 months, July 1963 onward — the start date is itself a real
validation: B/M-based signals require Compustat coverage, which begins ~1962-63,
matching the literature):

| Characteristic | Mean λ | NW SE | t-stat | p-value | N months |
|---|---:|---:|---:|---:|---:|
| NetDebtFinance | 0.018241 | 0.002270 | 8.03 | <0.001 | 636 |
| InvestPPEInv | 0.012823 | 0.001819 | 7.05 | <0.001 | 738 |
| AssetGrowth | 0.007660 | 0.001100 | 6.97 | <0.001 | 738 |
| BM | 0.003423 | 0.000564 | 6.07 | <0.001 | 738 |
| Mom12m | 0.009188 | 0.001791 | 5.13 | <0.001 | 738 |
| OperProf | 0.005112 | 0.001375 | 3.72 | <0.001 | 738 |
| Accruals | 0.010176 | 0.003555 | 2.86 | 0.004 | 738 |
| BetaTailRisk | 0.004445 | 0.001592 | 2.79 | 0.005 | 738 |
| CashProd | 0.000011 | 0.000008 | 1.40 | 0.160 | 738 |

**Interpretation:** 8 of 9 characteristics are statistically significant, several
strongly so. `BM` reproduces the Phase 1/2 value story at the individual-firm
level (closing the conceptual loop between "B/M drives HML's construction" and
"B/M independently predicts firm-level returns"). `AssetGrowth`/`Accruals`
carry positive coefficients here despite the literature's usual negative sign —
this is expected, not a bug: OSAP's raw file (`signed_predictors_dl_wide.csv`)
deliberately sign-flips every characteristic so a positive coefficient always
means "points the theoretically expected direction," to allow pooled
comparison across 200+ signals. `CashProd`'s null result is a useful negative
control — a real anomaly panel should not have every signal come back
significant.

**This table is a small, direct, self-produced instance of the "factor zoo"
problem** — many individually-significant candidate predictors, no way yet to
tell which carry genuinely independent information versus which are redundant
with each other (Daniel & Titman 1997's characteristics-vs-covariances
question). That is exactly the problem Phase 4 (and Baba-Yara's actual method)
exists to solve.

**Code:** built in `notebooks/5_path_a_phase1_data_construction.ipynb`.

---

## Known issues / housekeeping

- **Notebook naming drift.** `notebooks/06_phase2_fama_macbeth.ipynb` was
  originally intended to hold Phase 2 onward, but all actual Phase 1-3 work
  (confirmed via file modification timestamps and content search) lives in
  `notebooks/5_path_a_phase1_data_construction.ipynb`, which has grown to cover
  all three phases. `06_phase2_fama_macbeth.ipynb` is still the original empty
  2-cell stub. Not a data-loss issue — the work is saved — but planning docs
  that reference "notebook 06" for Phase 2/3 are stale; this audit uses the
  actual file.
- **Stray build artifacts** (`learning/NEXT_SESSION_PLAN.{html,log,tex}`,
  `learning/.Rhistory`) were generated by a PDF/HTML knit of
  `NEXT_SESSION_PLAN.md` and added to `.gitignore` rather than committed —
  they're regenerable byproducts, not source content.
- **`learning/pipeline_walkthrough.md` and `learning/pandas_numpy_cheatsheet.csv`**
  cover Phase 1 (fully) and Phase 2 (concepts). Phase 3's join/winsorization/
  function-abstraction content is not yet written up there — pending.

---

## What's next

See Phase 4 and Phase 5 outlines (communicated separately) — coding begins
after Baba-Yara's "In Search of Sparsity" working paper has been read in full,
so that Phase 4's implementation choices are made with the actual paper's
methodology in view, not a guess at it.
