from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn


console = Console()


@dataclass(slots=True)
class StudySpec:
    symbol: str
    csv_path: Path
    frequency: str
    contribution: float
    horizons: tuple[int, ...]
    start_date: date | None = None
    end_date: date | None = None


def run_dca_study(
    specs: list[StudySpec],
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict[str, object]] = []
    window_rows: list[dict[str, object]] = []

    total_steps = 0
    prepared: list[tuple[StudySpec, pd.DataFrame]] = []
    for spec in specs:
        frame = _load_frame(spec.csv_path, spec.symbol, spec.start_date, spec.end_date)
        sampled = _sample_schedule(frame, spec.frequency)
        prepared.append((spec, sampled))
        total_steps += 1
        for years in spec.horizons:
            total_steps += len(_rolling_windows(spec, sampled, years))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Running DCA study", total=total_steps)

        for spec, sampled in prepared:
            summary_rows.append(_full_period_summary(spec, sampled))
            progress.advance(task)

            for years in spec.horizons:
                windows = _rolling_windows(spec, sampled, years)
                for row in windows:
                    window_rows.append(row)
                    progress.advance(task)

    summary_frame = pd.DataFrame(summary_rows).sort_values(["symbol", "frequency"]).reset_index(drop=True)
    window_frame = pd.DataFrame(window_rows).sort_values(["symbol", "frequency", "years", "start_date"]).reset_index(drop=True)

    window_stats = (
        window_frame.groupby(["symbol", "frequency", "years"], as_index=False)
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
    )

    summary_path = output_dir / "dca_summary.csv"
    stats_path = output_dir / "dca_window_stats.csv"
    windows_path = output_dir / "dca_windows.csv"
    summary_frame.to_csv(summary_path, index=False)
    window_stats.to_csv(stats_path, index=False)
    window_frame.to_csv(windows_path, index=False)

    console.print(f"[green]Wrote[/green] {summary_path}")
    console.print(f"[green]Wrote[/green] {stats_path}")
    console.print(f"[green]Wrote[/green] {windows_path}")
    return summary_frame, window_stats


def _load_frame(csv_path: Path, symbol: str, start_date: date | None = None, end_date: date | None = None) -> pd.DataFrame:
    frame = pd.read_csv(csv_path, parse_dates=["date"])
    if "symbol" in frame.columns:
        mask = frame["symbol"].astype(str).str.upper().eq(symbol.upper())
        if mask.any():
            frame = frame.loc[mask]
    if start_date is not None:
        frame = frame.loc[frame["date"] >= pd.Timestamp(start_date)]
    if end_date is not None:
        frame = frame.loc[frame["date"] <= pd.Timestamp(end_date)]
    frame = frame.sort_values("date").reset_index(drop=True)
    return frame


def _sample_schedule(frame: pd.DataFrame, frequency: str) -> pd.DataFrame:
    if frequency == "monthly":
        sampled = frame.groupby(frame["date"].dt.to_period("M")).first().reset_index(drop=True)
    elif frequency == "weekly":
        sampled = frame.groupby(frame["date"].dt.to_period("W-MON")).first().reset_index(drop=True)
    else:
        raise ValueError(f"Unsupported frequency: {frequency}")
    sampled = sampled[["date", "adj_close"]].copy()
    sampled["adj_close"] = sampled["adj_close"].astype(float)
    return sampled


def _full_period_summary(spec: StudySpec, sampled: pd.DataFrame) -> dict[str, object]:
    contrib = np.full(len(sampled), spec.contribution, dtype=float)
    shares = contrib / sampled["adj_close"].to_numpy()
    total_contribution = float(contrib.sum())
    final_value = float(shares.cumsum()[-1] * sampled["adj_close"].iloc[-1])
    years = (sampled["date"].iloc[-1] - sampled["date"].iloc[0]).days / 365.25
    cagr = (final_value / total_contribution) ** (1 / years) - 1 if years > 0 else 0.0
    return {
        "symbol": spec.symbol,
        "frequency": spec.frequency,
        "start_date": sampled["date"].iloc[0].date().isoformat(),
        "end_date": sampled["date"].iloc[-1].date().isoformat(),
        "contribution_per_period": spec.contribution,
        "periods": len(sampled),
        "total_contribution": total_contribution,
        "final_value": final_value,
        "total_return_pct": final_value / total_contribution - 1,
        "cagr_proxy": cagr,
    }


def _rolling_windows(spec: StudySpec, sampled: pd.DataFrame, years: int) -> list[dict[str, object]]:
    prices = sampled["adj_close"].to_numpy()
    dates = sampled["date"].to_numpy()
    shares = spec.contribution / prices
    prefix = np.concatenate([[0.0], np.cumsum(shares)])
    rows = []
    timestamps = pd.to_datetime(sampled["date"]).reset_index(drop=True)
    for i in range(0, len(sampled)):
        target_end = timestamps.iloc[i] + pd.DateOffset(years=years)
        eligible = timestamps[timestamps >= target_end]
        if eligible.empty:
            break
        j = int(eligible.index[0])
        shares_acc = float(prefix[j + 1] - prefix[i])
        periods = j - i + 1
        total_contribution = spec.contribution * periods
        final_value = shares_acc * float(prices[j])
        total_return_pct = final_value / total_contribution - 1
        elapsed_years = (dates[j] - dates[i]).astype("timedelta64[D]").astype(int) / 365.25
        cagr = (final_value / total_contribution) ** (1 / elapsed_years) - 1 if elapsed_years > 0 else 0.0
        rows.append(
            {
                "symbol": spec.symbol,
                "frequency": spec.frequency,
                "years": years,
                "start_date": pd.Timestamp(dates[i]).date().isoformat(),
                "end_date": pd.Timestamp(dates[j]).date().isoformat(),
                "total_contribution": total_contribution,
                "final_value": final_value,
                "total_return_pct": total_return_pct,
                "cagr": cagr,
            }
        )
    return rows
