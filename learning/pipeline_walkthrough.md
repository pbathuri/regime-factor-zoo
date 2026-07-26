# RegimeFactorZoo — Pipeline Walkthrough (Sections 1–8)

An immersive, line-by-line tour of the FF3-from-scratch data pipeline. For every
step: **what DataFrame went in, what pandas/numpy operation touched it, what came
out, and *why* — connecting the code to the finance.**

Read this like a story about data moving through transformations. By the end you
should be able to re-derive any section without looking at the notebook.

> Companion file: `pandas_numpy_cheatsheet.csv` — every method here, tabulated for
> quick lookup + reapplication.

---

## The big picture (what we're building)

We are reconstructing the **Fama-French 3 factors** (Mkt-RF, SMB, HML) from *raw*
CRSP prices and Compustat accounting data — the way academic papers actually do it,
not by downloading Ken French's finished series. The data flow:

```
crsp_monthly.parquet ─┐
                      ├─(ME: price × shares)──────────────┐
compustat_annual ─────┤                                   │
                      ├─(BE: Davis-FF book equity)──┐     │
crsp_compustat_link ──┘                             │     │
                                                    ▼     ▼
                                   link merge → B/M = BE / ME_Dec
                                                    │
                                    + June ME (size) + NYSE breakpoints
                                                    │
                                       2×3 sort → 6 portfolios
                                                    │
                              value-weighted returns → SMB, HML  (Sections 9–10)
```

Two databases, two identity systems (`permno` for CRSP, `gvkey` for Compustat), one
translation table (the link). The whole game is joining market data to accounting
data *without cheating on timing*.

---

## Section 1 — Inspect raw CRSP

**In:** `crsp_monthly.parquet` (3.4M rows) → **DataFrame `crsp_month`.**

```python
crsp_month = pd.read_parquet(Data / "crsp_monthly.parquet")
```
`pd.read_parquet` reads a columnar binary file into memory as a DataFrame. Parquet
is typed and compressed, so 3.4M rows load in seconds and dtypes arrive correct.

```python
crsp_month.shape        # (3409860, 13)  — attribute, no ()
crsp_month.columns.tolist()
crsp_month.dtypes
```
These are **inspection** calls — they don't change data, they describe it. `.shape`
is an attribute (tuple); `.columns.tolist()` turns the column Index into a plain list;
`.dtypes` shows that `date` parsed as `datetime64` and numerics as nullable `Float64`.

```python
assert crsp_month["shrcd"].isin([10, 11]).all(), "shrcd leaked"
assert crsp_month["exchcd"].isin([1, 2, 3]).all(), "exchcd leaked"
```
`.isin([...])` returns a **boolean Series** (True where the value is in the set).
`.all()` collapses that Series to a single bool. Wrapped in `assert`, it's a
**tripwire**: if the SQL pull ever let a non-common-share or wrong-exchange row
through, the notebook stops here instead of silently corrupting portfolios.
*Finance meaning:* FF(1993) uses only common stocks (shrcd 10/11) on NYSE/AMEX/NASDAQ
(exchcd 1/2/3) — no ADRs, REITs, closed-end funds.

```python
crsp_month["prc"].isna().sum()   # 16,262 missing prices
```
`.isna()` → boolean Series (True where missing); `.sum()` counts the Trues (True=1).
High NA in `ret` is normal — IPO/delisting months have no return.

**Out:** the same `crsp_month`, now *trusted* (filters verified, NA understood).

---

## Section 2 — Market Equity (ME)

**In:** `crsp_month`. **Goal:** each stock-month's market cap.

```python
crsp_month["absprc"] = crsp_month["prc"].abs()
crsp_month["me"] = crsp_month["absprc"] * crsp_month["shrout"] / 1_000
```
`.abs()` fixes CRSP's **negative-price convention**: a negative `prc` means "no trade
that day; this is the bid-ask midpoint." Market cap can't be negative, so we take the
magnitude. Then **Series arithmetic** (elementwise) multiplies price × shares. The
`/1_000` converts to **$ millions** because CRSP stores `shrout` in *thousands* of
shares — the single easiest unit bug in all of empirical finance.
*Validation:* Apple Dec-2023 → 2,976,557 ($M) = **$2.98T**. Correct.

```python
crsp_month = crsp_month.sort_values(["permno","date"]).reset_index(drop=True)
crsp_month = crsp_month.dropna(subset=["me"]).reset_index(drop=True)
```
`.sort_values` orders rows (stock, then time). `.reset_index(drop=True)` renumbers
0..n and throws away the old index. `.dropna(subset=["me"])` removes rows where ME
couldn't be computed — and note the *subtlety*: since `me = absprc × shrout`, a NaN in
**either** input makes `me` NaN, so dropping on `me` catches both cases in one move.

```python
top10 = crsp_month[crsp_month["date"]=="2023-12-29"].nlargest(10, "me")
```
**Boolean filter** to one date, then `.nlargest(10,"me")` returns the 10 biggest by
market cap. They came back as Apple/Microsoft/Alphabet/Amazon/NVIDIA/... — the sanity
check that the whole ME computation is right.

**Out:** `crsp_month` with a validated `me` column ($ millions).

---

## Section 3 — Clean Compustat

**In:** `compustat_annual.parquet` (572,820 rows) → **DataFrame `compustat_annual`**,
then filtered → **`comp`.**

```python
compustat_annual["datadate"] = pd.to_datetime(compustat_annual["datadate"])
```
`pd.to_datetime` parses the fiscal-year-end date into real `datetime64` so we can do
date math and use `.dt` later.

```python
comp = compustat_annual[
    (compustat_annual["indfmt"]=="INDL") &
    (compustat_annual["datafmt"]=="STD") &
    (compustat_annual["popsrc"]=="D") &
    (compustat_annual["consol"]=="C")
].copy()
```
Four boolean masks combined with `&` (each **parenthesised** — required, or Python's
operator precedence breaks it). `.copy()` makes `comp` independent so later column
assignments don't mutate the parent or raise SettingWithCopyWarning.
*Finance meaning:* Compustat stores the *same* company-year in multiple "formats"
(industrial vs financial, consolidated vs not, domestic vs Canadian, standard vs
restated). Without these 4 filters you double- or triple-count every firm.

```python
comp = comp.sort_values(["gvkey","fyear","datadate"])
comp = comp.drop_duplicates(["gvkey","fyear"], keep="last")
assert comp.groupby(["gvkey","fyear"]).size().max() == 1
```
Even after the 4 filters, some firms have two rows in one `fyear` (fiscal-year-end
*changes*). `.sort_values` then `.drop_duplicates(keep="last")` keeps the latest
`datadate` per (gvkey, fyear). The `.groupby([...]).size().max()==1` assert proves
uniqueness: group the rows, count each group, and the biggest group must be 1.

**Out:** `comp` — one clean accounting row per company-year.

---

## Section 4 — Book Equity (Davis-Fama-French 2000)

**In:** `comp`. **Goal:** each company-year's book value of equity.

```python
def book_equity(row):
    if pd.notna(row["seq"]):                               se = row["seq"]
    elif pd.notna(row["ceq"]) and pd.notna(row["pstk"]):   se = row["ceq"] + row["pstk"]
    elif pd.notna(row["at"]) and pd.notna(row["lt"]):      se = row["at"] - row["lt"]
    else:                                                  se = np.nan
    ps = row["pstkrv"] if pd.notna(row["pstkrv"]) else (
         row["pstkl"]  if pd.notna(row["pstkl"])  else (
         row["pstk"]   if pd.notna(row["pstk"])   else 0))
    tx = row["txditc"] if pd.notna(row["txditc"]) else 0
    return se + tx - ps

comp["be"] = comp.apply(book_equity, axis=1)
```
`pd.notna(x)` is the **scalar-safe** null test (works on one cell). The function is a
**fallback ladder**: use the best available source for stockholders' equity, else the
next. `.apply(func, axis=1)` runs it **once per row** (`axis=1` = across columns of a
row). It's slower than vectorized math but necessary here because the logic branches
per row. *Gotcha we hit:* `row.lt` grabs pandas' `.lt` **method**, so we use
bracket access `row["lt"]` for the `lt` (total liabilities) column.

```python
comp = comp[comp["be"] > 0].copy()
```
Drops negative **and** NaN book equity in one filter — because `NaN > 0` is `False`.
*Finance meaning:* FF(1993) excludes negative-BE firms (the B/M ratio loses economic
meaning). *Validation:* Apple FY2023 BE = **$62.7B**. Correct.

**Out:** `comp` with a positive `be` column ($ millions).

---

## Section 5 — Bridge Compustat → CRSP (the link table)

**In:** `comp` + `crsp_compustat_link.parquet` → **DataFrame `merged`.**

```python
link = link[link["linktype"].isin(["LU","LC"]) & link["linkprim"].isin(["P","C"])].copy()
link["linkenddt"] = link["linkenddt"].fillna(pd.Timestamp("2099-12-31"))
```
The link table translates `gvkey` ↔ `permno`, each valid over a date window
[`linkdt`, `linkenddt`]. `.fillna(pd.Timestamp("2099-12-31"))` is the crucial move:
a **NaT** end-date means "link still active." If we left it NaT, the later
`datadate <= linkenddt` comparison would be False for every currently-listed firm and
we'd silently drop Apple. Filling with a far-future date keeps active links alive.

```python
merged = comp.merge(link, on="gvkey", how="inner")
merged = merged[(merged["datadate"] >= merged["linkdt"]) &
                (merged["datadate"] <= merged["linkenddt"])].copy()
assert merged.groupby(["gvkey","fyear"])["permno"].nunique().max() == 1
```
`.merge(on="gvkey", how="inner")` is a **SQL join**: every Compustat row is matched to
its link rows sharing `gvkey`. The boolean range filter then keeps only rows where the
accounting date falls inside the link's validity window. The assert uses
`.nunique()` (count of *distinct* permnos per group) to prove each (gvkey, fyear) maps
to exactly one permno — no ambiguous identity.
*Validation:* Apple gvkey 001690 now carries permno 14593 on the same row as its BE.

**Out:** `merged` (293,055 rows) — each row knows both its accounting value (be) and
its CRSP identity (permno).

---

## Section 6 — Book-to-Market with look-ahead-safe timing

**In:** `merged` + December ME from `crsp_month`. **Goal:** B/M ratio, timed so we
never use data we couldn't have known.

```python
merged["be_calyear"] = merged["datadate"].dt.year        # calendar year the fiscal year ended

dec = crsp_month[crsp_month["date"].dt.month == 12].copy()
dec["calyear"] = dec["date"].dt.year
dec = dec[["permno","calyear","me"]].rename(columns={"me":"me_dec"})
```
`.dt.year` / `.dt.month` are **datetime accessors** — they pull integers out of a
datetime column. We build a lookup of each stock's **December** market cap per year,
renamed `me_dec` so it never gets confused with other ME columns.

```python
m = merged.merge(dec, left_on=["permno","be_calyear"],
                      right_on=["permno","calyear"], how="inner")
m["bm"] = m["be"] / m["me_dec"]
```
`left_on` / `right_on` join on **differently-named** keys: BE's calendar year
(`be_calyear`) to December ME's year (`calyear`). Then elementwise division gives B/M.
*Finance meaning (the whole point):* book equity from a fiscal year ending in calendar
year *Y* is paired with **December-*Y*** market equity — both definitely public — and
this pairing is used to form portfolios the following **June**. The 6-month gap is the
look-ahead guard: no using a 10-K before it was filed.
*Validation:* Apple B/M ≈ **0.02** (expensive growth stock); the highest B/M names are
distressed micro-caps (market cap near zero, positive book) — exactly right.

**Out:** `m` — the (permno, fiscal-year) panel with `be`, `me_dec`, and `bm`.

---

## Section 7 — Second ME + NYSE breakpoints  *(you build this)*

**In:** `m` + **June** ME from `crsp_month`. **Goal:** the *size* measure and the cut
lines for the sort.

Key ideas:
- `m["portfolio_year"] = m["be_calyear"] + 1` — the B/M from FY-ending-*Y* forms a
  portfolio in **June of Y+1**.
- Build a **June ME** lookup (`me_june`) exactly like the December one, but
  `month == 6` — this is the *size* number (measured at formation), a *different*
  value from the December ME (which only fed the B/M denominator).
- **NYSE breakpoints per year:** filter to `exchcd == 1` **first**, then
  `groupby("portfolio_year")` and take `me_june.median()` (size cut) and
  `bm.quantile(0.30)` / `.quantile(0.70)` (value cuts). NYSE-only because NASDAQ is
  swamped with tiny firms — using the full universe would sort by *exchange*, not size.

New skills: `groupby().quantile(q)`, assembling several group-Series into one
`breakpoints` DataFrame.

**Out:** `breakpoints` (per portfolio_year: size_median, bm_p30, bm_p70) + `m` carrying
`me_june`.

---

## Section 8 — The 2×3 sort → 6 portfolios  *(you build this)*

**In:** `m` + `breakpoints`. **Goal:** label every stock-year with one of six buckets.

- Merge `breakpoints` back onto `m` (on `portfolio_year`) so each row carries *its
  year's* cut lines.
- **Size (2 groups):** `np.where(me_june < size_median, "S", "B")` — vectorized
  if-else, two outcomes.
- **Value (3 groups):** `np.select([bm < bm_p30, bm >= bm_p70], ["L","H"], default="M")`
  — vectorized multi-way if, the right tool for 3+ branches.
- **Combine:** string concatenation `size_bucket + "/" + bm_bucket` → `"S/H"` etc.
- `.value_counts()` should show all six labels, with far more *Small* by count (tiny
  firms are numerous) but they'll be light in dollars — which is why Section 9
  **value-weights**.

*Why 2×3 (coarse size, fine value)?* FF isolate the value effect, so the B/M dimension
gets the finer 3-way cut; size gets a simple median split.

**Out:** `m` with a `portfolio` label per stock-year — ready for return aggregation.

---

## Sections 9–10 — DONE and validated

- **9 — value-weighted monthly returns:** held each June-formed portfolio for 12
  months using the calendar rule `form_year = year if month>=7 else year-1`
  (the "formation date ≠ return date" panel pattern), value-weighting each portfolio
  by June ME via `np.average(ret, weights=me_june)`. Produced a 726×6 matrix of
  monthly portfolio returns.
- **10 — SMB & HML + validation:** SMB = avg(SL,SM,SH) − avg(BL,BM,BH);
  HML = avg(SH,BH) − avg(SL,BL). Aligned to Ken French via `PeriodIndex` and compared
  with `series.corr()`.
  **Result: SMB corr = 0.976, HML corr = 0.965 over 726 months (1964–2024).** Both
  clear the 0.95 win condition — a genuine from-scratch FF3 replication. The ~3% gap
  from 1.00 is convention (frozen vs drifting value weights, delisting/microcap
  screens, breakpoint timing), not error.

**Phase 1 is complete.** The repo now contains SMB, HML, and Mkt-RF built from raw
CRSP prices + Compustat balance sheets, validated against the published series.

---

## Phase 2 — Fama-MacBeth: is the risk *priced*? (concepts, to build)

Phase 1 proved the factors exist. Phase 2 asks whether **bearing** their risk is
**rewarded** — do assets more exposed to a factor earn more, on average, across the
cross-section? A factor can be real yet command no premium.

**The two-pass method** (Fama & MacBeth 1973, *Journal of Political Economy*):

1. **Pass 1 — time-series (once).** For each of the 25 size-B/M test portfolios,
   regress its returns on the 3 factors over the whole history. The slopes are that
   portfolio's **betas** — how sensitive it is to each factor. (FF3 regression, run 25
   times.) *Sanity:* small-value portfolio → high SMB and HML betas.

2. **Pass 2 — cross-sectional (every month).** For each month, take that month's 25
   returns as the **outcome (y)** and the Pass-1 betas as the **regressors (x)**; the
   estimated slopes are the **λ's (lambdas)** — the price the market paid for each
   factor's risk that month. Do this for all ~726 months → a *time series* of λ's.
   NOTE: λ is the *output* of the regression (the slope), not the outcome variable.

3. **Aggregate + inference.** Average each factor's λ. Test whether it's reliably
   nonzero. **Do not** use `mean/(std/√T)` — the monthly λ's are autocorrelated, so
   that naive standard error is too small and the t-stat too big (you'd falsely call a
   factor "priced"). Use **Newey-West** HAC standard errors (Newey & West 1987,
   *Econometrica*), which correct the variance by adding lagged autocovariances with
   declining weights (also handles heteroskedasticity — hence "HAC").

**What "priced" means:** a positive, significant average λ on HML says value exposure
is *compensated* across assets — the empirical content of "the value premium is real."

**Test assets:** the 25 portfolios (`25_portfolios_5x5_vw.parquet`) — designed for
exactly this (Fama & French 1993). **Modern framing:** λ = price of risk
(Cochrane, *Asset Pricing* 2005, ch. 12; Cochrane 2011 AFA "Discount Rates").
**Why it's the floor for later phases:** the factor-zoo / sparse-selection work
(Phases 3–4, Baba-Yara) is literally "of hundreds of candidate factors, which λ's are
nonzero?" — unanswerable until you can estimate one λ correctly.

**Milestones:** M1 = 25×3 beta matrix · M2 = monthly λ series · M3 = Newey-West
t-stats · M4 = clean (λ, t-stat) results table for the memo.

**Likely new tools:** `statsmodels` OLS (`sm.OLS`, `sm.add_constant`,
`.fit(cov_type="HAC", cov_kwds={"maxlags":k})`, `.params`, `.tvalues`), and a
`groupby("date").apply(...)` to run one cross-sectional regression per month.

---

## The through-line

Every section is the same motif: **take a DataFrame, add a carefully-timed column,
filter to what's legitimate, join to the next data source on the right keys, and
assert an invariant before moving on.** The finance lives in the *timing* (Dec ME vs
June ME, t vs t−1) and the *filters* (common shares, NYSE breakpoints, positive BE);
the pandas is just the vehicle. Master this motif and you can build any factor in the
zoo.
