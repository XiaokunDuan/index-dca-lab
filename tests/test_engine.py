from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from dca_backtest.engine import BacktestEngine
from dca_backtest.models import BacktestConfig
from dca_backtest.plots import generate_study_plots
from dca_backtest.providers import LocalCsvProvider
from dca_backtest.study import StudySpec, run_dca_study


def _history(prices: list[float], start: str = "2024-01-01") -> pd.DataFrame:
    dates = pd.bdate_range(start=start, periods=len(prices))
    return pd.DataFrame(
        {
            "symbol": ["SPY"] * len(prices),
            "trade_date": dates,
            "open": prices,
            "high": prices,
            "low": prices,
            "close": prices,
            "adj_close": prices,
            "volume": [1000] * len(prices),
            "dividend": [0.0] * len(prices),
            "split_factor": [0.0] * len(prices),
        }
    )


def test_weekly_dca_contributes_once_per_matching_weekday() -> None:
    engine = BacktestEngine()
    history = _history([100, 101, 102, 103, 104])
    config = BacktestConfig(
        symbol="SPY",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 5),
        frequency="weekly",
        base_contribution=100,
        weekly_anchor=0,
    )

    result = engine.run(history, config)

    assert result.summary["total_base_contribution"] == 100.0
    assert result.summary["trade_count"] == 1


def test_drawdown_threshold_triggers_once_until_new_high() -> None:
    engine = BacktestEngine()
    history = _history([100, 95, 94, 101, 90, 89])
    config = BacktestConfig(
        symbol="SPY",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 8),
        frequency="weekly",
        base_contribution=100,
        weekly_anchor=0,
        drawdown_thresholds=(0.05,),
        dip_multiplier=2.0,
    )

    result = engine.run(history, config)

    assert len(result.trigger_log) == 2
    assert list(result.trigger_log["trade_date"].dt.date.astype(str)) == ["2024-01-02", "2024-01-05"]
    assert result.summary["total_dip_contribution"] == 400.0


def test_same_day_dca_and_dip_stack_together() -> None:
    engine = BacktestEngine()
    history = _history([100, 80, 79, 78, 77], start="2024-01-08")
    config = BacktestConfig(
        symbol="SPY",
        start_date=date(2024, 1, 8),
        end_date=date(2024, 1, 12),
        frequency="weekly",
        base_contribution=100,
        weekly_anchor=0,
        drawdown_thresholds=(0.1,),
        dip_multiplier=2.0,
    )

    result = engine.run(history, config)
    monday_flows = result.cashflow_log[result.cashflow_log["trade_date"].dt.date.astype(str) == "2024-01-08"]
    tuesday_flows = result.cashflow_log[result.cashflow_log["trade_date"].dt.date.astype(str) == "2024-01-09"]

    assert monday_flows["amount"].sum() == 100.0
    assert tuesday_flows["amount"].sum() == 200.0
    assert result.summary["total_contribution"] == 300.0


def test_local_csv_provider_reads_processed_shape(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02"],
            "open": [100, 101],
            "high": [101, 102],
            "low": [99, 100],
            "close": [100, 101],
            "adj_close": [100, 101],
            "volume": [1000, 1200],
            "symbol": ["SP500", "SP500"],
        }
    ).to_csv(csv_path, index=False)

    provider = LocalCsvProvider(csv_path)
    history = provider.fetch_history("SP500", date(2024, 1, 1), date(2024, 1, 2))

    assert list(history.columns) == [
        "symbol",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "dividend",
        "split_factor",
    ]
    assert len(history) == 2


def test_study_dca_outputs_reports(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    dates = pd.date_range("2020-01-01", periods=72, freq="MS")
    pd.DataFrame(
        {
            "date": dates,
            "open": [100 + i for i in range(len(dates))],
            "high": [101 + i for i in range(len(dates))],
            "low": [99 + i for i in range(len(dates))],
            "close": [100 + i for i in range(len(dates))],
            "adj_close": [100 + i for i in range(len(dates))],
            "volume": [1000] * len(dates),
            "symbol": ["SP500"] * len(dates),
        }
    ).to_csv(csv_path, index=False)

    summary, stats = run_dca_study(
        [StudySpec(symbol="SP500", csv_path=csv_path, frequency="monthly", contribution=1000, horizons=(5,))],
        output_dir=tmp_path / "reports",
    )

    assert not summary.empty
    assert not stats.empty
    assert (tmp_path / "reports" / "dca_summary.csv").exists()
    assert (tmp_path / "reports" / "dca_window_stats.csv").exists()


def test_generate_study_plots_writes_pngs(tmp_path: Path) -> None:
    csv_path = tmp_path / "sp500.csv"
    ndx_path = tmp_path / "ndx100.csv"
    dates = pd.date_range("2020-01-01", periods=72, freq="MS")
    sample = pd.DataFrame(
        {
            "date": dates,
            "open": [100 + i for i in range(len(dates))],
            "high": [101 + i for i in range(len(dates))],
            "low": [99 + i for i in range(len(dates))],
            "close": [100 + i for i in range(len(dates))],
            "adj_close": [100 + i for i in range(len(dates))],
            "volume": [1000] * len(dates),
            "symbol": ["SP500"] * len(dates),
        }
    )
    sample.to_csv(csv_path, index=False)
    sample.assign(symbol="NDX100", adj_close=sample["adj_close"] * 1.5).to_csv(ndx_path, index=False)

    run_dca_study(
        [
            StudySpec(symbol="SP500", csv_path=csv_path, frequency="monthly", contribution=1000, horizons=(5,)),
            StudySpec(symbol="NDX100", csv_path=ndx_path, frequency="monthly", contribution=1000, horizons=(5,)),
        ],
        output_dir=tmp_path / "reports",
    )
    outputs = generate_study_plots(tmp_path / "reports", csv_path, ndx_path)
    assert outputs
    assert all(path.exists() for path in outputs)
