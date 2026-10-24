"""Plot saved portfolio sample CVaR; no data generation or data writes.

Run: /opt/miniconda3/bin/python3 plot_panel.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent


def main() -> None:
    data = json.loads((ROOT / "data" / "panel_cvar.json").read_text())
    rows = {row["slice"]: row for row in data["portfolios"]}
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.5), sharey=True)
    figure.suptitle("CRSP portfolio sample 95% CVaR by volatility regime")
    quintiles = range(1, 6)
    for ax, sort, title in zip(
        axes, ("size", "book-to-market"), ("Size quintiles", "Book-to-market quintiles")
    ):
        for regime, label, style, color in (
            ("high", "High volatility", "o-", "C3"),
            ("low", "Low volatility", "s--", "C0"),
        ):
            values = [100 * rows[f"{sort}_q{q}_{regime}"]["sample_cvar"] for q in quintiles]
            ax.plot(quintiles, values, style, color=color, label=label)
        ax.set_title(title)
        ax.set_xlabel("NYSE-breakpoint quintile (1 = lowest, 5 = highest)")
        ax.set_xticks(list(quintiles))
        ax.set_ylabel("Sample 95% CVaR (% monthly loss)")
        ax.grid(axis="y", linewidth=0.4, color="0.8")
        ax.legend(frameon=False)
    axes[0].set_ylim(0, 110 * max(row["sample_cvar"] for row in rows.values()))
    figure.text(
        0.5, 0.02,
        "Source: data/panel_cvar.json, 1973-07–2024-12; figure 2026-10-23; equal-weighted portfolios, loss = −return; no population error bars.",
        ha="center", fontsize=8,
    )
    figure.tight_layout(rect=(0, 0.08, 1, 0.94))
    output = ROOT / "figures" / "panel_cvar.png"
    output.parent.mkdir(exist_ok=True)
    figure.savefig(output, dpi=160)
    plt.close(figure)
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
