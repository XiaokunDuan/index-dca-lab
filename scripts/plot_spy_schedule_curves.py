from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from dca_backtest.providers import YahooFinanceProvider


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
OUTPUT_DIR = PROJECT_ROOT / "data" / "reports"
WEEKLY_OUTPUT = OUTPUT_DIR / "plot_spy_weekly_weekday_curves.png"
MONTHLY_OUTPUT = OUTPUT_DIR / "plot_spy_monthly_trading_day_curves.png"


def build_portfolio_curve(history: pd.DataFrame, schedule: pd.Series, amount: float) -> pd.DataFrame:
    frame = history[["trade_date", "adj_close"]].copy().sort_values("trade_date").reset_index(drop=True)
    frame["trade_date"] = pd.to_datetime(frame["trade_date"])
    frame["buy_amount"] = 0.0
    frame.loc[schedule.values, "buy_amount"] = amount
    frame["shares_bought"] = frame["buy_amount"] / frame["adj_close"]
    frame["cum_shares"] = frame["shares_bought"].cumsum()
    frame["cum_contribution"] = frame["buy_amount"].cumsum()
    frame["market_value"] = frame["cum_shares"] * frame["adj_close"]
    frame["wealth_multiple"] = frame["market_value"] / frame["cum_contribution"].replace(0, np.nan)
    return frame


def weekly_schedule(frame: pd.DataFrame, weekday: int) -> pd.Series:
    return frame["trade_date"].dt.weekday.eq(weekday)


def monthly_schedule(frame: pd.DataFrame, monthly_anchor: int) -> pd.Series:
    rank = frame["trade_date"].groupby(frame["trade_date"].dt.to_period("M")).rank(method="first")
    return rank.eq(monthly_anchor)


def main() -> None:
    provider = YahooFinanceProvider(cache_dir=PROJECT_ROOT / "data")
    history = provider.fetch_history("SPY", date(1993, 1, 22), date(2026, 4, 15))
    history["trade_date"] = pd.to_datetime(history["trade_date"])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    weekday_names = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri"}
    weekly_curves: list[tuple[str, pd.DataFrame]] = []
    for wd in range(5):
        curve = build_portfolio_curve(history, weekly_schedule(history, wd), 1000.0)
        weekly_curves.append((weekday_names[wd], curve))

    fig, axes = plt.subplots(2, 1, figsize=(13, 10), sharex=True)
    for label, curve in weekly_curves:
        axes[0].plot(curve["trade_date"], curve["market_value"], label=f"{label}  end=${curve['market_value'].iloc[-1]:,.0f}", linewidth=1.8)
        axes[1].plot(curve["trade_date"], curve["wealth_multiple"], label=label, linewidth=1.6)
    axes[0].set_title("SPY Weekly DCA by Weekday")
    axes[0].set_ylabel("Portfolio Value (USD)")
    axes[0].set_yscale("log")
    axes[0].grid(alpha=0.3)
    axes[0].legend(fontsize=9, ncol=2)
    axes[1].set_title("SPY Weekly DCA Wealth Multiple by Weekday")
    axes[1].set_ylabel("Portfolio / Contributed Capital")
    axes[1].set_xlabel("Date")
    axes[1].grid(alpha=0.3)
    axes[1].legend(fontsize=9, ncol=3)
    fig.tight_layout()
    fig.savefig(WEEKLY_OUTPUT, dpi=180, bbox_inches="tight")
    plt.close(fig)

    monthly_curves: list[tuple[str, pd.DataFrame]] = []
    for anchor in range(1, 21):
        curve = build_portfolio_curve(history, monthly_schedule(history, anchor), 1000.0)
        if curve["buy_amount"].sum() == 0:
            continue
        monthly_curves.append((f"Day {anchor}", curve))

    fig, axes = plt.subplots(2, 1, figsize=(13, 10), sharex=True)
    cmap = plt.get_cmap("tab20")
    for idx, (label, curve) in enumerate(monthly_curves):
        color = cmap(idx % 20)
        axes[0].plot(curve["trade_date"], curve["market_value"], label=f"{label}", linewidth=1.2, color=color)
        axes[1].plot(curve["trade_date"], curve["wealth_multiple"], label=f"{label}", linewidth=1.2, color=color)
    axes[0].set_title("SPY Monthly DCA by Nth Trading Day of Month")
    axes[0].set_ylabel("Portfolio Value (USD)")
    axes[0].set_yscale("log")
    axes[0].grid(alpha=0.3)
    axes[0].legend(fontsize=7, ncol=4)
    axes[1].set_title("SPY Monthly DCA Wealth Multiple by Nth Trading Day")
    axes[1].set_ylabel("Portfolio / Contributed Capital")
    axes[1].set_xlabel("Date")
    axes[1].grid(alpha=0.3)
    axes[1].legend(fontsize=7, ncol=4)
    fig.tight_layout()
    fig.savefig(MONTHLY_OUTPUT, dpi=180, bbox_inches="tight")
    plt.close(fig)

    print(WEEKLY_OUTPUT)
    print(MONTHLY_OUTPUT)


if __name__ == "__main__":
    main()
