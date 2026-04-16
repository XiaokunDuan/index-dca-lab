from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
DATA_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"
OUTPUT = REPORTS_DIR / "plot_2000_ndx100_vs_sp500_recovery.png"


def load_index(csv_name: str, symbol: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / csv_name, parse_dates=["date"])
    if "symbol" in df.columns:
        df = df[df["symbol"].astype(str).str.upper() == symbol.upper()]
    return df[["date", "adj_close"]].sort_values("date").reset_index(drop=True)


def first_recovery_date(df: pd.DataFrame, peak_date: pd.Timestamp) -> tuple[pd.Timestamp, float]:
    start_price = float(df.loc[df["date"] == peak_date, "adj_close"].iloc[0])
    after = df[df["date"] > peak_date].copy()
    recovery = after[after["adj_close"] >= start_price].iloc[0]
    return pd.Timestamp(recovery["date"]), float(start_price)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    peak_date = pd.Timestamp("2000-03-27")

    sp500 = load_index("sp500_daily.csv", "SP500")
    ndx100 = load_index("ndx100_daily.csv", "NDX100")

    sp500_recovery, sp500_start = first_recovery_date(sp500, peak_date)
    ndx100_recovery, ndx100_start = first_recovery_date(ndx100, peak_date)

    end_date = max(sp500_recovery, ndx100_recovery)

    sp = sp500[(sp500["date"] >= peak_date) & (sp500["date"] <= end_date)].copy()
    nd = ndx100[(ndx100["date"] >= peak_date) & (ndx100["date"] <= end_date)].copy()

    sp["normalized"] = sp["adj_close"] / sp500_start
    nd["normalized"] = nd["adj_close"] / ndx100_start
    sp["drawdown_pct"] = (sp["normalized"] - 1.0) * 100
    nd["drawdown_pct"] = (nd["normalized"] - 1.0) * 100

    fig, axes = plt.subplots(2, 1, figsize=(13, 10), sharex=True)

    axes[0].plot(sp["date"], sp["normalized"], color="#1f77b4", linewidth=2.2, label="SP500")
    axes[0].plot(nd["date"], nd["normalized"], color="#d62728", linewidth=2.2, label="NDX100")
    axes[0].axhline(1.0, color="#333333", linestyle="--", linewidth=1)
    axes[0].axvline(sp500_recovery, color="#1f77b4", linestyle=":", linewidth=1.5, alpha=0.8)
    axes[0].axvline(ndx100_recovery, color="#d62728", linestyle=":", linewidth=1.5, alpha=0.8)
    axes[0].annotate(
        f"SP500 recovered\n{sp500_recovery.date().isoformat()}\n{(sp500_recovery - peak_date).days} days",
        xy=(sp500_recovery, 1.0),
        xytext=(-70, 25),
        textcoords="offset points",
        color="#1f77b4",
        fontsize=9,
        arrowprops={"arrowstyle": "-", "color": "#1f77b4"},
    )
    axes[0].annotate(
        f"NDX100 recovered\n{ndx100_recovery.date().isoformat()}\n{(ndx100_recovery - peak_date).days} days",
        xy=(ndx100_recovery, 1.0),
        xytext=(-70, -45),
        textcoords="offset points",
        color="#d62728",
        fontsize=9,
        arrowprops={"arrowstyle": "-", "color": "#d62728"},
    )
    axes[0].set_title("2000 Bubble Peak to Recovery: NDX100 vs SP500")
    axes[0].set_ylabel("Normalized to 1.0 at 2000-03-27")
    axes[0].grid(alpha=0.3)
    axes[0].legend()

    axes[1].plot(sp["date"], sp["drawdown_pct"], color="#1f77b4", linewidth=2.2, label="SP500")
    axes[1].plot(nd["date"], nd["drawdown_pct"], color="#d62728", linewidth=2.2, label="NDX100")
    axes[1].axhline(0, color="#333333", linestyle="--", linewidth=1)
    axes[1].set_title("Drawdown from the 2000-03-27 Peak")
    axes[1].set_ylabel("Drawdown (%)")
    axes[1].grid(alpha=0.3)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(OUTPUT, dpi=180, bbox_inches="tight")
    print(OUTPUT)


if __name__ == "__main__":
    main()
