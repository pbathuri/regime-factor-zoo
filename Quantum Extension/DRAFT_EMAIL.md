To: Kevin Zumbrun <kzumbrun@iu.edu>
Subject: Numerical error budgets in an amplitude-estimation example

Dear Professor Zumbrun,

I am in your numerical analysis course, and I have put together a short note connecting my work on regime-conditional factor models with quantum amplitude estimation. The question is what an a priori amplitude-estimation bound actually controls once discretization and encoding errors enter the reported quantity. The call example has a useful quadrature wrinkle: Gauss-Hermite is non-monotone on the kinked payoff, and refining a fixed-window grid leaves a truncation bias.

I have attached FINAL_WRITEUP.pdf (with FINAL_WRITEUP.md as the source), along with scaling_methods.png, scaling_details.png, and panel_cvar.png. The note retains the failed single-shot bound check and the legacy CVaR encoding mismatch. The noisy results are unmitigated Qiskit Aer simulations of a dated calibration snapshot, not live hardware; the Big Red run is a reproduction check. I make no novelty or wall-clock speedup claim.

If you have time, I would appreciate your thoughts on the error decomposition and on whether an Evans-function or winding-number viewpoint suggests a useful way to think about the estimator's error bar. I am posing that as a question, without claiming a connection. Thank you for taking a look.

Best,
Pradyot Bathuri
