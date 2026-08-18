
from pathlib import Path

import pandas as pd

WINDOW = 12

BURN_IN = 120

Q = 0.70

OUT = Path("data/factors/regimes.parquet")

def load_mktrf() -> pd.Series:

    ff = pd.read_parquet("data/pulls/ff3_monthly_wrds.parquet")

    ff["date"] = pd.to_datetime(ff["date"])

    s = ff.set_index("date")["mktrf"].sort_index()

    s.index = s.index.to_period("M").to_timestamp("M")

    s = s[s.index >= "1963-07-31"]   # align with test-asset sample
    return s.rename("mktrf")



def label(mktrf: pd.Series) -> pd.DataFrame:

    df = pd.DataFrame({"mktrf": mktrf})



    df["rv"] = df["mktrf"].rolling(WINDOW, min_periods=WINDOW).std()



    df["threshold"] = df["rv"].expanding(min_periods=BURN_IN).quantile(Q)



    df["regime"] = (df["rv"] > df["threshold"]).map({True: "high", False: "low"})



    df.loc[df.index[:BURN_IN], "regime"] = pd.NA

    return df

if __name__ == "__main__":

    df = label(load_mktrf())

    lab = df.dropna(subset=["regime"])

    print(f"labeled months: {len(lab)}  high={(lab.regime=='high').sum()}  low={(lab.regime=='low').sum()}")

    print("\nTop 20 realized-vol months:")

    print(df["rv"].nlargest(20).to_string())

    print("\nRegime counts by decade:")

    dec = lab.groupby([lab.index.year // 10 * 10, "regime"]).size().unstack(fill_value=0)

    dec["pct_high"] = (dec["high"] / dec.sum(axis=1)).round(2)

    print(dec)

    OUT.parent.mkdir(parents=True, exist_ok=True)

    df.to_parquet(OUT)

