"""Canonical amplitude estimation.

Q is the product of two reflections,
    Q = -(I - 2|ψ⟩⟨ψ|) S_χ,
where S_χ flips the sign of the marked basis states (the least-significant bit).
On the plane spanned by the marked and unmarked parts of |ψ⟩, the eigenvalues
are e^{±2iθ} with marked probability a = sin²θ.

Phase estimation with M = 2^m bins returns a bin k and the estimate
sin²(π k / M). Brassard, Høyer, Mosca and Tapp, as quoted by Montanaro
(Proc. R. Soc. A, 2015, Theorem 2), give

    |ã - a| ≤ 2π √(a(1-a)) / t + π² / t²

with probability at least 8/π². In this implementation t = M, the number of
phase bins. The circuit's controlled powers apply Q a total of M - 1 times;
the inequality we enforce in the tests is the one with t = M, checked on a
grid of amplitudes rather than assumed from a page number.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SUCCESS_PROBABILITY = 8.0 / np.pi**2


def brassard_bound(amplitude: float, t: int) -> float:
    a = float(amplitude)
    if t < 1:
        raise ValueError("t must be positive")
    if a < -1e-12 or a > 1.0 + 1e-12:
        raise ValueError(f"amplitude {a} is outside [0, 1]")
    a = min(1.0, max(0.0, a))
    return float(2.0 * np.pi * np.sqrt(a * (1.0 - a)) / t + np.pi**2 / t**2)


def marked_probability(psi: np.ndarray) -> float:
    state = np.asarray(psi, dtype=np.complex128).reshape(-1)
    norm = np.linalg.norm(state)
    if norm <= 0.0:
        raise ValueError("state has zero norm")
    state = state / norm
    return float(np.sum(np.abs(state[1::2]) ** 2))


def grover_from_state(psi: np.ndarray) -> np.ndarray:
    """Q = -(I - 2|ψ⟩⟨ψ|) S_χ, with S_χ = diag(+1, -1, +1, -1, ...)."""
    state = np.asarray(psi, dtype=np.complex128).reshape(-1)
    norm = np.linalg.norm(state)
    if norm <= 0.0:
        raise ValueError("state has zero norm")
    state = state / norm
    dim = state.size
    reflection = np.eye(dim, dtype=np.complex128) - 2.0 * np.outer(state, state.conj())
    sign_chi = np.ones(dim, dtype=np.complex128)
    sign_chi[1::2] = -1.0
    return -(reflection @ np.diag(sign_chi))


def grover_from_unitary(preparation: np.ndarray) -> np.ndarray:
    """Q = -A S_0 A† S_χ. Equals grover_from_state(A|0⟩) when A is unitary."""
    matrix = np.asarray(preparation, dtype=np.complex128)
    dim = matrix.shape[0]
    if matrix.shape != (dim, dim):
        raise ValueError("preparation must be square")
    reflect_zero = np.eye(dim, dtype=np.complex128)
    reflect_zero[0, 0] = -1.0
    sign_chi = np.ones(dim, dtype=np.complex128)
    sign_chi[1::2] = -1.0
    return -(matrix @ reflect_zero @ matrix.conj().T @ np.diag(sign_chi))


def ry_preparation(theta: float) -> np.ndarray:
    """Ry(2θ), so Ry(2θ)|0⟩ = cosθ|0⟩ + sinθ|1⟩ and a = sin²θ."""
    cosine, sine = np.cos(theta), np.sin(theta)
    return np.array([[cosine, -sine], [sine, cosine]], dtype=np.complex128)


def _powers(operator: np.ndarray, state: np.ndarray, count: int) -> np.ndarray:
    """Rows are Q^0|ψ⟩, ..., Q^{count-1}|ψ⟩. Rejects a drift off the unit sphere."""
    evolved = np.empty((count, state.size), dtype=np.complex128)
    vector = np.asarray(state, dtype=np.complex128).copy()
    for power in range(count):
        norm = np.linalg.norm(vector)
        if not np.isfinite(norm) or abs(norm - 1.0) > 1e-8:
            raise RuntimeError(f"Q^{power} left the unit sphere (norm {norm})")
        evolved[power] = vector
        vector = operator @ vector
    return evolved


def outcome_distribution(operator: np.ndarray, psi: np.ndarray, phase_bits: int) -> tuple[np.ndarray, np.ndarray]:
    """Exact measurement law of canonical phase estimation on Q.

    Returns (estimates, probabilities) indexed by the phase bin k = 0..M-1.
    The estimate in bin k is sin²(π k / M).
    """
    if phase_bits < 1:
        raise ValueError("phase_bits must be at least 1")
    bins = 1 << phase_bits
    state = np.asarray(psi, dtype=np.complex128).reshape(-1)
    state = state / np.linalg.norm(state)
    evolved = _powers(operator, state, bins)
    index = np.arange(bins)
    phase = np.exp(-2j * np.pi * np.outer(index, index) / bins) / bins
    amplitudes = phase @ evolved
    probabilities = np.real(np.sum(np.abs(amplitudes) ** 2, axis=1))
    total = float(probabilities.sum())
    if not np.isfinite(total) or abs(total - 1.0) > 1e-8:
        raise RuntimeError(f"outcome probabilities sum to {total}")
    probabilities = probabilities / total
    estimates = np.sin(np.pi * index / bins) ** 2
    return estimates, probabilities


def weighted_median(values: np.ndarray, probabilities: np.ndarray) -> float:
    order = np.argsort(values)
    cumulative = np.cumsum(probabilities[order])
    position = int(np.searchsorted(cumulative, 0.5, side="left"))
    position = min(position, values.size - 1)
    return float(values[order][position])


def success_probability(estimates: np.ndarray, probabilities: np.ndarray, amplitude: float, t: int) -> float:
    width = brassard_bound(amplitude, t)
    inside = np.abs(estimates - amplitude) <= width + 1e-12
    return float(probabilities[inside].sum())


@dataclass(frozen=True)
class AmplitudeEstimation:
    estimates: np.ndarray
    probabilities: np.ndarray
    amplitude: float
    phase_bins: int
    median: float
    shot: float
    success_probability: float
    bound: float

    @property
    def median_error(self) -> float:
        return abs(self.median - self.amplitude)

    @property
    def median_inside(self) -> bool:
        return self.median_error <= self.bound + 1e-12


def estimate(psi: np.ndarray, phase_bits: int, seed: int = 0) -> AmplitudeEstimation:
    state = np.asarray(psi, dtype=np.complex128).reshape(-1)
    state = state / np.linalg.norm(state)
    amplitude = marked_probability(state)
    operator = grover_from_state(state)
    estimates, probabilities = outcome_distribution(operator, state, phase_bits)
    bins = 1 << phase_bits
    width = brassard_bound(amplitude, bins)
    generator = np.random.default_rng(seed)
    shot_bin = int(generator.choice(bins, p=probabilities))
    return AmplitudeEstimation(
        estimates=estimates,
        probabilities=probabilities,
        amplitude=amplitude,
        phase_bins=bins,
        median=weighted_median(estimates, probabilities),
        shot=float(estimates[shot_bin]),
        success_probability=success_probability(estimates, probabilities, amplitude, bins),
        bound=width,
    )
