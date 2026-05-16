"""
Download Fama-French + momentum factors from Ken French's library,
plus SPY benchmark from yfinance.

Replaces the WRDS pull for the public-data version of RegimeFactorZoo.
"""
import argparse
from pathlib import Path

import pandas as pd
import pandas_datareader.data as pdr
import yfinance as yf


def download_ff_factors(out_dir: Path) -> None:
    """Pull FF3 and momentum factor returns (monthly), save as parquet."""
    out_dir.mkdir(parents=True, exist_ok=True)

    ff3 = pdr.DataReader(
        "F-F_Research_Data_Factors", "famafrench", start="1926-07-01"
    )[0]
    ff3.index = ff3.index.to_timestamp()
    ff3.to_parquet(out_dir / "ff3_monthly.parquet")
    print(f"FF3: {ff3.shape}, {ff3.index.min().date()} → {ff3.index.max().date()}")

    mom = pdr.DataReader(
        "F-F_Momentum_Factor", "famafrench", start="1926-11-01"
    )[0]
    mom.index = mom.index.to_timestamp()
    mom.to_parquet(out_dir / "momentum_monthly.parquet")
    print(f"Momentum: {mom.shape}")

    ff5 = pdr.DataReader(
        "F-F_Research_Data_5_Factors_2x3", "famafrench", start="1963-07-01"
    )[0]
    ff5.index = ff5.index.to_timestamp()
    ff5.to_parquet(out_dir / "ff5_monthly.parquet")
    print(f"FF5: {ff5.shape}")


def download_spy(out_dir: Path) -> None:
    """Pull SPY daily prices from yfinance."""
    out_dir.mkdir(parents=True, exist_ok=True)
    spy = yf.download("SPY", start="1993-01-29", auto_adjust=False, progress=False)
    spy.to_parquet(out_dir / "spy_daily.parquet")
    print(f"SPY: {spy.shape}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="data/pulls", help="output directory")
    args = p.parse_args()
    out_dir = Path(args.out)

    download_ff_factors(out_dir)
    download_spy(out_dir)
    print(f"\nDone. Files in {out_dir.resolve()}")


if __name__ == "__main__":
    main()
