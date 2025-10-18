from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import pandas as pd

from config import FEE_CONFIG
from .base import Strategy


@dataclass
class DailyBreakoutParams:
    breakout_lookback: int = 50
    exit_lookback: int = 20
    atr_period: int = 14
    risk_per_trade: float = 0.01
    atr_position_multiplier: float = 2.0
    maker_fee: float = field(default_factory=lambda: FEE_CONFIG.maker_fee)
    taker_fee: float = field(default_factory=lambda: FEE_CONFIG.taker_fee)


@dataclass
class TradeRecord:
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    qty: float = 0.0
    pnl: float = 0.0
    pnl_r: float = 0.0
    fees: float = 0.0
    reason: str = ""
    risk_capital: float = 0.0


class DailyTrendBreakoutStrategy(Strategy):
    """Simplified Turtle-style breakout strategy on daily data (long-only)."""

    def __init__(self, params: Optional[DailyBreakoutParams] = None):
        self.params = params or DailyBreakoutParams()
        super().__init__(name="Daily Trend Breakout")

    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"])
            df = df.sort_values("time").set_index("time")

        df["high_breakout"] = df["high"].rolling(self.params.breakout_lookback).max().shift(1)
        df["low_exit"] = df["low"].rolling(self.params.exit_lookback).min().shift(1)

        df["atr"] = (
            pd.concat(
                [
                    (df["high"] - df["low"]),
                    (df["high"] - df["close"].shift(1)).abs(),
                    (df["low"] - df["close"].shift(1)).abs(),
                ],
                axis=1,
            ).max(axis=1)
        ).rolling(self.params.atr_period).mean()

        df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["high_breakout", "low_exit", "atr"])
        return df

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError("Use simulate() for execution-driven strategy.")

    def simulate(self, data: pd.DataFrame, initial_capital: float = 1_000.0):
        df = self.prepare_data(data)
        params = self.params

        equity_net = initial_capital
        total_fees = 0.0
        equity_curve = []
        timestamps = []

        position = 0
        qty = 0.0
        entry_price = 0.0
        atr_at_entry = 0.0
        risk_capital = 0.0

        trade_record: Optional[TradeRecord] = None
        trades: List[TradeRecord] = []

        for ts, row in df.iterrows():
            timestamps.append(ts)

            breakout_level = row["high_breakout"]
            exit_level = row["low_exit"]
            atr = row["atr"]
            price = row["close"]

            if position == 0:
                if price > breakout_level and atr > 0:
                    risk_capital = equity_net * params.risk_per_trade
                    risk_per_unit = params.atr_position_multiplier * atr
                    qty = risk_capital / risk_per_unit if risk_per_unit > 0 else 0.0
                    if qty > 0:
                        entry_price = price
                        atr_at_entry = atr
                        fee = qty * entry_price * params.taker_fee
                        equity_net -= fee
                        total_fees += fee
                        trade_record = TradeRecord(
                            entry_time=ts,
                            entry_price=entry_price,
                            qty=qty,
                            fees=fee,
                            risk_capital=risk_capital,
                        )
                        position = 1

            else:
                should_exit = price < exit_level
                if should_exit:
                    exit_price = price
                    fee = qty * exit_price * params.taker_fee
                    pnl = (exit_price - entry_price) * qty
                    equity_net += pnl - fee
                    total_fees += fee
                    if trade_record:
                        trade_record.exit_time = ts
                        trade_record.exit_price = exit_price
                        trade_record.pnl = pnl
                        trade_record.fees += fee
                        trade_record.reason = "exit_breakdown"
                        trade_record.pnl_r = pnl / risk_capital if risk_capital else 0.0
                        trades.append(trade_record)

                    position = 0
                    qty = 0.0
                    entry_price = 0.0
                    atr_at_entry = 0.0
                    risk_capital = 0.0
                    trade_record = None

            current_equity = equity_net
            if position == 1 and qty > 0:
                current_equity += (price - entry_price) * qty
            equity_curve.append(current_equity)

        if position == 1 and qty > 0:
            final_price = df.iloc[-1]["close"]
            fee = qty * final_price * params.taker_fee
            pnl = (final_price - entry_price) * qty
            equity_net += pnl - fee
            total_fees += fee
            if trade_record:
                trade_record.exit_time = df.index[-1]
                trade_record.exit_price = final_price
                trade_record.pnl = pnl
                trade_record.fees += fee
                trade_record.reason = "final_close"
                trade_record.pnl_r = pnl / risk_capital if risk_capital else 0.0
                trades.append(trade_record)
            equity_curve[-1] = equity_net

        equity_series = pd.Series(equity_curve, index=timestamps)
        total_return_net = equity_series.iloc[-1] / initial_capital - 1

        prepared = df.copy()
        prepared["equity_net"] = equity_series

        return {
            "trades": trades,
            "equity_net": equity_series,
            "equity_gross": equity_series + total_fees,  # rough gross approximation
            "total_return_net": total_return_net,
            "total_return_gross": total_return_net + total_fees / initial_capital,
            "fees_paid": total_fees,
            "data": prepared,
        }
