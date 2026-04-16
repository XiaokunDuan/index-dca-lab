from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
DATA_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"

MONTHLY_CONTRIBUTION = 1000.0
HORIZONS_BY_SYMBOL = {
    "SP500": [5, 10, 20, 30],
    "NDX100": [5, 10, 20, 30],
}

DETAIL_CSV = REPORTS_DIR / "lump_sum_vs_dca_detail.csv"
SUMMARY_CSV = REPORTS_DIR / "lump_sum_vs_dca_summary.csv"
PLOT_MEDIAN = REPORTS_DIR / "plot_lump_sum_vs_dca_median.png"
PLOT_POSITIVE = REPORTS_DIR / "plot_lump_sum_vs_dca_positive_rate.png"
PLOT_WORST = REPORTS_DIR / "plot_lump_sum_vs_dca_worst_case.png"


def load_index(csv_name: str, symbol: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / csv_name, parse_dates=["date"])
    if "symbol" in df.columns:
        df = df[df["symbol"].astype(str).str.upper() == symbol.upper()]
    return df[["date", "adj_close"]].sort_values("date").reset_index(drop=True)


def find_window_end(dates: pd.Series, start_date: pd.Timestamp, years: int) -> int | None:
    end_target = start_date + pd.DateOffset(years=years)
    end_idx = int(dates.searchsorted(end_target, side="left"))
    if end_idx >= len(dates):
        return None
    return end_idx


def run_study_for_symbol(df: pd.DataFrame, symbol: str, horizons: list[int]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    dates = df["date"]
    prices = df["adj_close"]
    for i, start_date in enumerate(dates):
        for years in horizons:
            end_idx = find_window_end(dates, start_date, years)
            if end_idx is None:
                continue
            window = df.iloc[i : end_idx + 1].copy()
            periods = len(window)
            total_budget = MONTHLY_CONTRIBUTION * periods

            start_price = float(window["adj_close"].iloc[0])
            end_price = float(window["adj_close"].iloc[-1])

            lump_shares = total_budget / start_price
            lump_final_value = lump_shares * end_price
            lump_return = lump_final_value / total_budget - 1.0
            lump_cagr = (lump_final_value / total_budget) ** (1.0 / years) - 1.0

            dca_shares = (MONTHLY_CONTRIBUTION / window["adj_close"]).sum()
            dca_final_value = dca_shares * end_price
            dca_return = dca_final_value / total_budget - 1.0
            dca_cagr = (dca_final_value / total_budget) ** (1.0 / years) - 1.0

            rows.append(
                {
                    "symbol": symbol,
                    "years": years,
                    "start_date": start_date.date().isoformat(),
                    "end_date": window["date"].iloc[-1].date().isoformat(),
                    "periods": periods,
                    "total_budget": total_budget,
                    "lump_sum_total_return_pct": lump_return,
                    "lump_sum_cagr": lump_cagr,
                    "dca_total_return_pct": dca_return,
                    "dca_cagr": dca_cagr,
                    "return_gap_pct": lump_return - dca_return,
                }
            )
    return pd.DataFrame(rows)


def summarize(detail: pd.DataFrame) -> pd.DataFrame:
    summary = (
        detail.groupby(["symbol", "years"], as_index=False)
        .agg(
            samples=("start_date", "size"),
            lump_sum_positive_rate=("lump_sum_total_return_pct", lambda s: float((s > 0).mean())),
            dca_positive_rate=("dca_total_return_pct", lambda s: float((s > 0).mean())),
            lump_sum_median_cagr=("lump_sum_cagr", "median"),
            dca_median_cagr=("dca_cagr", "median"),
            lump_sum_worst_cagr=("lump_sum_cagr", "min"),
            dca_worst_cagr=("dca_cagr", "min"),
            lump_sum_median_total_return_pct=("lump_sum_total_return_pct", "median"),
            dca_median_total_return_pct=("dca_total_return_pct", "median"),
            avg_return_gap_pct=("return_gap_pct", "mean"),
        )
        .sort_values(["symbol", "years"])
    )
    return summary


def plot_metric(summary: pd.DataFrame, path: Path, metric_lump: str, metric_dca: str, ylabel: str, title_suffix: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, symbol in zip(axes, ["SP500", "NDX100"]):
        sub = summary[summary["symbol"] == symbol].sort_values("years")
        ax.plot(sub["years"], sub[metric_lump] * 100, marker="o", linewidth=2.2, color="#4c78a8", label="Lump sum")
        ax.plot(sub["years"], sub[metric_dca] * 100, marker="o", linewidth=2.2, color="#f58518", label="Monthly DCA")
        ax.set_title(f"{symbol}: {title_suffix}")
        ax.set_xlabel("Holding Years")
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.3)
        ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    for symbol, csv_name in [("SP500", "sp500_daily.csv"), ("NDX100", "ndx100_daily.csv")]:
        frames.append(run_study_for_symbol(load_index(csv_name, symbol), symbol, HORIZONS_BY_SYMBOL[symbol]))
    detail = pd.concat(frames, ignore_index=True)
    summary = summarize(detail)
    detail.to_csv(DETAIL_CSV, index=False)
    summary.to_csv(SUMMARY_CSV, index=False)

    plot_metric(summary, PLOT_MEDIAN, "lump_sum_median_cagr", "dca_median_cagr", "Median CAGR (%)", "Median Outcome")
    plot_metric(summary, PLOT_POSITIVE, "lump_sum_positive_rate", "dca_positive_rate", "Positive Windows (%)", "Positive Return Rate")
    plot_metric(summary, PLOT_WORST, "lump_sum_worst_cagr", "dca_worst_cagr", "Worst CAGR (%)", "Worst-Case Outcome")

    print(DETAIL_CSV)
    print(SUMMARY_CSV)
    print(PLOT_MEDIAN)
    print(PLOT_POSITIVE)
    print(PLOT_WORST)


if __name__ == "__main__":
    main()
