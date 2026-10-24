"""Scaling sweeps that fit on this Mac.

Classical quadrature and statevector amplitude estimation are exact and cheap.
The noisy circuits stay at 3–6 qubits, which is the size already measured on the
Kingston snapshot. A 156-qubit job or a Big Red allocation would not change
the gate noise those circuits see.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime.fake_provider import FakeKingston

import circuits
import estimation
import likelihood
import problems
import run_device

OUT = Path(__file__).resolve().parent / "data" / "scale_sweep.json"
NODE_COUNTS = (4, 8, 16, 32, 64, 96, 128, 256, 384, 512)
MONTE_CARLO_PATHS = (256, 1024, 4096, 16384, 65536, 262144)
MONTE_CARLO_SEEDS = 24
PHASE_BITS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
THETA = 0.7
NOISY_NODES = (4, 8, 16, 32)
NOISY_CALL_SEEDS = 8
NOISY_SHOTS = 4096
AMPLIFICATION = (0, 1, 2, 4, 8, 12, 16)
AMPLIFICATION_SEEDS = 16
CVAR_QUBITS = (3, 4, 5, 6, 7, 8)


def _log10_abs(value: float, floor: float = 1e-16) -> float:
    return float(np.log10(max(abs(value), floor)))


def classical_call() -> dict:
    closed = problems.black_scholes_call()
    _, window = problems.windowed_call_integral(4.0)
    hermite = []
    grid = []
    for nodes in NODE_COUNTS:
        hermite_price = problems.gaussian_expectation(nodes, problems.call_payoff_of_normal)
        grid_price = problems.grid_call_price(nodes)
        hermite.append(
            {
                "nodes": nodes,
                "price": hermite_price,
                "abs_error": abs(hermite_price - closed),
                "log10_abs_error": _log10_abs(hermite_price - closed),
            }
        )
        grid.append(
            {
                "nodes": nodes,
                "price": grid_price,
                "abs_error": abs(grid_price - closed),
                "log10_abs_error": _log10_abs(grid_price - closed),
            }
        )
    probe = problems.call_payoff_of_normal(np.random.default_rng(0).standard_normal(200_000))
    sigma = float(probe.std(ddof=1))
    monte_carlo = []
    for paths in MONTE_CARLO_PATHS:
        errors = []
        for seed in range(MONTE_CARLO_SEEDS):
            price, _ = problems.monte_carlo_call(paths, seed)
            errors.append(abs(price - closed))
        errors_array = np.asarray(errors)
        monte_carlo.append(
            {
                "paths": paths,
                "median_abs_error": float(np.median(errors_array)),
                "log10_median_abs_error": _log10_abs(float(np.median(errors_array))),
                "theoretical_stderr": sigma / np.sqrt(paths),
                "log10_theoretical_stderr": _log10_abs(sigma / np.sqrt(paths)),
            }
        )
    return {
        "black_scholes": closed,
        "window_renormalized": window,
        "window_abs_error": abs(window - closed),
        "log10_window_abs_error": _log10_abs(window - closed),
        "payoff_std": sigma,
        "gauss_hermite": hermite,
        "uniform_grid": grid,
        "monte_carlo": monte_carlo,
    }


def amplitude_estimation() -> dict:
    amplitude = float(np.sin(THETA) ** 2)
    preparation, _, _ = circuits.preparation_and_grover(THETA)
    rows = []
    for bits in PHASE_BITS:
        result = estimation.estimate(preparation[:, 0], bits, seed=0)
        rows.append(
            {
                "phase_bits": bits,
                "t": result.phase_bins,
                "median_abs_error": result.median_error,
                "log10_median_abs_error": _log10_abs(result.median_error),
                "bound": result.bound,
                "log10_bound": _log10_abs(result.bound),
                "success_probability": result.success_probability,
                "shot_abs_error": abs(result.shot - amplitude),
                "shot_inside": abs(result.shot - amplitude) <= result.bound + 1e-12,
            }
        )
    _, masses, positive, discount = problems.uniform_spot_grid(16)
    state, marked, payoff_max = problems.encode_nonnegative(masses, positive)
    scale = discount * payoff_max
    discrete = scale * marked
    closed = problems.black_scholes_call()
    call_rows = []
    for bits in (2, 4, 6, 8, 10):
        result = estimation.estimate(state, bits, seed=0)
        price = scale * result.median
        price_bound = scale * result.bound
        call_rows.append(
            {
                "phase_bits": bits,
                "t": result.phase_bins,
                "price": price,
                "abs_error_vs_grid": abs(price - discrete),
                "abs_error_vs_black_scholes": abs(price - closed),
                "log10_abs_error_vs_grid": _log10_abs(price - discrete),
                "price_bound": price_bound,
                "log10_price_bound": _log10_abs(price_bound),
                "success_probability": result.success_probability,
                "median_inside": result.median_inside,
            }
        )
    return {
        "theta": THETA,
        "amplitude": amplitude,
        "ry": rows,
        "call_grid_price": discrete,
        "call_scale": scale,
        "call": call_rows,
    }


def cvar_bins() -> dict:
    _, closed = problems.gaussian_var_cvar()
    losses = problems.normal_losses()
    rows = []
    for qubits in CVAR_QUBITS:
        legacy = problems.legacy_cvar(losses, problems.CVAR_ALPHA, n_qubits=qubits)
        rows.append(
            {
                "qubits": qubits,
                "bins": 1 << qubits,
                "returned_cvar": legacy.returned_cvar,
                "abs_error": abs(legacy.returned_cvar - closed),
                "log10_abs_error": _log10_abs(legacy.returned_cvar - closed),
                "sample_cvar": legacy.sample_cvar,
            }
        )
    return {"closed_form": closed, "histogram": rows}


def noisy_scaling(snapshot_backend, ideal, noisy) -> dict:
    closed = problems.black_scholes_call()
    call_rows = []
    for nodes in NOISY_NODES:
        print(f"noisy call loader n={nodes}", flush=True)
        _, masses, positive, discount = problems.uniform_spot_grid(nodes)
        state, marked, payoff_max = problems.encode_nonnegative(masses, positive)
        scale = discount * payoff_max
        discrete = scale * marked
        compiled = run_device.compile_circuit(circuits.call_loader_circuit(state), noisy)
        facts = run_device.circuit_facts(compiled)
        ideal_prices = []
        noisy_prices = []
        noisy_frequencies = []
        for seed in range(NOISY_CALL_SEEDS):
            ideal_counts = run_device.run_counts(compiled, ideal, NOISY_SHOTS, seed)
            noisy_counts = run_device.run_counts(compiled, noisy, NOISY_SHOTS, seed)
            ideal_prices.append(scale * run_device.good_fraction(ideal_counts))
            frequency = run_device.good_fraction(noisy_counts)
            noisy_frequencies.append(frequency)
            noisy_prices.append(scale * frequency)
        call_rows.append(
            {
                "nodes": nodes,
                "qubits": int(np.log2(state.size)),
                "depth": facts["depth"],
                "cz": facts["operations"].get("cz", 0),
                "discrete_price": discrete,
                "marked_probability": marked,
                "mean_ideal_price": float(np.mean(ideal_prices)),
                "mean_noisy_price": float(np.mean(noisy_prices)),
                "mean_noisy_frequency": float(np.mean(noisy_frequencies)),
                "abs_error_vs_black_scholes": abs(float(np.mean(noisy_prices)) - closed),
                "log10_abs_error_vs_black_scholes": _log10_abs(float(np.mean(noisy_prices)) - closed),
            }
        )
    amplitude = float(np.sin(THETA) ** 2)
    compiled_by_m = {}
    amp_facts = {}
    for repetitions in AMPLIFICATION:
        compiled_by_m[repetitions] = run_device.compile_circuit(
            circuits.amplification_circuit(THETA, repetitions), noisy
        )
        amp_facts[str(repetitions)] = run_device.circuit_facts(compiled_by_m[repetitions])
    amp_rows = []
    print("noisy one-qubit amplification", flush=True)
    for repetitions in AMPLIFICATION:
        formula = likelihood.ideal_probability(repetitions, amplitude)
        ideal_hats = []
        noisy_hats = []
        for seed in range(AMPLIFICATION_SEEDS):
            ideal_counts = run_device.run_counts(compiled_by_m[repetitions], ideal, NOISY_SHOTS, seed)
            noisy_counts = run_device.run_counts(compiled_by_m[repetitions], noisy, NOISY_SHOTS, seed)
            ideal_hats.append(run_device.good_fraction(ideal_counts))
            noisy_hats.append(run_device.good_fraction(noisy_counts))
        amp_rows.append(
            {
                "m": repetitions,
                "ideal_formula": formula,
                "mean_ideal_frequency": float(np.mean(ideal_hats)),
                "mean_noisy_frequency": float(np.mean(noisy_hats)),
                "cz": amp_facts[str(repetitions)]["operations"].get("cz", 0),
                "depth": amp_facts[str(repetitions)]["depth"],
            }
        )
    return {"call": call_rows, "amplification": amp_rows, "shots": NOISY_SHOTS}


def main() -> None:
    print("classical and statevector sweeps", flush=True)
    payload = {
        "machine": "local Mac",
        "why_not_bigred": "circuits are 1–6 qubits; the login node also rejected non-interactive SSH",
        "why_not_ibm_hardware": "no IBM Quantum account is saved",
        "noise_model": "FakeKingston snapshot 2026-04-15, Aer, no mitigation",
        "classical": classical_call(),
        "amplitude_estimation": amplitude_estimation(),
        "cvar": cvar_bins(),
    }
    snapshot = FakeKingston()
    noisy = AerSimulator.from_backend(snapshot)
    ideal = AerSimulator()
    payload["noisy"] = noisy_scaling(snapshot, ideal, noisy)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
