"""
WRDS connection helper.

Centralizes connection logic so every puller can call get_connection()
without re-implementing credential handling. Uses .env for username/
password if present; falls back to wrds' built-in pgpass / interactive
prompt.
"""
from __future__ import annotations

import os
from pathlib import Path

import wrds
from dotenv import load_dotenv

# Load .env from project root if present
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def get_connection() -> wrds.Connection:
    """Return an authenticated WRDS connection.

    Resolution order:
      1. WRDS_USERNAME + WRDS_PASSWORD in environment (from .env)
      2. ~/.pgpass entry for wrds-pgdata.wharton.upenn.edu
      3. Interactive prompt (will hang in non-interactive runs — don't use in cron)
    """
    username = os.getenv("WRDS_USERNAME")
    if username:
        return wrds.Connection(wrds_username=username)
    return wrds.Connection()


def test_connection() -> None:
    """Quick smoke test: list available libraries and sample one row."""
    db = get_connection()
    libs = db.list_libraries()
    print(f"Connected. {len(libs)} libraries visible.")
    # Sample one row from CRSP monthly stock file to verify access
    sample = db.raw_sql("SELECT * FROM crsp.msf LIMIT 1", date_cols=["date"])
    print(f"crsp.msf sample row shape: {sample.shape}")
    print(sample)
    db.close()


if __name__ == "__main__":
    test_connection()
