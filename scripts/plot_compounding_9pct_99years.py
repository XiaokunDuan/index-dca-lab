from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
OUTPUT = PROJECT_ROOT / "data" / "reports" / "plot_compounding_9pct_99years.png"


def main() -> None:
    years = list(range(1, 100))
    multiples = [(1.09) ** year for year in years]
    frame = pd.DataFrame({"year": years, "multiple": multiples})

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=True)

    axes[0].plot(frame["year"], frame["multiple"], color="#1f77b4", linewidth=2.2)
    axes[0].set_title("Compounding at 9% Annual Return for 99 Years")
    axes[0].set_ylabel("Growth Multiple")
    axes[0].grid(alpha=0.3)

    axes[1].plot(frame["year"], frame["multiple"], color="#d62728", linewidth=2.2)
    axes[1].set_title("Same Curve on Log Scale")
    axes[1].set_xlabel("Years")
    axes[1].set_ylabel("Growth Multiple (log scale)")
    axes[1].set_yscale("log")
    axes[1].grid(alpha=0.3)

    for marker_year in [10, 20, 30, 50, 70, 99]:
        value = (1.09) ** marker_year
        axes[0].scatter(marker_year, value, color="black", s=20)
        axes[0].annotate(f"{marker_year}y\\n{value:.1f}x", (marker_year, value), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=8)
        axes[1].scatter(marker_year, value, color="black", s=20)

    fig.tight_layout()
    fig.savefig(OUTPUT, dpi=180, bbox_inches="tight")
    print(OUTPUT)


if __name__ == "__main__":
    main()
