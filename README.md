# RegimeFactorZoo

**Empirical asset pricing meets ML: a regime-stable factor zoo on CRSP/Compustat data.**

Replicates and extends Baba-Yara (2026) *In Search of Sparsity* — testing whether sparse factor selections persist across VIX-defined market regimes.

---

## What this does

1. Pulls CRSP + Compustat from WRDS → clean returns panel
2. Reproduces Fama-French 3-factor + momentum (validated against Ken French's library)
3. Runs ML-based factor selection: OLS / Lasso / Ridge / ElasticNet / XGBoost / sparse-Bayesian
4. **Original contribution:** regime-stability split by VIX percentile + 2008/2020 regime breaks
5. Reports OOS results with proper walk-forward time-series CV + transaction-cost overlay (5 bps/turn)

## Quickstart

```bash
make data   # pull CRSP + Compustat → data/pulls/
make run    # run full pipeline → results/
```

## Status

| Milestone | Target | Done |
|-----------|--------|------|
| Repo skeleton + WRDS connection | May 17 | [ ] |
| FF3 reproduction ±1% vs Ken French | May 31 | [ ] |
| Fama-MacBeth table + Newey-West SE | Jun 14 | [ ] |
| Lasso/Ridge/EN OOS with TS-CV | Jun 28 | [ ] |
| XGBoost + sparse-Bayesian | Jul 12 | [ ] |
| Regime-stability extension (VIX split) | Jul 26 | [ ] |
| Derivatives Monte Carlo branch | Aug 7 | [ ] |
| v1.0 public release + memo.pdf | Aug 17 | [ ] |

## Structure

```
regime-factor-zoo/
├── data/pulls/          # cached parquet from WRDS
├── data/factors/        # FF3, FF5, momentum, q-factor
├── src/data/            # WRDS pull + characteristics
├── src/factors/         # factor reproductions
├── src/models/          # linear, trees, bayesian
├── src/eval/            # time-series CV + TCA
├── src/regimes/         # VIX-split regime analysis
├── derivatives/         # qhpc_cache Monte Carlo extension
├── notes/               # one .md per paper
├── papers/              # PDFs + papers.bib
└── tests/
```

## Papers

See `papers/papers.bib` and `notes/` for detailed notes on each.

Core references: Cochrane (2011), Fama-French (1993), Baba-Yara (2026), Gu-Kelly-Xiu (2020).

---

*Started May 2026. Part of PhD application portfolio (CMU/Stanford/UPenn target, Fall 2027).*
