from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
OUTPUT = PROJECT_ROOT / "data" / "reports" / "plot_drawdown_recovery_math.png"


def main() -> None:
    drawdowns = [10, 20, 30, 40, 50, 60, 70, 80, 82.9, 90]
    recoveries = [1 / (1 - d / 100) - 1 for d in drawdowns]
    frame = pd.DataFrame(
        {
            "drawdown_pct": drawdowns,
            "required_gain_pct": [value * 100 for value in recoveries],
        }
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.plot(frame["drawdown_pct"], frame["required_gain_pct"], color="#d62728", linewidth=2.4, marker="o")
    ax.set_title("The Mathematics of Drawdowns: Recovery Gets Hard Fast")
    ax.set_xlabel("Drawdown (%)")
    ax.set_ylabel("Gain Needed to Break Even (%)")
    ax.grid(alpha=0.3)

    for _, row in frame.iterrows():
        x = row["drawdown_pct"]
        y = row["required_gain_pct"]
        ax.annotate(f"{y:.0f}%", (x, y), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8, weight="bold")

    fig.tight_layout()
    fig.savefig(OUTPUT, dpi=180, bbox_inches="tight")
    print(OUTPUT)


if __name__ == "__main__":
    main()
