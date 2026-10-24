"""CVaR split on the local labeled market excess return.

Loss is -mktrf from data/factors/regimes.parquet. The histogram conditional
mean and the amplitude-estimation bar are the same calculations as run.py.
This sample has no closed form.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import estimation
import problems

ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / "data" / "factors" / "regimes.parquet"
OUT = Path(__file__).resolve().parent / "data" / "market_regimes.json"
ALPHA = problems.CVAR_ALPHA
QUBITS = 5
PHASE_BITS = (4, 6, 8, 10)


def _block(name: str, returns: np.ndarray) -> dict:
    losses = -np.asarray(returns, dtype=float)
    legacy = problems.legacy_cvar(losses, ALPHA, n_qubits=QUBITS)
    excess = np.maximum(legacy.centers - legacy.value_at_risk, 0.0)
    state, amplitude, excess_max = problems.encode_nonnegative(legacy.masses, excess)
    discrete_excess = amplitude * excess_max
    discrete_cvar = legacy.value_at_risk + discrete_excess / (1.0 - ALPHA)
    factor = excess_max / (1.0 - ALPHA)
    rows = []
    for bits in PHASE_BITS:
        result = estimation.estimate(state, bits, seed=0)
        estimated = legacy.value_at_risk + result.median * excess_max / (1.0 - ALPHA)
        rows.append(
            {
                "t": result.phase_bins,
                "cvar": estimated,
                "error_vs_discrete": estimated - discrete_cvar,
                "propagated_bar": factor * result.bound,
                "median_inside": result.median_inside,
                "success_probability": result.success_probability,
            }
        )
    return {
        "slice": name,
        "months": int(losses.size),
        "mean_return": float(np.mean(returns)),
        "sample_var": legacy.value_at_risk,
        "sample_cvar": legacy.sample_cvar,
        "histogram_cvar": legacy.returned_cvar,
        "discrete_cvar": discrete_cvar,
        "propagation_factor": factor,
        "amplitude_estimation": rows,
    }


def main() -> None:
    if not SERIES.is_file():
        raise FileNotFoundError(f"missing local series {SERIES}")
    frame = pd.read_parquet(SERIES)
    labeled = frame.dropna(subset=["regime"])
    blocks = [
        _block("labeled", labeled["mktrf"].to_numpy()),
        _block("high", labeled.loc[labeled["regime"] == "high", "mktrf"].to_numpy()),
        _block("low", labeled.loc[labeled["regime"] == "low", "mktrf"].to_numpy()),
    ]
    payload = {
        "series": "data/factors/regimes.parquet",
        "column": "mktrf",
        "loss": "-mktrf",
        "alpha": ALPHA,
        "histogram_qubits": QUBITS,
        "units": "decimal monthly excess return, as stored",
        "slices": blocks,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    for block in blocks:
        last = block["amplitude_estimation"][-1]
        print(
            f"{block['slice']:8}  n={block['months']:4d}  "
            f"mean={block['mean_return']:+.5f}  "
            f"sample CVaR={block['sample_cvar']:.5f}  "
            f"histogram CVaR={block['histogram_cvar']:.5f}  "
            f"t={last['t']} AE CVaR={last['cvar']:.5f}  "
            f"bar={last['propagated_bar']:.5f}"
        )
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
