# RegimeFactorZoo

Does sparse factor selection in asset pricing hold up across volatility regimes?

Undergraduate research project, IU Bloomington, summer 2026.

## Replication

Reproduces the continuous spike-and-slab estimator of Bryzgalova, Huang &
Julliard (2023, JF 78:1) on their 51-factor, 60-portfolio setup, using their
replication archive. At prior Sharpe ratio 2:

- Posterior inclusion probabilities match Table III (BEH_PEAD 0.704, MKT 0.578,
  CMA* 0.544)
- BMA risk prices match their published lambda.bma.csv to 1e-14
- Data check: their OA15 quantity computes to 3.2199 against the 3.219911 in
  their code comments

Details in report/REPLICATION_NOTE.md.

## Extension (in progress)

BHJ split their sample by calendar date. This project conditions selection on
volatility state instead:

- Regime labels from trailing 12-month realized market volatility, with an
  expanding-percentile threshold so no future information enters the label
- Same estimator run separately on high-vol (184 months) and low-vol (335)
- Preliminary: PIP correlation across regimes is 0.24 with the prior held fixed,
  0.19 with per-regime calibration. Largest gaps are BAB, ROE, UMD, MKT, all
  weighted more heavily in calm markets.

This is not yet a result. Two random splits of the same data would also produce
a correlation below one. The matched-size permutation null
(R/05_permutation_null.R) has not been run; until it is, the number above means
nothing on its own.

## Earlier phases

FF3 rebuilt from CRSP and validated against Ken French (SMB 0.976, HML 0.965);
Fama-MacBeth with Newey-West errors on OSAP characteristics. See notebooks/.

## Layout

    src/data/       WRDS pulls, test-asset construction
    src/factors/    FF3 from scratch
    src/regimes/    volatility regime labeling
    src/models/     penalized SDF (frequentist companion)
    src/eval/       regime stability, permutation null
    R/              BHJ replication and regime split
    notes/          paper reading notes

## Running it

Requires WRDS access and R 4.5 with BayesianFactorZoo (CRAN archive).
Data directories are gitignored.

    python -m src.regimes.vol_regimes
    Rscript R/02_replicate_table3.R      # SIM and PSI_IDX via env vars
