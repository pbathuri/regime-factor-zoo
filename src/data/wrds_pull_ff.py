"""
Pull Fama-French factors from WRDS (alternative to Ken French's library).

The WRDS-hosted FF tables are updated more frequently than the public CSVs
and are joinable inside SQL with CRSP/Compustat. Useful when the public
pandas-datareader pull breaks (which it does whenever pandas upgrades).

Output: data/pulls/ff3_monthly_wrds.parquet, ff5_monthly_wrds.parquet,
        momentum_monthly_wrds.parquet
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.data.wrds_connect import get_connection

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "data" / "pulls"


def pull_ff3_monthly(db) -> pd.DataFrame:
    """FF3 monthly factor returns from WRDS (ff.factors_monthly)."""
    query = """
        SELECT date, mktrf, smb, hml, rf, umd
        FROM ff.factors_monthly
        ORDER BY date
    """
    return db.raw_sql(query, date_cols=["date"])


def pull_ff5_monthly(db) -> pd.DataFrame:
    """FF5 monthly factor returns. Adds RMW (profitability) and CMA (investment)."""
    query = """
        SELECT date, mktrf, smb, hml, rmw, cma, rf
        FROM ffa.fivefactors_monthly
        ORDER BY date
    """
    return db.raw_sql(query, date_cols=["date"])


def pull_ff3_daily(db) -> pd.DataFrame:
    """FF3 daily factor returns from WRDS (ff.factors_daily)."""
    query = """
        SELECT date, mktrf, smb, hml, rf, umd
        FROM ff.factors_daily
        ORDER BY date
    """
    return db.raw_sql(query, date_cols=["date"])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(DEFAULT_OUT))
    p.add_argument("--with-daily", action="store_true", help="also pull daily factors")
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    db = get_connection()

    print("Pulling FF3 + momentum (monthly) from WRDS ...")
    ff3 = pull_ff3_monthly(db)
    ff3.to_parquet(out / "ff3_monthly_wrds.parquet")
    print(f"  {ff3.shape[0]:,} rows → {out / 'ff3_monthly_wrds.parquet'}")

    print("Pulling FF5 (monthly) from WRDS ...")
    try:
        ff5 = pull_ff5_monthly(db)
        ff5.to_parquet(out / "ff5_monthly_wrds.parquet")
        print(f"  {ff5.shape[0]:,} rows → {out / 'ff5_monthly_wrds.parquet'}")
    except Exception as e:
        print(f"  Skipped FF5 (table may be in different lib): {e}")

    if args.with_daily:
        print("Pulling FF3 + momentum (daily) from WRDS ...")
        ff3d = pull_ff3_daily(db)
        ff3d.to_parquet(out / "ff3_daily_wrds.parquet")
        print(f"  {ff3d.shape[0]:,} rows → {out / 'ff3_daily_wrds.parquet'}")

    db.close()
    print("Done.")


if __name__ == "__main__":
    main()
