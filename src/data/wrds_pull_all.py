"""
Orchestrator: pull all WRDS data the project depends on in one shot.

Runs (in order):
  1. wrds_connect.test_connection()  — smoke test
  2. wrds_pull_ff.main()             — FF factors (small, fast)
  3. wrds_pull_crsp.main()           — CRSP monthly + daily
  4. wrds_pull_compustat.main()      — Compustat annual + quarterly + link

Run from project root: python -m src.data.wrds_pull_all
"""
from __future__ import annotations

import time

from src.data import wrds_connect, wrds_pull_compustat, wrds_pull_crsp, wrds_pull_ff


def run_all() -> None:
    t0 = time.time()

    print("=" * 70)
    print("STEP 1/4 — Connection smoke test")
    print("=" * 70)
    wrds_connect.test_connection()

    print("\n" + "=" * 70)
    print("STEP 2/4 — Fama-French factors")
    print("=" * 70)
    wrds_pull_ff.main()

    print("\n" + "=" * 70)
    print("STEP 3/4 — CRSP returns (monthly + daily)")
    print("=" * 70)
    wrds_pull_crsp.main()

    print("\n" + "=" * 70)
    print("STEP 4/4 — Compustat fundamentals")
    print("=" * 70)
    wrds_pull_compustat.main()

    elapsed = (time.time() - t0) / 60
    print(f"\nFull WRDS pull complete in {elapsed:.1f} min.")


if __name__ == "__main__":
    run_all()
