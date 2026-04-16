from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd
from rich.console import Console

from .engine import BacktestEngine
from .models import BacktestConfig
from .plots import generate_study_plots
from .providers import LocalCsvProvider, YahooFinanceProvider
from .study import StudySpec, run_dca_study


console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backtest DCA plus drawdown-buy ETF strategies.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="Download and cache daily history.")
    _add_common_data_args(fetch)

    backtest = subparsers.add_parser("backtest", help="Run one strategy backtest.")
    _add_common_data_args(backtest)
    _add_strategy_args(backtest)

    scan = subparsers.add_parser("scan", help="Run a threshold and multiplier grid scan.")
    _add_common_data_args(scan)
    _add_strategy_args(scan)
    scan.add_argument(
        "--threshold-grid",
        nargs="+",
        required=True,
        help="Space-separated threshold sets, each set comma-separated. Example: 0.1,0.2 0.1,0.2,0.3",
    )
    scan.add_argument("--multiplier-grid", nargs="+", required=True, type=float)

    study = subparsers.add_parser("study-dca", help="Run rolling DCA study with progress bars.")
    study.add_argument("--output-dir", default="data/reports")
    study.add_argument("--contribution", type=float, default=1000.0)
    study.add_argument("--frequencies", nargs="+", default=["monthly", "weekly"], choices=["monthly", "weekly"])
    study.add_argument("--horizons", nargs="+", type=int, default=[5, 10, 15, 20, 30])
    study.add_argument("--start", type=_parse_date, help="Optional common study start date")
    study.add_argument("--end", type=_parse_date, help="Optional common study end date")
    study.add_argument(
        "--dataset",
        action="append",
        required=True,
        help="Dataset spec in the form SYMBOL=path/to/file.csv. Repeat for multiple datasets.",
    )

    plot = subparsers.add_parser("plot-dca", help="Render PNG charts from DCA study outputs.")
    plot.add_argument("--reports-dir", default="data/reports")
    plot.add_argument("--sp500-csv", required=True)
    plot.add_argument("--ndx100-csv", required=True)
    plot.add_argument("--start", type=_parse_date, help="Optional common plot start date")
    plot.add_argument("--end", type=_parse_date, help="Optional common plot end date")

    return parser.parse_args()


def _add_common_data_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--start", required=True, type=_parse_date)
    parser.add_argument("--end", required=True, type=_parse_date)
    parser.add_argument("--provider", choices=["yahoo", "local-csv"], default="yahoo")
    parser.add_argument("--csv-path", help="Required when --provider local-csv")
    parser.add_argument("--cache-dir", default="data")


def _add_strategy_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--frequency", choices=["weekly", "monthly"], required=True)
    parser.add_argument("--base-contribution", type=float, required=True)
    parser.add_argument("--weekly-anchor", type=int, default=0, help="0=Monday ... 4=Friday")
    parser.add_argument("--monthly-anchor", type=int, default=1, help="Nth trading day of month, starting from 1")
    parser.add_argument("--drawdown-thresholds", default="", help="Comma-separated positive decimals, e.g. 0.1,0.2")
    parser.add_argument("--dip-multiplier", type=float, default=0.0)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_thresholds(value: str) -> tuple[float, ...]:
    if not value.strip():
        return ()
    return tuple(float(part.strip()) for part in value.split(",") if part.strip())


def _build_config(args: argparse.Namespace, thresholds: tuple[float, ...] | None = None, multiplier: float | None = None) -> BacktestConfig:
    return BacktestConfig(
        symbol=args.symbol.upper(),
        start_date=args.start,
        end_date=args.end,
        frequency=args.frequency,
        base_contribution=args.base_contribution,
        weekly_anchor=args.weekly_anchor,
        monthly_anchor=args.monthly_anchor,
        drawdown_thresholds=thresholds if thresholds is not None else _parse_thresholds(args.drawdown_thresholds),
        dip_multiplier=multiplier if multiplier is not None else args.dip_multiplier,
    )


def _print_frame(frame: pd.DataFrame) -> None:
    if frame.empty:
        print("(empty)")
        return
    print(frame.to_string(index=False))


def _build_provider(args: argparse.Namespace):
    if args.provider == "yahoo":
        return YahooFinanceProvider(cache_dir=Path(args.cache_dir))
    if args.provider == "local-csv":
        if not args.csv_path:
            raise ValueError("--csv-path is required when --provider local-csv")
        return LocalCsvProvider(csv_path=args.csv_path)
    raise ValueError(f"Unsupported provider: {args.provider}")


def main() -> None:
    args = parse_args()
    if args.command == "plot-dca":
        outputs = generate_study_plots(
            reports_dir=Path(args.reports_dir),
            sp500_csv=Path(args.sp500_csv),
            ndx100_csv=Path(args.ndx100_csv),
            start_date=args.start,
            end_date=args.end,
        )
        console.print("[bold]Generated plots[/bold]")
        for path in outputs:
            console.print(str(path))
        return

    if args.command == "study-dca":
        specs = []
        for item in args.dataset:
            if "=" not in item:
                raise ValueError(f"Invalid --dataset value: {item}")
            symbol, path = item.split("=", 1)
            for frequency in args.frequencies:
                specs.append(
                    StudySpec(
                        symbol=symbol.upper(),
                        csv_path=Path(path),
                        frequency=frequency,
                        contribution=args.contribution,
                        horizons=tuple(args.horizons),
                        start_date=args.start,
                        end_date=args.end,
                    )
                )
        summary, stats = run_dca_study(specs, output_dir=Path(args.output_dir))
        console.print("\n[bold]Full-Period Summary[/bold]")
        _print_frame(summary)
        console.print("\n[bold]Window Stats[/bold]")
        _print_frame(stats)
        return

    provider = _build_provider(args)
    engine = BacktestEngine()

    if args.command == "fetch":
        history = provider.fetch_history(args.symbol.upper(), args.start, args.end)
        print(f"Fetched {len(history)} rows for {args.symbol.upper()} into {Path(args.cache_dir).resolve()}")
        return

    history = provider.fetch_history(args.symbol.upper(), args.start, args.end)

    if args.command == "backtest":
        config = _build_config(args)
        result = engine.run(history, config)
        comparison = engine.compare(history, config)
        print("Summary")
        _print_frame(pd.DataFrame([result.summary]))
        print("\nComparison")
        _print_frame(comparison)
        print("\nRecent Cashflows")
        _print_frame(result.cashflow_log.tail(10))
        return

    if args.command == "scan":
        rows = []
        for threshold_set in args.threshold_grid:
            thresholds = _parse_thresholds(threshold_set)
            for multiplier in args.multiplier_grid:
                config = _build_config(args, thresholds=thresholds, multiplier=multiplier)
                summary = engine.run(history, config).summary
                rows.append(summary)

        ranking = pd.DataFrame(rows).sort_values(
            by=["final_value", "cagr", "max_drawdown"],
            ascending=[False, False, False],
        )
        _print_frame(ranking)
        return

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
