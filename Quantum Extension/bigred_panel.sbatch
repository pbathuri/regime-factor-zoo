#!/bin/bash
#SBATCH --job-name=panel_cvar
#SBATCH --partition=general
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=panel_cvar_%j.out
#SBATCH --error=panel_cvar_%j.err

# Optional rerun of panel_cvar.py --firm-ae.
# On this Mac the portfolio pass took about 8 seconds and one firm estimate
# at 256 bins took about 3 milliseconds, so the full panel does not need
# the cluster. Submit from Quantum Extension only after an interactive login
# and after these files are on the node:
#   data/pulls/crsp_monthly.parquet
#   data/pulls/compustat_annual.parquet
#   data/pulls/crsp_compustat_link.parquet
#   data/factors/regimes.parquet

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
module load cray-python
source "${HOME}/venvs/panel-cvar/bin/activate"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
python3 -c "import numpy, scipy, pandas, pyarrow"
python3 panel_cvar.py --firm-ae
