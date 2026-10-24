# Big Red 200 run

`panel_cvar.py --firm-ae` on IU Big Red 200, 22 Oct 2026.

- Job 8688102, partition `general`, account `c02261`, one node `nid0398`.
- About 60 seconds of compute. Queue plus run was under two minutes.
- HPE Cray EX, AMD EPYC. `module load cray-python` gives Python 3.11.7 with
  NumPy 1.24.4, SciPy, pandas 1.5.3. A `--system-site-packages` venv plus
  `pyarrow==16.1.0`. Newer pyarrow wants NumPy 2.0, which the Cray stack does
  not ship, so the version is pinned down rather than upgrading NumPy under
  Cray SciPy.
- Output in `bigred_out/`: `panel_cvar_8688102.out`, an empty
  `panel_cvar_8688102.err`, and `panel_cvar.json`.

The cluster result equals the Mac result to the last digit: every portfolio
CVaR, the firm summary, and the firm-level amplitude-estimation line are
identical. The single-thread arithmetic is the same on both machines, so Big
Red did not make the calculation faster or the noise more real. It is a clean
reproduction on a second architecture, nothing more. The `machine` field in
the cluster JSON still reads `local Mac` because the script does not detect the
host; the provenance is this file and the job id, not that label.

The job in this repository that is actually cluster-sized is
`R/05_permutation_null.R`: fifty matched splits, two regimes, fifty thousand
MCMC draws each. That has not been run.
