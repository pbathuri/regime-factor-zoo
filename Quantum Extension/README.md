# Quantum Extension

The amplitude-estimation audit, kept next to the local factor data.

The public GitHub tree does not include `data/`. This folder is for the local checkout, where `data/factors/regimes.parquet` is the labeled market excess return (`mktrf`, high or low from trailing 12-month realized volatility).

`market_check.py` reads that series and prints the same split already used on the normal sample: the sample CVaR of the loss `-mktrf`, the histogram conditional mean, and the amplitude-estimation bar on the excess. There is no Gaussian closed form for these months. The script does not select factors.

`panel_cvar.py` is the same split on the local CRSP monthly panel, July 1973 through December 2024, with NYSE size and book-to-market quintiles from Compustat. The result is `data/panel_cvar.json`. `bigred_panel.sbatch` reruns the per-firm estimates on Big Red after an interactive login. That pass took about a minute on this Mac.

The rest of the folder is the audit itself.

- `NOTE.md` is the statevector note.
- `MEASUREMENTS.md` is the Kingston snapshot note.
- `data/` holds `kingston_snapshot.json`, `scale_sweep.json`, and, after `market_check.py`, `market_regimes.json`.
- `figures/` holds the scaling plots.

From this directory:

```
/opt/miniconda3/bin/python3 test_audit.py
/opt/miniconda3/bin/python3 market_check.py
```

Qiskit checks still use the environment at `~/Desktop/quantum/.venv`.
