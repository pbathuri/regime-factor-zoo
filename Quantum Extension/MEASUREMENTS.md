# Device-noise measurements

These runs use Qiskit 2.6.0 and Aer 0.18.0. The noise model is `FakeKingston` from Qiskit IBM Runtime 0.50.0, a local copy of the `ibm_kingston` calibration dated 2026-04-15 09:15:15+02:00 (156 qubits). Aer applies that coupling map and those gate errors. This is not a job submitted to the device. No IBM Quantum account is saved on this machine, and a non-interactive login to Big Red 200 was rejected (`Permission denied (keyboard-interactive)`). Nothing here was error-mitigated. `optimization_level=1`. Each application of the Grover operator `Q` is a separate gate, with a barrier before it, so the transpiler does not replace `Q^m` by one rotation.

The snapshot’s median errors are `2.36×10⁻⁴` for `sx`, `1.83×10⁻³` for `cz`, and `9.5×10⁻³` for readout. It also contains gates whose recorded error is 1. The layouts below did not use those gates. Raw counts are in `data/kingston_snapshot.json`.

The known amplitude in the first two experiments is `a = sin²(0.7) = 0.4150164285`. The call is the same 16-node loader as in `NOTE.md`: discrete price `8.0085199051`, Black–Scholes price `8.0213522351`, marked probability `0.0677149409`, price scale `118.268137`.

## One-qubit amplification

`A = Ry(2θ)` and then `m` applications of `Q`, with `m ∈ {0,1,2,4,8}`. After transpilation these circuits have no `cz` gates. Depth runs from 5 to 37. Twenty seeds, 8192 shots each.

| m | ideal sin²((2m+1)θ) | mean ideal frequency | mean noisy frequency |
| ---: | ---: | ---: | ---: |
| 0 | 0.4150 | 0.4142 | 0.4162 |
| 1 | 0.7451 | 0.7460 | 0.7413 |
| 2 | 0.1230 | 0.1230 | 0.1314 |
| 4 | 0.0003 | 0.0003 | 0.0123 |
| 8 | 0.3821 | 0.3821 | 0.3854 |

At `m = 4` the ideal probability is nearly zero and the noisy frequency sits at about `0.012`, the size of the readout error on the qubit that was used. The oscillation is otherwise intact. A maximum-likelihood fit with the noiseless model `κ = 0` has median absolute error `3.0×10⁻³` on the noisy shots and `5.7×10⁻⁷` on the ideal shots. The classical estimator that uses only `m = 0` has median absolute error `5.1×10⁻³` on the same noisy shots. The two-parameter fit of Tanaka, Suzuki, Uno, Raymond, Onodera, and Yamamoto (Quantum Information Processing, 2021) selects `κ = 0.01` on every seed. That is one step of the search grid, so the data support a small damping and do not resolve it further.

This circuit never leaves one qubit. It does not test the call loader.

## Canonical phase estimation

Phase estimation of the same `Q`, with the powers left unfused. `m = 2` uses 3 qubits, depth 64, 14 `cz` gates. `m = 3` uses 4 qubits, depth 151, 35 `cz` gates. Ten seeds, 8192 shots.

For this particular `a`, the likely phase bins all give the estimate `sin²(πk/M) = 1/2`. Ideal and noisy medians are `0.5` on every seed. The absolute error is `0.08498`. The Brassard bar is `1.391` at `m = 2` and `0.541` at `m = 3`, so every run sits inside a bar that is too wide to be informative. The ideal shot histogram matches the exact distribution (median total variation `0.004` and `0.007`). The noisy histogram moves by median total variation `0.021` at `m = 2` and `0.047` at `m = 3`. The median estimate does not register that movement, because the bins it lands on share one value.

## The call loader

State preparation of the 16-node call state, then one measurement of the marked qubit. No amplification. Depth 195, 62 `cz` gates, physical qubits 90, 89, 91, 88, and 98. On those qubits the snapshot’s readout errors are between `0.004` and `0.010`, and the `cz` errors on the edges between them are between `0.0011` and `0.0018`. Five seeds, 8192 shots.

| seed | ideal price | noisy price | noisy marked frequency |
| ---: | ---: | ---: | ---: |
| 0 | 8.027 | 12.878 | 0.1089 |
| 1 | 8.186 | 12.892 | 0.1090 |
| 2 | 7.868 | 12.502 | 0.1057 |
| 3 | 7.984 | 12.546 | 0.1061 |
| 4 | 8.070 | 12.835 | 0.1085 |

The sampling standard error of an ideal 8192-shot estimate is `scale × √(a(1−a)/8192) = 0.328`. The ideal prices sit in that window around `8.01`. The noisy prices sit between `12.50` and `12.89`.

A rough check, not a fit: surviving a `cz` error of `1.6×10⁻³` through 62 gates leaves a fraction `(1 − 1.6×10⁻³)^62 ≈ 0.906` of the ideal probability, and replacing the rest by `1/2` gives

```
0.906 × 0.0677 + 0.094 × 1/2 ≈ 0.109.
```

The five noisy frequencies are `0.106` to `0.109`. Readout error alone, about `0.01`, would have moved `0.068` only to about `0.076`. The shift is the two-qubit depth.

## What the recent experiments already said

Tanaka et al. ran maximum-likelihood amplitude estimation on IBM hardware and found a query-count improvement on a 2-qubit circuit together with an error floor; on their 3-qubit integration the error stayed above the classical estimator. Ghosh et al. (IEEE Transactions on Quantum Engineering, 2024) report a 10-qubit hardware demonstration of iterative amplitude estimation for energy-contract risk, after approximate compiling and error mitigation. The Kingston numbers above are the unmitigated snapshot. On the one-qubit circuit the ideal frequencies survive. On the call loader they do not: the measured price is about `12.7` against a discrete value of `8.01` and a closed form of `8.02`.

Reproduce with the project virtualenv:

```
.venv/bin/python test_qiskit_audit.py
.venv/bin/python run_device.py
```
