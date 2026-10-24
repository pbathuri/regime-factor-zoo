# Checking an amplitude-estimation bound on two expectations

The contract is the European call used in `cirq_engine.py` (`S0 = 100`, `K = 105`, `r = 0.05`, `σ = 0.2`, `T = 1`). Its Black–Scholes price is `8.0213522351`. A direct Gaussian integral of the same payoff agrees with that value to `6 × 10⁻¹⁰`.

For a standard normal loss and level `α = 0.95`, the closed forms are

```
VaR  = Φ⁻¹(α) = 1.6448536270
CVaR = φ(Φ⁻¹(α)) / (1 − α) = 2.0627128075
```

A tail integral of `x φ(x)` reproduces the CVaR value to `10⁻¹⁵`.

Canonical amplitude estimation is the algorithm of Brassard, Høyer, Mosca and Tapp. The Grover operator is the product of two reflections,

```
Q = −(I − 2|ψ⟩⟨ψ|) S_χ,
```

with `S_χ` the sign flip on the marked basis states. Phase estimation with `M = 2^m` bins returns the estimate `sin²(π k / M)`. The inequality checked below, in the form stated by Montanaro (Proc. R. Soc. A, 2015, Theorem 2), is

```
|ã − a| ≤ 2π √(a(1−a)) / t + π² / t²,    t = M,
```

with probability at least `8/π² ≈ 0.810569`. Here `t` is the number of phase bins. The controlled powers apply `Q` a total of `M − 1` times. Every median below is the median of that exact outcome distribution, computed from the statevector. A single shot is a draw from the same distribution and is not required to land inside the bar. On a grid of 25 amplitudes and `m = 1,…,7`, the smallest success probability was still above `8/π²`, and every median was inside the bar.

The marked probability is `a = E[f]`, where `0 ≤ f ≤ 1` is the integrand divided by a fixed upper bound. The bound controls `a`. Multiplying by that upper bound, and in the CVaR case also by `1/(1−α)`, turns a small error in `a` into a larger error in the reported expectation.

## The call

The existing loader places `2^n` nodes uniformly in the spot on the window `±4` standard deviations of `log S_T`, and assigns masses proportional to the lognormal density. As the node count grows, that rule converges to the call integral restricted to the window and then rescaled to mass 1, not to the Black–Scholes value. The rescaled window integral is `8.0177885991`, which is `0.00356` below the closed form. At 256 nodes the loader returns `8.0178887418` and sits on that floor. Further qubits inside the same window do not remove it.

Gauss–Hermite quadrature integrates against the Gaussian weight on the whole line and is exact for polynomials in the shock through degree `2n−1`. The call payoff is only continuous. At 16 nodes its price is `8.1919279328` (error `+0.171`). At 96 nodes the error is `−0.00130`. At equal node count, the 16-node spot grid is closer to the closed form (price `8.0085199051`, error `−0.0128`) than 16-node Gauss–Hermite. That is a fact about this kinked payoff, not a ranking of the two rules in general.

Amplitude estimation is applied to the 16-node spot grid. It estimates that discrete expectation. The encoding uses `payoff_max = 124.331874`, so `a = 0.06771494` and the price scale is `118.268`.

| t | median price | error vs grid | error vs Black–Scholes | price bar | P(inside) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 16 | 4.50131 | −3.507 | −3.520 | 16.23 | 0.921 |
| 64 | 6.98248 | −1.026 | −1.039 | 3.20 | 0.843 |
| 256 | 7.68228 | −0.326 | −0.339 | 0.747 | 0.815 |
| 1024 | 8.04384 | +0.0353 | +0.0225 | 0.183 | 0.934 |

At `t = 16` the bar is 16 dollars on an 8 dollar option, so the inequality holds and does not constrain the price. At `t = 1024` the median is 3.5 cents from the grid value and 2 cents from Black–Scholes, inside a bar of 18 cents. The distance to Black–Scholes still contains the grid’s own `−1.3` cent bias. Four thousand ninety-six shots of the same state, seed 42, give price `7.85374`. The binomial standard error of that shot estimator is `0.464`. Four thousand ninety-six ordinary Monte Carlo paths, seed 7, give `7.78626` with standard error `0.204`.

## The conditional value at risk

`quantum_cvar` builds a histogram, runs a comparator, and returns the conditional mean of the upper bin centers. That mean does not use the amplitude-estimation output. On 20,000 standard normal draws, seed 11, with 32 bins, the sample CVaR is `2.0606125246`. The returned histogram mean is `1.9303992869`, which is `0.132` below the closed form, and it is the same number at every `t`.

The comparator step `(hi − lo) / (2^n − 1)` is not the histogram bin width `(hi − lo) / 2^n`. On this sample the flagged tail starts at a bin center `1.5946`, below the sample VaR `1.6358`, and contains mass `0.06835` rather than `0.05`. The conditional mean of that larger set is pulled down.

The same atoms do carry the excess. With `f = (center − sample VaR)_+ / max`, the exact discrete expectation assembles to

```
sample VaR + E[(center − sample VaR)_+] / (1 − α) = 2.0603234871.
```

The propagation factor is `max / (1 − α) = 41.5955`. Amplitude estimation of this `f` (`a = 0.01020645`) gives:

| t | median CVaR | error vs discrete assembly | error vs closed form | propagated bar | one shot inside the bar |
| ---: | ---: | ---: | ---: | ---: | --- |
| 16 | 3.21892 | +1.159 | +1.156 | 3.245 | no |
| 64 | 2.03540 | −0.0249 | −0.0273 | 0.511 | yes |
| 256 | 2.03540 | −0.0249 | −0.0273 | 0.109 | yes |
| 1024 | 2.06068 | +0.00036 | −0.00203 | 0.0260 | yes |

The `t = 16` shot misses the bar. The success probability on that row is `0.8589`, which is still above `8/π²`. At `t = 1024` the remaining `0.002` gap to the closed form is the gap already present in the discrete assembly (`2.06032` against `2.06271`). The median adds `0.00036` to that.

The comparator circuit in the existing code estimates a tail probability, not this excess. On the same histogram that probability is `a = 0.06835`. At `t = 64` its median estimate is inside its own bar (`|error| = 0.00931`, bar `0.0272`, success probability `0.833`).

## What this does not say

The tables above are statevector calculations of the measurement distribution. They are not hardware runs, and the wall-clock time of the statevector is not a speedup. The following section is a separate, noisy circuit execution. The query bound is quadratic in `1/ε`, not exponential. No claim is made that pricing this call, or computing this Gaussian CVaR, is a new algorithm. Both expectations are classical textbook calculations; the quantum routine is being checked against them.

The Evans function is a different certificate. For a viscous shock it is an analytic function of the spectral parameter, and spectral stability is a winding number, made rigorous when the numerical error is small enough for Rouché’s theorem. Amplitude estimation certifies a different integral, with the bound above. A matrix eigenvalue count, quantum phase estimation included, answers a different question when the linearized operator has no spectral gap. This note does not compute an Evans function.

## Device noise

`MEASUREMENTS.md` records the same circuits executed in Qiskit Aer with the `ibm_kingston` calibration snapshot of 2026-04-15. No error mitigation. The one-qubit Grover sequence has no two-qubit gates, and its frequencies track `sin²((2m+1)θ)` out to eight applications, with a floor of about `0.012` where the ideal probability is nearly zero. Phase estimation at `t = 4` and `t = 8` returns the bin value `1/2` on every ideal and noisy seed; the Brassard bar at those sizes is wider than the gap from `1/2` to `sin²(0.7)`, so landing inside the bar is not evidence. The 16-node call loader, 62 `cz` gates deep, measures a marked frequency of about `0.107` instead of `0.0677`. The five noisy prices lie between `12.50` and `12.89`, against the grid price `8.009` and the Black–Scholes price `8.021`.

There is no saved IBM Quantum account on this machine, and Big Red 200 refused a non-interactive login, so these are not live-device shots.

## Reproduce

```
/opt/miniconda3/bin/python3 test_audit.py
/opt/miniconda3/bin/python3 run.py
.venv/bin/python test_qiskit_audit.py
.venv/bin/python run_device.py
```

The system Python on this machine has a broken SciPy install. Both commands need NumPy and a working SciPy. The audit is `test_audit.py`: closed forms against integrals, the Grover eigenvalues `e^{±2iθ}`, the probability floor on the amplitude grid, the call and CVaR medians inside the bar, the legacy CVaR equal to the histogram conditional mean, and the `t = 16` CVaR shot outside the bar.
