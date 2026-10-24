"""Audit of the amplitude-estimation bound and of the two closed forms.

The probability floor is 8/π². A row passes when the exact success probability
is at least that floor and the median of the outcome distribution lies inside
the Brassard bar. One measured shot is allowed to fall outside the bar.
"""

from __future__ import annotations

import unittest

import numpy as np
from scipy import integrate, stats

import estimation
import problems


class GroverTests(unittest.TestCase):
    def test_state_reflection_matches_ry_unitary(self) -> None:
        for theta in (0.2, 0.7, 1.1, np.pi / 5):
            preparation = estimation.ry_preparation(theta)
            from_unitary = estimation.grover_from_unitary(preparation)
            from_state = estimation.grover_from_state(preparation[:, 0])
            self.assertTrue(np.allclose(from_unitary, from_state, atol=1e-10))
            phases = np.angle(np.linalg.eigvals(from_state))
            self.assertTrue(np.allclose(sorted(np.abs(phases)), [2 * theta, 2 * theta], atol=1e-8))

    def test_marked_probability_of_ry(self) -> None:
        theta = 0.4
        state = estimation.ry_preparation(theta)[:, 0]
        self.assertAlmostEqual(estimation.marked_probability(state), np.sin(theta) ** 2, places=12)


class BoundTests(unittest.TestCase):
    def test_probability_floor_and_median_on_a_grid(self) -> None:
        floor = estimation.SUCCESS_PROBABILITY
        worst = 1.0
        for phase_bits in range(1, 8):
            for theta in np.linspace(0.03, np.pi / 2 - 0.03, 25):
                state = estimation.ry_preparation(float(theta))[:, 0]
                result = estimation.estimate(state, phase_bits, seed=0)
                worst = min(worst, result.success_probability)
                self.assertGreaterEqual(result.success_probability, floor - 1e-9)
                self.assertTrue(result.median_inside)
                self.assertAlmostEqual(result.amplitude, np.sin(theta) ** 2, places=12)
        self.assertGreaterEqual(worst, floor - 1e-9)

    def test_powers_match_a_second_implementation(self) -> None:
        theta = np.pi / 6
        preparation = estimation.ry_preparation(theta)
        operator = estimation.grover_from_unitary(preparation)
        state = preparation[:, 0]
        bins = 16
        evolved = estimation._powers(operator, state, bins)
        vector = state.astype(np.complex128).copy()
        for power in range(bins):
            self.assertTrue(np.allclose(evolved[power], vector, atol=1e-10))
            vector = operator @ vector


class ClosedFormTests(unittest.TestCase):
    def test_black_scholes_matches_gaussian_integral(self) -> None:
        def integrand(shock: float) -> float:
            return float(problems.call_payoff_of_normal(np.array([shock]))[0] * stats.norm.pdf(shock))

        integral, _ = integrate.quad(integrand, -20.0, 20.0, epsabs=1e-13)
        self.assertAlmostEqual(problems.black_scholes_call(), integral, delta=1e-9)

    def test_gaussian_cvar_matches_tail_integral(self) -> None:
        value_at_risk, cvar = problems.gaussian_var_cvar()

        def integrand(loss: float) -> float:
            return loss * stats.norm.pdf(loss)

        integral, _ = integrate.quad(integrand, value_at_risk, 30.0, epsabs=1e-13)
        self.assertAlmostEqual(cvar, integral / (1.0 - problems.CVAR_ALPHA), places=12)

    def test_gauss_hermite_integrates_fourth_moment(self) -> None:
        for n_nodes in (4, 8):
            self.assertAlmostEqual(
                problems.gaussian_expectation(n_nodes, lambda shock: shock**4),
                3.0,
                places=10,
            )


class CallComparisonTests(unittest.TestCase):
    def test_recorded_relationship_between_grid_and_hermite(self) -> None:
        closed = problems.black_scholes_call()
        hermite, _, _ = problems.gauss_hermite_call(16)
        grid = problems.grid_call_price(16)
        # Measured for this contract. Gauss–Hermite is exact for polynomials in
        # the Gaussian shock; the call payoff is only continuous, and at 16
        # nodes the uniform spot grid is closer to the closed form.
        self.assertGreater(abs(hermite - closed), abs(grid - closed))

    def test_fine_grid_sits_on_the_window_floor(self) -> None:
        closed = problems.black_scholes_call()
        _, renormalized = problems.windowed_call_integral(4.0)
        fine = problems.grid_call_price(256)
        self.assertLess(abs(fine - renormalized), 5e-4)
        self.assertGreater(abs(renormalized - closed), 2e-3)

    def test_hermite_error_decreases(self) -> None:
        closed = problems.black_scholes_call()
        errors = [
            abs(problems.gaussian_expectation(n, problems.call_payoff_of_normal) - closed)
            for n in (16, 32, 96)
        ]
        self.assertGreater(errors[0], errors[1])
        self.assertGreater(errors[1], errors[2])

    def test_amplitude_estimation_tracks_the_grid_not_the_closed_form(self) -> None:
        _, masses, positive, discount = problems.uniform_spot_grid(16)
        state, amplitude, payoff_max = problems.encode_nonnegative(masses, positive)
        scale = discount * payoff_max
        discrete_price = scale * amplitude
        closed = problems.black_scholes_call()
        self.assertGreater(abs(discrete_price - closed), 1e-3)
        for phase_bits in (4, 6, 8, 10):
            result = estimation.estimate(state, phase_bits, seed=0)
            self.assertAlmostEqual(result.amplitude, amplitude, places=12)
            self.assertGreaterEqual(result.success_probability, estimation.SUCCESS_PROBABILITY - 1e-9)
            self.assertTrue(result.median_inside)
            median_price = scale * result.median
            self.assertLessEqual(abs(median_price - discrete_price), scale * result.bound + 1e-9)


class CvarTests(unittest.TestCase):
    def test_legacy_value_is_the_histogram_mean_and_misses_the_closed_form(self) -> None:
        _, closed = problems.gaussian_var_cvar()
        legacy = problems.legacy_cvar(problems.normal_losses(), problems.CVAR_ALPHA, n_qubits=5)
        tail = legacy.masses[legacy.tail_index :]
        centers = legacy.centers[legacy.tail_index :]
        conditional = float(np.sum(tail * centers) / tail.sum())
        self.assertAlmostEqual(legacy.returned_cvar, conditional, places=12)
        self.assertGreater(abs(legacy.returned_cvar - closed), 0.05)
        # Rebuilding the histogram does not consult a phase-bit count.
        again = problems.legacy_cvar(problems.normal_losses(), problems.CVAR_ALPHA, n_qubits=5)
        self.assertEqual(legacy.returned_cvar, again.returned_cvar)

    def test_excess_amplitude_obeys_the_bound_and_scales(self) -> None:
        legacy = problems.legacy_cvar(problems.normal_losses(), problems.CVAR_ALPHA, n_qubits=5)
        excess = np.maximum(legacy.centers - legacy.value_at_risk, 0.0)
        state, amplitude, excess_max = problems.encode_nonnegative(legacy.masses, excess)
        factor = excess_max / (1.0 - problems.CVAR_ALPHA)
        self.assertGreater(factor, 10.0)
        previous_bar = None
        for phase_bits in (4, 6, 8, 10):
            result = estimation.estimate(state, phase_bits, seed=0)
            self.assertAlmostEqual(result.amplitude, amplitude, places=12)
            self.assertGreaterEqual(result.success_probability, estimation.SUCCESS_PROBABILITY - 1e-9)
            self.assertTrue(result.median_inside)
            if previous_bar is not None:
                self.assertLess(result.bound, previous_bar)
            previous_bar = result.bound
        coarse = estimation.estimate(state, phase_bits=4, seed=0)
        self.assertGreaterEqual(coarse.success_probability, estimation.SUCCESS_PROBABILITY - 1e-9)
        self.assertFalse(abs(coarse.shot - coarse.amplitude) <= coarse.bound + 1e-12)
        # The legacy number is invariant under the query count that moves the bar.
        self.assertEqual(
            problems.legacy_cvar(problems.normal_losses(), n_qubits=5).returned_cvar,
            legacy.returned_cvar,
        )


if __name__ == "__main__":
    unittest.main()
