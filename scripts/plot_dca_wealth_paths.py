from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
DATA_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"

CONTRIBUTION = 1000.0
SUMMARY_CSV = REPORTS_DIR / "dca_wealth_path_summary.csv"
PLOT_SP500 = REPORTS_DIR / "plot_sp500_dca_wealth_path.png"
PLOT_NDX100 = REPORTS_DIR / "plot_ndx100_dca_wealth_path.png"


def load_index(csv_name: str, symbol: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / csv_name, parse_dates=["date"])
    if "symbol" in df.columns:
        df = df[df["symbol"].astype(str).str.upper() == symbol.upper()]
    return df[["date", "adj_close"]].sort_values("date").reset_index(drop=True)


def monthly_schedule(df: pd.DataFrame) -> pd.DataFrame:
    sampled = df.groupby(df["date"].dt.to_period("M")).first().reset_index(drop=True).copy()
    sampled["contribution"] = CONTRIBUTION
    sampled["shares_bought"] = sampled["contribution"] / sampled["adj_close"]
    sampled["shares"] = sampled["shares_bought"].cumsum()
    sampled["invested_capital"] = sampled["contribution"].cumsum()
    sampled["market_value"] = sampled["shares"] * sampled["adj_close"]
    sampled["unrealized_pnl"] = sampled["market_value"] - sampled["invested_capital"]
    sampled["wealth_multiple"] = sampled["market_value"] / sampled["invested_capital"]
    sampled["is_above_water"] = sampled["unrealized_pnl"] >= 0
    return sampled


def summarize_path(symbol: str, path: pd.DataFrame) -> dict[str, object]:
    breakeven_crossings = int(path["is_above_water"].astype(int).diff().fillna(0).eq(1).sum())
    first_breakeven = path.loc[path["market_value"] >= path["invested_capital"], "date"]
    first_double = path.loc[path["wealth_multiple"] >= 2.0, "date"]
    max_underwater = float(path["unrealized_pnl"].min())
    worst_row = path.loc[path["unrealized_pnl"].idxmin()]
    return {
        "symbol": symbol,
        "frequency": "monthly",
        "contribution_per_period": CONTRIBUTION,
        "start_date": path["date"].iloc[0].date().isoformat(),
        "end_date": path["date"].iloc[-1].date().isoformat(),
        "total_contribution": float(path["invested_capital"].iloc[-1]),
        "final_value": float(path["market_value"].iloc[-1]),
        "final_unrealized_pnl": float(path["unrealized_pnl"].iloc[-1]),
        "final_wealth_multiple": float(path["wealth_multiple"].iloc[-1]),
        "breakeven_crossings": breakeven_crossings,
        "first_breakeven_date": first_breakeven.iloc[0].date().isoformat() if not first_breakeven.empty else "",
        "first_double_date": first_double.iloc[0].date().isoformat() if not first_double.empty else "",
        "max_underwater": max_underwater,
        "max_underwater_date": pd.Timestamp(worst_row["date"]).date().isoformat(),
    }


def plot_path(symbol: str, path: pd.DataFrame, output_path: Path, color: str) -> None:
    summary = summarize_path(symbol, path)
    first_breakeven = pd.Timestamp(summary["first_breakeven_date"]) if summary["first_breakeven_date"] else None
    first_double = pd.Timestamp(summary["first_double_date"]) if summary["first_double_date"] else None
    worst_date = pd.Timestamp(summary["max_underwater_date"])

    fig, axes = plt.subplots(3, 1, figsize=(13, 12), sharex=True)

    axes[0].plot(path["date"], path["invested_capital"], color="#666666", linewidth=2.0, label="Cumulative invested")
    axes[0].plot(path["date"], path["market_value"], color=color, linewidth=2.2, label="Account value")
    axes[0].set_title(f"{symbol} Monthly DCA Wealth Path")
    axes[0].set_ylabel("USD")
    axes[0].grid(alpha=0.3)
    axes[0].legend()

    axes[1].fill_between(path["date"], path["unrealized_pnl"], 0, where=path["unrealized_pnl"] >= 0, color="#54a24b", alpha=0.35)
    axes[1].fill_between(path["date"], path["unrealized_pnl"], 0, where=path["unrealized_pnl"] < 0, color="#e45756", alpha=0.35)
    axes[1].plot(path["date"], path["unrealized_pnl"], color="#333333", linewidth=1.5)
    axes[1].axhline(0, color="#333333", linewidth=1.0, linestyle="--")
    axes[1].scatter([worst_date], [summary["max_underwater"]], color="#e45756", s=40, zorder=5)
    axes[1].annotate(
        f"Max underwater\n{worst_date.date().isoformat()}\n${summary['max_underwater']:,.0f}",
        xy=(worst_date, summary["max_underwater"]),
        xytext=(15, -35),
        textcoords="offset points",
        fontsize=9,
        arrowprops={"arrowstyle": "-", "color": "#555555"},
    )
    axes[1].set_ylabel("Unrealized P/L")
    axes[1].grid(alpha=0.3)

    axes[2].plot(path["date"], path["wealth_multiple"], color=color, linewidth=2.0, label="Wealth multiple")
    axes[2].axhline(1.0, color="#333333", linewidth=1.0, linestyle="--")
    axes[2].axhline(2.0, color="#999999", linewidth=1.0, linestyle=":")
    if first_breakeven is not None:
        axes[2].axvline(first_breakeven, color="#54a24b", linewidth=1.2, linestyle=":")
        axes[2].annotate(
            f"First breakeven\n{first_breakeven.date().isoformat()}",
            xy=(first_breakeven, 1.0),
            xytext=(10, 12),
            textcoords="offset points",
            fontsize=9,
            color="#2f7d32",
        )
    if first_double is not None:
        axes[2].axvline(first_double, color="#1f77b4", linewidth=1.2, linestyle=":")
        axes[2].annotate(
            f"First 2x\n{first_double.date().isoformat()}",
            xy=(first_double, 2.0),
            xytext=(10, -18),
            textcoords="offset points",
            fontsize=9,
            color="#1f77b4",
        )
    axes[2].set_ylabel("Value / Invested")
    axes[2].set_xlabel("Date")
    axes[2].grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    sp500 = monthly_schedule(load_index("sp500_daily.csv", "SP500"))
    ndx100 = monthly_schedule(load_index("ndx100_daily.csv", "NDX100"))

    summaries = [
        summarize_path("SP500", sp500),
        summarize_path("NDX100", ndx100),
    ]
    pd.DataFrame(summaries).to_csv(SUMMARY_CSV, index=False)

    plot_path("SP500", sp500, PLOT_SP500, "#1f77b4")
    plot_path("NDX100", ndx100, PLOT_NDX100, "#d62728")

    print(SUMMARY_CSV)
    print(PLOT_SP500)
    print(PLOT_NDX100)


if __name__ == "__main__":
    main()
