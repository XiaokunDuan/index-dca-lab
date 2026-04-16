from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
DATA_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"

DETAIL_CSV = REPORTS_DIR / "worst_start_study.csv"
SUMMARY_CSV = REPORTS_DIR / "worst_start_summary.csv"
PLOT_COMPARE = REPORTS_DIR / "plot_worst_start_lump_vs_dca.png"
PLOT_SUMMARY = REPORTS_DIR / "plot_worst_start_summary.png"

TOP_N = 5
MONTHLY_CONTRIBUTION = 1000.0
HORIZONS_BY_SYMBOL: dict[str, list[int]] = {
    "SP500": [5, 10, 20, 30],
    "NDX100": [5, 10, 20, 30],
}
COLORS = {"lump_sum": "#4c78a8", "dca": "#f58518"}


def load_index(csv_name: str, symbol: str) -> pd.DataFrame:
    path = DATA_DIR / csv_name
    df = pd.read_csv(path, parse_dates=["date"])
    if "symbol" in df.columns:
        df = df[df["symbol"].astype(str).str.upper() == symbol.upper()]
    return df[["date", "adj_close"]].sort_values("date").reset_index(drop=True)


def xirr(cashflows: list[tuple[pd.Timestamp, float]]) -> float:
    if not cashflows:
        return np.nan
    dates = [pd.Timestamp(d) for d, _ in cashflows]
    amounts = [float(a) for _, a in cashflows]
    t0 = dates[0]
    years = np.array([(d - t0).days / 365.25 for d in dates], dtype=float)

    def npv(rate: float) -> float:
        if rate <= -0.999999:
            return np.inf
        return float(np.sum(np.array(amounts) / np.power(1.0 + rate, years)))

    low, high = -0.9999, 10.0
    f_low, f_high = npv(low), npv(high)
    expand = 0
    while np.sign(f_low) == np.sign(f_high) and expand < 25:
        high *= 2
        f_high = npv(high)
        expand += 1
    if np.sign(f_low) == np.sign(f_high):
        return np.nan
    for _ in range(200):
        mid = (low + high) / 2
        f_mid = npv(mid)
        if abs(f_mid) < 1e-9:
            return mid
        if np.sign(f_mid) == np.sign(f_low):
            low, f_low = mid, f_mid
        else:
            high, f_high = mid, f_mid
    return (low + high) / 2


def find_window_end(dates: pd.Series, start_date: pd.Timestamp, years: int) -> int | None:
    end_target = start_date + pd.DateOffset(years=years)
    end_idx = int(dates.searchsorted(end_target, side="left"))
    if end_idx >= len(dates):
        return None
    return end_idx


def build_lump_sum_windows(df: pd.DataFrame, symbol: str, years: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    dates = df["date"]
    prices = df["adj_close"]

    for i, start_date in enumerate(dates):
        end_idx = find_window_end(dates, start_date, years)
        if end_idx is None:
            break
        start_price = float(prices.iloc[i])
        end_price = float(prices.iloc[end_idx])
        total_return_pct = end_price / start_price - 1.0
        cagr = (end_price / start_price) ** (1.0 / years) - 1.0
        rows.append(
            {
                "symbol": symbol,
                "years": years,
                "start_date": start_date,
                "end_date": dates.iloc[end_idx],
                "start_price": start_price,
                "end_price": end_price,
                "lump_sum_total_return_pct": total_return_pct,
                "lump_sum_cagr": cagr,
            }
        )

    return pd.DataFrame(rows)


def run_monthly_dca(df: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp) -> dict[str, float]:
    frame = df[(df["date"] >= start_date) & (df["date"] <= end_date)].copy()
    frame["month"] = frame["date"].dt.to_period("M")
    dca_days = frame.groupby("month", as_index=False).first()
    cashflows: list[tuple[pd.Timestamp, float]] = []
    total_shares = 0.0
    total_contribution = 0.0

    for row in dca_days.itertuples(index=False):
        price = float(row.adj_close)
        amount = MONTHLY_CONTRIBUTION
        shares = amount / price
        total_shares += shares
        total_contribution += amount
        cashflows.append((pd.Timestamp(row.date), -amount))

    final_price = float(frame["adj_close"].iloc[-1])
    final_value = total_shares * final_price
    cashflows.append((pd.Timestamp(frame["date"].iloc[-1]), final_value))
    total_return_pct = final_value / total_contribution - 1.0 if total_contribution else np.nan
    xirr_value = xirr(cashflows)

    return {
        "dca_total_contribution": total_contribution,
        "dca_final_value": final_value,
        "dca_total_return_pct": total_return_pct,
        "dca_xirr": xirr_value,
        "dca_trade_count": len(dca_days),
    }


def study_symbol(df: pd.DataFrame, symbol: str, horizons: list[int]) -> pd.DataFrame:
    all_rows: list[dict[str, object]] = []
    for years in horizons:
        lump = build_lump_sum_windows(df, symbol, years)
        worst = lump.nsmallest(TOP_N, "lump_sum_total_return_pct").copy().sort_values("start_date")
        worst["rank"] = np.arange(1, len(worst) + 1)
        for row in worst.itertuples(index=False):
            dca = run_monthly_dca(df, pd.Timestamp(row.start_date), pd.Timestamp(row.end_date))
            lump_budget = dca["dca_total_contribution"]
            lump_final_value = lump_budget * (1.0 + float(row.lump_sum_total_return_pct))
            all_rows.append(
                {
                    "symbol": symbol,
                    "years": years,
                    "rank": int(row.rank),
                    "start_date": pd.Timestamp(row.start_date).date().isoformat(),
                    "end_date": pd.Timestamp(row.end_date).date().isoformat(),
                    "start_price": float(row.start_price),
                    "end_price": float(row.end_price),
                    "planned_budget": lump_budget,
                    "lump_sum_final_value": lump_final_value,
                    "lump_sum_total_return_pct": float(row.lump_sum_total_return_pct),
                    "lump_sum_cagr": float(row.lump_sum_cagr),
                    **dca,
                }
            )
    return pd.DataFrame(all_rows)


def plot_compare(detail: pd.DataFrame) -> None:
    combos = [("SP500", 5), ("SP500", 10), ("SP500", 20), ("SP500", 30), ("NDX100", 5), ("NDX100", 10), ("NDX100", 20), ("NDX100", 30)]
    fig, axes = plt.subplots(4, 2, figsize=(16, 18), sharey=True)
    axes = axes.flatten()

    for ax, (symbol, years) in zip(axes, combos):
        sub = detail[(detail["symbol"] == symbol) & (detail["years"] == years)].sort_values("rank")
        x = np.arange(len(sub))
        width = 0.38
        labels = [f"#{int(r)}\n{d[2:]}" for r, d in zip(sub["rank"], sub["start_date"])]
        ax.bar(x - width / 2, sub["lump_sum_total_return_pct"] * 100, width=width, color=COLORS["lump_sum"], label="Lump sum")
        ax.bar(x + width / 2, sub["dca_total_return_pct"] * 100, width=width, color=COLORS["dca"], label="Monthly DCA")
        ax.axhline(0, color="#333333", linewidth=0.8)
        ax.set_title(f"{symbol} worst {years}Y start dates")
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylabel("Total return over equal budget (%)")
        ax.grid(axis="y", alpha=0.25)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False)
    fig.suptitle("Worst Start Dates: Lump Sum vs Monthly DCA", y=0.995, fontsize=15)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(PLOT_COMPARE, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_summary(summary: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, symbol in zip(axes, ["SP500", "NDX100"]):
        sub = summary[summary["symbol"] == symbol].sort_values("years")
        ax.plot(sub["years"], sub["median_lump_sum_total_return_pct"] * 100, marker="o", linewidth=2.2, color=COLORS["lump_sum"], label="Worst-5 lump sum median")
        ax.plot(sub["years"], sub["median_dca_total_return_pct"] * 100, marker="o", linewidth=2.2, color=COLORS["dca"], label="Worst-5 DCA median")
        ax.set_title(f"{symbol} worst-start median outcome")
        ax.set_xlabel("Holding Years")
        ax.set_ylabel("Total return over equal budget (%)")
        ax.axhline(0, color="#333333", linewidth=0.8)
        ax.grid(alpha=0.3)
        ax.legend()
    fig.tight_layout()
    fig.savefig(PLOT_SUMMARY, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    datasets = {
        "SP500": load_index("sp500_daily.csv", "SP500"),
        "NDX100": load_index("ndx100_daily.csv", "NDX100"),
    }

    details = []
    for symbol, df in datasets.items():
        details.append(study_symbol(df, symbol, HORIZONS_BY_SYMBOL[symbol]))
    detail = pd.concat(details, ignore_index=True)
    detail.to_csv(DETAIL_CSV, index=False)

    summary = (
        detail.groupby(["symbol", "years"], as_index=False)
        .agg(
            median_lump_sum_total_return_pct=("lump_sum_total_return_pct", "median"),
            worst_lump_sum_total_return_pct=("lump_sum_total_return_pct", "min"),
            median_dca_total_return_pct=("dca_total_return_pct", "median"),
            worst_dca_total_return_pct=("dca_total_return_pct", "min"),
            median_dca_xirr=("dca_xirr", "median"),
        )
        .sort_values(["symbol", "years"])
    )
    summary.to_csv(SUMMARY_CSV, index=False)

    plot_compare(detail)
    plot_summary(summary)

    print(DETAIL_CSV)
    print(SUMMARY_CSV)
    print(PLOT_COMPARE)
    print(PLOT_SUMMARY)


if __name__ == "__main__":
    main()
