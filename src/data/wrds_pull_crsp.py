"""
Pull CRSP monthly + daily returns from WRDS.

Filters to common shares (shrcd 10, 11) on major exchanges (exchcd 1, 2, 3).
Output: data/pulls/crsp_monthly.parquet, crsp_daily.parquet
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.data.wrds_connect import get_connection

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "data" / "pulls"


def pull_crsp_monthly(db, start: str = "1963-07-01", end: str = "2024-12-31") -> pd.DataFrame:
    """Monthly stock file with share-code and exchange filters."""
    query = f"""
        SELECT a.permno,
               a.permco,
               a.date,
               a.ret,
               a.retx,
               a.shrout,
               a.prc,
               a.vol,
               a.cfacshr,
               b.shrcd,
               b.exchcd,
               b.siccd,
               b.ticker
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


def pull_crsp_daily(db, start: str = "2000-01-01", end: str = "2024-12-31") -> pd.DataFrame:
    """Daily stock file. Defaults to 2000+ because daily 1963-99 is huge."""
    query = f"""
        SELECT a.permno,
               a.date,
               a.ret,
               a.retx,
               a.prc,
               a.vol,
               b.shrcd,
               b.exchcd
        FROM crsp.dsf AS a
        LEFT JOIN crsp.msenames AS b
            ON a.permno = b.permno
            AND b.namedt <= a.date
            AND a.date <= b.nameendt
        WHERE a.date BETWEEN '{start}' AND '{end}'
          AND b.shrcd IN (10, 11)
          AND b.exchcd IN (1, 2, 3)
    """
    return db.raw_sql(query, date_cols=["date"])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(DEFAULT_OUT))
    p.add_argument("--monthly-start", default="1963-07-01")
    p.add_argument("--monthly-end", default="2024-12-31")
    p.add_argument("--daily-start", default="2000-01-01")
    p.add_argument("--daily-end", default="2024-12-31")
    p.add_argument("--skip-daily", action="store_true", help="skip daily pull (large)")
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    db = get_connection()
    print(f"Pulling CRSP monthly {args.monthly_start} → {args.monthly_end} ...")
    msf = pull_crsp_monthly(db, args.monthly_start, args.monthly_end)
    msf.to_parquet(out / "crsp_monthly.parquet")
    print(f"  {msf.shape[0]:,} rows × {msf.shape[1]} cols → {out / 'crsp_monthly.parquet'}")

    if not args.skip_daily:
        print(f"Pulling CRSP daily {args.daily_start} → {args.daily_end} (this may take a few minutes) ...")
        dsf = pull_crsp_daily(db, args.daily_start, args.daily_end)
        dsf.to_parquet(out / "crsp_daily.parquet")
        print(f"  {dsf.shape[0]:,} rows × {dsf.shape[1]} cols → {out / 'crsp_daily.parquet'}")

    db.close()
    print("Done.")


if __name__ == "__main__":
    main()
