from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

import pandas as pd


Frequency = Literal["weekly", "monthly"]


@dataclass(slots=True)
class BacktestConfig:
    symbol: str
    start_date: date
    end_date: date
    frequency: Frequency
    base_contribution: float
    weekly_anchor: int = 0
    monthly_anchor: int = 1
    drawdown_thresholds: tuple[float, ...] = ()
    dip_multiplier: float = 0.0
    price_field: str = "adj_close"
    enable_dca: bool = True
    enable_dip_buy: bool = True

    def normalized_thresholds(self) -> tuple[float, ...]:
        cleaned = sorted({abs(value) for value in self.drawdown_thresholds if value > 0})
        return tuple(cleaned)


@dataclass(slots=True)
class BacktestResult:
    summary: dict[str, float | str]
    equity_curve: pd.DataFrame
    cashflow_log: pd.DataFrame
    trigger_log: pd.DataFrame
