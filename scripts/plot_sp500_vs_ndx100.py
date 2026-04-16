from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
OUTPUT = PROJECT_ROOT / "data" / "reports" / "plot_sp500_vs_ndx100_index.png"


def load_index(csv_name: str, symbol: str) -> pd.DataFrame:
    path = PROJECT_ROOT / "data" / "processed" / csv_name
    df = pd.read_csv(path, parse_dates=["date"])
    if "symbol" in df.columns:
        df = df[df["symbol"].astype(str).str.upper() == symbol.upper()]
    return df[["date", "adj_close"]].sort_values("date").reset_index(drop=True)


def main() -> None:
    sp500 = load_index("sp500_daily.csv", "SP500")
    ndx100 = load_index("ndx100_daily.csv", "NDX100")

    common_start = max(sp500["date"].min(), ndx100["date"].min())
    sp = sp500[sp500["date"] >= common_start].copy()
    nd = ndx100[ndx100["date"] >= common_start].copy()
    sp["normalized"] = sp["adj_close"] / sp["adj_close"].iloc[0]
    nd["normalized"] = nd["adj_close"] / nd["adj_close"].iloc[0]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(13, 10))

    axes[0].plot(sp["date"], sp["normalized"], label="SP500 Index", color="#1f77b4", linewidth=2.2)
    axes[0].plot(nd["date"], nd["normalized"], label="NDX100 Index", color="#d62728", linewidth=2.2)
    axes[0].set_title(f"SP500 Index vs NDX100 Index Since {common_start.date().isoformat()} (Normalized)")
    axes[0].set_ylabel("Growth of 1 Unit")
    axes[0].set_yscale("log")
    axes[0].grid(alpha=0.3)
    axes[0].legend()

    axes[1].plot(sp500["date"], sp500["adj_close"], label="SP500 Index", color="#1f77b4", linewidth=1.8)
    axes[1].plot(ndx100["date"], ndx100["adj_close"], label="NDX100 Index", color="#d62728", linewidth=1.8)
    axes[1].set_title("Raw Index Levels (Not Comparable in Absolute Level, Only for Context)")
    axes[1].set_ylabel("Index Level")
    axes[1].grid(alpha=0.3)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(OUTPUT, dpi=180, bbox_inches="tight")
    print(OUTPUT)


if __name__ == "__main__":
    main()
