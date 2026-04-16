from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests


PROJECT_ROOT = Path("/Users/dxk/code/active/personal/active/etf-dca-backtest")
DATA_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"

SHILLER_XLS = DATA_DIR / "shiller_ie_data.xls"
SHILLER_URL = "http://www.econ.yale.edu/~shiller/data/ie_data.xls"

DETAIL_CSV = REPORTS_DIR / "cape_forward_return_detail.csv"
SUMMARY_CSV = REPORTS_DIR / "cape_forward_return_summary.csv"
PLOT_BUCKETS = REPORTS_DIR / "plot_cape_bucket_forward_returns.png"
PLOT_SCATTER = REPORTS_DIR / "plot_cape_scatter_forward_returns.png"

HORIZONS = [10, 20, 30]
MONTHLY_CONTRIBUTION = 1000.0
BUCKET_LABELS = ["Low CAPE", "Mid CAPE", "High CAPE"]


def ensure_shiller() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SHILLER_XLS.exists():
        r = requests.get(SHILLER_URL, timeout=30)
        r.raise_for_status()
        SHILLER_XLS.write_bytes(r.content)
    return SHILLER_XLS


def load_cape() -> pd.DataFrame:
    path = ensure_shiller()
    raw = pd.read_excel(path, sheet_name="Data", header=None)
    data = raw.iloc[7:].reset_index(drop=True)
    data.columns = data.iloc[0]
    data = data.iloc[1:].copy()
    data = data.rename(columns={"Date": "date_code", "CAPE": "cape"})
    data["date_code"] = pd.to_numeric(data["date_code"], errors="coerce")
    data["cape"] = pd.to_numeric(data["cape"], errors="coerce")
    data = data.dropna(subset=["date_code", "cape"])
    year = data["date_code"].astype(int)
    month = ((data["date_code"] - year) * 100).round().astype(int)
    month = month.clip(lower=1, upper=12)
    data["month"] = pd.to_datetime(dict(year=year, month=month, day=1))
    data = data[["month", "cape"]].sort_values("month").reset_index(drop=True)
    return data


def load_sp500_monthly() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "sp500_daily.csv", parse_dates=["date"])
    if "symbol" in df.columns:
        df = df[df["symbol"].astype(str).str.upper() == "SP500"]
    monthly = df.groupby(df["date"].dt.to_period("M")).first().reset_index(drop=True)
    monthly["month"] = monthly["date"].dt.to_period("M").dt.to_timestamp()
    return monthly[["date", "month", "adj_close"]].sort_values("date").reset_index(drop=True)


def run_monthly_dca(window: pd.DataFrame) -> tuple[float, float]:
    total_contribution = MONTHLY_CONTRIBUTION * len(window)
    shares = (MONTHLY_CONTRIBUTION / window["adj_close"]).sum()
    final_value = float(shares * window["adj_close"].iloc[-1])
    return total_contribution, final_value / total_contribution - 1.0


def build_detail() -> pd.DataFrame:
    cape = load_cape()
    sp = load_sp500_monthly()
    merged = sp.merge(cape, on="month", how="inner").sort_values("date").reset_index(drop=True)

    rows: list[dict[str, object]] = []
    for i in range(len(merged)):
        start_date = merged.loc[i, "date"]
        start_price = float(merged.loc[i, "adj_close"])
        start_cape = float(merged.loc[i, "cape"])
        for years in HORIZONS:
            target_end = start_date + pd.DateOffset(years=years)
            eligible = merged[merged["date"] >= target_end]
            if eligible.empty:
                continue
            end_idx = int(eligible.index[0])
            window = merged.iloc[i : end_idx + 1].copy()
            end_price = float(window["adj_close"].iloc[-1])
            lump_return = end_price / start_price - 1.0
            lump_cagr = (end_price / start_price) ** (1.0 / years) - 1.0
            total_contribution, dca_return = run_monthly_dca(window)
            rows.append(
                {
                    "start_date": start_date.date().isoformat(),
                    "end_date": window["date"].iloc[-1].date().isoformat(),
                    "years": years,
                    "start_cape": start_cape,
                    "lump_sum_total_return_pct": lump_return,
                    "lump_sum_cagr": lump_cagr,
                    "dca_total_contribution": total_contribution,
                    "dca_total_return_pct": dca_return,
                }
            )

    detail = pd.DataFrame(rows)
    detail["cape_bucket"] = detail.groupby("years")["start_cape"].transform(
        lambda s: pd.qcut(s, 3, labels=BUCKET_LABELS, duplicates="drop")
    )
    return detail


def summarize(detail: pd.DataFrame) -> pd.DataFrame:
    summary = (
        detail.groupby(["years", "cape_bucket"], as_index=False)
        .agg(
            samples=("start_cape", "size"),
            median_cape=("start_cape", "median"),
            lump_sum_median_cagr=("lump_sum_cagr", "median"),
            lump_sum_worst_cagr=("lump_sum_cagr", "min"),
            dca_median_total_return_pct=("dca_total_return_pct", "median"),
            dca_worst_total_return_pct=("dca_total_return_pct", "min"),
        )
        .sort_values(["years", "median_cape"])
    )
    return summary


def plot_buckets(summary: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    width = 0.22
    for ax, years in zip(axes, HORIZONS[:2]):
        sub = summary[summary["years"] == years].copy()
        x = range(len(sub))
        ax.bar([i - width / 2 for i in x], sub["lump_sum_median_cagr"] * 100, width=width, color="#4c78a8", label="Lump sum median CAGR")
        ax.bar([i + width / 2 for i in x], sub["dca_median_total_return_pct"] * 100, width=width, color="#f58518", label="DCA median total return")
        ax.set_xticks(list(x))
        ax.set_xticklabels(sub["cape_bucket"])
        ax.set_title(f"Start CAPE bucket vs {years}Y forward outcome")
        ax.set_ylabel("Percent")
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(PLOT_BUCKETS, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_scatter(detail: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
    for ax, years in zip(axes, HORIZONS):
        sub = detail[detail["years"] == years]
        ax.scatter(sub["start_cape"], sub["lump_sum_cagr"] * 100, alpha=0.35, s=16, color="#4c78a8", label="Lump sum CAGR")
        coeff = pd.Series(sub["lump_sum_cagr"] * 100).corr(pd.Series(sub["start_cape"]))
        ax.set_title(f"{years}Y forward return vs start CAPE\ncorr={coeff:.2f}")
        ax.set_xlabel("Start CAPE")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Lump sum CAGR (%)")
    fig.tight_layout()
    fig.savefig(PLOT_SCATTER, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    detail = build_detail()
    summary = summarize(detail)
    detail.to_csv(DETAIL_CSV, index=False)
    summary.to_csv(SUMMARY_CSV, index=False)
    plot_buckets(summary)
    plot_scatter(detail)
    print(SHILLER_XLS)
    print(DETAIL_CSV)
    print(SUMMARY_CSV)
    print(PLOT_BUCKETS)
    print(PLOT_SCATTER)


if __name__ == "__main__":
    main()
