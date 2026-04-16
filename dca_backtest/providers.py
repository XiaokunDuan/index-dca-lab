from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf


class DataProvider(ABC):
    @abstractmethod
    def fetch_history(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Return normalized daily history."""


class LocalCsvProvider(DataProvider):
    def __init__(self, csv_path: str | Path) -> None:
        self.csv_path = Path(csv_path)

    def fetch_history(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV not found: {self.csv_path}")

        frame = pd.read_csv(self.csv_path, parse_dates=["date"])
        required = {"date", "open", "high", "low", "close", "adj_close", "volume", "symbol"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"CSV missing required columns: {sorted(missing)}")

        filtered = frame.copy()
        filtered["symbol"] = filtered["symbol"].astype(str)
        symbol_mask = filtered["symbol"].str.upper().eq(symbol.upper())
        if symbol_mask.any():
            filtered = filtered.loc[symbol_mask]

        filtered = filtered.rename(columns={"date": "trade_date"})
        filtered["trade_date"] = pd.to_datetime(filtered["trade_date"])
        filtered = filtered.loc[
            (filtered["trade_date"] >= pd.Timestamp(start_date))
            & (filtered["trade_date"] <= pd.Timestamp(end_date))
        ].copy()
        filtered["dividend"] = 0.0
        filtered["split_factor"] = 0.0

        ordered = [
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
        return filtered[ordered].sort_values("trade_date").reset_index(drop=True)


class YahooFinanceProvider(DataProvider):
    def __init__(self, cache_dir: str | Path | None = None) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_history(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        cache_path = None
        if self.cache_dir:
            cache_path = self.cache_dir / f"{symbol}_{start_date}_{end_date}.csv"
            if cache_path.exists():
                cached = pd.read_csv(cache_path, parse_dates=["trade_date"])
                return cached

        history = yf.Ticker(symbol).history(
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            auto_adjust=False,
            actions=True,
        )
        if history.empty:
            raise ValueError(f"No history returned for {symbol} between {start_date} and {end_date}")

        normalized = history.reset_index().rename(
            columns={
                "Date": "trade_date",
                "Close": "close",
                "Adj Close": "adj_close",
                "Dividends": "dividend",
                "Stock Splits": "split_factor",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Volume": "volume",
            }
        )
        normalized["trade_date"] = pd.to_datetime(normalized["trade_date"]).dt.tz_localize(None)
        normalized["symbol"] = symbol
        normalized["dividend"] = normalized.get("dividend", 0.0).fillna(0.0)
        normalized["split_factor"] = normalized.get("split_factor", 0.0).fillna(0.0)

        expected = [
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
        normalized = normalized[expected].sort_values("trade_date").reset_index(drop=True)

        if cache_path:
            normalized.to_csv(cache_path, index=False)

        return normalized
