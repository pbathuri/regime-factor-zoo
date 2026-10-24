"""The Qiskit circuits must reproduce the audited statevector algorithm when no noise is present."""

from __future__ import annotations

import unittest

import numpy as np
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime.fake_provider import FakeKingston

import circuits
import estimation
import likelihood
import run_device


def _probabilities(circuit) -> np.ndarray:
    stripped = circuit.remove_final_measurements(inplace=False)
    state = Statevector.from_instruction(stripped)
    return np.abs(np.asarray(state.data)) ** 2


class AmplificationTests(unittest.TestCase):
    def test_probabilities_match_the_ideal_formula(self) -> None:
        theta = 0.7
        amplitude = float(np.sin(theta) ** 2)
        for repetitions in (0, 1, 2, 4, 8):
            probabilities = _probabilities(circuits.amplification_circuit(theta, repetitions))
            self.assertAlmostEqual(probabilities[1], likelihood.ideal_probability(repetitions, amplitude), places=10)

    def test_tanaka_at_zero_kappa_is_the_ideal_formula(self) -> None:
        amplitude = 0.31
        for repetitions in range(6):
            self.assertAlmostEqual(
                likelihood.tanaka_probability(repetitions, amplitude, 0.0),
                likelihood.ideal_probability(repetitions, amplitude),
                places=12,
            )


class CanonicalTests(unittest.TestCase):
    def test_phase_distribution_matches_numpy(self) -> None:
        theta = 0.7
        phase_bits = 3
        circuit = circuits.canonical_ae_circuit(theta, phase_bits)
        probabilities = _probabilities(circuit)
        bins = 1 << phase_bits
        # System qubit is the highest index, so it is the most-significant bit.
        phase = probabilities.reshape(2, bins).sum(axis=0)
        preparation, _, _ = circuits.preparation_and_grover(theta)
        operator = estimation.grover_from_state(preparation[:, 0])
        estimates, exact = estimation.outcome_distribution(operator, preparation[:, 0], phase_bits)
        self.assertTrue(np.allclose(phase, exact, atol=1e-8))
        self.assertTrue(np.allclose(estimates, np.sin(np.pi * np.arange(bins) / bins) ** 2))

    def test_ideal_shots_use_the_same_bin_order(self) -> None:
        backend = AerSimulator.from_backend(FakeKingston())
        compiled = run_device.compile_circuit(circuits.canonical_ae_circuit(0.7, 3), backend)
        counts = run_device.run_counts(compiled, AerSimulator(), 8192, 0)
        histogram = run_device.phase_histogram(counts, 3)
        preparation, _, _ = circuits.preparation_and_grover(0.7)
        operator = estimation.grover_from_state(preparation[:, 0])
        _, exact = estimation.outcome_distribution(operator, preparation[:, 0], 3)
        total_variation = float(0.5 * np.abs(histogram - exact).sum())
        self.assertLess(total_variation, 0.05)


class LikelihoodTests(unittest.TestCase):
    def test_noiseless_grid_recovers_a_known_amplitude(self) -> None:
        amplitude = 0.31
        records = []
        for repetitions in (0, 1, 2, 4):
            probability = likelihood.ideal_probability(repetitions, amplitude)
            shots = 4000
            good = int(round(probability * shots))
            records.append((repetitions, good, shots))
        fit = likelihood.maximum_likelihood(records, kappa_fixed=0.0, amplitude_grid=4001)
        self.assertLess(abs(fit["amplitude"] - amplitude), 5e-3)
        self.assertEqual(fit["kappa"], 0.0)


if __name__ == "__main__":
    unittest.main()
