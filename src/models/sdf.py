"""Penalized SDF estimation: b = Sigma^-1 mu via regressing 1 on factor returns."""
import numpy as np, pandas as pd
from sklearn.linear_model import ElasticNet
from sklearn.model_selection import TimeSeriesSplit

def fit_sdf(X: pd.DataFrame, alpha: float, l1_ratio: float = 0.5):
    """Return (b_original_units, support) for one penalty level."""
    sd = X.std(ddof=1).values                 # scale only
    Xs = X.values / sd                        # NO centering: mu is the signal
    y = np.ones(len(X))
    m = ElasticNet(alpha=alpha, l1_ratio=l1_ratio,
                   fit_intercept=False, max_iter=50_000, tol=1e-6)
    m.fit(Xs, y)
    b = pd.Series(m.coef_ / sd, index=X.columns)   # back to original units
    return b, set(X.columns[m.coef_ != 0])

def cv_alpha(X: pd.DataFrame, alphas, l1_ratio=0.5, n_splits=5):
    """Walk-forward CV. Score = OOS pricing error of the SDF."""
    tscv, out = TimeSeriesSplit(n_splits=n_splits), []
    for a in alphas:
        errs = []
        for tr, te in tscv.split(X):
            sd = X.iloc[tr].std(ddof=1).values
            m = ElasticNet(alpha=a, l1_ratio=l1_ratio, fit_intercept=False,
                           max_iter=50_000, tol=1e-6)
            m.fit(X.iloc[tr].values / sd, np.ones(len(tr)))
            pred = (X.iloc[te].values / sd) @ m.coef_
            errs.append(np.mean((1 - pred) ** 2))   # OOS SDF pricing error
        out.append((a, float(np.mean(errs))))
    return pd.DataFrame(out, columns=["alpha", "cv_mse"])

if __name__ == "__main__":
    X = pd.read_parquet("data/factors/bhj_tradable_34.parquet")
    alphas = np.logspace(-5, -1, 40)
    cv = cv_alpha(X, alphas)
    best = cv.loc[cv.cv_mse.idxmin(), "alpha"]
    b, sup = fit_sdf(X, best)
    print(f"best alpha={best:.2e}   selected {len(sup)}/{len(X.columns)}")
    print("\nnonzero b (original units), by |magnitude|:")
    print(b[b != 0].reindex(b.abs().sort_values(ascending=False).index).dropna().round(2).to_string())
    print("\nsparsity path:")
    for a in np.logspace(-5, -1, 9):
        _, s = fit_sdf(X, a)
        print(f"  alpha={a:.1e}  k={len(s):2d}  {sorted(s) if len(s)<=8 else ''}")
