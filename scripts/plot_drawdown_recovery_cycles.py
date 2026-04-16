from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
DATA_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROJECT_ROOT / "data" / "reports"


@dataclass
class RecoveryEpisode:
    symbol: str
    peak_date: pd.Timestamp
    trough_date: pd.Timestamp
    recovery_date: pd.Timestamp | None
    max_drawdown_pct: float
    days_peak_to_trough: int
    days_trough_to_recovery: int | None
    days_peak_to_recovery: int | None


def load_index(csv_name: str, symbol: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / csv_name, parse_dates=["date"])
    df = df[df["symbol"].astype(str).str.upper() == symbol.upper()].copy()
    df = df.sort_values("date").reset_index(drop=True)
    return df[["date", "adj_close"]]


def extract_recovery_episodes(frame: pd.DataFrame, symbol: str) -> list[RecoveryEpisode]:
    episodes: list[RecoveryEpisode] = []
    peak_price = float(frame["adj_close"].iloc[0])
    peak_date = pd.Timestamp(frame["date"].iloc[0])
    trough_price = peak_price
    trough_date = peak_date
    in_drawdown = False

    for row in frame.itertuples(index=False):
        current_date = pd.Timestamp(row.date)
        price = float(row.adj_close)

        if price >= peak_price:
            if in_drawdown:
                episodes.append(
                    RecoveryEpisode(
                        symbol=symbol,
                        peak_date=peak_date,
                        trough_date=trough_date,
                        recovery_date=current_date,
                        max_drawdown_pct=(trough_price / peak_price - 1.0) * 100,
                        days_peak_to_trough=(trough_date - peak_date).days,
                        days_trough_to_recovery=(current_date - trough_date).days,
                        days_peak_to_recovery=(current_date - peak_date).days,
                    )
                )
                in_drawdown = False

            peak_price = price
            peak_date = current_date
            trough_price = price
            trough_date = current_date
            continue

        if not in_drawdown:
            in_drawdown = True
            trough_price = price
            trough_date = current_date
        elif price < trough_price:
            trough_price = price
            trough_date = current_date

    if in_drawdown:
        episodes.append(
            RecoveryEpisode(
                symbol=symbol,
                peak_date=peak_date,
                trough_date=trough_date,
                recovery_date=None,
                max_drawdown_pct=(trough_price / peak_price - 1.0) * 100,
                days_peak_to_trough=(trough_date - peak_date).days,
                days_trough_to_recovery=None,
                days_peak_to_recovery=None,
            )
        )

    return episodes


def to_frame(episodes: list[RecoveryEpisode]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": ep.symbol,
                "peak_date": ep.peak_date.date().isoformat(),
                "trough_date": ep.trough_date.date().isoformat(),
                "recovery_date": ep.recovery_date.date().isoformat() if ep.recovery_date is not None else None,
                "max_drawdown_pct": ep.max_drawdown_pct,
                "days_peak_to_trough": ep.days_peak_to_trough,
                "days_trough_to_recovery": ep.days_trough_to_recovery,
                "days_peak_to_recovery": ep.days_peak_to_recovery,
            }
            for ep in episodes
        ]
    )


def plot_top_recovery_cycles(all_episodes: pd.DataFrame, output_path: Path) -> None:
    top = (
        all_episodes.dropna(subset=["recovery_date"])
        .sort_values(["symbol", "max_drawdown_pct"])
        .groupby("symbol", as_index=False, group_keys=False)
        .head(5)
        .copy()
    )
    top["label"] = (
        top["symbol"]
        + " | "
        + top["peak_date"].str.slice(0, 4)
        + "->"
        + top["trough_date"].str.slice(0, 4)
    )
    top["recovery_years"] = top["days_peak_to_recovery"] / 365.25
    top["fall_years"] = top["days_peak_to_trough"] / 365.25

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    colors = top["symbol"].map({"SP500": "#1f77b4", "NDX100": "#d62728"})
    axes[0].barh(top["label"], top["max_drawdown_pct"], color=colors)
    axes[0].set_title("Top Completed Drawdowns by Depth")
    axes[0].set_xlabel("Max Drawdown (%)")
    axes[0].grid(axis="x", alpha=0.3)

    axes[1].barh(top["label"], top["recovery_years"], color=colors)
    axes[1].set_title("Time from Peak to Full Recovery")
    axes[1].set_xlabel("Years")
    axes[1].grid(axis="x", alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_recovery_scatter(all_episodes: pd.DataFrame, output_path: Path) -> None:
    frame = all_episodes.dropna(subset=["recovery_date"]).copy()
    frame["recovery_years"] = frame["days_peak_to_recovery"] / 365.25
    frame["fall_years"] = frame["days_peak_to_trough"] / 365.25

    fig, ax = plt.subplots(figsize=(11, 7))
    for symbol, color in [("SP500", "#1f77b4"), ("NDX100", "#d62728")]:
        sub = frame[frame["symbol"] == symbol]
        ax.scatter(
            -sub["max_drawdown_pct"],
            sub["recovery_years"],
            label=symbol,
            color=color,
            alpha=0.75,
            s=45,
        )
    ax.set_title("Drawdown Depth vs Recovery Time")
    ax.set_xlabel("Drawdown Depth (%)")
    ax.set_ylabel("Years from Peak to Recovery")
    ax.grid(alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    sp500 = load_index("sp500_daily.csv", "SP500")
    ndx100 = load_index("ndx100_daily.csv", "NDX100")

    episodes = extract_recovery_episodes(sp500, "SP500") + extract_recovery_episodes(ndx100, "NDX100")
    frame = to_frame(episodes).sort_values(["symbol", "max_drawdown_pct"]).reset_index(drop=True)
    csv_path = REPORT_DIR / "drawdown_recovery_cycles.csv"
    frame.to_csv(csv_path, index=False)

    top_path = REPORT_DIR / "plot_drawdown_recovery_cycles_top.png"
    scatter_path = REPORT_DIR / "plot_drawdown_recovery_cycles_scatter.png"
    plot_top_recovery_cycles(frame, top_path)
    plot_recovery_scatter(frame, scatter_path)

    print(csv_path)
    print(top_path)
    print(scatter_path)


if __name__ == "__main__":
    main()
