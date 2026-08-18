"""Phase 5: is sparse SDF factor selection stable across volatility regimes?

Design notes:
  - alpha is FIXED at the full-sample CV optimum and applied to both regimes.
    Per-regime CV would confound regime differences with penalty differences.
  - Null must preserve group SIZES: smaller samples select fewer factors
    mechanically, so an unmatched null would manufacture significance.
  - Two nulls: iid month shuffle, and block shuffle. Regime labels are highly
    autocorrelated (crises span consecutive months), so the iid null is
    anti-conservative. The block null is the honest one.
"""
import numpy as np, pandas as pd
from pathlib import Path
from src.models.sdf import fit_sdf, cv_alpha

N_PERM, BLOCK, SEED = 1000, 12, 42
OUT = Path("report/phase5_regime_stability.csv")


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a | b) else np.nan


def to_clusters(support: set, cmap: dict) -> set:
    return {cmap[f] for f in support if f in cmap}


def load():
    X = pd.read_parquet("data/factors/bhj_tradable_34.parquet")
    reg = pd.read_parquet("data/factors/regimes.parquet")["regime"].dropna()
    cl = pd.read_csv("data/factors/factor_clusters.csv")
    cmap = dict(zip(cl.factor, cl.cluster_name))
    idx = X.index.intersection(reg.index)
    return X.loc[idx], reg.loc[idx].astype(str), cmap


def split_supports(X, mask_hi, alpha):
    _, s_hi = fit_sdf(X[mask_hi], alpha)
    _, s_lo = fit_sdf(X[~mask_hi], alpha)
    return s_hi, s_lo


def iid_null(X, n_hi, alpha, cmap, rng):
    out = []
    for _ in range(N_PERM):
        m = np.zeros(len(X), bool)
        m[rng.choice(len(X), n_hi, replace=False)] = True
        a, b = split_supports(X, m, alpha)
        out.append((jaccard(a, b), jaccard(to_clusters(a, cmap), to_clusters(b, cmap))))
    return np.array(out)


def block_null(X, n_hi, alpha, cmap, rng):
    """Shuffle contiguous blocks, preserving autocorrelation in the labels."""
    n = len(X)
    blocks = [np.arange(i, min(i + BLOCK, n)) for i in range(0, n, BLOCK)]
    out = []
    for _ in range(N_PERM):
        order = rng.permutation(len(blocks))
        pick, m = [], np.zeros(n, bool)
        for bi in order:
            pick.extend(blocks[bi])
            if len(pick) >= n_hi:
                break
        m[np.array(pick[:n_hi])] = True
        a, b = split_supports(X, m, alpha)
        out.append((jaccard(a, b), jaccard(to_clusters(a, cmap), to_clusters(b, cmap))))
    return np.array(out)


def pval(null_vals, obs):
    """Two-sided-aware: report both tails, since MORE stability is also a finding."""
    lo = float(np.mean(null_vals <= obs))
    hi = float(np.mean(null_vals >= obs))
    return lo, hi


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    X, reg, cmap = load()
    mask_hi = (reg == "high").values
    n_hi = int(mask_hi.sum())
    print(f"merged months: {len(X)}   high={n_hi}  low={len(X)-n_hi}")
    print(f"window: {X.index.min().date()} -> {X.index.max().date()}")

    alphas = np.logspace(-4, 1.5, 60)
    cv = cv_alpha(X, alphas)
    alpha = float(cv.loc[cv.cv_mse.idxmin(), "alpha"])
    b_full, s_full = fit_sdf(X, alpha)
    print(f"\nfixed alpha={alpha:.4f}  full-sample support k={len(s_full)}")

    s_hi, s_lo = split_supports(X, mask_hi, alpha)
    c_hi, c_lo = to_clusters(s_hi, cmap), to_clusters(s_lo, cmap)
    j_f, j_c = jaccard(s_hi, s_lo), jaccard(c_hi, c_lo)

    print(f"\nHIGH-vol support (k={len(s_hi)}): {sorted(s_hi)}")
    print(f"LOW-vol  support (k={len(s_lo)}): {sorted(s_lo)}")
    print(f"\nonly in HIGH: {sorted(s_hi - s_lo)}")
    print(f"only in LOW : {sorted(s_lo - s_hi)}")
    print(f"\nJaccard  factor-level = {j_f:.3f}   cluster-level = {j_c:.3f}")

    rows = []
    for name, fn in (("iid", iid_null), ("block", block_null)):
        nl = fn(X, n_hi, alpha, cmap, rng)
        for lvl, obs, col in (("factor", j_f, 0), ("cluster", j_c, 1)):
            lo, hi = pval(nl[:, col], obs)
            print(f"{name:5s} null {lvl:7s}: mean={nl[:,col].mean():.3f} "
                  f"sd={nl[:,col].std():.3f}  p(null<=obs)={lo:.3f}  p(null>=obs)={hi:.3f}")
            rows.append(dict(null=name, level=lvl, observed=obs,
                             null_mean=nl[:, col].mean(), null_sd=nl[:, col].std(),
                             p_less=lo, p_greater=hi))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\n-> {OUT}")
