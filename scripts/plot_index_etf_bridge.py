from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from dca_backtest.providers import YahooFinanceProvider


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
OUTPUT = PROJECT_ROOT / "data" / "reports" / "plot_index_etf_bridge.png"


def load_index(csv_name: str, symbol: str) -> pd.DataFrame:
    path = PROJECT_ROOT / "data" / "processed" / csv_name
    df = pd.read_csv(path, parse_dates=["date"])
    if "symbol" in df.columns:
        df = df[df["symbol"].astype(str).str.upper() == symbol.upper()]
    return df[["date", "adj_close"]].sort_values("date").reset_index(drop=True)


def load_etf(symbol: str, start_date: date) -> pd.DataFrame:
    provider = YahooFinanceProvider(cache_dir=PROJECT_ROOT / "data")
    df = provider.fetch_history(symbol, start_date, date(2026, 4, 15))
    return df.rename(columns={"trade_date": "date"})[["date", "adj_close"]].sort_values("date").reset_index(drop=True)


def normalize_from_start(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["normalized"] = out["adj_close"] / out["adj_close"].iloc[0]
    return out


def main() -> None:
    sp500 = normalize_from_start(load_index("sp500_daily.csv", "SP500"))
    ndx100 = normalize_from_start(load_index("ndx100_daily.csv", "NDX100"))
    spy = normalize_from_start(load_etf("SPY", date(1993, 1, 22)))
    voo = normalize_from_start(load_etf("VOO", date(2010, 9, 7)))
    qqq = normalize_from_start(load_etf("QQQ", date(1999, 3, 10)))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(13, 10), sharex=False)

    axes[0].plot(sp500["date"], sp500["normalized"], label="SP500 Index", color="#1f77b4", linewidth=2.2)
    axes[0].plot(spy["date"], spy["normalized"], label="SPY ETF", color="#2ca02c", linewidth=1.6)
    axes[0].plot(voo["date"], voo["normalized"], label="VOO ETF", color="#ff7f0e", linewidth=1.6)
    axes[0].set_title("S&P 500 Index History vs SPY / VOO ETF History")
    axes[0].set_ylabel("Normalized to 1.0 at each series start")
    axes[0].set_yscale("log")
    axes[0].grid(alpha=0.3)
    axes[0].legend()

    axes[1].plot(ndx100["date"], ndx100["normalized"], label="NDX100 Index", color="#d62728", linewidth=2.2)
    axes[1].plot(qqq["date"], qqq["normalized"], label="QQQ ETF", color="#9467bd", linewidth=1.8)
    axes[1].set_title("Nasdaq-100 Index History vs QQQ ETF History")
    axes[1].set_ylabel("Normalized to 1.0 at each series start")
    axes[1].set_yscale("log")
    axes[1].grid(alpha=0.3)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(OUTPUT, dpi=180, bbox_inches="tight")
    print(OUTPUT)


if __name__ == "__main__":
    main()
