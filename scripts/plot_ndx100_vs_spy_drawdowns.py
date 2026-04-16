from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
OUTPUT = PROJECT_ROOT / "data" / "reports" / "plot_ndx100_vs_spy_drawdowns.png"


def load_ndx100() -> pd.DataFrame:
    path = PROJECT_ROOT / "data" / "processed" / "ndx100_daily.csv"
    df = pd.read_csv(path, parse_dates=["date"])
    df = df[df["symbol"].astype(str).str.upper() == "NDX100"].copy()
    return df[["date", "adj_close"]].sort_values("date").reset_index(drop=True)


def load_spy() -> pd.DataFrame:
    path = PROJECT_ROOT / "data" / "SPY_1993-01-22_2026-04-15.csv"
    df = pd.read_csv(path, parse_dates=["trade_date"])
    df = df.rename(columns={"trade_date": "date"})
    return df[["date", "adj_close"]].sort_values("date").reset_index(drop=True)


def add_drawdown(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["peak"] = out["adj_close"].cummax()
    out["drawdown"] = out["adj_close"] / out["peak"] - 1.0
    return out


def main() -> None:
    ndx100 = add_drawdown(load_ndx100())
    spy = add_drawdown(load_spy())

    common_start = max(ndx100["date"].min(), spy["date"].min())
    nd = ndx100[ndx100["date"] >= common_start].copy()
    sp = spy[spy["date"] >= common_start].copy()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(13, 10), sharex=False)

    axes[0].plot(nd["date"], nd["drawdown"] * 100, label="NDX100 Index", color="#d62728", linewidth=2.0)
    axes[0].plot(sp["date"], sp["drawdown"] * 100, label="SPY ETF", color="#2ca02c", linewidth=2.0)
    axes[0].set_title(f"NDX100 Index vs SPY ETF Drawdowns Since {common_start.date().isoformat()}")
    axes[0].set_ylabel("Drawdown (%)")
    axes[0].grid(alpha=0.3)
    axes[0].legend()

    axes[1].plot(ndx100["date"], ndx100["drawdown"] * 100, label="NDX100 full history", color="#d62728", linewidth=1.8)
    axes[1].plot(spy["date"], spy["drawdown"] * 100, label="SPY full history", color="#2ca02c", linewidth=1.8)
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
