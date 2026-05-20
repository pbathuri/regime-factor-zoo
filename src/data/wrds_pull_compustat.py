"""
Pull Compustat fundamentals (annual + quarterly) from WRDS.

Pulls the most common accounting items needed for Fama-French style
characteristics (book equity, total assets, sales, etc.) and joins to
the CRSP-Compustat link table.

Output: data/pulls/compustat_annual.parquet, compustat_quarterly.parquet,
        crsp_compustat_link.parquet
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.data.wrds_connect import get_connection

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "data" / "pulls"


# Core accounting items for Fama-French + factor zoo work
ANNUAL_ITEMS = [
    "gvkey", "datadate", "fyear", "fyr", "indfmt", "consol", "popsrc", "datafmt",
    "at",       # total assets
    "lt",       # total liabilities
    "ceq",      # common equity
    "seq",      # stockholders equity
    "txditc",   # deferred taxes + investment tax credit
    "pstkrv",   # preferred stock — redemption value
    "pstkl",    # preferred stock — liquidating value
    "pstk",     # preferred stock — par value
    "sale",     # sales / revenue
    "cogs",     # cost of goods sold
    "xsga",     # SG&A
    "ib",       # income before extraordinary items
    "ni",       # net income
    "oibdp",    # operating income before depreciation
    "dp",       # depreciation + amortization
    "capx",     # capital expenditure
    "ppent",    # net PP&E
    "ppegt",    # gross PP&E
    "che",      # cash + ST investments
    "dlc",      # debt in current liabilities
    "dltt",     # long-term debt
    "csho",     # common shares outstanding
    "prcc_f",   # price close — fiscal year end
]


def pull_compustat_annual(db, start: str = "1962-01-01", end: str = "2024-12-31") -> pd.DataFrame:
    """Annual fundamentals (funda), standard filters for North America industrial."""
    cols = ", ".join(ANNUAL_ITEMS)
    query = f"""
        SELECT {cols}
        FROM comp.funda
        WHERE datadate BETWEEN '{start}' AND '{end}'
          AND indfmt = 'INDL'
          AND consol = 'C'
          AND popsrc = 'D'
          AND datafmt = 'STD'
    """
    return db.raw_sql(query, date_cols=["datadate"])


def pull_compustat_quarterly(db, start: str = "1985-01-01", end: str = "2024-12-31") -> pd.DataFrame:
    """Quarterly fundamentals (fundq) — narrower set of items."""
    query = f"""
        SELECT gvkey, datadate, fyearq, fqtr, indfmt, consol, popsrc, datafmt,
               atq, ltq, ceqq, seqq, txditcq, pstkq,
               saleq, cogsq, ibq, niq, oibdpq, dpq,
               cheq, dlcq, dlttq, cshoq, prccq
        FROM comp.fundq
        WHERE datadate BETWEEN '{start}' AND '{end}'
          AND indfmt = 'INDL'
          AND consol = 'C'
          AND popsrc = 'D'
          AND datafmt = 'STD'
    """
    return db.raw_sql(query, date_cols=["datadate"])


def pull_crsp_compustat_link(db) -> pd.DataFrame:
    """CRSP-Compustat merged linktable — needed to join CRSP permno to Compustat gvkey."""
    query = """
        SELECT gvkey, lpermno AS permno, lpermco AS permco,
               linktype, linkprim, liid, linkdt, linkenddt
        FROM crsp.ccmxpf_linktable
        WHERE linktype IN ('LU', 'LC')
          AND linkprim IN ('P', 'C')
    """
    return db.raw_sql(query, date_cols=["linkdt", "linkenddt"])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(DEFAULT_OUT))
    p.add_argument("--annual-start", default="1962-01-01")
    p.add_argument("--annual-end", default="2024-12-31")
    p.add_argument("--skip-quarterly", action="store_true")
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    db = get_connection()

    print(f"Pulling Compustat annual {args.annual_start} → {args.annual_end} ...")
    funda = pull_compustat_annual(db, args.annual_start, args.annual_end)
    funda.to_parquet(out / "compustat_annual.parquet")
    print(f"  {funda.shape[0]:,} rows × {funda.shape[1]} cols → {out / 'compustat_annual.parquet'}")

    if not args.skip_quarterly:
        print("Pulling Compustat quarterly ...")
        fundq = pull_compustat_quarterly(db)
        fundq.to_parquet(out / "compustat_quarterly.parquet")
        print(f"  {fundq.shape[0]:,} rows × {fundq.shape[1]} cols → {out / 'compustat_quarterly.parquet'}")

    print("Pulling CRSP-Compustat link table ...")
    link = pull_crsp_compustat_link(db)
    link.to_parquet(out / "crsp_compustat_link.parquet")
    print(f"  {link.shape[0]:,} rows × {link.shape[1]} cols → {out / 'crsp_compustat_link.parquet'}")

    db.close()
    print("Done.")


if __name__ == "__main__":
    main()
