from __future__ import annotations

from dataclasses import asdict

import numpy as np
import pandas as pd

from .models import BacktestConfig, BacktestResult


class BacktestEngine:
    def run(self, history: pd.DataFrame, config: BacktestConfig) -> BacktestResult:
        frame = history.copy().sort_values("trade_date").reset_index(drop=True)
        if frame.empty:
            raise ValueError("History is empty")
        if config.price_field not in frame.columns:
            raise ValueError(f"Missing price field: {config.price_field}")

        price_col = config.price_field
        frame["trade_date"] = pd.to_datetime(frame["trade_date"])
        frame["is_dca_day"] = self._build_schedule(frame, config)
        frame["price"] = frame[price_col].astype(float)
        if (frame["price"] <= 0).any():
            raise ValueError("Non-positive prices found in history")

        peak_price = 0.0
        triggered_thresholds: set[float] = set()
        total_shares = 0.0
        total_base_contribution = 0.0
        total_dip_contribution = 0.0
        cashflow_rows: list[dict[str, float | str]] = []
        trigger_rows: list[dict[str, float | str]] = []
        equity_rows: list[dict[str, float | str]] = []

        for row in frame.itertuples(index=False):
            trade_date = pd.Timestamp(row.trade_date)
            price = float(row.price)
            if price > peak_price:
                peak_price = price
                triggered_thresholds.clear()

            drawdown = 0.0 if peak_price == 0 else price / peak_price - 1.0
            base_amount = config.base_contribution if config.enable_dca and row.is_dca_day else 0.0
            dip_amount = 0.0

            if config.enable_dip_buy:
                for threshold in config.normalized_thresholds():
                    if drawdown <= -threshold and threshold not in triggered_thresholds:
                        triggered_thresholds.add(threshold)
                        amount = config.base_contribution * config.dip_multiplier
                        dip_amount += amount
                        trigger_rows.append(
                            {
                                "trade_date": trade_date,
                                "threshold": threshold,
                                "drawdown": drawdown,
                                "extra_contribution": amount,
                                "price": price,
                            }
                        )

            trade_amount = base_amount + dip_amount
            shares_bought = trade_amount / price if trade_amount > 0 else 0.0
            total_shares += shares_bought
            total_base_contribution += base_amount
            total_dip_contribution += dip_amount

            if base_amount > 0:
                cashflow_rows.append(
                    {
                        "trade_date": trade_date,
                        "event_type": "dca",
                        "amount": base_amount,
                        "price": price,
                        "shares_bought": base_amount / price,
                        "drawdown": drawdown,
                    }
                )
            if dip_amount > 0:
                cashflow_rows.append(
                    {
                        "trade_date": trade_date,
                        "event_type": "dip",
                        "amount": dip_amount,
                        "price": price,
                        "shares_bought": dip_amount / price,
                        "drawdown": drawdown,
                    }
                )

            market_value = total_shares * price
            total_contribution = total_base_contribution + total_dip_contribution
            equity_rows.append(
                {
                    "trade_date": trade_date,
                    "price": price,
                    "shares": total_shares,
                    "invested_capital": total_contribution,
                    "market_value": market_value,
                    "equity_gain": market_value - total_contribution,
                    "strategy_drawdown": 0.0,
                }
            )

        equity_curve = pd.DataFrame(equity_rows)
        equity_curve["equity_peak"] = equity_curve["market_value"].cummax()
        equity_curve["strategy_drawdown"] = np.where(
            equity_curve["equity_peak"] > 0,
            equity_curve["market_value"] / equity_curve["equity_peak"] - 1.0,
            0.0,
        )

        cashflow_log = pd.DataFrame(cashflow_rows)
        trigger_log = pd.DataFrame(trigger_rows)
        summary = self._build_summary(
            config=config,
            equity_curve=equity_curve,
            cashflow_log=cashflow_log,
            total_base_contribution=total_base_contribution,
            total_dip_contribution=total_dip_contribution,
        )
        return BacktestResult(
            summary=summary,
            equity_curve=equity_curve,
            cashflow_log=cashflow_log,
            trigger_log=trigger_log,
        )

    def compare(self, history: pd.DataFrame, config: BacktestConfig) -> pd.DataFrame:
        pure_dca = BacktestConfig(
            **{
                **asdict(config),
                "enable_dip_buy": False,
            }
        )
        combo = BacktestConfig(**asdict(config))
        results = [
            ("pure_dca", self.run(history, pure_dca).summary),
            ("dca_plus_dip", self.run(history, combo).summary),
        ]
        return pd.DataFrame([{**summary, "strategy": name} for name, summary in results])

    def _build_schedule(self, history: pd.DataFrame, config: BacktestConfig) -> pd.Series:
        dates = pd.to_datetime(history["trade_date"])
        if config.frequency == "weekly":
            return dates.dt.weekday.eq(config.weekly_anchor)
        if config.frequency == "monthly":
            month_rank = dates.groupby(dates.dt.to_period("M")).rank(method="first")
            return month_rank.eq(config.monthly_anchor)
        raise ValueError(f"Unsupported frequency: {config.frequency}")

    def _build_summary(
        self,
        *,
        config: BacktestConfig,
        equity_curve: pd.DataFrame,
        cashflow_log: pd.DataFrame,
        total_base_contribution: float,
        total_dip_contribution: float,
    ) -> dict[str, float | str]:
        final_value = float(equity_curve["market_value"].iloc[-1])
        total_contribution = total_base_contribution + total_dip_contribution
        total_return = final_value - total_contribution
        total_return_pct = total_return / total_contribution if total_contribution else 0.0
        elapsed_days = max(
            1,
            int((equity_curve["trade_date"].iloc[-1] - equity_curve["trade_date"].iloc[0]).days),
        )
        elapsed_years = elapsed_days / 365.25
        cagr = (
            (final_value / total_contribution) ** (1 / elapsed_years) - 1
            if total_contribution > 0 and final_value > 0 and elapsed_years > 0
            else 0.0
        )
        average_cost = total_contribution / equity_curve["shares"].iloc[-1] if equity_curve["shares"].iloc[-1] else 0.0
        return {
            "symbol": config.symbol,
            "frequency": config.frequency,
            "start_date": equity_curve["trade_date"].iloc[0].date().isoformat(),
            "end_date": equity_curve["trade_date"].iloc[-1].date().isoformat(),
            "base_contribution": config.base_contribution,
            "dip_multiplier": config.dip_multiplier,
            "drawdown_thresholds": ",".join(str(x) for x in config.normalized_thresholds()),
            "total_contribution": round(total_contribution, 2),
            "total_base_contribution": round(total_base_contribution, 2),
            "total_dip_contribution": round(total_dip_contribution, 2),
            "final_value": round(final_value, 2),
            "total_return": round(total_return, 2),
            "total_return_pct": round(total_return_pct, 6),
            "cagr": round(cagr, 6),
            "max_drawdown": round(float(equity_curve["strategy_drawdown"].min()), 6),
            "ending_shares": round(float(equity_curve["shares"].iloc[-1]), 6),
            "average_cost": round(float(average_cost), 6),
            "trade_count": int(len(cashflow_log)),
        }
