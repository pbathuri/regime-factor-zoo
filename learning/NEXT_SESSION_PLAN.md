---
output:
  pdf_document: default
  html_document: default
---
# Next Session — Continuation Plan
*Written end of session, post-ARPM-bootcamp return. Read this first when you wake up.*

---

## ⚠️ FIRST THING — before anything else

**Save `notebooks/06_phase2_fama_macbeth.ipynb` if you haven't.** As of this writing, the
file on disk still has only the 2-cell empty stub — tonight's code (units fix, joins,
Mkt-RF merge, excess returns) exists only in the live kernel. If the kernel died or you
closed without saving, **don't panic** — the exact code is reproduced in full below,
under "Fallback: tonight's code, verbatim." Re-run it, confirm the shape checks match,
and you're back to exactly where you left off in ~2 minutes.

Either way: **commit once the notebook is saved and Pass 1 is done tomorrow** (see
commit message template at the bottom).

---

## Where you actually are right now

| Phase | Status |
|---|---|
| **Phase 1 — from-scratch FF3** | ✅ **Done, validated, committed.** SMB corr 0.976, HML corr 0.965 vs Ken French, 726 months (1964–2024). |
| **Phase 2 — Fama-MacBeth prep** | ✅ Done tonight (pending save/commit). See below. |
| **Phase 2 — Pass 1 (betas)** | ⬜ **Next thing to build.** |
| **Phase 2 — Pass 2 (lambdas) + Newey-West** | ⬜ After Pass 1. |
| **Phase 3 — factor zoo (characteristics)** | ⬜ Not started. See acceleration note below. |
| **Phase 4 — sparse-Bayesian selection** | ⬜ Not started — this is Baba-Yara's actual methodology. |
| **Phase 5 — regime-stability split** | ⬜ Not started — this is YOUR original contribution. |
| **Phase 6 — memo + outreach** | ⬜ Not started. |

### What "Phase 2 prep, done tonight" means concretely

You now have (or will have, once re-run) a table called `merged` with:
- Your own validated factors: `SMB_me`, `HML_me` (decimal)
- The published market factor: `mktrf`, `rf` (decimal, from WRDS — already trusted, dual-source-validated back in Phase 0)
- The 25 Ken-French test-asset portfolios (`s1_b1` … `s5_b5`), converted from percent to
  decimal, and converted from **total returns to excess returns** (subtracted `rf`)
- All aligned on a monthly `PeriodIndex`, inner-joined so every row has real data in every column
- Expected shape: **(726, 29)** — 2 own factors + mktrf + rf + 25 excess-return portfolios

This table (`merged`) is the **complete input** Pass 1 needs. No more data prep required.

---

## Fallback: tonight's code, verbatim (only needed if the notebook didn't save)

```python
# --- Fix units on the 25-portfolio file ---
ex = ex / 100.0

# --- Align index types (PeriodIndex, same trick used throughout Phase 1) ---
factors_aligned = factors.copy()
factors_aligned.index = pd.to_datetime(factors_aligned.index).to_period("M")

ex_aligned = ex.copy()
ex_aligned.index = pd.to_datetime(ex_aligned.index).to_period("M")

# --- Join own factors + 25 portfolios (inner join = auto date-trim) ---
merged = factors_aligned.join(ex_aligned, how="inner")

# --- Load Mkt-RF + RF from the trusted WRDS source (already decimal) ---
wrds = pd.read_parquet(Data / "ff3_monthly_wrds.parquet")
wrds = wrds[["date", "mktrf", "rf"]].copy()
wrds = wrds.set_index("date")
wrds.index = pd.to_datetime(wrds.index).to_period("M")

# --- Join market factor + risk-free rate in ---
merged = merged.join(wrds, how="inner")

# --- Convert the 25 portfolios from total returns to EXCESS returns ---
portfolio_cols = [f"s{s}_b{b}" for s in range(1, 6) for b in range(1, 6)]
merged[portfolio_cols] = merged[portfolio_cols].sub(merged["rf"], axis=0)

# --- Sanity check ---
print("Final shape:", merged.shape)              # expect (726, 29)
print(merged.columns.tolist())
print(merged[["SMB_me", "HML_me", "mktrf", "rf", "s1_b1", "s5_b5"]].tail())
```

---

## Concept recap — what Pass 1 actually is (re-read before building)

**The question:** for each of the 25 test portfolios, how sensitive is it to each of the
three factors? This is pure **time-series regression**, run 25 separate times:

```
r_i,t (excess) = α_i + β_i,MKT·mktrf_t + β_i,SMB·SMB_me_t + β_i,HML·HML_me_t + ε_i,t
```

For **one** portfolio: `y` = that portfolio's 726-month excess-return column (shape
`(726,)`), `X` = `[const, mktrf, SMB_me, HML_me]` (shape `(726, 4)`). Run
`sm.OLS(y, X).fit()`, keep `.params` (drop the intercept), store the 3 betas. Do this
once per portfolio column, stack into a **25×3 beta matrix**.

**Sanity check to run once you have it** (this is the thing you correctly predicted
weeks ago): `s1_b5` (small, high B/M — small-value) should show noticeably higher SMB
*and* HML betas than `s5_b1` (big, low B/M — big-growth). If that pattern doesn't show
up, something upstream is wrong — go back and check the `s1`/`b1` direction convention
before doubting the regression itself.

### After Pass 1 — Pass 2 + Newey-West (same session, if time allows)

- **Pass 2:** every month, cross-sectional regression — the 25 excess returns *that
  month* as `y`, the Pass-1 betas as `X` (fixed, same for every month). The slope you
  get out is that month's **λ** (lambda) for each factor. Loop over all 726 months
  (`groupby` on the date index) → a 726-row table of monthly λ's.
- **Newey-West:** average each factor's λ column. Test significance with
  `sm.OLS(lam_series, np.ones(len(lam_series))).fit(cov_type="HAC", cov_kwds={"maxlags": 6})`
  — NOT a naive `mean/std`, because the λ's are autocorrelated (re-read your own
  reasoning on this from earlier tonight if it's fuzzy).
- **Output:** a clean table — factor, mean λ, Newey-West t-stat. This is a real,
  citable result. It answers "is this risk priced?"

### References (for when you want depth, not just the mechanics)
- **Fama & MacBeth (1973), *JPE*** — the two-pass method itself
- **Newey & West (1987), *Econometrica*** — the HAC correction
- **Fama & French (1993), *JFE*** — the 25-portfolio test-asset design
- **Brooks, *Introductory Econometrics for Finance*, 4th ed., §5.5** — autocorrelation/HAC
  intuition, worked with figures (read this first if Newey-West still feels shaky)
- **Brooks §14.2 "Tests of the CAPM and the Fama-French Methodology"** — a finance-native
  worked Fama-MacBeth example; read this **after** you've built Pass 1, not before — it
  lands as confirmation instead of abstraction
- **Cochrane, *Asset Pricing* (2005), ch. 12 §12.2–12.3** — only if you want the deeper
  GMM-connected framing; optional, not required for correctness

---

## The accelerated path to Baba-Yara's actual paper

You asked specifically how to get to his working paper territory faster. Here's the
honest map — no phase gets skipped on rigor, but Phase 3 has a real shortcut worth
taking.

### Phase 3 — don't hand-build 40 characteristics from raw Compustat

You already proved you can do this rigorously (Phase 1 — one characteristic, B/M, built
completely from scratch with correct timing, breakpoints, and validation). That's the
credential. Repeating that process 40 more times for a full "factor zoo" would take many
additional weeks and wouldn't teach you anything new — it's the same skill, repeated.

**Faster, equally legitimate path:** use the **Open Source Asset Pricing (OSAP)**
dataset (Chen & Zimmermann) — the same standardized characteristic panel Baba-Yara's
own methodology assumes. This isn't cutting corners; it's what working researchers
actually do — build core methodology from scratch once to prove competence (done), then
use established, peer-vetted infrastructure for breadth. URL:
`https://www.openassetpricing.com/data/` (already scoped as a data source back when
WRDS summer-access was denied). Pull their signed-predictors panel, join it onto your
own validated returns/portfolio structure.

### Phase 4 — sparse-Bayesian selection (this IS Baba-Yara's method)

Once you have a wide characteristic panel (from OSAP) plus your own validated factor
infrastructure: start with **Lasso/Ridge** (classical baselines, `sklearn`, you already
have the time-series-CV concept from earlier planning) to get a first-pass sense of
which characteristics survive regularization. Then move to a **sparse-Bayesian factor
model** (`PyMC` or `numpyro`) — spike-and-slab or horseshoe priors — which is the actual
methodological core of "In Search of Sparsity." This is the phase where you're no longer
just replicating FF3, you're doing something structurally similar to his paper.

### Phase 5 — regime-stability split (your original contribution)

VIX-percentile split (or 2008/2020 regime breaks) on whichever factors survive Phase 4's
sparse selection. The question: **do the same factors get selected in high-VIX vs
low-VIX regimes, or does the sparse selection itself change?** This is the piece that
isn't in his paper — it's your extension, and it's what makes the eventual email to him
a research conversation instead of a fan letter.

### Phase 6 — memo + outreach
1-page PDF (figure top, 3-paragraph narrative), repo polish, then the actual email.

---

## Practical sequencing for tomorrow

1. Save/verify notebook 06 (or re-run the fallback block above — 2 min either way)
2. Re-read the "Concept recap" section above (5 min)
3. Build Pass 1 (the 25×3 beta loop) — this is genuinely the biggest remaining lift in
   Phase 2, budget real focused time for it
4. Run the small-value vs big-growth sanity check
5. If time remains: Pass 2 + Newey-West in the same session
6. Commit — suggested message:
   `feat(notebook06): Phase 2 prep + Pass 1 betas — [ADD: small-value vs big-growth check result]`

---

## File map (so a fresh session/you-tomorrow can navigate instantly)

| File | What it is |
|---|---|
| `notebooks/5_path_a_phase1_data_construction.ipynb` | Phase 1, complete — FF3 from scratch |
| `notebooks/06_phase2_fama_macbeth.ipynb` | Phase 2, in progress — **work here tomorrow** |
| `learning/pipeline_walkthrough.md` | Line-by-line narrative of every section built so far |
| `learning/pandas_numpy_cheatsheet.csv` | Every pandas/numpy method used, with your own examples |
| `learning/NEXT_SESSION_PLAN.md` | This file |
| `data/pulls/25_portfolios_5x5_vw.parquet` | 25 test-asset portfolios (1926–2026, percent, total returns — raw) |
| `data/pulls/ff3_monthly_wrds.parquet` | Trusted published Mkt-RF/RF/SMB/HML (decimal) |

Welcome back from ARPM — go build Pass 1.
