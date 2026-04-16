from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
OUTPUT = PROJECT_ROOT / "data" / "reports" / "plot_compounding_8_9_10_comparison.png"


def main() -> None:
    years = list(range(0, 100))
    rates = {
        "8%": 1.08,
        "9%": 1.09,
        "10%": 1.10,
    }
    colors = {
        "8%": "#1f77b4",
        "9%": "#d62728",
        "10%": "#2ca02c",
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(13, 10), sharex=True)

    marker_years = [10, 20, 30, 40, 50, 70, 99]
    label_offsets = {
        "8%": (0, -16),
        "9%": (0, 8),
        "10%": (0, 16),
    }

    for label, growth in rates.items():
        frame = pd.DataFrame(
            {
                "year": years,
                "multiple": [growth**year for year in years],
            }
        )
        color = colors[label]
        axes[0].plot(frame["year"], frame["multiple"], label=f"{label} annual return", color=color, linewidth=2.4)
        axes[1].plot(frame["year"], frame["multiple"], label=f"{label} annual return", color=color, linewidth=2.4)

        for marker_year in marker_years:
            value = growth**marker_year
            axes[0].scatter(marker_year, value, color=color, s=26)
            dx, dy = label_offsets[label]
            axes[0].annotate(
                f"{value:.1f}x",
                (marker_year, value),
                textcoords="offset points",
                xytext=(dx, dy),
                ha="center",
                fontsize=8,
                color=color,
                weight="bold",
            )
            axes[1].scatter(marker_year, value, color=color, s=26)

    axes[0].set_title("How 1% Changes Long-Term Wealth: 8% vs 9% vs 10% for 99 Years")
    axes[0].set_ylabel("Multiple of Initial Principal")
    axes[0].grid(alpha=0.3)
    axes[0].legend()

    axes[1].set_title("Same Curves on Log Scale")
    axes[1].set_xlabel("Years")
    axes[1].set_ylabel("Multiple of Initial Principal (log scale)")
    axes[1].set_yscale("log")
    axes[1].grid(alpha=0.3)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(OUTPUT, dpi=180, bbox_inches="tight")
    print(OUTPUT)


if __name__ == "__main__":
    main()
