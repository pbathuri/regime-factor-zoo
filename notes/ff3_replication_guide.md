# FF3 Replication Guide — Fama & French (1993)

**Milestone**: Jun 7, 2026 · Commit validated results to `results/ff3_replication.csv`
**Time budget**: ~90 min for core + ~30 min overachieve
**Entry point**: `notebooks/03_ff3_replication.ipynb`

---

## What "replication" means here

You're not rebuilding the portfolios from CRSP. You're using:
- **Ken French's prebuilt portfolio returns** (25 size/BM sorted portfolios, already downloaded)
- **Ken French's prebuilt factor returns** (Mkt-RF, SMB, HML, already in your parquet)

You run the **same time-series OLS regressions** that appear in **Table 3** of the paper and check whether your numbers match. This validates that (a) you understand the model and (b) your data pipeline is correct.

---

## The model (write this from memory before coding)

For each portfolio p, each month t:

```
R(p,t) - Rf(t)  =  α  +  β·[Mkt-RF(t)]  +  s·[SMB(t)]  +  h·[HML(t)]  +  ε(t)
```

- `R(p,t) - Rf(t)` — excess return of portfolio p in month t
- `α` (alpha/intercept) — return unexplained by the 3 factors. Should be ≈ 0 if model is correct
- `β` — market loading (exposure to market premium). Should be ≈ 1
- `s` — SMB loading (size exposure). Positive = small-cap tilt; negative = large-cap tilt
- `h` — HML loading (value exposure). Positive = value tilt; negative = growth tilt
- `R²` — fraction of variance explained. Should be high (0.80–0.97)

**Key intuition**: Fama & French claim that after controlling for market risk, the *pattern* of returns across size/BM groups is fully captured by SMB and HML — so α ≈ 0 everywhere. Your job is to verify this numerically.

---

## Step 0 — Read the paper first (30 min)

Open `papers/fama_french_1993.pdf`. Read in this order:

| Section | What to extract |
|---------|----------------|
| Abstract (p.3) | The core claim in 2 sentences |
| §I Introduction (p.3–4) | Why the size/value premiums needed explanation |
| §II The Data (p.5–9) | How the 25 portfolios are formed (SIZE × B/M sort) |
| §III.A Time-series regressions (p.14–17) | The exact regression equation you'll code |
| **Table 3** (p.17–18) | **The numbers you will reproduce** |
| §III.B Interpretation (p.18–21) | What the factor loadings mean economically |

**Do this**: After reading §III.A, write the OLS regression equation on paper before touching the keyboard.

**Table 3 layout** (25 rows = 25 portfolios, 5×5 grid):
- Rows = SIZE quintiles: ME1 (smallest) → ME5 (largest)
- Cols = B/M quintiles: BM1 (growth, low B/M) → BM5 (value, high B/M)
- For each portfolio: `α   t(α)   β   t(β)   s   t(s)   h   t(h)   R²`

---

## Step 1 — Inspect your data (15 min)

Open `notebooks/03_ff3_replication.ipynb` and work through the exercises.

Your files:
```
data/pulls/ff3_monthly.parquet          # Mkt-RF, SMB, HML, Rf — monthly, percent
data/pulls/25_portfolios_5x5_vw.parquet # 25 portfolio returns — monthly, percent
                                         # columns: s1_b1, s1_b2, ..., s5_b5
                                         # s = size quintile, b = B/M quintile
```

**Exercise 1.1** — Load both files. Print shape, date range, first 3 rows.

**Exercise 1.2** — Look at the column names of the portfolio data. Map them to the paper's notation:
- `s1_b1` = ME1 BM1 = **Small Growth** (smallest firms, lowest B/M) — this is your "growth" extreme
- `s1_b5` = ME1 BM5 = **Small Value** (smallest firms, highest B/M) — small value
- `s5_b1` = ME5 BM1 = **Large Growth** — large-cap growth (think S&P 500 growth stocks)
- `s5_b5` = ME5 BM5 = **Large Value** — large-cap value

**Exercise 1.3** — Subset to the original FF1993 sample period: **July 1963 – December 1991**.
> Why does sample period matter? What would happen to your α estimates if you used 1926–2026 instead?

---

## Step 2 — Align the data (10 min)

The factors and portfolio returns are both in percent per month and cover the same dates — but you need to confirm alignment before regressing.

**Exercise 2.1** — Create a single aligned DataFrame for the 1963–1991 period containing:
- `mktrf`, `smb`, `hml`, `rf` (from ff3_monthly)
- all 25 portfolio columns (from 25_portfolios)
- a new column `excess_s1_b1 = s1_b1 - rf` (just for one portfolio to start)

Hint: Use `pd.concat([factors, portfolios], axis=1)` and then check for NaNs with `.isnull().sum()`.

**Exercise 2.2** — Sanity check: plot the `s1_b1` portfolio and `s5_b5` portfolio on the same chart. Do small-growth vs. large-value show the expected pattern?

---

## Step 3 — OLS for one portfolio (20 min)

**The tool**: `statsmodels.api.OLS` — not sklearn. Reason: statsmodels gives you t-statistics, p-values, and R² without extra work. sklearn's `LinearRegression` doesn't give you the statistics needed for Table 3.

**Exercise 3.1** — Import statsmodels and write OLS for portfolio `s1_b1` only.

The statsmodels pattern is:
```python
import statsmodels.api as sm

# X needs a constant column for the intercept
X = sm.add_constant(factors[['mktrf', 'smb', 'hml']])
y = excess_returns['s1_b1']  # Rp - Rf

model = sm.OLS(y, X).fit()
print(model.summary())
```

**Exercise 3.2** — Read the `model.summary()` output. Identify:
- `const` — this is your α. Is it close to 0? Is it statistically significant (|t| > 2)?
- `mktrf` coefficient — this is β
- `smb` coefficient — this is s
- `hml` coefficient — this is h
- `R-squared` — this is R²

**Exercise 3.3** — Compare your `s1_b1` coefficients to Table 3 row ME1 BM1 in the paper.

Expected direction (not exact numbers — you find the exact numbers in the paper):
- α: small negative (small growth tends to underperform after factor adjustment)
- β: close to 1 but slightly above (small stocks have somewhat higher market exposure)
- s: large positive (small growth = heavy small-cap tilt → high SMB loading)
- h: negative (growth stocks = low B/M → negative HML loading)
- R²: roughly 0.85–0.92

---

## Step 4 — Loop over all 25 portfolios (25 min)

Now scale up. Write a function `run_ff3_ts_regression(excess_returns, factors)` that:
1. Takes a Series of excess returns (one portfolio) and a DataFrame of factors
2. Fits OLS with a constant
3. Returns a dict with: `alpha, t_alpha, beta, s, h, r2, n`

Then loop over all 25 portfolios, collect results into a DataFrame, and reshape into a 5×5 grid.

**Exercise 4.1** — Write the function. Don't hardcode column names — use positions or pass column names as arguments.

**Exercise 4.2** — Loop. Pattern:
```python
results = []
for col in portfolio_cols:
    excess = aligned[col] - aligned['rf']
    r = run_ff3_ts_regression(excess, aligned[['mktrf','smb','hml']])
    r['portfolio'] = col
    results.append(r)

results_df = pd.DataFrame(results).set_index('portfolio')
```

**Exercise 4.3** — Check your results against these directional constraints from Table 3:

| Pattern | What to check |
|---------|--------------|
| s loading (SMB) | Should decrease monotonically as SIZE increases (s1 > s2 > s3 > s4 > s5) |
| h loading (HML) | Should increase monotonically as B/M increases (b1 < b2 < b3 < b4 < b5) |
| R² | Should be > 0.80 for most portfolios; only small-growth may dip below |
| α | Should be mostly close to 0; few should have |t(α)| > 2 |

If your s and h loadings don't show these monotone patterns, there's a bug (usually: wrong sample period, or you forgot to subtract Rf from the portfolio returns).

---

## Step 5 — Build Table 3 equivalent and save (10 min)

**Exercise 5.1** — Reshape the `alpha` column into a 5×5 DataFrame with SIZE as rows and B/M as columns. This is the "alpha matrix" — the classic way to present FF3 results.

```python
# Hint: use .values.reshape(5, 5) if portfolios are ordered s1_b1..s1_b5, s2_b1..s5_b5
alpha_matrix = results_df['alpha'].values.reshape(5, 5)
alpha_df = pd.DataFrame(alpha_matrix,
                        index=['Small','2','3','4','Large'],
                        columns=['Growth','2','3','4','Value'])
```

**Exercise 5.2** — Save the full results to `results/ff3_replication.csv`. Required columns:
`portfolio, alpha, t_alpha, beta, s, h, r2, n`

**Exercise 5.3** — Print a summary line:
```
Mean |α|: X.XX %/month   Max |α|: X.XX %/month   Mean R²: 0.XX
```

**Commit target**: `git commit -m "feat: FF3 baseline replication validated"` once mean |α| < 0.25%/month and mean R² > 0.85.

---

## Step 6 — Validate against Table 3 (sanity check)

Open the paper's Table 3. Pick 4 corner portfolios and compare:

| Portfolio | Paper α | Your α | Paper R² | Your R² |
|-----------|---------|--------|----------|---------|
| s1_b1 (Small Growth) | find in paper | ? | find in paper | ? |
| s1_b5 (Small Value)  | find in paper | ? | find in paper | ? |
| s5_b1 (Large Growth) | find in paper | ? | find in paper | ? |
| s5_b5 (Large Value)  | find in paper | ? | find in paper | ? |

Your numbers won't be exactly equal to the paper's — Ken French occasionally revises historical data. But they should be within ±0.05% for α and ±0.02 for R².

---

## Overachieve extensions (do these if you finish early)

### Extension A — Alpha heatmap
```python
import seaborn as sns
sns.heatmap(alpha_df, annot=True, fmt='.2f', center=0, cmap='RdBu_r')
```
The heatmap should show near-zero alphas across the grid — the visual proof that FF3 "works."

### Extension B — t-stat heatmap
Same structure but with `t_alpha`. Highlights where the model still leaves unexplained return. Classic finding: `s1_b1` (small growth) often has a significant negative alpha even after FF3.

### Extension C — Newey-West standard errors
The OLS standard errors assume iid errors, but financial returns exhibit heteroskedasticity and mild autocorrelation. Newey-West (HAC) gives more honest t-stats. In statsmodels:
```python
model_nw = sm.OLS(y, X).fit(cov_type='HAC', cov_kwds={'maxlags': 3})
```
Compare the NW t-stats to the OLS t-stats for α. Does statistical significance change?

### Extension D — CAPM comparison
For each portfolio, also run the CAPM (one-factor) version:
```
Rp - Rf = α_CAPM + β·(Mkt-RF) + ε
```
Compare `α_CAPM` vs `α_FF3`. The difference shows how much of the size/value premium the 3-factor model "explains away." This is a perfect lead-in to the Fama-MacBeth table (your next RFZ task).

---

## FAQ

**Q: Why subtract Rf from the portfolio return?**  
You're modeling *excess* returns — compensation above the risk-free rate. The factors (Mkt-RF, SMB, HML) are themselves excess returns. Regressing raw returns on excess-return factors would give you a biased intercept.

**Q: Why statsmodels instead of sklearn?**  
sklearn's `LinearRegression` gives coefficients but no t-statistics or R². For academic finance work you always need t-stats to assess whether α is statistically different from 0.

**Q: Why does small growth tend to have a negative alpha?**  
This is sometimes called the "small-growth anomaly" — the FF3 model slightly *over-predicts* what small-growth stocks should earn because the model assumes small stocks earn the full SMB premium and growth stocks earn the full (negative) HML premium, but in reality small-growth firms have other characteristics that reduce returns.

**Q: What if my R² is too low (< 0.7) for some portfolios?**  
Almost certainly you forgot to subtract Rf from the portfolio returns before regressing. The dependent variable must be *excess* returns, not raw returns.

---

## Git discipline

Every time you complete a step: `git add notebooks/03_ff3_replication.ipynb && git commit -m "wip: step N done"`

Final commit when results are validated:
```bash
git add results/ff3_replication.csv notebooks/03_ff3_replication.ipynb src/factors/fama_french.py
git commit -m "feat: FF3 baseline replication validated"
```
