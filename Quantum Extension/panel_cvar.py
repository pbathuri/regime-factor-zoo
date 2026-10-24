"""CVaR split on CRSP common stocks, sorted with Compustat book equity.

Uses the local pulls, not a new WRDS query:

    data/pulls/crsp_monthly.parquet        1963-07 through 2024-12
    data/pulls/compustat_annual.parquet    book equity
    data/pulls/crsp_compustat_link.parquet
    data/factors/regimes.parquet           high / low market-vol labels

The monthly return is CRSP ret as stored. The pull has no delisting return.
Size and book-to-market quintiles use NYSE breakpoints. A stock's June market
equity sorts it from the following July through the next June. Book-to-market
uses book equity and December market equity from the previous calendar year.
Book equity is stockholders' equity, else common equity plus preferred, else
assets minus liabilities, plus deferred taxes, minus preferred (redemption,
else liquidating, else par).

Each series below is an equal-weighted average of firm returns in that month.
The CVaR numbers are for the loss, minus that average, inside one volatility
regime. Amplitude estimation is the same histogram excess estimator as
market_check.py. It estimates that discrete histogram, not a closed form.

--firm-ae adds one statevector estimate per firm with at least 60 months in
a regime. That loop is the piece sized for Big Red.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import problems
from market_check import _block

ROOT = Path(__file__).resolve().parents[1]
PULLS = ROOT / "data" / "pulls"
REGIMES = ROOT / "data" / "factors" / "regimes.parquet"
OUT = Path(__file__).resolve().parent / "data" / "panel_cvar.json"
MIN_NAMES = 10
MIN_FIRM_MONTHS = 60


def _book_equity(annual: pd.DataFrame) -> pd.Series:
    equity = annual["seq"].copy()
    equity = equity.fillna(annual["ceq"] + annual["pstk"].fillna(0))
    equity = equity.fillna(annual["at"] - annual["lt"])
    preferred = annual["pstkrv"].fillna(annual["pstkl"]).fillna(annual["pstk"])
    return equity + annual["txditc"].fillna(0) - preferred.fillna(0)


def _quintile(value: pd.Series, edges: pd.DataFrame) -> pd.Series:
    merged = edges.reindex(value.index)
    above = (
        (value > merged["q20"]).astype(int)
        + (value > merged["q40"]).astype(int)
        + (value > merged["q60"]).astype(int)
        + (value > merged["q80"]).astype(int)
    )
    return (above + 1).where(merged["q20"].notna() & value.notna())


def _breakpoints(frame: pd.DataFrame, value: str) -> pd.DataFrame:
    nyse = frame.loc[frame["exchcd"] == 1, ["form_year", value]].dropna()
    edges = nyse.groupby("form_year")[value].quantile([0.2, 0.4, 0.6, 0.8]).unstack()
    edges.columns = ["q20", "q40", "q60", "q80"]
    return edges


def load_panel() -> tuple[pd.DataFrame, dict]:
    crsp = pd.read_parquet(
        PULLS / "crsp_monthly.parquet",
        columns=["permno", "date", "ret", "shrout", "prc", "shrcd", "exchcd"],
    )
    crsp["permno"] = crsp["permno"].astype("int64")
    crsp["date"] = pd.to_datetime(crsp["date"])
    crsp["ret"] = pd.to_numeric(crsp["ret"], errors="coerce")
    crsp["me"] = crsp["prc"].abs() * pd.to_numeric(crsp["shrout"], errors="coerce")
    crsp = crsp.dropna(subset=["ret", "date"])
    crsp = crsp.loc[crsp["ret"] >= -1.0]
    crsp = crsp.drop_duplicates(["permno", "date"])
    crsp["year"] = crsp["date"].dt.year
    crsp["month"] = crsp["date"].dt.month
    crsp["form_year"] = np.where(crsp["month"] >= 7, crsp["year"], crsp["year"] - 1)

    regimes = pd.read_parquet(REGIMES)
    regimes = regimes.dropna(subset=["regime"]).copy()
    regimes.index = pd.to_datetime(regimes.index).to_period("M")
    crsp["ym"] = crsp["date"].dt.to_period("M")
    crsp = crsp.merge(
        regimes[["regime"]],
        left_on="ym",
        right_index=True,
        how="inner",
    )

    june = crsp.loc[(crsp["month"] == 6) & (crsp["me"] > 0), ["permno", "year", "me", "exchcd"]]
    june = june.drop_duplicates(["permno", "year"]).rename(columns={"year": "form_year", "me": "me_june"})
    june = june.join(_breakpoints(june.rename(columns={"me_june": "me"}), "me"), on="form_year")
    june["size_q"] = _quintile(june["me_june"], june[["q20", "q40", "q60", "q80"]])
    crsp = crsp.merge(june[["permno", "form_year", "size_q"]], on=["permno", "form_year"], how="left")

    annual = pd.read_parquet(
        PULLS / "compustat_annual.parquet",
        columns=["gvkey", "datadate", "seq", "ceq", "pstk", "at", "lt", "txditc", "pstkrv", "pstkl"],
    )
    annual["datadate"] = pd.to_datetime(annual["datadate"])
    annual["be"] = _book_equity(annual)
    annual = annual.loc[annual["be"] > 0, ["gvkey", "datadate", "be"]]
    annual["calyear"] = annual["datadate"].dt.year
    annual = annual.sort_values("datadate").drop_duplicates(["gvkey", "calyear"], keep="last")
    annual["asof"] = pd.to_datetime(annual["calyear"].astype(str) + "-12-31")

    link = pd.read_parquet(PULLS / "crsp_compustat_link.parquet")
    link = link.loc[link["linktype"].isin(["LC", "LU"]) & link["linkprim"].isin(["P", "C"])].copy()
    link["permno"] = link["permno"].astype("int64")
    link["linkdt"] = pd.to_datetime(link["linkdt"])
    link["linkenddt"] = pd.to_datetime(link["linkenddt"]).fillna(pd.Timestamp("2099-12-31"))
    link["prim_rank"] = np.where(link["linkprim"] == "P", 0, 1)
    matched = annual.merge(link, on="gvkey", how="inner")
    matched = matched.loc[(matched["linkdt"] <= matched["asof"]) & (matched["asof"] <= matched["linkenddt"])]
    matched = matched.sort_values("prim_rank").drop_duplicates(["permno", "calyear"])

    december = crsp.loc[(crsp["month"] == 12) & (crsp["me"] > 0), ["permno", "year", "me", "exchcd"]]
    december = december.drop_duplicates(["permno", "year"]).rename(columns={"year": "calyear", "me": "me_dec"})
    books = matched.merge(december, on=["permno", "calyear"], how="inner")
    books["bm"] = books["be"] / books["me_dec"]
    books = books.loc[np.isfinite(books["bm"]) & (books["bm"] > 0)].copy()
    books["form_year"] = books["calyear"] + 1
    books = books.join(_breakpoints(books, "bm"), on="form_year")
    books["bm_q"] = _quintile(books["bm"], books[["q20", "q40", "q60", "q80"]])
    crsp = crsp.merge(books[["permno", "form_year", "bm_q"]], on=["permno", "form_year"], how="left")

    coverage = {
        "crsp_file": "data/pulls/crsp_monthly.parquet",
        "compustat_file": "data/pulls/compustat_annual.parquet",
        "months": int(crsp["ym"].nunique()),
        "first_month": str(crsp["ym"].min()),
        "last_month": str(crsp["ym"].max()),
        "firm_months": int(len(crsp)),
        "permnos": int(crsp["permno"].nunique()),
        "with_size_quintile": int(crsp["size_q"].notna().sum()),
        "with_bm_quintile": int(crsp["bm_q"].notna().sum()),
        "high_firm_months": int((crsp["regime"] == "high").sum()),
        "low_firm_months": int((crsp["regime"] == "low").sum()),
        "delisting_return": "not in the CRSP pull",
        "new_wrds_query": False,
    }
    return crsp, coverage


def _portfolio_returns(panel: pd.DataFrame, column: str, bucket: int) -> dict[str, np.ndarray]:
    subset = panel.loc[panel[column] == bucket, ["ym", "regime", "ret"]]
    grouped = subset.groupby("ym", observed=True)
    counts = grouped["ret"].size()
    means = grouped["ret"].mean()
    regime = grouped["regime"].first()
    keep = counts >= MIN_NAMES
    out = {}
    for name in ("high", "low"):
        mask = keep & (regime == name)
        out[name] = means.loc[mask].to_numpy(dtype=float)
    return out


def _firm_rows(panel: pd.DataFrame) -> pd.DataFrame:
    usable = panel.dropna(subset=["ret", "regime"])
    grouped = usable.groupby(["permno", "regime"], observed=True)["ret"]
    records = []
    for (permno, regime), returns in grouped:
        values = returns.to_numpy(dtype=float)
        if values.size < MIN_FIRM_MONTHS:
            continue
        losses = -values
        threshold = float(np.quantile(losses, problems.CVAR_ALPHA))
        tail = losses[losses >= threshold]
        legacy = problems.legacy_cvar(losses, problems.CVAR_ALPHA, n_qubits=5)
        records.append(
            {
                "permno": int(permno),
                "regime": str(regime),
                "months": int(values.size),
                "sample_cvar": float(tail.mean()) if tail.size else threshold,
                "histogram_cvar": legacy.returned_cvar,
            }
        )
    firms = pd.DataFrame.from_records(records)
    if firms.empty:
        return firms
    size = (
        panel.dropna(subset=["size_q"])
        .groupby("permno")["size_q"]
        .agg(lambda values: int(np.bincount(values.astype(int), minlength=6).argmax()))
    )
    firms["size_q"] = firms["permno"].map(size)
    return firms


def _firm_summary(firms: pd.DataFrame) -> dict:
    def pack(frame: pd.DataFrame) -> dict:
        gap = frame["histogram_cvar"] - frame["sample_cvar"]
        return {
            "firms": int(len(frame)),
            "median_sample_cvar": float(frame["sample_cvar"].median()),
            "p10_sample_cvar": float(frame["sample_cvar"].quantile(0.10)),
            "p90_sample_cvar": float(frame["sample_cvar"].quantile(0.90)),
            "median_histogram_minus_sample": float(gap.median()),
        }

    by_regime = {name: pack(firms.loc[firms["regime"] == name]) for name in ("high", "low")}
    by_size = []
    for regime in ("high", "low"):
        for quintile in range(1, 6):
            frame = firms.loc[(firms["regime"] == regime) & (firms["size_q"] == quintile)]
            if frame.empty:
                continue
            row = pack(frame)
            row["regime"] = regime
            row["size_q"] = quintile
            by_size.append(row)
    return {"min_months": MIN_FIRM_MONTHS, "by_regime": by_regime, "by_size_quintile": by_size}


def _firm_ae(firms_source: pd.DataFrame, limit: int | None) -> dict:
    usable = firms_source.dropna(subset=["ret", "regime"])
    grouped = list(usable.groupby(["permno", "regime"], observed=True)["ret"])
    chosen = [(key, returns) for key, returns in grouped if len(returns) >= MIN_FIRM_MONTHS]
    if limit is not None:
        chosen = chosen[:limit]
    inside = 0
    bars = []
    for _, returns in chosen:
        losses = -returns.to_numpy(dtype=float)
        legacy = problems.legacy_cvar(losses, problems.CVAR_ALPHA, n_qubits=5)
        excess = np.maximum(legacy.centers - legacy.value_at_risk, 0.0)
        if float(excess.max()) <= 0.0:
            continue
        state, _, excess_max = problems.encode_nonnegative(legacy.masses, excess)
        result = estimation_at(state, excess_max)
        inside += int(result["median_inside"])
        bars.append(result["propagated_bar"])
    return {
        "phase_bits": 8,
        "firms_estimated": len(bars),
        "fraction_median_inside_bar": float(inside / len(bars)) if bars else None,
        "median_propagated_bar": float(np.median(bars)) if bars else None,
    }


def estimation_at(state: np.ndarray, excess_max: float) -> dict:
    import estimation

    result = estimation.estimate(state, phase_bits=8, seed=0)
    factor = excess_max / (1.0 - problems.CVAR_ALPHA)
    return {
        "median_inside": bool(result.median_inside),
        "propagated_bar": float(factor * result.bound),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--firm-ae", action="store_true")
    parser.add_argument("--firm-limit", type=int, default=None)
    args = parser.parse_args()

    print("building the CRSP-Compustat panel", flush=True)
    panel, coverage = load_panel()
    print(
        f"firm-months {coverage['firm_months']}  permnos {coverage['permnos']}  "
        f"{coverage['first_month']} to {coverage['last_month']}",
        flush=True,
    )

    portfolios = []
    for column, label in (("size_q", "size"), ("bm_q", "book-to-market")):
        for bucket in range(1, 6):
            series = _portfolio_returns(panel, column, bucket)
            for regime, returns in series.items():
                print(f"{label} q{bucket} {regime}  months={returns.size}", flush=True)
                block = _block(f"{label}_q{bucket}_{regime}", returns)
                block["portfolio_months"] = int(returns.size)
                portfolios.append(block)

    print("firm-level sample and histogram CVaR", flush=True)
    firms = _firm_rows(panel)
    summary = _firm_summary(firms)
    payload = {
        "machine": "local Mac",
        "alpha": problems.CVAR_ALPHA,
        "units": "decimal monthly return",
        "coverage": coverage,
        "portfolios": portfolios,
        "firms": summary,
    }
    if args.firm_ae:
        print("per-firm amplitude estimation", flush=True)
        payload["firm_amplitude_estimation"] = _firm_ae(panel, args.firm_limit)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    for block in portfolios:
        last = block["amplitude_estimation"][-1]
        print(
            f"{block['slice']:24}  n={block['portfolio_months']:4d}  "
            f"sample={block['sample_cvar']:.4f}  histogram={block['histogram_cvar']:.4f}  "
            f"t={last['t']} AE={last['cvar']:.4f}  bar={last['propagated_bar']:.4f}"
        )
    high = summary["by_regime"]["high"]
    low = summary["by_regime"]["low"]
    print(
        f"firms >= {MIN_FIRM_MONTHS} months  "
        f"high {high['firms']} median CVaR {high['median_sample_cvar']:.4f}  "
        f"low {low['firms']} median CVaR {low['median_sample_cvar']:.4f}"
    )
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
