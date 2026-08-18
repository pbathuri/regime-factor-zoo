# Exact replication of Bryzgalova, Huang & Julliard (2023), JF 78(1)

**Status:** verified to machine precision at prior SR = 2.

- Data check: `sum(diag(t(corr_Rf.demean) %*% corr_Rf.demean))/N` = 3.2199,
  matching the value stated in their Table3.R OA15 comment (3.219911).
- BMA risk prices vs published `lambda.bma.csv` column X2:
  correlation = 1, max absolute difference = 1.02e-14 across all 52 entries
  (intercept + 51 factors).
- Estimator: their `continuous.spike.cs` (GLS, Y = cbind(f1, R), p = 17 + 60 = 77),
  500,000 MCMC draws, 50,000 burn-in, r = 0.001, aw = bw = 1.
- Test assets: 60 anomaly portfolios (`MonthlyPortfolios.xlsx`), of which the
  first 34 columns are the tradable factors themselves.
- Factors: `MonthlyFactors.xlsx`, sheet "51 factors - ranked" (ordering matters:
  17 non-tradable first, then 34 tradable).

**Note on their RNG convention:** `set.seed(i)` is called inside the MCMC loop,
making output exactly reproducible but departing from standard Gibbs sampling
assumptions. Tested separately in `R/03_seed_experiment.R`.

**Environment:** R 4.5.2 (Framework build, not Homebrew 4.6.1 — MCMCpack is only
installed in the former; use the absolute Rscript path in scripts).
