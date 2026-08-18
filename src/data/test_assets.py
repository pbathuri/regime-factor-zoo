"""Build BHJ test-asset matrix: FF25 size/BM + 30 industry portfolios."""
from pathlib import Path
import pandas as pd

OUT = Path("data/factors/test_assets_55.parquet")

def build() -> pd.DataFrame:
    ff25 = pd.read_parquet("data/factors/ff25_monthly.parquet")
    ind30 = pd.read_parquet("data/factors/ind30_monthly.parquet")

    ff25.columns = [f"ff25_{c.strip().replace(' ', '_')}" for c in ff25.columns]
    ind30.columns = [f"ind_{c.strip()}" for c in ind30.columns]

    R = pd.concat([ff25, ind30], axis=1)
    R = R.mask(R <= -99.0)                 # Ken French missing sentinels
    R = R / 100.0                          # percent -> decimal
    R.index = R.index.to_timestamp("M")    # Period -> Timestamp
    R.index.name = "date"
    return R

if __name__ == "__main__":
    R = build()
    print(R.shape, R.index.min().date(), R.index.max().date())
    print("NaNs per column (nonzero only):")
    print(R.isna().sum()[lambda s: s > 0])
    print(R.describe().T[["mean", "std", "min", "max"]].head())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    R.to_parquet(OUT)
    print("->", OUT)
