"""Maximum-likelihood amplitude estimation under Tanaka's depolarizing model.

The ideal probability after m applications of Q is sin^2((2m+1) θ), with
sin^2 θ = a. Tanaka, Suzuki, Uno, Raymond, Onodera and Yamamoto
(Quantum Information Processing, 2021; arXiv:2006.16223) replace that with

    P(m; a, κ) = 1/2 - (1/2) exp(-κ m) cos(2 (2m+1) θ).

κ = 0 is the noiseless model. κ > 0 is a nuisance parameter, not a measurement.
"""

from __future__ import annotations

import numpy as np


def ideal_probability(repetitions: int, amplitude: float) -> float:
    theta = np.arcsin(np.sqrt(amplitude))
    return float(np.sin((2 * repetitions + 1) * theta) ** 2)


def tanaka_probability(repetitions: int, amplitude: float, kappa: float) -> float:
    if kappa < 0.0:
        raise ValueError("kappa must be nonnegative")
    theta = np.arcsin(np.sqrt(float(amplitude)))
    probability = 0.5 - 0.5 * np.exp(-kappa * repetitions) * np.cos(2.0 * (2 * repetitions + 1) * theta)
    return float(np.clip(probability, 0.0, 1.0))


def log_likelihood(records: list[tuple[int, int, int]], amplitude: float, kappa: float) -> float:
    """records are (repetitions, good_shots, total_shots)."""
    total = 0.0
    for repetitions, good, shots in records:
        if shots <= 0 or not 0 <= good <= shots:
            raise ValueError("invalid shot record")
        probability = tanaka_probability(repetitions, amplitude, kappa)
        probability = min(1.0 - 1e-15, max(1e-15, probability))
        total += good * np.log(probability) + (shots - good) * np.log(1.0 - probability)
    return float(total)


def maximum_likelihood(
    records: list[tuple[int, int, int]],
    *,
    kappa_fixed: float | None = 0.0,
    amplitude_grid: int = 2001,
    kappa_grid: int = 161,
    kappa_max: float = 1.6,
) -> dict[str, float]:
    """Grid maximizer. kappa_fixed=0 is the noiseless model. None fits κ as well."""
    amplitudes = np.linspace(1e-4, 1.0 - 1e-4, amplitude_grid)
    if kappa_fixed is None:
        kappas = np.linspace(0.0, kappa_max, kappa_grid)
    else:
        kappas = np.array([float(kappa_fixed)])
    best = (-np.inf, float(amplitudes[0]), float(kappas[0]))
    for amplitude in amplitudes:
        for kappa in kappas:
            score = log_likelihood(records, float(amplitude), float(kappa))
            if score > best[0]:
                best = (score, float(amplitude), float(kappa))
    return {"log_likelihood": best[0], "amplitude": best[1], "kappa": best[2]}
