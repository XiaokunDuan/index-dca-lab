from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def generate_study_plots(
    reports_dir: Path,
    sp500_csv: Path,
    ndx100_csv: Path,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Path]:
    reports_dir = Path(reports_dir)
    summary = pd.read_csv(reports_dir / "dca_summary.csv")
    stats = pd.read_csv(reports_dir / "dca_window_stats.csv")
    sp500 = pd.read_csv(sp500_csv, parse_dates=["date"])
    ndx100 = pd.read_csv(ndx100_csv, parse_dates=["date"])
    if start_date is not None:
        sp500 = sp500.loc[sp500["date"] >= pd.Timestamp(start_date)]
        ndx100 = ndx100.loc[ndx100["date"] >= pd.Timestamp(start_date)]
    if end_date is not None:
        sp500 = sp500.loc[sp500["date"] <= pd.Timestamp(end_date)]
        ndx100 = ndx100.loc[ndx100["date"] <= pd.Timestamp(end_date)]

    output_paths = [
        _plot_full_period_summary(summary, reports_dir / "plot_full_period_summary.png"),
        _plot_positive_rate(stats, reports_dir / "plot_positive_rate.png"),
        _plot_cagr_summary(stats, reports_dir / "plot_cagr_summary.png"),
        _plot_normalized_indices(sp500, ndx100, reports_dir / "plot_indices_normalized_since_1985.png"),
        _plot_sp500_long_run(sp500, reports_dir / "plot_sp500_long_run.png"),
        _plot_ndx100_long_run(ndx100, reports_dir / "plot_ndx100_long_run.png"),
    ]
    return output_paths


def _plot_full_period_summary(summary: pd.DataFrame, output_path: Path) -> Path:
    frame = summary.copy()
    frame["label"] = frame["symbol"] + "-" + frame["frequency"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].bar(frame["label"], frame["cagr_proxy"] * 100, color=["#1f77b4", "#6baed6", "#d62728", "#ff9896"])
    axes[0].set_title("Full-Period DCA CAGR Proxy")
    axes[0].set_ylabel("Percent")
    axes[0].tick_params(axis="x", rotation=20)

    axes[1].bar(frame["label"], frame["total_return_pct"], color=["#1f77b4", "#6baed6", "#d62728", "#ff9896"])
    axes[1].set_title("Full-Period DCA Total Return Multiple")
    axes[1].set_ylabel("Multiple over capital")
    axes[1].tick_params(axis="x", rotation=20)

    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path


def _plot_positive_rate(stats: pd.DataFrame, output_path: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, frequency in zip(axes, ["monthly", "weekly"]):
        sub = stats[stats["frequency"] == frequency].sort_values(["symbol", "years"])
        for symbol, color in [("SP500", "#1f77b4"), ("NDX100", "#d62728")]:
            series = sub[sub["symbol"] == symbol]
            ax.plot(series["years"], series["positive_rate"] * 100, marker="o", linewidth=2, label=symbol, color=color)
        ax.set_title(f"Positive Return Rate by Horizon ({frequency})")
        ax.set_xlabel("Holding Years")
        ax.set_ylabel("Positive Windows (%)")
        ax.set_ylim(0, 105)
        ax.grid(alpha=0.3)
        ax.legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path


def _plot_cagr_summary(stats: pd.DataFrame, output_path: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, frequency in zip(axes, ["monthly", "weekly"]):
        sub = stats[stats["frequency"] == frequency].sort_values(["symbol", "years"])
        for symbol, color in [("SP500", "#1f77b4"), ("NDX100", "#d62728")]:
            series = sub[sub["symbol"] == symbol]
            ax.plot(series["years"], series["median_cagr"] * 100, marker="o", linewidth=2, label=f"{symbol} median", color=color)
            ax.plot(series["years"], series["worst_cagr"] * 100, linestyle="--", linewidth=1.8, label=f"{symbol} worst", color=color, alpha=0.65)
        ax.set_title(f"Median vs Worst CAGR ({frequency})")
        ax.set_xlabel("Holding Years")
        ax.set_ylabel("CAGR (%)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path


def _plot_normalized_indices(sp500: pd.DataFrame, ndx100: pd.DataFrame, output_path: Path) -> Path:
    sp500 = sp500.copy()
    ndx100 = ndx100.copy()
    sp500["date"] = pd.to_datetime(sp500["date"])
    ndx100["date"] = pd.to_datetime(ndx100["date"])

    common_start = max(sp500["date"].min(), ndx100["date"].min())
    sp = sp500[sp500["date"] >= common_start].copy()
    nd = ndx100[ndx100["date"] >= common_start].copy()
    sp["normalized"] = sp["adj_close"] / sp["adj_close"].iloc[0]
    nd["normalized"] = nd["adj_close"] / nd["adj_close"].iloc[0]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(sp["date"], sp["normalized"], label="SP500", color="#1f77b4", linewidth=2)
    ax.plot(nd["date"], nd["normalized"], label="NDX100", color="#d62728", linewidth=2)
    ax.set_title(f"Normalized Spot Index Paths Since {common_start.date().isoformat()}")
    ax.set_ylabel("Growth of 1 Unit")
    ax.grid(alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path


def _plot_sp500_long_run(sp500: pd.DataFrame, output_path: Path) -> Path:
    sp500 = sp500.copy()
    sp500["date"] = pd.to_datetime(sp500["date"])
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(sp500["date"], sp500["adj_close"], color="#1f77b4", linewidth=1.8)
    ax.set_title("SP500 Spot Index Long-Run History")
    ax.set_ylabel("Adjusted Close")
    ax.set_yscale("log")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path


def _plot_ndx100_long_run(ndx100: pd.DataFrame, output_path: Path) -> Path:
    ndx100 = ndx100.copy()
    ndx100["date"] = pd.to_datetime(ndx100["date"])
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(ndx100["date"], ndx100["adj_close"], color="#d62728", linewidth=1.8)
    ax.set_title("NDX100 Spot Index Long-Run History")
    ax.set_ylabel("Adjusted Close")
    ax.set_yscale("log")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path
