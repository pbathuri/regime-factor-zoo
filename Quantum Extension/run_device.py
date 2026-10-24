"""Run the audited circuits on an ideal sampler and on IBM's Kingston noise snapshot.

FakeKingston is a local Aer simulation of the coupling map and calibration
published with qiskit-ibm-runtime. It is not a job on the ibmq device, and
Big Red 200 is not used: the login node rejected non-interactive SSH.
No readout mitigation and no error-mitigation pass is applied.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime.fake_provider import FakeKingston

import circuits
import estimation
import likelihood
import problems

SHOTS = 8192
THETA = 0.7
AMPLIFICATION_REPETITIONS = (0, 1, 2, 4, 8)
PHASE_BITS = (2, 3)
AMPLIFICATION_SEEDS = range(20)
CANONICAL_SEEDS = range(10)
CALL_SEEDS = range(5)
DATA_PATH = Path(__file__).resolve().parent / "data" / "kingston_snapshot.json"


def _median(values: list[float]) -> float:
    ordered = np.sort(np.asarray(values, dtype=float))
    return float(ordered[len(ordered) // 2])


def calibration(backend) -> dict:
    properties = backend.properties()
    collected: dict[str, list[float]] = {"sx": [], "cz": [], "rz": [], "x": []}
    for gate in properties.gates:
        if gate.gate not in collected:
            continue
        for parameter in gate.parameters:
            if parameter.name == "gate_error" and parameter.value is not None:
                collected[gate.gate].append(float(parameter.value))
    readout = []
    for qubit in range(backend.num_qubits):
        readout.append(float(properties.readout_error(qubit)))
    summary = {}
    for name, values in collected.items():
        if not values:
            continue
        array = np.asarray(values, dtype=float)
        summary[name] = {
            "count": int(array.size),
            "median": float(np.median(array)),
            "min": float(array.min()),
            "max": float(array.max()),
        }
    readout_array = np.asarray(readout, dtype=float)
    summary["readout"] = {
        "count": int(readout_array.size),
        "median": float(np.median(readout_array)),
        "min": float(readout_array.min()),
        "max": float(readout_array.max()),
    }
    summary["last_update_date"] = str(properties.last_update_date)
    summary["num_qubits"] = int(backend.num_qubits)
    return summary


def compile_circuit(circuit, backend):
    compiled = transpile(circuit, backend=backend, optimization_level=1, seed_transpiler=0)
    return compiled


def circuit_facts(compiled) -> dict:
    counts = {name: int(number) for name, number in compiled.count_ops().items()}
    layout = getattr(compiled, "layout", None)
    physical = None
    if layout is not None:
        physical = [int(qubit) for qubit in layout.final_index_layout(filter_ancillas=True)]
    return {
        "depth": int(compiled.depth()),
        "size": int(compiled.size()),
        "operations": counts,
        "physical_qubits": physical,
    }


def run_counts(compiled, backend, shots: int, seed: int) -> dict[str, int]:
    result = backend.run(compiled, shots=shots, seed_simulator=seed).result()
    raw = result.get_counts()
    return {str(key): int(value) for key, value in raw.items()}


def good_fraction(counts: dict[str, int]) -> float:
    total = sum(counts.values())
    good = sum(value for key, value in counts.items() if key.replace(" ", "")[-1] == "1")
    return good / total


def phase_histogram(counts: dict[str, int], phase_bits: int) -> np.ndarray:
    bins = 1 << phase_bits
    histogram = np.zeros(bins, dtype=float)
    total = sum(counts.values())
    for key, value in counts.items():
        index = int(key.replace(" ", ""), 2)
        histogram[index % bins] += value
    return histogram / total


def weighted_median_from_histogram(estimates: np.ndarray, probabilities: np.ndarray) -> float:
    return estimation.weighted_median(estimates, probabilities)


def _records(repetition_counts: list[tuple[int, dict[str, int]]]) -> list[tuple[int, int, int]]:
    records = []
    for repetitions, counts in repetition_counts:
        shots = sum(counts.values())
        good = int(round(good_fraction(counts) * shots))
        records.append((repetitions, good, shots))
    return records


def amplification_bundle(compiled_by_m, ideal, noisy) -> dict:
    amplitude = float(np.sin(THETA) ** 2)
    per_seed = []
    for seed in AMPLIFICATION_SEEDS:
        ideal_counts = []
        noisy_counts = []
        for repetitions in AMPLIFICATION_REPETITIONS:
            ideal_counts.append((repetitions, run_counts(compiled_by_m[repetitions], ideal, SHOTS, seed)))
            noisy_counts.append((repetitions, run_counts(compiled_by_m[repetitions], noisy, SHOTS, seed)))
        ideal_fit = likelihood.maximum_likelihood(_records(ideal_counts), kappa_fixed=0.0)
        noisy_fit = likelihood.maximum_likelihood(_records(noisy_counts), kappa_fixed=0.0)
        noisy_aware = likelihood.maximum_likelihood(_records(noisy_counts), kappa_fixed=None)
        classical_probability = good_fraction(noisy_counts[0][1])
        per_seed.append(
            {
                "seed": int(seed),
                "ideal_kappa0": ideal_fit,
                "noisy_kappa0": noisy_fit,
                "noisy_tanaka": noisy_aware,
                "noisy_classical_m0": classical_probability,
                "noisy_frequencies": [
                    {"m": repetitions, "p_hat": good_fraction(counts)} for repetitions, counts in noisy_counts
                ],
                "ideal_frequencies": [
                    {"m": repetitions, "p_hat": good_fraction(counts)} for repetitions, counts in ideal_counts
                ],
            }
        )
    def errors(key: str) -> list[float]:
        return [abs(item[key]["amplitude"] - amplitude) for item in per_seed]

    return {
        "amplitude": amplitude,
        "shots_per_circuit": SHOTS,
        "repetitions": list(AMPLIFICATION_REPETITIONS),
        "seeds": len(per_seed),
        "ideal_kappa0_median_abs_error": _median(errors("ideal_kappa0")),
        "noisy_kappa0_median_abs_error": _median(errors("noisy_kappa0")),
        "noisy_tanaka_median_abs_error": _median(
            [abs(item["noisy_tanaka"]["amplitude"] - amplitude) for item in per_seed]
        ),
        "noisy_classical_m0_median_abs_error": _median(
            [abs(item["noisy_classical_m0"] - amplitude) for item in per_seed]
        ),
        "tanaka_kappa_median": _median([item["noisy_tanaka"]["kappa"] for item in per_seed]),
        "runs": per_seed,
    }


def canonical_bundle(compiled_by_bits, ideal, noisy) -> dict:
    amplitude = float(np.sin(THETA) ** 2)
    out = {"amplitude": amplitude, "shots": SHOTS, "by_phase_bits": {}}
    for phase_bits, compiled in compiled_by_bits.items():
        bins = 1 << phase_bits
        estimates = np.sin(np.pi * np.arange(bins) / bins) ** 2
        bound = estimation.brassard_bound(amplitude, bins)
        preparation, _, _ = circuits.preparation_and_grover(THETA)
        operator = estimation.grover_from_state(preparation[:, 0])
        _, exact = estimation.outcome_distribution(operator, preparation[:, 0], phase_bits)
        runs = []
        for seed in CANONICAL_SEEDS:
            ideal_counts = run_counts(compiled, ideal, SHOTS, seed)
            noisy_counts = run_counts(compiled, noisy, SHOTS, seed)
            ideal_hist = phase_histogram(ideal_counts, phase_bits)
            noisy_hist = phase_histogram(noisy_counts, phase_bits)
            ideal_est = weighted_median_from_histogram(estimates, ideal_hist)
            noisy_est = weighted_median_from_histogram(estimates, noisy_hist)
            runs.append(
                {
                    "seed": int(seed),
                    "ideal_median": ideal_est,
                    "noisy_median": noisy_est,
                    "ideal_abs_error": abs(ideal_est - amplitude),
                    "noisy_abs_error": abs(noisy_est - amplitude),
                    "ideal_inside_bar": abs(ideal_est - amplitude) <= bound + 1e-12,
                    "noisy_inside_bar": abs(noisy_est - amplitude) <= bound + 1e-12,
                    "ideal_tv_to_exact": float(0.5 * np.abs(ideal_hist - exact).sum()),
                    "noisy_counts": noisy_counts,
                }
            )
        noisy_inside = sum(item["noisy_inside_bar"] for item in runs) / len(runs)
        out["by_phase_bits"][str(phase_bits)] = {
            "phase_bins": bins,
            "brassard_bound": bound,
            "exact_success_probability": estimation.success_probability(estimates, exact, amplitude, bins),
            "noisy_fraction_inside_bar": noisy_inside,
            "ideal_median_abs_error": _median([item["ideal_abs_error"] for item in runs]),
            "noisy_median_abs_error": _median([item["noisy_abs_error"] for item in runs]),
            "ideal_median_tv": _median([item["ideal_tv_to_exact"] for item in runs]),
            "runs": runs,
        }
    return out


def call_bundle(compiled, ideal, noisy) -> dict:
    _, masses, positive, discount = problems.uniform_spot_grid(16)
    _state, amplitude, payoff_max = problems.encode_nonnegative(masses, positive)
    scale = discount * payoff_max
    discrete = scale * amplitude
    closed = problems.black_scholes_call()
    runs = []
    for seed in CALL_SEEDS:
        ideal_counts = run_counts(compiled, ideal, SHOTS, seed)
        noisy_counts = run_counts(compiled, noisy, SHOTS, seed)
        ideal_price = scale * good_fraction(ideal_counts)
        noisy_price = scale * good_fraction(noisy_counts)
        runs.append(
            {
                "seed": int(seed),
                "ideal_price": ideal_price,
                "noisy_price": noisy_price,
                "ideal_abs_error_vs_bs": abs(ideal_price - closed),
                "noisy_abs_error_vs_bs": abs(noisy_price - closed),
                "ideal_abs_error_vs_grid": abs(ideal_price - discrete),
                "noisy_abs_error_vs_grid": abs(noisy_price - discrete),
                "noisy_counts": noisy_counts,
            }
        )
    return {
        "black_scholes": closed,
        "discrete_grid_price": discrete,
        "marked_probability": amplitude,
        "scale": scale,
        "shots": SHOTS,
        "ideal_median_abs_error_vs_grid": _median([item["ideal_abs_error_vs_grid"] for item in runs]),
        "noisy_median_abs_error_vs_grid": _median([item["noisy_abs_error_vs_grid"] for item in runs]),
        "noisy_median_abs_error_vs_bs": _median([item["noisy_abs_error_vs_bs"] for item in runs]),
        "runs": runs,
    }


def build_payload() -> dict:
    snapshot = FakeKingston()
    noisy = AerSimulator.from_backend(snapshot)
    ideal = AerSimulator()
    facts = {}

    amplification_circuits = {}
    for repetitions in AMPLIFICATION_REPETITIONS:
        compiled = compile_circuit(circuits.amplification_circuit(THETA, repetitions), noisy)
        amplification_circuits[repetitions] = compiled
        facts[f"amplification_m{repetitions}"] = circuit_facts(compiled)
    print("running amplification sequences", flush=True)
    amplification = amplification_bundle(amplification_circuits, ideal, noisy)

    canonical_circuits = {}
    for phase_bits in PHASE_BITS:
        compiled = compile_circuit(circuits.canonical_ae_circuit(THETA, phase_bits), noisy)
        canonical_circuits[phase_bits] = compiled
        facts[f"canonical_m{phase_bits}"] = circuit_facts(compiled)
    print("running canonical phase estimation", flush=True)
    canonical = canonical_bundle(canonical_circuits, ideal, noisy)

    _, masses, positive, _discount = problems.uniform_spot_grid(16)
    state, _, _ = problems.encode_nonnegative(masses, positive)
    print("running call-loader circuit", flush=True)
    call_compiled = compile_circuit(circuits.call_loader_circuit(state), noisy)
    facts["call_loader"] = circuit_facts(call_compiled)
    call = call_bundle(call_compiled, ideal, noisy)

    return {
        "backend": "FakeKingston",
        "simulator": "qiskit_aer AerSimulator.from_backend",
        "mitigation": "none",
        "optimization_level": 1,
        "theta": THETA,
        "calibration": calibration(snapshot),
        "circuits": facts,
        "amplification": amplification,
        "canonical": canonical,
        "call_loader": call,
    }


def main() -> None:
    payload = build_payload()
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    calibration_block = payload["calibration"]
    print(f"wrote {DATA_PATH}")
    print(f"snapshot date {calibration_block['last_update_date']} qubits {calibration_block['num_qubits']}")
    print(
        "median gate error sx {sx:.3e} cz {cz:.3e} readout {ro:.3e}".format(
            sx=calibration_block["sx"]["median"],
            cz=calibration_block["cz"]["median"],
            ro=calibration_block["readout"]["median"],
        )
    )
    amp = payload["amplification"]
    print(
        "amplification median |error|  ideal κ=0 {ideal:.4e}  noisy κ=0 {noisy:.4e}  "
        "Tanaka (a,κ) {tanaka:.4e}  classical m=0 {classical:.4e}  fitted κ {kappa:.4f}".format(
            ideal=amp["ideal_kappa0_median_abs_error"],
            noisy=amp["noisy_kappa0_median_abs_error"],
            tanaka=amp["noisy_tanaka_median_abs_error"],
            classical=amp["noisy_classical_m0_median_abs_error"],
            kappa=amp["tanaka_kappa_median"],
        )
    )
    for bits, block in payload["canonical"]["by_phase_bits"].items():
        print(
            f"canonical m={bits} bound {block['brassard_bound']:.4e}  "
            f"ideal median |err| {block['ideal_median_abs_error']:.4e}  "
            f"noisy median |err| {block['noisy_median_abs_error']:.4e}  "
            f"noisy fraction inside bar {block['noisy_fraction_inside_bar']:.2f}  "
            f"ideal TV {block['ideal_median_tv']:.4e}"
        )
    call = payload["call_loader"]
    print(
        "call loader median |error| vs grid  ideal {ideal:.4e}  noisy {noisy:.4e}  "
        "noisy vs Black-Scholes {bs:.4e}".format(
            ideal=call["ideal_median_abs_error_vs_grid"],
            noisy=call["noisy_median_abs_error_vs_grid"],
            bs=call["noisy_median_abs_error_vs_bs"],
        )
    )
    for name, info in payload["circuits"].items():
        cz = info["operations"].get("cz", 0)
        print(f"  {name}: depth {info['depth']}  cz {cz}  qubits {info['physical_qubits']}")


if __name__ == "__main__":
    main()
