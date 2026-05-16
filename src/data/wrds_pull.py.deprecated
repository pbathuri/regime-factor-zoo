"""
Pull CRSP monthly returns + Compustat fundamentals from WRDS.
Saves to data/pulls/ as parquet.

Usage: python src/data/wrds_pull.py
"""
import os
import wrds
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parents[2] / "data" / "pulls"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_connection():
    return wrds.Connection()


def pull_crsp_monthly(db, start="1963-07-01", end="2023-12-31") -> pd.DataFrame:
    """Pull CRSP monthly stock file (msf) for common shares on NYSE/AMEX/NASDAQ."""
    query = f"""
        SELECT a.permno, a.date, a.ret, a.shrout, a.prc, a.exchcd, a.siccd,
               b.shrcd, b.exchcd as exchcd2
        FROM crsp.msf AS a
        LEFT JOIN crsp.msenames AS b
            ON a.permno = b.permno
            AND b.namedt <= a.date
            AND a.date <= b.nameendt
        WHERE a.date BETWEEN '{start}' AND '{end}'
          AND b.shrcd IN (10, 11)
          AND b.exchcd IN (1, 2, 3)
    """
    return db.raw_sql(query, date_cols=["date"])


def pull_ff_factors(db) -> pd.DataFrame:
    """Pull Fama-French 3 factors from CRSP."""
    return db.get_table("ff", "factors_monthly")


if __name__ == "__main__":
    print("Connecting to WRDS...")
    db = get_connection()

    print("Pulling CRSP monthly returns...")
    crsp = pull_crsp_monthly(db)
    crsp.to_parquet(DATA_DIR / "crsp_monthly.parquet")
    print(f"Saved {len(crsp):,} rows → data/pulls/crsp_monthly.parquet")

    print("Pulling FF factors...")
    ff = pull_ff_factors(db)
    ff.to_parquet(DATA_DIR / "ff_factors.parquet")
    print(f"Saved {len(ff):,} rows → data/pulls/ff_factors.parquet")

    db.close()
    print("Done.")
