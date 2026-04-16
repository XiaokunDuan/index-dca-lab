from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
INPUT = PROJECT_ROOT / "data" / "processed" / "sp500_daily.csv"
OUTPUT = PROJECT_ROOT / "data" / "reports" / "plot_sp500_real_99y_growth.png"


def main() -> None:
    df = pd.read_csv(INPUT, parse_dates=["date"])
    df = df[df["symbol"].astype(str).str.upper() == "SP500"].copy()
    df = df.sort_values("date").reset_index(drop=True)

    start_price = float(df["adj_close"].iloc[0])
    df["multiple"] = df["adj_close"] / start_price

    marker_years = [1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 98]
    start_date = df["date"].iloc[0]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(13, 10), sharex=True)

    axes[0].plot(df["date"], df["multiple"], color="#1f77b4", linewidth=2.0)
    axes[0].set_title("SP500 Real 99-Year History: Growth Multiple of Initial Principal")
    axes[0].set_ylabel("Multiple of Initial Principal")
    axes[0].grid(alpha=0.3)

    axes[1].plot(df["date"], df["multiple"], color="#d62728", linewidth=2.0)
    axes[1].set_title("Same SP500 Growth Path on Log Scale")
    axes[1].set_xlabel("Date")
    axes[1].set_ylabel("Multiple of Initial Principal (log scale)")
    axes[1].set_yscale("log")
    axes[1].grid(alpha=0.3)

    for years in marker_years:
        target_date = start_date + pd.DateOffset(years=years)
        eligible = df[df["date"] >= target_date]
        if eligible.empty:
            continue
        row = eligible.iloc[0]
        x = row["date"]
        y = float(row["multiple"])
        axes[0].scatter(x, y, color="black", s=22)
        axes[0].annotate(
            f"{years}y\n{y:.1f}x",
            (x, y),
            textcoords="offset points",
            xytext=(0, 7),
            ha="center",
            fontsize=8,
            weight="bold",
        )
        axes[1].scatter(x, y, color="black", s=22)

    final_row = df.iloc[-1]
    axes[0].scatter(final_row["date"], final_row["multiple"], color="#2ca02c", s=28)
    axes[0].annotate(
        f"End\n{float(final_row['multiple']):.1f}x",
        (final_row["date"], float(final_row["multiple"])),
        textcoords="offset points",
        xytext=(-18, -18),
        ha="right",
        fontsize=9,
        color="#2ca02c",
        weight="bold",
    )
    axes[1].scatter(final_row["date"], float(final_row["multiple"]), color="#2ca02c", s=28)

    fig.tight_layout()
    fig.savefig(OUTPUT, dpi=180, bbox_inches="tight")
    print(OUTPUT)


if __name__ == "__main__":
    main()
