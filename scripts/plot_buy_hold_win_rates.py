from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
DATA_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"
STATS_CSV = REPORTS_DIR / "buy_hold_window_stats.csv"
WINDOWS_CSV = REPORTS_DIR / "buy_hold_windows.csv"
PLOT_POSITIVE = REPORTS_DIR / "plot_buy_hold_positive_rate.png"
PLOT_CAGR = REPORTS_DIR / "plot_buy_hold_cagr_summary.png"
PLOT_HOLDING = REPORTS_DIR / "plot_buy_hold_holding_periods.png"

HORIZONS_BY_SYMBOL: dict[str, list[int]] = {
    "SP500": [1, 3, 5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90],
    "NDX100": [1, 3, 5, 10, 15, 20, 25, 30, 35, 40],
}

COLORS = {
    "SP500": "#1f77b4",
    "NDX100": "#d62728",
}


def load_index(csv_name: str, symbol: str) -> pd.DataFrame:
    path = DATA_DIR / csv_name
    df = pd.read_csv(path, parse_dates=["date"])
    if "symbol" in df.columns:
        df = df[df["symbol"].astype(str).str.upper() == symbol.upper()]
    return df[["date", "adj_close"]].sort_values("date").reset_index(drop=True)


def build_windows(df: pd.DataFrame, symbol: str, horizons: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    dates = df["date"]
    prices = df["adj_close"]

    for years in horizons:
        for i, start_date in enumerate(dates):
            end_target = start_date + pd.DateOffset(years=years)
            end_idx = dates.searchsorted(end_target, side="left")
            if end_idx >= len(df):
                break
            start_price = float(prices.iloc[i])
            end_price = float(prices.iloc[end_idx])
            total_return = end_price / start_price - 1.0
            cagr = (end_price / start_price) ** (1.0 / years) - 1.0
            rows.append(
                {
                    "symbol": symbol,
                    "start_date": start_date,
                    "end_date": dates.iloc[end_idx],
                    "years": years,
                    "start_price": start_price,
                    "end_price": end_price,
                    "total_return_pct": total_return,
                    "cagr": cagr,
                }
            )

    windows = pd.DataFrame(rows)
    stats = (
        windows.groupby(["symbol", "years"], as_index=False)
        .agg(
            window_count=("total_return_pct", "size"),
            positive_rate=("total_return_pct", lambda s: float((s > 0).mean())),
            median_total_return=("total_return_pct", "median"),
            worst_total_return=("total_return_pct", "min"),
            best_total_return=("total_return_pct", "max"),
            median_cagr=("cagr", "median"),
            worst_cagr=("cagr", "min"),
            best_cagr=("cagr", "max"),
        )
        .sort_values(["symbol", "years"])
    )
    return windows, stats


def plot_positive_rate(stats: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    for symbol in ["SP500", "NDX100"]:
        series = stats[stats["symbol"] == symbol]
        ax.plot(
            series["years"],
            series["positive_rate"] * 100,
            marker="o",
            linewidth=2.2,
            color=COLORS[symbol],
            label=symbol,
        )
    ax.set_title("Buy-and-Hold Positive Return Rate by Holding Period")
    ax.set_xlabel("Holding Years")
    ax.set_ylabel("Positive Windows (%)")
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOT_POSITIVE, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_cagr_summary(stats: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, symbol in zip(axes, ["SP500", "NDX100"]):
        series = stats[stats["symbol"] == symbol]
        ax.plot(series["years"], series["median_cagr"] * 100, marker="o", linewidth=2.2, color=COLORS[symbol], label="Median CAGR")
        ax.plot(series["years"], series["worst_cagr"] * 100, linestyle="--", linewidth=2.0, color=COLORS[symbol], alpha=0.75, label="Worst CAGR")
        ax.fill_between(series["years"], series["worst_cagr"] * 100, series["best_cagr"] * 100, color=COLORS[symbol], alpha=0.08)
        ax.set_title(f"{symbol} Rolling Buy-and-Hold CAGR")
        ax.set_xlabel("Holding Years")
        ax.set_ylabel("CAGR (%)")
        ax.grid(alpha=0.3)
        ax.legend()
    fig.tight_layout()
    fig.savefig(PLOT_CAGR, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_holding_periods(stats: pd.DataFrame) -> None:
    sp = stats[stats["symbol"] == "SP500"].set_index("years")
    nd = stats[stats["symbol"] == "NDX100"].set_index("years")
    common_years = sorted(set(sp.index).intersection(set(nd.index)))
    comp = pd.DataFrame(
        {
            "years": common_years,
            "SP500_positive_rate": [sp.loc[y, "positive_rate"] * 100 for y in common_years],
            "NDX100_positive_rate": [nd.loc[y, "positive_rate"] * 100 for y in common_years],
            "SP500_median_cagr": [sp.loc[y, "median_cagr"] * 100 for y in common_years],
            "NDX100_median_cagr": [nd.loc[y, "median_cagr"] * 100 for y in common_years],
        }
    )

    fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    axes[0].plot(comp["years"], comp["SP500_positive_rate"], marker="o", linewidth=2.2, color=COLORS["SP500"], label="SP500")
    axes[0].plot(comp["years"], comp["NDX100_positive_rate"], marker="o", linewidth=2.2, color=COLORS["NDX100"], label="NDX100")
    axes[0].set_title("Positive Return Rate at Shared Holding Periods")
    axes[0].set_ylabel("Positive Windows (%)")
    axes[0].set_ylim(0, 105)
    axes[0].grid(alpha=0.3)
    axes[0].legend()

    axes[1].plot(comp["years"], comp["SP500_median_cagr"], marker="o", linewidth=2.2, color=COLORS["SP500"], label="SP500")
    axes[1].plot(comp["years"], comp["NDX100_median_cagr"], marker="o", linewidth=2.2, color=COLORS["NDX100"], label="NDX100")
    axes[1].set_title("Median Rolling Buy-and-Hold CAGR at Shared Holding Periods")
    axes[1].set_xlabel("Holding Years")
    axes[1].set_ylabel("Median CAGR (%)")
    axes[1].grid(alpha=0.3)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(PLOT_HOLDING, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    datasets = {
        "SP500": load_index("sp500_daily.csv", "SP500"),
        "NDX100": load_index("ndx100_daily.csv", "NDX100"),
    }

    all_windows: list[pd.DataFrame] = []
    all_stats: list[pd.DataFrame] = []
    for symbol, df in datasets.items():
        windows, stats = build_windows(df, symbol, HORIZONS_BY_SYMBOL[symbol])
        all_windows.append(windows)
        all_stats.append(stats)

    windows_frame = pd.concat(all_windows, ignore_index=True)
    stats_frame = pd.concat(all_stats, ignore_index=True)

    windows_frame.to_csv(WINDOWS_CSV, index=False)
    stats_frame.to_csv(STATS_CSV, index=False)

    plot_positive_rate(stats_frame)
    plot_cagr_summary(stats_frame)
    plot_holding_periods(stats_frame)

    print(WINDOWS_CSV)
    print(STATS_CSV)
    print(PLOT_POSITIVE)
    print(PLOT_CAGR)
    print(PLOT_HOLDING)


if __name__ == "__main__":
    main()
