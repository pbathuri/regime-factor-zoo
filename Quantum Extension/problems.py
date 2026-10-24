"""Two expectations with closed forms, and the loaders used by the existing code.

The call loader follows cirq_engine.price: uniform nodes in the spot on a
±4-standard-deviation log-window, with node masses proportional to the
lognormal density. The constant bin width cancels when the masses are
normalized. Source:
Desktop/My_Track/Course_progress_IUB/Research_Cache-Primary/HPC_Research/jk/src/qhpc_cache/quantum_engines/cirq_engine.py

The legacy CVaR number follows quantum_cvar: a sample quantile, a histogram,
then the conditional mean of the upper bins. The amplitude-estimation result
is not an input. Source:
Desktop/Work/qlpc-paper-qnlpai-2026/qlpc/quantum_risk.py
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    from scipy import integrate, special, stats
except ImportError as exc:
    raise ImportError(
        "SciPy did not import. On this machine run /opt/miniconda3/bin/python3."
    ) from exc

# Same contract as the self-test in cirq_engine.py.
CALL_SPOT = 100.0
CALL_STRIKE = 105.0
CALL_RATE = 0.05
CALL_VOL = 0.2
CALL_EXPIRY = 1.0

CVAR_MEAN = 0.0
CVAR_SIGMA = 1.0
CVAR_ALPHA = 0.95


def black_scholes_call(
    spot: float = CALL_SPOT,
    strike: float = CALL_STRIKE,
    rate: float = CALL_RATE,
    volatility: float = CALL_VOL,
    expiry: float = CALL_EXPIRY,
) -> float:
    width = volatility * np.sqrt(expiry)
    d1 = (np.log(spot / strike) + (rate + 0.5 * volatility**2) * expiry) / width
    d2 = d1 - width
    return float(spot * stats.norm.cdf(d1) - strike * np.exp(-rate * expiry) * stats.norm.cdf(d2))


def call_payoff_of_normal(
    shock: np.ndarray,
    spot: float = CALL_SPOT,
    strike: float = CALL_STRIKE,
    rate: float = CALL_RATE,
    volatility: float = CALL_VOL,
    expiry: float = CALL_EXPIRY,
) -> np.ndarray:
    width = volatility * np.sqrt(expiry)
    terminal = spot * np.exp((rate - 0.5 * volatility**2) * expiry + width * shock)
    return np.exp(-rate * expiry) * np.maximum(terminal - strike, 0.0)


def gaussian_expectation(n_nodes: int, function) -> float:
    """Gauss–Hermite rule for E[function(Z)], Z standard normal."""
    nodes, weights = special.roots_hermite(n_nodes)
    shock = np.sqrt(2.0) * nodes
    probability = weights / np.sqrt(np.pi)
    return float(np.sum(probability * function(shock)))


def gauss_hermite_call(n_nodes: int) -> tuple[float, np.ndarray, np.ndarray]:
    """Return (price, probability masses, undiscounted positive part at the nodes).

    The price is the discounted expectation. Masses sum to 1 and are the
    Gauss–Hermite weights in the standard-normal coordinate.
    """
    nodes, weights = special.roots_hermite(n_nodes)
    shock = np.sqrt(2.0) * nodes
    probability = np.asarray(weights / np.sqrt(np.pi), dtype=float)
    width = CALL_VOL * np.sqrt(CALL_EXPIRY)
    terminal = CALL_SPOT * np.exp((CALL_RATE - 0.5 * CALL_VOL**2) * CALL_EXPIRY + width * shock)
    positive = np.maximum(terminal - CALL_STRIKE, 0.0)
    price = float(np.exp(-CALL_RATE * CALL_EXPIRY) * np.sum(probability * positive))
    return price, probability, positive


def windowed_call_integral(half_width: float = 4.0) -> tuple[float, float]:
    """Integrate the call density on [-half_width, half_width].

    Returns the un-normalized integral and the same integral divided by the
    window mass. The second one is the limit of the cirq loader as the number
    of nodes grows: tails are dropped and the window is rescaled to mass 1.
    """

    def integrand(shock: float) -> float:
        return float(call_payoff_of_normal(np.array([shock]))[0] * stats.norm.pdf(shock))

    truncated, _ = integrate.quad(integrand, -half_width, half_width, epsabs=1e-13)
    mass = float(stats.norm.cdf(half_width) - stats.norm.cdf(-half_width))
    return float(truncated), float(truncated / mass)


def uniform_spot_grid(n_nodes: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """cirq_engine loader. Returns spots, masses, undiscounted payoffs, discount."""
    if n_nodes < 2:
        raise ValueError("n_nodes must be at least 2")
    width = CALL_VOL * np.sqrt(CALL_EXPIRY)
    log_mean = np.log(CALL_SPOT) + (CALL_RATE - 0.5 * CALL_VOL**2) * CALL_EXPIRY
    low = CALL_SPOT * np.exp((CALL_RATE - 0.5 * CALL_VOL**2) * CALL_EXPIRY - 4.0 * width)
    high = CALL_SPOT * np.exp((CALL_RATE - 0.5 * CALL_VOL**2) * CALL_EXPIRY + 4.0 * width)
    spots = np.linspace(low, high, n_nodes)
    log_spot = np.log(np.maximum(spots, 1e-12))
    density = np.exp(-0.5 * ((log_spot - log_mean) / width) ** 2) / (
        spots * width * np.sqrt(2.0 * np.pi)
    )
    density = np.maximum(density, 0.0)
    total = float(density.sum())
    if total <= 0.0:
        raise RuntimeError("uniform-grid density vanished")
    masses = density / total
    positive = np.maximum(spots - CALL_STRIKE, 0.0)
    return spots, masses, positive, float(np.exp(-CALL_RATE * CALL_EXPIRY))


def grid_call_price(n_nodes: int) -> float:
    _, masses, positive, discount = uniform_spot_grid(n_nodes)
    return float(discount * np.sum(masses * positive))


def monte_carlo_call(n_paths: int, seed: int) -> tuple[float, float]:
    generator = np.random.default_rng(seed)
    samples = call_payoff_of_normal(generator.standard_normal(n_paths))
    mean = float(samples.mean())
    stderr = float(samples.std(ddof=1) / np.sqrt(n_paths))
    return mean, stderr


def gaussian_var_cvar(mean: float = CVAR_MEAN, sigma: float = CVAR_SIGMA, alpha: float = CVAR_ALPHA) -> tuple[float, float]:
    """Closed forms for a normal loss. CVaR is the upper-tail conditional mean."""
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie in (0, 1)")
    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    threshold = float(stats.norm.ppf(alpha))
    value_at_risk = mean + sigma * threshold
    cvar = mean + sigma * float(stats.norm.pdf(threshold)) / (1.0 - alpha)
    return value_at_risk, cvar


@dataclass(frozen=True)
class LegacyCvar:
    """What quantum_cvar returns, with the histogram it actually averages."""

    value_at_risk: float
    sample_cvar: float
    returned_cvar: float
    masses: np.ndarray
    centers: np.ndarray
    tail_index: int

    @property
    def tail_probability(self) -> float:
        return float(self.masses[self.tail_index :].sum())


def legacy_cvar(losses: np.ndarray, alpha: float = CVAR_ALPHA, n_qubits: int = 5) -> LegacyCvar:
    """Histogram conditional mean used as the returned CVaR in quantum_cvar.

    The threshold index matches the integer comparator in that function:
    bin width in the comparator is (hi - lo) / (2^n - 1), not the histogram width.
    """
    samples = np.asarray(losses, dtype=float).reshape(-1)
    if samples.size == 0:
        raise ValueError("losses are empty")
    bins = 1 << n_qubits
    value_at_risk = float(np.quantile(samples, alpha))
    tail = samples[samples >= value_at_risk]
    sample_cvar = float(tail.mean()) if tail.size else value_at_risk
    low = float(samples.min())
    high = float(samples.max())
    if high <= low:
        high = low + 1e-6
    edges = np.linspace(low, high, bins + 1)
    counts, _ = np.histogram(samples, bins=edges)
    total = int(counts.sum())
    if total == 0:
        raise RuntimeError("histogram is empty")
    masses = counts / total
    centers = 0.5 * (edges[:-1] + edges[1:])
    comparator_width = (high - low) / (bins - 1)
    tail_index = int(np.clip(round((value_at_risk - low) / comparator_width), 1, bins - 1))
    tail_mass = float(masses[tail_index:].sum())
    if tail_mass <= 0.0:
        returned = value_at_risk
    else:
        returned = float(np.sum(masses[tail_index:] * centers[tail_index:]) / tail_mass)
    return LegacyCvar(
        value_at_risk=value_at_risk,
        sample_cvar=sample_cvar,
        returned_cvar=returned,
        masses=masses,
        centers=centers,
        tail_index=tail_index,
    )


def normal_losses(n_samples: int = 20000, seed: int = 11) -> np.ndarray:
    """Univariate normal losses. risk.py draws correlated Gaussians; a portfolio of those is univariate normal, and this is the case with a closed form."""
    return np.random.default_rng(seed).normal(CVAR_MEAN, CVAR_SIGMA, n_samples)


def expectation_state(masses: np.ndarray, fraction: np.ndarray) -> np.ndarray:
    """|ψ⟩ = Σ √p_i |i⟩ (√(1-f_i)|0⟩ + √f_i|1⟩), objective bit least significant.

    The marked probability equals Σ p_i f_i.
    """
    probability = np.asarray(masses, dtype=float).reshape(-1)
    values = np.asarray(fraction, dtype=float).reshape(-1)
    if probability.shape != values.shape:
        raise ValueError("masses and fraction have different shapes")
    if np.any(probability < -1e-12):
        raise ValueError("a mass is negative")
    total = float(probability.sum())
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"masses sum to {total}")
    if np.any(values < -1e-12) or np.any(values > 1.0 + 1e-12):
        raise ValueError("fraction leaves [0, 1]")
    probability = probability / total
    values = np.clip(values, 0.0, 1.0)
    state = np.empty(2 * probability.size, dtype=np.complex128)
    state[0::2] = np.sqrt(probability * (1.0 - values))
    state[1::2] = np.sqrt(probability * values)
    return state


def encode_nonnegative(masses: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Encode values / max(values) into the objective bit.

    Returns the state, the marked probability a = E[values] / max(values),
    and that maximum. The expectation is a * maximum.
    """
    level = np.asarray(values, dtype=float).reshape(-1)
    maximum = float(level.max())
    if maximum <= 0.0:
        raise ValueError("values are identically zero")
    fraction = level / maximum
    state = expectation_state(masses, fraction)
    amplitude = float(np.sum(np.asarray(masses, dtype=float) * fraction))
    return state, amplitude, maximum
