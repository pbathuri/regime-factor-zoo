"""
Fama-French 3-factor utilities.

Loads, aligns, and compares FF3 monthly series from two sources:
 - Ken French Data Library (via pandas-datareader pull)
 - WRDS (ff.factors_monthly)

Provides loader + comparison + summary-stats helpers used by
notebooks/02_ff3_validation_and_eda.ipynb.

Milestone: Jun 7, 2026 — FF3 reproduction validated.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "pulls"
PUB_PATH = DATA_DIR / "ff3_monthly.parquet"
WRDS_PATH = DATA_DIR / "ff3_monthly_wrds.parquet"


def load_public_ff3() -> pd.DataFrame:
    """Load Ken French FF3 (public). Returns DataFrame with columns
    [mktrf, smb, hml, rf], DatetimeIndex (monthly), values in PERCENT."""
    df = pd.read_parquet(PUB_PATH).copy()
    df.columns = [c.lower().replace("-", "") for c in df.columns]
    # Ken French publishes values in percent (e.g. 1.5 = 1.5%)
    if df.index.name is None:
        df.index.name = "date"
    return df.sort_index()


def load_wrds_ff3() -> pd.DataFrame:
    """Load FF3 from WRDS pull. Returns DataFrame aligned to public schema.
    WRDS publishes in decimal (e.g. 0.015 = 1.5%); convert to percent."""
    df = pd.read_parquet(WRDS_PATH).copy()
    df.columns = [c.lower() for c in df.columns]
    if "date" in df.columns:
        df = df.set_index("date")
    df.index = pd.to_datetime(df.index)
    # WRDS uses decimal; multiply by 100 to match Ken French's percent
    factor_cols = [c for c in ["mktrf", "smb", "hml", "rf", "umd"] if c in df.columns]
    df[factor_cols] = df[factor_cols] * 100.0
    return df.sort_index()


def align(pub: pd.DataFrame, wrds: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Restrict both DataFrames to overlapping months + matching columns."""
    common_cols = sorted(set(pub.columns) & set(wrds.columns))
    pub2 = pub[common_cols]
    wrds2 = wrds[common_cols]
    # Normalize to month-start (some sources use month-end)
    pub2.index = pub2.index.to_period("M").to_timestamp()
    wrds2.index = wrds2.index.to_period("M").to_timestamp()
    common_dates = pub2.index.intersection(wrds2.index)
    return pub2.loc[common_dates].sort_index(), wrds2.loc[common_dates].sort_index()


def compare(pub: pd.DataFrame, wrds: pd.DataFrame) -> pd.DataFrame:
    """Per-column: mean abs diff, max abs diff, Pearson correlation."""
    rows = []
    for col in pub.columns:
        diff = pub[col] - wrds[col]
        rows.append({
            "factor": col,
            "n_months": len(diff),
            "mean_abs_diff_pct": diff.abs().mean(),
            "max_abs_diff_pct": diff.abs().max(),
            "rmse_pct": np.sqrt((diff ** 2).mean()),
            "correlation": pub[col].corr(wrds[col]),
        })
    return pd.DataFrame(rows).set_index("factor")


def summary_stats(ff: pd.DataFrame) -> pd.DataFrame:
    """Per-factor: mean (monthly %), annualized vol, annualized Sharpe.
    Assumes input in percent per month."""
    rows = []
    for col in ff.columns:
        x = ff[col].dropna()
        m_monthly = x.mean()
        s_monthly = x.std()
        # Annualize: mean × 12, std × sqrt(12); Sharpe uses excess return
        m_ann = m_monthly * 12.0
        s_ann = s_monthly * (12.0 ** 0.5)
        sharpe = m_ann / s_ann if col != "rf" and s_ann > 0 else float("nan")
        rows.append({
            "factor": col,
            "n_months": len(x),
            "mean_monthly_pct": m_monthly,
            "mean_annual_pct": m_ann,
            "vol_annual_pct": s_ann,
            "sharpe_annual": sharpe,
        })
    return pd.DataFrame(rows).set_index("factor")


def cumulative_returns(ff: pd.DataFrame, factors=("mktrf", "smb", "hml")) -> pd.DataFrame:
    """Compound monthly returns into cumulative wealth (value of $1 invested).
    Assumes input in percent per month."""
    r = ff[list(factors)] / 100.0  # percent → decimal
    return (1.0 + r).cumprod()
