---
title: "What an amplitude-estimation error bar actually controls"
author: "Pradyot Bathuri"
date: "23 October 2026"
fontsize: 10pt
geometry: margin=0.8in
colorlinks: false
header-includes: |
  \makeatletter
  \renewcommand{\maketitle}{\begin{center}{\large\bfseries\@title\par}\smallskip\@author\quad---\quad\@date\end{center}\medskip}
  \makeatother
  \setlength{\LTpre}{3pt}
  \setlength{\LTpost}{4pt}
  \setlength{\parskip}{3pt}
---

## Error budget and quadrature

A certified estimate of a badly encoded amplitude is not a certified price or CVaR. Linking my regime-conditional factor models to amplitude estimation, I separate target, encoding and estimation errors; no novelty, new pricing method or interval-arithmetic proof is claimed. For $S_0=100$, $K=105$, $r=0.05$, $\sigma=0.2$, $T=1$ year, and standard-normal distribution/density $\Phi,\phi$, the call and normal-loss references are
$$
C=S_0\Phi(d_1)-Ke^{-rT}\Phi(d_2)=8.0213522351,\qquad
d_{1,2}=\frac{\log(S_0/K)+(r\pm\sigma^2/2)T}{\sigma\sqrt T},
$$
$$
L\sim N(\mu,\sigma_L^2):\quad q_\alpha=\mu+\sigma_L\Phi^{-1}(\alpha),\qquad
\operatorname{CVaR}_\alpha(L)=\mu+\frac{\sigma_L\phi(\Phi^{-1}(\alpha))}{1-\alpha}.
$$
At $\mu=0$, $\sigma_L=1$, $\alpha=0.95$: VaR $1.6448536270$, CVaR $2.0627128075$ (standard-normal loss units; `problems.py`, `test_audit.py`, fresh `run.py` output in `verification/run_report.txt`). For masses $p_i$, $0\le f_i\le1$, $a=\sum_i p_i f_i$, canonical estimation returns $\widehat a=\sin^2(\pi k/t)$, $t=2^m$ phase bins. In `estimation.py`, Brassard-Hoyer-Mosca-Tapp gives
$$
\Pr\{|\widehat a-a|\le B_t(a)\}\ge\frac8{\pi^2}=0.810569\ldots,\qquad
B_t(a)=\frac{2\pi\sqrt{a(1-a)}}t+\frac{\pi^2}{t^2}.
$$
This ideal-oracle, probabilistic a priori bar uses known encoded $a$; otherwise $a(1-a)\le1/4$ gives $B_t(a)\le\pi/t+\pi^2/t^2$. It is not a shot-derived interval; scaling converts units, not coverage of quadrature, quantile, sampling or hardware error. At fixed encoding/success probability, ideal query improvement is quadratic ($1/\epsilon$ versus Monte Carlo's $1/\epsilon^2$), not exponential: $t-1$ uses of $Q$, plus loading/compilation costs. Statevector simulation is not a wall-clock speedup. With discounted payoff maximum $s$, $C_h=sa_h$, $\widehat C_h=s\widehat a_h$:
$$
\widehat C_h-C=(\widehat C_h-C_h)+(C_h-C),\quad
C_h-C=(C_h-C_W)+(C_W-C).
$$
Only estimation has bar $sB_t(a_h)$; price certification also needs encoding error, measured here against a closed form without interval enclosure. Uniform **spot** nodes spanning the range corresponding to shocks $[-4,4]$ use normalized lognormal-density masses: $C_W=8.0177885991$, bias $C_W-C=-0.0035636360$. The $\pm4\sigma$ window sets an asymptotic floor, not a finite-grid lower bound: cancellation gives $0.00061609$-dollar error at 96 nodes; at 256, price $8.0178887418$. Full-domain Gauss-Hermite is non-monotone on the strike kink despite polynomial exactness, and worse at 16 nodes. One small error proves neither convergence nor a general quadrature ranking.

| Nodes | Gauss-Hermite price | Signed error | Uniform-grid price | Signed error |
| ---: | ---: | ---: | ---: | ---: |
| 16 | 8.19192793 | +0.17057570 | 8.00851991 | -0.01283233 |
| 64 | 8.03695667 | +0.01560444 | 8.01769175 | -0.00366048 |
| 96 | 8.02005137 | -0.00130087 | 8.02073615 | -0.00061609 |
| 128 | 8.01162193 | -0.00973030 | 8.01852537 | -0.00282686 |
| 256 | 7.99900672 | -0.02234551 | 8.01788874 | -0.00346349 |
| 512 | 8.01974650 | -0.00160574 | 8.01775543 | -0.00359680 |

Source: `data/scale_sweep.json`, `classical`; prices/signed errors in dollars versus Black-Scholes.

Figure 1 (`figures/scaling_methods.png`): `data/scale_sweep.json`, regenerated 23 October 2026; noisy panel: unmitigated 15 April 2026 FakeKingston/Aer simulation. Monte Carlo uses 24 seeds/path count and separately simulated payoff SD for its dashed standard-error reference, not a rigorous finite-sample bound; node/path/phase-bin budgets imply no equal end-to-end costs.

## Amplitude estimation against its bar

For $a=\sin^2(0.7)=0.4150164285$, medians are descriptive, classically computed probability-weighted medians of the exact statevector distribution, not shots or experimental repetitions. Success probabilities describe random outcomes: they may decrease as bars narrow; stationary phase-bin medians are not failures. The minimum remains above $8/\pi^2$.

| Phase bins $t$ | Absolute median error | Amplitude bar | Probability inside bar |
| ---: | ---: | ---: | ---: |
| 16 | 0.08498357 | 0.23204574 | 0.828128 |
| 64 | 0.01256159 | 0.05078272 | 0.894985 |
| 128 | 0.01161833 | 0.02478897 | 0.811465 |
| 256 | 0.00049737 | 0.01224389 | 0.996277 |
| 1024 | 0.00049737 | 0.00303273 | 0.949507 |

The 16-node call uses $a_h=0.0677149409$, $s=118.268137$ dollars, and grid reference $8.0085199051$, not Black-Scholes. At $t=16$ its bar exceeds the price; at $t=1024$ the Black-Scholes error $+0.022486$ dollars combines positive estimation error and negative grid bias.

| $t$ | Median price | Error vs grid | Price bar | Probability inside |
| ---: | ---: | ---: | ---: | ---: |
| 16 | 4.501313 | -3.507207 | 16.228894 | 0.921119 |
| 64 | 6.982476 | -1.026044 | 3.202297 | 0.843049 |
| 256 | 7.682285 | -0.326235 | 0.747141 | 0.814712 |
| 1024 | 8.043838 | +0.035319 | 0.183446 | 0.933545 |

Both tables: `data/scale_sweep.json`, `amplitude_estimation`; call prices, signed errors and bars in dollars.

Known-amplitude/call seeded shots satisfy their bars; Gaussian CVaR retains its miss. For 20,000 losses, seed 11, 32 bins: excess assembly $2.0603234871$; $t=16$ median $3.2189159024$, bar $3.245422$, **seed-0 single shot outside its bar**, success probability $0.858922$, consistent with the theorem. At $t=1024$: median $2.0606839698$, bar $0.02604439$ (`run.py`, existing audit). No filtering or every-shot guarantee.

Figure 2 (`figures/scaling_details.png`): `data/scale_sweep.json`, regenerated 23 October 2026; shots/legacy baseline retained, no-CZ panel: unmitigated 15 April 2026 FakeKingston/Aer simulation.

## Simulated noise

**FakeKingston is the ibm_kingston calibration snapshot of 15 April 2026 in Qiskit Aer, not live hardware; no mitigation.** This sweep (earlier runs: `MEASUREMENTS.md`) averages eight seeds, 4,096 shots each, without call-loader amplification. Shift from the grid grows with CZ count, alongside changing nodes/depth/compilation: no isolated CZ causality. More shots reduce fluctuations, not bias.

| Spot nodes | CZ gates | Grid price | Ideal Aer mean | Noisy Aer mean | Noisy minus grid |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 7 | 4.017360 | 3.981011 | 5.688189 | +1.670829 |
| 8 | 23 | 8.037867 | 8.034206 | 10.585951 | +2.548085 |
| 16 | 62 | 8.008520 | 7.860962 | 12.816472 | +4.807952 |
| 32 | 132 | 7.983626 | 7.850134 | 17.761154 | +9.777529 |

Source: `data/scale_sweep.json`; prices and shifts in dollars.

The rough CZ-survival check mixes with $1/2$: $w=(1-p)^g$, $a_{\mathrm{mix}}=wa+(1-w)/2$. For $p=0.0016$, $g=62$, $w\simeq0.9055$, $a=0.0677$: prediction $a_{\mathrm{mix}}\simeq0.109$, measured $0.108368$. Omitting relaxation/readout/individual-gate details, this is no fit, mechanism proof, bound or price adjustment. The one-qubit no-CZ control follows $\sin^2((2m+1)\theta)$, $\theta=0.7$: at $m=4$, ideal $0.00028271$, noisy $0.01234436$ (floor near a zero). Averaging 16 seeds, 4,096 shots each, largely preserves oscillations through $m=16$, without testing multiqubit preparation. Earlier canonical $t=4,8$ runs: ideal/noisy medians $1/2$, error $0.08498$, ideal bars $1.391,0.541$. Wide bars diagnose little; coarse medians hide distribution changes; the ideal theorem does not certify noise.

**Established work:** Montanaro, [*Quantum speedup of Monte Carlo methods* (2015)](https://arxiv.org/abs/1504.06987); Woerner and Egger, [*Quantum risk analysis* (2019)](https://www.nature.com/articles/s41534-019-0130-6); Tanaka et al., [*Amplitude estimation via maximum likelihood on noisy quantum computer* (2021)](https://link.springer.com/article/10.1007/s11128-021-03215-9): prior work, no novelty claim.

## Empirical CVaR, reproduction and an open question

For loss = minus monthly return and $\alpha=0.95$, distinguish sample tail mean $S$, legacy comparator-selected histogram mean $H$, and excess assembly $D$. With sample quantile $q$, centers $c_i$, masses $p_i$:
$$
D=q+\frac{\sum_i p_i(c_i-q)_+}{1-\alpha},\quad
\widehat D=q+\frac{E_{\max}}{1-\alpha}\widehat a,\quad E_{\max}=\max_i(c_i-q)_+,\quad
\widehat D-S=(\widehat D-D)+(D-S).
$$
The bar $E_{\max}B_t(a)/(1-\alpha)$ covers only $\widehat D-D$ at fixed $q$/encoding, not population sampling or regime-label uncertainty. $D-S$ combines binning and finite-sample threshold/tail conventions: `sample_cvar` averages observations at/above `numpy.quantile`'s threshold, not necessarily the excess formula with divisor $1-\alpha$; $q$ need not be the histogram quantile. Hence $D-S$ is not pure quantum error, nor $D$ exact histogram CVaR. **Legacy $H$ is deliberately unchanged: a comparator mismatch**, using width $(\mathrm{hi}-\mathrm{lo})/(2^n-1)$ versus histogram width $(\mathrm{hi}-\mathrm{lo})/2^n$. Gaussian selected-tail mass: $0.06835$, not $0.05$; $H=1.9303992869$, $S=2.0606125246$. Because $H$ ignores amplitude output, accurate tail-probability estimation cannot repair it (Figure 2). `panel_cvar.py`: 3,090,082 firm-months, 25,048 identifiers, 618 months (July 1973 through December 2024); equal-weighted size/book-to-market quintiles, NYSE breakpoints, at least ten names/month, 221 high-/385 low-volatility months each. Delisting returns are missing; these descriptive conditional samples give no out-of-sample guarantee. At $t=1024$, all 20 medians meet bars against $D$, but only seven sample $S$ values occupy those AE-centered intervals: no population coverage claim.

| Portfolio / regime | Sample $S$ | Legacy $H$ | Excess $D$ | AE median $\widehat D$ | AE bar |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Size Q1 / high | 17.00793 | 16.40728 | 17.72510 | 17.68646 | 0.27221 |
| Size Q1 / low | 9.34103 | 8.44610 | 9.40425 | 9.44051 | 0.12100 |
| Book/market Q5 / high | 17.10908 | 14.52532 | 17.57854 | 17.48918 | 0.29696 |

Source: `data/panel_cvar.json`; $t=1024$, percent monthly loss, bars in percentage points.

Figure 3 (`figures/panel_cvar.png`): `data/panel_cvar.json`, July 1973-December 2024, regenerated 23 October 2026; equal-weighted $S$, all quintiles/saved regimes, no inferred confidence intervals.

`market_check.py` uses loss $=-\mathrm{mktrf}$ (stored monthly market excess return), with 634 labeled months: 223 high, 411 low. These windows differ from the quintile windows; without a population closed form, the same bar covers only fixed $D$.

| Regime | Months | Sample $S$ | Legacy $H$ | Excess $D$ | AE median | AE bar |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| All labeled | 634 | 10.36406 | 10.04906 | 10.30354 | 10.30477 | 0.17646 |
| High volatility | 223 | 13.14417 | 13.16031 | 13.40383 | 13.37826 | 0.18181 |
| Low volatility | 411 | 7.56905 | 7.40225 | 7.62960 | 7.66911 | 0.09236 |

Source: `data/market_regimes.json`; $t=1024$, percent monthly excess-return loss, bars in percentage points.

High-volatility target mismatch $D-S\simeq0.25966$ points versus median error $-0.02557$ points: both high/low sample values fall outside AE-centered bars although AE medians meet bars against $D$. The AE summary covers 17,468 **firm-regime pairs**, not unique firms, with at least 60 months/regime, at $t=256$: every median inside its bar; median bar $0.01072510$ decimal monthly loss = $1.07251$ percentage points, not empirical single-shot coverage. Big Red 200 job **8688102**, 22 October 2026 (`BIGRED_RUN.md`), reran `panel_cvar.py --firm-ae` on AMD EPYC: `.out` records cluster path/matching results, `.err` is empty. Big Red reproduced the Mac on a second architecture at reporting precision (maximum absolute JSON difference $1.33\times10^{-15}$), not literal “last digit” identity. Provenance is the run record, not stale `machine: local Mac`. It did not make the noise more real or the math faster.

Could an Evans-function/winding-number viewpoint organize this error bar by identifying the certified object and whether perturbations preserve its conclusion, as in a Rouche argument? Added value beyond the decomposition is unknown: a question, not a claimed connection or implemented Evans function.

**Verified 23 October 2026:** 13 numerical/five Qiskit tests passed; redirected `scale_sweep.py` matched saved JSON exactly; `plot_scale.py` regenerated both figures, `plot_panel.py` the sole addition; SHA-256 checked protected data/tests/logs; no panel regeneration. Sources: `NOTE.md`, `MEASUREMENTS.md`, three application/sweep JSONs, `problems.py`, `estimation.py`, `run.py`, Big Red record.
