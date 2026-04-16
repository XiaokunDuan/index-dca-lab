from __future__ import annotations

from io import StringIO
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
DATA_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"

CPI_CSV = DATA_DIR / "cpi_aucsl.csv"
STATS_CSV = REPORTS_DIR / "real_buy_hold_window_stats.csv"
WINDOWS_CSV = REPORTS_DIR / "real_buy_hold_windows.csv"
PLOT_POSITIVE = REPORTS_DIR / "plot_real_buy_hold_positive_rate.png"
PLOT_CAGR = REPORTS_DIR / "plot_real_buy_hold_cagr_summary.png"
PLOT_GROWTH = REPORTS_DIR / "plot_real_vs_nominal_index_growth.png"

HORIZONS_BY_SYMBOL = {
    "SP500": [1, 3, 5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90],
    "NDX100": [1, 3, 5, 10, 15, 20, 25, 30, 35, 40],
}
COLORS = {"SP500": "#1f77b4", "NDX100": "#d62728"}
FRED_CPI_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL"


def ensure_cpi() -> pd.DataFrame:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CPI_CSV.exists():
        response = requests.get(FRED_CPI_URL, timeout=30)
        response.raise_for_status()
        CPI_CSV.write_text(response.text, encoding="utf-8")
    raw = pd.read_csv(CPI_CSV)
    if "DATE" in raw.columns:
        raw = raw.rename(columns={"DATE": "date"})
    elif "observation_date" in raw.columns:
        raw = raw.rename(columns={"observation_date": "date"})
    cpi = raw.rename(columns={"CPIAUCSL": "cpi"})
    cpi["date"] = pd.to_datetime(cpi["date"])
    cpi["cpi"] = pd.to_numeric(cpi["cpi"], errors="coerce")
    cpi = cpi.dropna(subset=["cpi"]).sort_values("date").reset_index(drop=True)
    return cpi


def load_index(csv_name: str, symbol: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / csv_name, parse_dates=["date"])
    if "symbol" in df.columns:
        df = df[df["symbol"].astype(str).str.upper() == symbol.upper()]
    return df[["date", "adj_close"]].sort_values("date").reset_index(drop=True)


def attach_real_prices(df: pd.DataFrame, cpi: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame["month"] = frame["date"].dt.to_period("M").dt.to_timestamp()
    merged = frame.merge(cpi.rename(columns={"date": "month"}), on="month", how="left")
    merged["cpi"] = merged["cpi"].ffill()
    latest_cpi = float(cpi["cpi"].iloc[-1])
    merged["real_adj_close"] = merged["adj_close"] * latest_cpi / merged["cpi"]
    return merged[["date", "adj_close", "real_adj_close"]]


def build_windows(df: pd.DataFrame, symbol: str, horizons: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    dates = df["date"]
    nominal = df["adj_close"]
    real = df["real_adj_close"]

    for years in horizons:
        for i, start_date in enumerate(dates):
            end_target = start_date + pd.DateOffset(years=years)
            end_idx = dates.searchsorted(end_target, side="left")
            if end_idx >= len(df):
                break

            nominal_return = float(nominal.iloc[end_idx] / nominal.iloc[i] - 1.0)
            real_return = float(real.iloc[end_idx] / real.iloc[i] - 1.0)
            nominal_cagr = float((nominal.iloc[end_idx] / nominal.iloc[i]) ** (1.0 / years) - 1.0)
            real_cagr = float((real.iloc[end_idx] / real.iloc[i]) ** (1.0 / years) - 1.0)
            rows.append(
                {
                    "symbol": symbol,
                    "years": years,
                    "start_date": start_date.date().isoformat(),
                    "end_date": dates.iloc[end_idx].date().isoformat(),
                    "nominal_total_return_pct": nominal_return,
                    "real_total_return_pct": real_return,
                    "nominal_cagr": nominal_cagr,
                    "real_cagr": real_cagr,
                }
            )

    windows = pd.DataFrame(rows)
    stats = (
        windows.groupby(["symbol", "years"], as_index=False)
        .agg(
            samples=("real_cagr", "size"),
            nominal_positive_rate=("nominal_total_return_pct", lambda s: float((s > 0).mean())),
            real_positive_rate=("real_total_return_pct", lambda s: float((s > 0).mean())),
            nominal_median_cagr=("nominal_cagr", "median"),
            real_median_cagr=("real_cagr", "median"),
            real_worst_cagr=("real_cagr", "min"),
            real_best_cagr=("real_cagr", "max"),
        )
        .sort_values(["symbol", "years"])
    )
    return windows, stats


def plot_positive_rate(stats: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, symbol in zip(axes, ["SP500", "NDX100"]):
        sub = stats[stats["symbol"] == symbol]
        ax.plot(sub["years"], sub["nominal_positive_rate"] * 100, marker="o", linewidth=2.0, color=COLORS[symbol], label="Nominal")
        ax.plot(sub["years"], sub["real_positive_rate"] * 100, marker="o", linewidth=2.0, linestyle="--", color=COLORS[symbol], alpha=0.75, label="Real")
        ax.set_title(f"{symbol}: Nominal vs Real Positive Rate")
        ax.set_xlabel("Holding Years")
        ax.set_ylabel("Positive Windows (%)")
        ax.set_ylim(0, 105)
        ax.grid(alpha=0.3)
        ax.legend()
    fig.tight_layout()
    fig.savefig(PLOT_POSITIVE, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_cagr(stats: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, symbol in zip(axes, ["SP500", "NDX100"]):
        sub = stats[stats["symbol"] == symbol]
        ax.plot(sub["years"], sub["nominal_median_cagr"] * 100, marker="o", linewidth=2.0, color=COLORS[symbol], label="Nominal median CAGR")
        ax.plot(sub["years"], sub["real_median_cagr"] * 100, marker="o", linewidth=2.0, linestyle="--", color=COLORS[symbol], alpha=0.75, label="Real median CAGR")
        ax.fill_between(sub["years"], sub["real_worst_cagr"] * 100, sub["real_best_cagr"] * 100, color=COLORS[symbol], alpha=0.08)
        ax.set_title(f"{symbol}: Nominal vs Real CAGR")
        ax.set_xlabel("Holding Years")
        ax.set_ylabel("Median CAGR (%)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(PLOT_CAGR, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_growth(sp500: pd.DataFrame, ndx100: pd.DataFrame) -> None:
    common_start = max(sp500["date"].min(), ndx100["date"].min())
    sp = sp500[sp500["date"] >= common_start].copy()
    nd = ndx100[ndx100["date"] >= common_start].copy()
    sp["nominal_norm"] = sp["adj_close"] / sp["adj_close"].iloc[0]
    sp["real_norm"] = sp["real_adj_close"] / sp["real_adj_close"].iloc[0]
    nd["nominal_norm"] = nd["adj_close"] / nd["adj_close"].iloc[0]
    nd["real_norm"] = nd["real_adj_close"] / nd["real_adj_close"].iloc[0]

    fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    axes[0].plot(sp["date"], sp["nominal_norm"], color="#1f77b4", linewidth=2.0, label="SP500 nominal")
    axes[0].plot(sp["date"], sp["real_norm"], color="#1f77b4", linewidth=2.0, linestyle="--", label="SP500 real")
    axes[0].set_title("SP500: Nominal vs Real Growth Since Common Start")
    axes[0].set_ylabel("Growth of 1 unit")
    axes[0].set_yscale("log")
    axes[0].grid(alpha=0.3)
    axes[0].legend()

    axes[1].plot(nd["date"], nd["nominal_norm"], color="#d62728", linewidth=2.0, label="NDX100 nominal")
    axes[1].plot(nd["date"], nd["real_norm"], color="#d62728", linewidth=2.0, linestyle="--", label="NDX100 real")
    axes[1].set_title("NDX100: Nominal vs Real Growth Since Common Start")
    axes[1].set_ylabel("Growth of 1 unit")
    axes[1].set_yscale("log")
    axes[1].grid(alpha=0.3)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(PLOT_GROWTH, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    cpi = ensure_cpi()
    cpi_start = pd.Timestamp(cpi["date"].min())
    sp500 = attach_real_prices(load_index("sp500_daily.csv", "SP500"), cpi)
    ndx100 = attach_real_prices(load_index("ndx100_daily.csv", "NDX100"), cpi)
    sp500 = sp500[sp500["date"] >= cpi_start].reset_index(drop=True)
    ndx100 = ndx100[ndx100["date"] >= cpi_start].reset_index(drop=True)

    all_windows = []
    all_stats = []
    for symbol, df in [("SP500", sp500), ("NDX100", ndx100)]:
        windows, stats = build_windows(df, symbol, HORIZONS_BY_SYMBOL[symbol])
        all_windows.append(windows)
        all_stats.append(stats)

    windows_frame = pd.concat(all_windows, ignore_index=True)
    stats_frame = pd.concat(all_stats, ignore_index=True)
    windows_frame.to_csv(WINDOWS_CSV, index=False)
    stats_frame.to_csv(STATS_CSV, index=False)

    plot_positive_rate(stats_frame)
    plot_cagr(stats_frame)
    plot_growth(sp500, ndx100)

    print(CPI_CSV)
    print(WINDOWS_CSV)
    print(STATS_CSV)
    print(PLOT_POSITIVE)
    print(PLOT_CAGR)
    print(PLOT_GROWTH)


if __name__ == "__main__":
    main()
