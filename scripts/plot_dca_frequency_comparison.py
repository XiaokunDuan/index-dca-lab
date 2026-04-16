from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
DATA_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"

ANNUAL_BUDGET = 12_000.0
FREQUENCY_CONFIG = {
    "weekly": {"periods_per_year": 52.0, "color": "#4c78a8"},
    "monthly": {"periods_per_year": 12.0, "color": "#f58518"},
    "quarterly": {"periods_per_year": 4.0, "color": "#54a24b"},
    "yearly": {"periods_per_year": 1.0, "color": "#e45756"},
}
HORIZONS_BY_SYMBOL = {
    "SP500": [5, 10, 20, 30, 40, 50, 60, 70, 80, 90],
    "NDX100": [5, 10, 20, 30, 35, 40],
}

SUMMARY_CSV = REPORTS_DIR / "dca_frequency_summary.csv"
WINDOWS_CSV = REPORTS_DIR / "dca_frequency_windows.csv"
STATS_CSV = REPORTS_DIR / "dca_frequency_window_stats.csv"
PLOT_POSITIVE = REPORTS_DIR / "plot_dca_frequency_positive_rate.png"
PLOT_CAGR = REPORTS_DIR / "plot_dca_frequency_cagr.png"
PLOT_FULL = REPORTS_DIR / "plot_dca_frequency_full_period.png"


def load_index(csv_name: str, symbol: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / csv_name, parse_dates=["date"])
    if "symbol" in df.columns:
        df = df[df["symbol"].astype(str).str.upper() == symbol.upper()]
    return df[["date", "adj_close"]].sort_values("date").reset_index(drop=True)


def sample_schedule(frame: pd.DataFrame, frequency: str) -> pd.DataFrame:
    dates = pd.to_datetime(frame["date"])
    if frequency == "weekly":
        sampled = frame.groupby(dates.dt.to_period("W-MON")).first().reset_index(drop=True)
    elif frequency == "monthly":
        sampled = frame.groupby(dates.dt.to_period("M")).first().reset_index(drop=True)
    elif frequency == "quarterly":
        sampled = frame.groupby(dates.dt.to_period("Q")).first().reset_index(drop=True)
    elif frequency == "yearly":
        sampled = frame.groupby(dates.dt.to_period("Y")).first().reset_index(drop=True)
    else:
        raise ValueError(f"Unsupported frequency: {frequency}")
    return sampled[["date", "adj_close"]].copy()


def full_period_summary(symbol: str, sampled: pd.DataFrame, frequency: str) -> dict[str, object]:
    contribution = ANNUAL_BUDGET / FREQUENCY_CONFIG[frequency]["periods_per_year"]
    contrib = np.full(len(sampled), contribution, dtype=float)
    shares = contrib / sampled["adj_close"].to_numpy()
    total_contribution = float(contrib.sum())
    final_value = float(shares.cumsum()[-1] * sampled["adj_close"].iloc[-1])
    years = (sampled["date"].iloc[-1] - sampled["date"].iloc[0]).days / 365.25
    cagr_proxy = (final_value / total_contribution) ** (1 / years) - 1 if years > 0 else np.nan
    return {
        "symbol": symbol,
        "frequency": frequency,
        "annual_budget": ANNUAL_BUDGET,
        "contribution_per_period": contribution,
        "periods": len(sampled),
        "start_date": sampled["date"].iloc[0].date().isoformat(),
        "end_date": sampled["date"].iloc[-1].date().isoformat(),
        "total_contribution": total_contribution,
        "final_value": final_value,
        "total_return_pct": final_value / total_contribution - 1.0,
        "cagr_proxy": cagr_proxy,
    }


def rolling_windows(symbol: str, sampled: pd.DataFrame, frequency: str, years: int) -> list[dict[str, object]]:
    contribution = ANNUAL_BUDGET / FREQUENCY_CONFIG[frequency]["periods_per_year"]
    prices = sampled["adj_close"].to_numpy(dtype=float)
    dates = pd.to_datetime(sampled["date"]).reset_index(drop=True)
    shares = contribution / prices
    prefix = np.concatenate([[0.0], np.cumsum(shares)])
    rows: list[dict[str, object]] = []
    for i in range(len(sampled)):
        target_end = dates.iloc[i] + pd.DateOffset(years=years)
        eligible = dates[dates >= target_end]
        if eligible.empty:
            break
        j = int(eligible.index[0])
        total_contribution = contribution * (j - i + 1)
        final_value = float((prefix[j + 1] - prefix[i]) * prices[j])
        total_return_pct = final_value / total_contribution - 1.0
        elapsed_years = (dates.iloc[j] - dates.iloc[i]).days / 365.25
        cagr = (final_value / total_contribution) ** (1 / elapsed_years) - 1.0 if elapsed_years > 0 else np.nan
        rows.append(
            {
                "symbol": symbol,
                "frequency": frequency,
                "years": years,
                "start_date": dates.iloc[i].date().isoformat(),
                "end_date": dates.iloc[j].date().isoformat(),
                "total_contribution": total_contribution,
                "final_value": final_value,
                "total_return_pct": total_return_pct,
                "cagr": cagr,
            }
        )
    return rows


def plot_positive_rate(stats: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, symbol in zip(axes, ["SP500", "NDX100"]):
        sub = stats[stats["symbol"] == symbol].sort_values(["frequency", "years"])
        for frequency in FREQUENCY_CONFIG:
            s = sub[sub["frequency"] == frequency]
            ax.plot(
                s["years"],
                s["positive_rate"] * 100,
                marker="o",
                linewidth=2.0,
                color=FREQUENCY_CONFIG[frequency]["color"],
                label=frequency,
            )
        ax.set_title(f"{symbol}: Positive Return Rate by DCA Frequency")
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
        sub = stats[stats["symbol"] == symbol].sort_values(["frequency", "years"])
        for frequency in FREQUENCY_CONFIG:
            s = sub[sub["frequency"] == frequency]
            ax.plot(
                s["years"],
                s["median_cagr"] * 100,
                marker="o",
                linewidth=2.0,
                color=FREQUENCY_CONFIG[frequency]["color"],
                label=frequency,
            )
        ax.set_title(f"{symbol}: Median Rolling CAGR by DCA Frequency")
        ax.set_xlabel("Holding Years")
        ax.set_ylabel("Median CAGR (%)")
        ax.grid(alpha=0.3)
        ax.legend()
    fig.tight_layout()
    fig.savefig(PLOT_CAGR, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_full_period(summary: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, symbol, metric, ylabel in [
        (axes[0], "SP500", "cagr_proxy", "CAGR proxy (%)"),
        (axes[1], "NDX100", "cagr_proxy", "CAGR proxy (%)"),
    ]:
        sub = summary[summary["symbol"] == symbol].copy()
        colors = [FREQUENCY_CONFIG[f]["color"] for f in sub["frequency"]]
        ax.bar(sub["frequency"], sub[metric] * 100, color=colors)
        ax.set_title(f"{symbol}: Full-Period DCA Frequency Comparison")
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOT_FULL, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    datasets = {
        "SP500": load_index("sp500_daily.csv", "SP500"),
        "NDX100": load_index("ndx100_daily.csv", "NDX100"),
    }

    summary_rows: list[dict[str, object]] = []
    window_rows: list[dict[str, object]] = []
    for symbol, frame in datasets.items():
        for frequency in FREQUENCY_CONFIG:
            sampled = sample_schedule(frame, frequency)
            summary_rows.append(full_period_summary(symbol, sampled, frequency))
            for years in HORIZONS_BY_SYMBOL[symbol]:
                window_rows.extend(rolling_windows(symbol, sampled, frequency, years))

    summary = pd.DataFrame(summary_rows).sort_values(["symbol", "frequency"]).reset_index(drop=True)
    windows = pd.DataFrame(window_rows).sort_values(["symbol", "frequency", "years", "start_date"]).reset_index(drop=True)
    stats = (
        windows.groupby(["symbol", "frequency", "years"], as_index=False)
        .agg(
            samples=("cagr", "size"),
            positive_rate=("total_return_pct", lambda s: float((s > 0).mean())),
            median_cagr=("cagr", "median"),
            worst_cagr=("cagr", "min"),
            best_cagr=("cagr", "max"),
            median_total_return_pct=("total_return_pct", "median"),
            worst_total_return_pct=("total_return_pct", "min"),
            best_total_return_pct=("total_return_pct", "max"),
        )
        .sort_values(["symbol", "frequency", "years"])
    )

    summary.to_csv(SUMMARY_CSV, index=False)
    windows.to_csv(WINDOWS_CSV, index=False)
    stats.to_csv(STATS_CSV, index=False)

    plot_positive_rate(stats)
    plot_cagr(stats)
    plot_full_period(summary)

    print(SUMMARY_CSV)
    print(WINDOWS_CSV)
    print(STATS_CSV)
    print(PLOT_POSITIVE)
    print(PLOT_CAGR)
    print(PLOT_FULL)


if __name__ == "__main__":
    main()
