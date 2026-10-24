"""Figures for the scaling sweep in data/scale_sweep.json.

Run with the conda interpreter, which has matplotlib:

    /opt/miniconda3/bin/python3 plot_scale.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "data" / "scale_sweep.json").read_text())
OUT = ROOT / "figures"
FIGURE_DATE = "2026-10-23"


def _save(figure, name: str) -> None:
    figure.text(
        0.5, 0.015,
        f"Source: data/scale_sweep.json; figure {FIGURE_DATE}; noise: FakeKingston calibration 2026-04-15 in Aer, no mitigation, not live hardware.",
        ha="center", fontsize=8,
    )
    figure.tight_layout(rect=(0, 0.065, 1, 0.95))
    figure.savefig(OUT / name, dpi=160)
    plt.close(figure)


def _finish(ax, xlabel: str, ylabel: str, title: str) -> None:
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, which="both", linewidth=0.4, color="0.75")
    ax.legend(frameon=False, fontsize=8)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    classical = DATA["classical"]
    closed = classical["black_scholes"]
    nodes = [row["nodes"] for row in classical["gauss_hermite"]]
    hermite = [row["abs_error"] for row in classical["gauss_hermite"]]
    grid = [row["abs_error"] for row in classical["uniform_grid"]]
    window = classical["window_abs_error"]

    figure, axes = plt.subplots(2, 2, figsize=(11.0, 8.2))
    figure.suptitle("Call-price error: quadrature, sampling, amplitude estimation and simulated noise")

    ax = axes[0, 0]
    ax.loglog(nodes, hermite, "o-", label="Gauss–Hermite", color="C0")
    ax.loglog(nodes, grid, "s-", label="uniform spot grid", color="C1")
    ax.axhline(window, color="0.35", linestyle="--", label="±4σ window limit")
    _finish(
        ax,
        "Quadrature nodes (count)",
        "absolute price error (dollars)",
        "Call price versus Black–Scholes 8.021",
    )

    ax = axes[0, 1]
    paths = [row["paths"] for row in classical["monte_carlo"]]
    ax.loglog(paths, [row["median_abs_error"] for row in classical["monte_carlo"]], "o-", label="median absolute error, 24 seeds", color="C0")
    ax.loglog(paths, [row["theoretical_stderr"] for row in classical["monte_carlo"]], "--", label="estimated payoff SD / √N", color="0.35")
    _finish(ax, "Monte Carlo paths (count)", "absolute price error (dollars)", "Monte Carlo rate for the same call")

    ae = DATA["amplitude_estimation"]
    ax = axes[1, 0]
    call_t = [row["t"] for row in ae["call"]]
    ax.loglog(call_t, [row["abs_error_vs_grid"] for row in ae["call"]], "o-", label="|median price − 16-node grid|", color="C0")
    ax.loglog(call_t, [row["price_bound"] for row in ae["call"]], "--", label="Brassard bar, in dollars", color="C3")
    _finish(ax, "Phase bins t = 2^m (count)", "absolute price error (dollars)", "Statevector amplitude estimation: 16-node call")

    ax = axes[1, 1]
    noisy_nodes = [row["cz"] for row in DATA["noisy"]["call"]]
    ax.plot(noisy_nodes, [row["discrete_price"] for row in DATA["noisy"]["call"]], "s--", label="grid price", color="0.35")
    ax.plot(noisy_nodes, [row["mean_ideal_price"] for row in DATA["noisy"]["call"]], "o-", label="ideal Aer shots", color="C0")
    ax.plot(noisy_nodes, [row["mean_noisy_price"] for row in DATA["noisy"]["call"]], "o-", label="FakeKingston in Aer (simulated)", color="C3")
    ax.axhline(closed, color="0.15", linestyle=":", label="Black–Scholes")
    _finish(ax, "CZ gates (count; 4, 8, 16, 32 nodes)", "call price (dollars)", "Call loader: 2026-04-15 snapshot in Aer")
    ax.set_xticks(noisy_nodes)

    _save(figure, "scaling_methods.png")

    figure, axes = plt.subplots(1, 3, figsize=(12.8, 4.5))
    figure.suptitle("Amplitude error, legacy Gaussian CVaR and the no-CZ control")

    ax = axes[0]
    ry = ae["ry"]
    ax.loglog([row["t"] for row in ry], [row["median_abs_error"] for row in ry], "o-", label="|median − sin²(0.7)|", color="C0")
    ax.loglog([row["t"] for row in ry], [row["bound"] for row in ry], "--", label="Brassard bar", color="C3")
    ax.loglog([row["t"] for row in ry], [row["shot_abs_error"] for row in ry], "x", label="one shot, seed 0", color="0.25")
    _finish(ax, "Phase bins t (count)", "absolute amplitude error (unitless)", "Known amplitude sin²(0.7)")

    ax = axes[1]
    cvar = DATA["cvar"]
    bins = [row["bins"] for row in cvar["histogram"]]
    ax.plot(bins, [row["returned_cvar"] for row in cvar["histogram"]], "o-", label="histogram conditional mean", color="C0")
    ax.axhline(cvar["histogram"][0]["sample_cvar"], color="0.35", linestyle="--", label="sample CVaR, same draws")
    ax.axhline(cvar["closed_form"], color="0.15", linestyle=":", label="closed form 2.063")
    ax.set_xscale("log", base=2)
    ax.set_xticks(bins)
    ax.set_xticklabels([str(b) for b in bins])
    _finish(ax, "Histogram bins (count)", "95% CVaR (standard-normal loss units)", "Legacy CVaR: comparator mismatch retained")

    ax = axes[2]
    amp = DATA["noisy"]["amplification"]
    ms = [row["m"] for row in amp]
    ax.plot(ms, [row["ideal_formula"] for row in amp], "o-", label="sin²((2m+1)θ)", color="C0")
    ax.plot(ms, [row["mean_noisy_frequency"] for row in amp], "s-", label="FakeKingston in Aer, 16 seeds", color="C3")
    _finish(ax, "Grover repetitions m (count)", "marked frequency (unitless)", "No CZ: 2026-04-15 snapshot in Aer")
    ax.set_xticks(ms)
    ax.set_ylim(-0.02, 1.05)

    _save(figure, "scaling_details.png")
    print(f"wrote {OUT / 'scaling_methods.png'}")
    print(f"wrote {OUT / 'scaling_details.png'}")


if __name__ == "__main__":
    main()
