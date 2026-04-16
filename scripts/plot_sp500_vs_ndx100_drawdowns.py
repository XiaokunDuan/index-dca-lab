from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
OUTPUT = PROJECT_ROOT / "data" / "reports" / "plot_sp500_vs_ndx100_drawdowns.png"


def load_series(csv_name: str, symbol: str) -> pd.DataFrame:
    path = PROJECT_ROOT / "data" / "processed" / csv_name
    df = pd.read_csv(path, parse_dates=["date"])
    df = df[df["symbol"].astype(str).str.upper() == symbol.upper()].copy()
    df = df.sort_values("date").reset_index(drop=True)
    return df[["date", "adj_close"]]


def add_drawdown(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["peak"] = out["adj_close"].cummax()
    out["drawdown"] = out["adj_close"] / out["peak"] - 1.0
    return out


def main() -> None:
    sp500 = add_drawdown(load_series("sp500_daily.csv", "SP500"))
    ndx100 = add_drawdown(load_series("ndx100_daily.csv", "NDX100"))

    common_start = max(sp500["date"].min(), ndx100["date"].min())
    sp = sp500[sp500["date"] >= common_start].copy()
    nd = ndx100[ndx100["date"] >= common_start].copy()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(13, 10), sharex=False)

    axes[0].plot(sp["date"], sp["drawdown"] * 100, label="SP500", color="#1f77b4", linewidth=2.0)
    axes[0].plot(nd["date"], nd["drawdown"] * 100, label="NDX100", color="#d62728", linewidth=2.0)
    axes[0].set_title(f"Historical Drawdowns Since {common_start.date().isoformat()}")
    axes[0].set_ylabel("Drawdown (%)")
    axes[0].grid(alpha=0.3)
    axes[0].legend()

    axes[1].plot(sp500["date"], sp500["drawdown"] * 100, label="SP500 full history", color="#1f77b4", linewidth=1.8)
    axes[1].plot(ndx100["date"], ndx100["drawdown"] * 100, label="NDX100 full history", color="#d62728", linewidth=1.8)
    axes[1].set_title("Full Available History Drawdowns")
    axes[1].set_xlabel("Date")
    axes[1].set_ylabel("Drawdown (%)")
    axes[1].grid(alpha=0.3)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(OUTPUT, dpi=180, bbox_inches="tight")
    print(OUTPUT)


if __name__ == "__main__":
    main()
