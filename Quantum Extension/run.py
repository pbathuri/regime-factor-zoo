"""Print the call-price comparison and the amplitude-estimation audit.

Run with a Python that has a working SciPy, for example
/opt/miniconda3/bin/python3 run.py
"""

from __future__ import annotations

import numpy as np

import estimation
import problems

PHASE_BITS = (4, 6, 8, 10)
SHOTS = 4096
SHOT_SEED = 42
MONTE_CARLO_PATHS = 4096
MONTE_CARLO_SEED = 7


def _row(cells: list[object]) -> str:
    return "  ".join(f"{cell}" for cell in cells)


def call_report() -> str:
    closed = problems.black_scholes_call()
    hermite_16, hermite_mass, hermite_positive = problems.gauss_hermite_call(16)
    hermite_96 = problems.gaussian_expectation(96, problems.call_payoff_of_normal)
    truncated, renormalized = problems.windowed_call_integral(4.0)
    grid_spots, grid_mass, grid_positive, discount = problems.uniform_spot_grid(16)
    grid_16 = float(discount * np.sum(grid_mass * grid_positive))
    grid_256 = problems.grid_call_price(256)
    monte_carlo, stderr = problems.monte_carlo_call(MONTE_CARLO_PATHS, MONTE_CARLO_SEED)
    grid_state, grid_amplitude, payoff_max = problems.encode_nonnegative(grid_mass, grid_positive)
    scale = discount * payoff_max
    generator = np.random.default_rng(SHOT_SEED)
    successes = int(generator.binomial(SHOTS, grid_amplitude))
    shot_price = scale * successes / SHOTS
    shot_se = scale * float(np.sqrt(grid_amplitude * (1.0 - grid_amplitude) / SHOTS))

    lines = [
        "European call. S0=100, K=105, r=0.05, sigma=0.2, T=1.",
        f"Black–Scholes price {closed:.10f}",
        "",
        _row(["estimator", "value", "error_vs_BS", "error_vs_discrete", "discrete_bar", "median_inside"]),
    ]
    discrete_rows = [
        ("black_scholes", closed, None),
        ("gauss_hermite_16", hermite_16, None),
        ("gauss_hermite_96", hermite_96, None),
        ("window_integral_unnormalized", truncated, None),
        ("window_renormalized_pm4sigma", renormalized, None),
        ("uniform_grid_16_exact", grid_16, grid_16),
        ("uniform_grid_16_shots_4096", shot_price, grid_16),
        ("uniform_grid_256_exact", grid_256, None),
        (f"monte_carlo_{MONTE_CARLO_PATHS}", monte_carlo, None),
    ]
    for name, value, discrete in discrete_rows:
        versus_closed = value - closed
        if discrete is None:
            versus_discrete = ""
            bar = ""
            inside = ""
        else:
            versus_discrete = f"{value - discrete:.6e}"
            bar = ""
            inside = ""
        lines.append(
            _row(
                [
                    name,
                    f"{value:.10f}",
                    f"{versus_closed:.6e}",
                    versus_discrete,
                    bar,
                    inside,
                ]
            )
        )

    lines.append("")
    lines.append(
        f"Uniform-grid encoding: payoff_max={payoff_max:.6f}, marked probability a={grid_amplitude:.8f}, "
        f"price scale={scale:.6f}."
    )
    lines.append(
        f"Shot estimator, {SHOTS} shots, seed {SHOT_SEED}: binomial standard error on the price {shot_se:.6e}."
    )
    lines.append(
        f"Monte Carlo standard error at {MONTE_CARLO_PATHS} paths, seed {MONTE_CARLO_SEED}: {stderr:.6e}."
    )
    lines.append("Amplitude estimation estimates the uniform-grid expectation, not the Black–Scholes value.")
    for bits in PHASE_BITS:
        result = estimation.estimate(grid_state, bits, seed=0)
        estimated_price = scale * result.median
        shot_value = scale * result.shot
        price_bar = scale * result.bound
        lines.append(
            _row(
                [
                    f"ae_median_t{result.phase_bins}",
                    f"{estimated_price:.10f}",
                    f"{estimated_price - closed:.6e}",
                    f"{estimated_price - grid_16:.6e}",
                    f"{price_bar:.6e}",
                    str(result.median_inside),
                ]
            )
        )
        lines.append(
            f"    t={result.phase_bins}  a={result.amplitude:.8f}  median_a={result.median:.8f}  "
            f"|median-a|={result.median_error:.3e}  bar={result.bound:.3e}  "
            f"P(inside)={result.success_probability:.6f}  floor={estimation.SUCCESS_PROBABILITY:.6f}  "
            f"one_shot_a={result.shot:.8f}  one_shot_price={shot_value:.6f}  "
            f"shot_inside={abs(result.shot - result.amplitude) <= result.bound + 1e-12}"
        )
    lines.append(f"Gauss–Hermite 16 mass check {float(hermite_mass.sum()):.12f}.")
    return "\n".join(lines)


def cvar_report() -> str:
    value_at_risk, closed = problems.gaussian_var_cvar()
    losses = problems.normal_losses()
    legacy = problems.legacy_cvar(losses, problems.CVAR_ALPHA, n_qubits=5)
    excess = np.maximum(legacy.centers - legacy.value_at_risk, 0.0)
    state, amplitude, excess_max = problems.encode_nonnegative(legacy.masses, excess)
    discrete_excess = amplitude * excess_max
    discrete_cvar = legacy.value_at_risk + discrete_excess / (1.0 - problems.CVAR_ALPHA)
    factor = excess_max / (1.0 - problems.CVAR_ALPHA)
    tail_fraction = np.zeros_like(legacy.masses)
    tail_fraction[legacy.tail_index :] = 1.0
    tail_state = problems.expectation_state(legacy.masses, tail_fraction)

    lines = [
        "Normal loss N(0,1), alpha=0.95. Sample of 20000, seed 11, 5-qubit histogram.",
        f"Closed form VaR {value_at_risk:.10f}  CVaR {closed:.10f}",
        f"Sample VaR {legacy.value_at_risk:.10f}  sample CVaR {legacy.sample_cvar:.10f}",
        f"Legacy returned CVaR (histogram conditional mean) {legacy.returned_cvar:.10f}",
        f"    error vs closed form {legacy.returned_cvar - closed:.6e}",
        f"    this number does not depend on an amplitude-estimation outcome.",
        f"Histogram tail probability from index {legacy.tail_index}: {legacy.tail_probability:.6f}",
        f"Exact discrete excess E[(center - sample VaR)+] = {discrete_excess:.8f}",
        f"Assembled discrete CVaR = sample VaR + excess / (1-alpha) = {discrete_cvar:.10f}",
        f"Excess maximum on the histogram {excess_max:.6f}. "
        f"Propagation factor max/(1-alpha) = {factor:.6f}.",
        "",
        "Tail-probability amplitude (the quantity the existing comparator circuit estimates):",
    ]
    tail = estimation.estimate(tail_state, phase_bits=6, seed=0)
    lines.append(
        f"    t={tail.phase_bins}  a={tail.amplitude:.8f}  median={tail.median:.8f}  "
        f"|err|={tail.median_error:.3e}  bar={tail.bound:.3e}  "
        f"P(inside)={tail.success_probability:.6f}  median_inside={tail.median_inside}"
    )
    lines.append("")
    lines.append("Corrected estimator: amplitude estimation of the excess, then sample VaR + â * max / (1-alpha).")
    for bits in PHASE_BITS:
        result = estimation.estimate(state, bits, seed=0)
        estimated_excess = result.median * excess_max
        estimated_cvar = legacy.value_at_risk + estimated_excess / (1.0 - problems.CVAR_ALPHA)
        cvar_bar = factor * result.bound
        lines.append(
            f"    t={result.phase_bins}  a={result.amplitude:.8f}  median_a={result.median:.8f}  "
            f"|a err|={result.median_error:.3e}  a bar={result.bound:.3e}  "
            f"P(inside)={result.success_probability:.6f}  median_inside={result.median_inside}"
        )
        lines.append(
            f"        CVaR={estimated_cvar:.10f}  error_vs_closed={estimated_cvar - closed:.6e}  "
            f"error_vs_discrete={estimated_cvar - discrete_cvar:.6e}  "
            f"propagated_bar={cvar_bar:.6e}  "
            f"one_shot_inside={abs(result.shot - result.amplitude) <= result.bound + 1e-12}"
        )
    lines.append(
        "The legacy conditional mean stays "
        f"{legacy.returned_cvar:.10f} at every t above."
    )
    return "\n".join(lines)


def main() -> None:
    print(call_report())
    print()
    print(cvar_report())


if __name__ == "__main__":
    main()
