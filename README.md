# RegimeFactorZoo

**Empirical asset pricing meets ML: a regime-stable factor zoo on CRSP/Compustat (with public-data fallback).**

Replicates and extends Baba-Yara (2026) *In Search of Sparsity* — testing whether sparse factor selections persist across VIX-defined market regimes.

---

## What this does

1. **Data layer (dual track):**
   - **Primary:** CRSP + Compustat + Fama-French via WRDS (academic credentials)
   - **Fallback:** Ken French Data Library + yfinance (no credentials needed; fully reproducible by any reviewer)
2. Reproduces Fama-French 3-factor + momentum (validated against Ken French's library)
3. Runs ML-based factor selection: OLS / Lasso / Ridge / ElasticNet / XGBoost / sparse-Bayesian
4. **Original contribution:** regime-stability split by VIX percentile + 2008 / 2020 regime breaks
5. Reports OOS results with proper walk-forward time-series CV + transaction-cost overlay (5 bps/turn)

## Quickstart

```bash
# 1. Clone + venv
git clone https://github.com/pbathuri/regime-factor-zoo.git
cd regime-factor-zoo
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

# 2a. WRDS path (requires institutional credentials)
cp .env.example .env
# Edit .env with your WRDS_USERNAME (password resolved via ~/.pgpass)
make wrds-test          # smoke test — confirms WRDS connection works
make wrds-quick         # ~1 min: FF3 + FF5 + momentum from WRDS
make wrds-data          # ~10-30 min: full CRSP + Compustat + FF pull

# 2b. OR public-data path (no credentials)
make public-data        # Ken French + yfinance, ~1 min
```

## First-time WRDS setup (run once)

The `wrds` Python package uses PostgreSQL's `.pgpass` file for credential management. Set it up once interactively:

```bash
source .venv/bin/activate
python -c "import wrds; wrds.Connection()"
```

Enter your WRDS username + password when prompted. The package writes credentials to `~/.pgpass` so subsequent runs are non-interactive. Add `WRDS_USERNAME=your_user` to `.env` to skip the username prompt.

## Data sources

| Source | What it gives you | When to use |
|---|---|---|
| **WRDS / CRSP (msf, dsf)** | Survivorship-bias-free returns, all NYSE/AMEX/NASDAQ common shares since 1962 | Production-quality factor builds |
| **WRDS / Compustat (funda, fundq)** | Firm fundamentals (book equity, sales, capex, etc.) for FF-style characteristics | Building the factor zoo |
| **WRDS / CCM linktable** | Joins CRSP `permno` ↔ Compustat `gvkey` | Any CRSP+Compustat join |
| **WRDS / ff.factors_monthly** | FF3 + UMD factor returns | Quick benchmark; updates more frequently than public CSVs |
| **Ken French library (pandas-datareader)** | FF3, FF5, momentum, 25 portfolios | No-WRDS reproducibility; reviewer-friendly |
| **yfinance** | SPY + individual tickers, daily OHLCV | Sanity checks, ETF benchmarks |
| **FRED** | VIX, treasury rates | Regime-cut covariates |

## Repo layout

```
regime-factor-zoo/
├── src/
│   ├── data/
│   │   ├── wrds_connect.py          ← connection helper (.env + .pgpass)
│   │   ├── wrds_pull_crsp.py        ← CRSP monthly + daily
│   │   ├── wrds_pull_compustat.py   ← Compustat annual + quarterly + link
│   │   ├── wrds_pull_ff.py          ← FF factors from WRDS
│   │   ├── wrds_pull_all.py         ← orchestrator
│   │   ├── download_factors.py      ← public-data fallback (Ken French + yfinance)
│   │   └── characteristics.py       ← firm characteristic constructors (WIP)
│   ├── factors/                     ← factor construction (Fama-MacBeth, etc.)
│   ├── models/                      ← OLS / Lasso / Ridge / XGBoost / Bayesian
│   ├── eval/                        ← time-series CV, transaction-cost overlay
│   └── regimes/                     ← VIX-percentile split, structural breaks
├── data/
│   ├── pulls/                       ← raw WRDS dumps (gitignored)
│   └── factors/                     ← constructed factors (gitignored)
├── notebooks/                       ← exploratory notebooks
├── derivatives/                     ← optional secondary track (Monte Carlo extension)
├── notes/                           ← paper notes
├── papers/                          ← reference PDFs (gitignored)
├── tests/                           ← pytest
└── Makefile                         ← `make help` for all targets
```

## Status

| Milestone | Target | Done |
|-----------|--------|------|
| Repo skeleton + venv + public-data layer | May 16 | ✅ |
| WRDS integration + dual-track data layer | May 19 | ✅ |
| FF3 reproduction ±1% vs Ken French | May 31 | ~ |
| Fama-MacBeth table + Newey-West SE | Jun 14 | ☐ |
| Lasso/Ridge/EN OOS with TS-CV | Jun 28 | ☐ |
| XGBoost + sparse-Bayesian | Jul 12 | ☐ |
| Regime-stability extension (VIX split) | Jul 26 | ☐ |
| Derivatives Monte Carlo branch | Aug 7 | ☐ |
| **v1.0 public release + memo.pdf** | **Aug 14** | ☐ |

## Reproducibility note

Every result in this repo is derived from a `make`-able pipeline. WRDS users get production-grade panel data; non-WRDS users still reproduce the entire empirical structure from Ken French + yfinance + FRED. No code path requires a paid data subscription.

## References

Core papers (see `papers/papers.bib` and `notes/` for detailed reading notes):

- Cochrane (2011) *Discount Rates* — AFA Presidential Address
- Fama & French (1993) *Common Risk Factors in Returns on Stocks and Bonds*
- Hou, Xue, Zhang (2015) *Digesting Anomalies: An Investment Approach*
- Gu, Kelly, Xiu (2020) *Empirical Asset Pricing via Machine Learning*
- **Baba-Yara (2026) *In Search of Sparsity: Bayesian Sparse Factor Models and the Factor Zoo*** (anchor paper)

## License

MIT (TBD — finalize before v1.0 public release Aug 14, 2026).

---

*Started May 2026. Part of PhD application portfolio (CMU / Stanford GSB / UPenn Wharton target, Fall 2027 applications).*
