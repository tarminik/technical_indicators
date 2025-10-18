from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import pandas as pd

from config import FEE_CONFIG
from indicators import ta
from .base import Strategy

EMA_SET = [8, 13, 21, 34, 55]


def resample_tf(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    return df.resample(rule, label="right", closed="right").agg(agg).dropna()


@dataclass
class EMARibbonParams:
    atr_period: int = 14
    atr_stop_multiplier: float = 1.2
    atr_trail_multiplier: float = 0.8
    reward_r_multiple: float = 1.8
    risk_per_trade: float = 0.005
    max_trades_per_day: int = 6
    time_stop_bars: int = 32  # M15 bars (~8 часов)
    maker_fee: float = field(default_factory=lambda: FEE_CONFIG.maker_fee)
    taker_fee: float = field(default_factory=lambda: FEE_CONFIG.taker_fee)


@dataclass
class TradeRecord:
    direction: int
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


class EMARibbonStrategy(Strategy):
    """EMA ribbon pullback strategy with higher timeframe trend filters."""

    def __init__(self, params: Optional[EMARibbonParams] = None):
        self.params = params or EMARibbonParams()
        super().__init__(name="EMA Ribbon Pullback")

    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        if "time" not in df.columns:
            raise ValueError("Dataset must include 'time'")
        df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time").set_index("time")

        for n in EMA_SET:
            df[f"ema{n}"] = df["close"].ewm(span=n, adjust=False).mean()

        atr = ta.ATR(df.reset_index(), period=self.params.atr_period)
        df["atr"] = atr.values

        h1 = resample_tf(df, "1h")
        h1["ema200"] = h1["close"].ewm(span=200, adjust=False).mean()
        h1["ema50"] = h1["close"].ewm(span=50, adjust=False).mean()

        h4 = resample_tf(df, "4h")
        h4["ema200"] = h4["close"].ewm(span=200, adjust=False).mean()

        df = df.join(
            h1[["close", "ema200", "ema50"]].rename(
                columns={"close": "close_h1", "ema200": "ema200_h1", "ema50": "ema50_h1"}
            ),
            how="left",
        )
        df = df.join(
            h4[["close", "ema200"]].rename(columns={"close": "close_h4", "ema200": "ema200_h4"}),
            how="left",
        )
        df = df.replace([np.inf, -np.inf], np.nan).ffill()
        needed = [f"ema{n}" for n in EMA_SET] + ["atr", "ema200_h1", "ema50_h1", "ema200_h4"]
        return df.dropna(subset=needed)

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError("Use simulate() for execution-driven strategy.")

    def simulate(self, data: pd.DataFrame, initial_capital: float = 1_000.0):
        df = self.prepare_data(data)
        params = self.params

        equity_net = initial_capital
        total_fees = 0.0
        equity_net_curve: List[float] = []
        equity_gross_curve: List[float] = []
        timestamps: List[pd.Timestamp] = []

        high_water_mark = equity_net

        position = 0
        qty = 0.0
        entry_price = 0.0
        stop_price = 0.0
        atr_at_entry = 0.0
        target_price = 0.0
        break_even = False
        bars_in_trade = 0
        risk_capital = 0.0

        current_day = None
        trades_today = 0

        trade_record: Optional[TradeRecord] = None
        trades: List[TradeRecord] = []

        min_low_tracker = df["low"].rolling(window=5, min_periods=1).min()
        max_high_tracker = df["high"].rolling(window=5, min_periods=1).max()

        for idx, (ts, row) in enumerate(df.iterrows()):
            timestamps.append(ts)
            day = ts.date()

            if current_day != day:
                current_day = day
                trades_today = 0

            atr = row["atr"]
            ema_values = [row[f"ema{n}"] for n in EMA_SET]
            ema8, ema13, ema21, ema34, ema55 = ema_values

            long_trend = (
                row["close_h1"] > row["ema200_h1"]
                and row["ema50_h1"] > row["ema200_h1"]
                and row["close_h4"] > row["ema200_h4"]
            )
            short_trend = (
                row["close_h1"] < row["ema200_h1"]
                and row["ema50_h1"] < row["ema200_h1"]
                and row["close_h4"] < row["ema200_h4"]
            )

            stacked_long = ema8 > ema13 > ema21 > ema34 > ema55
            stacked_short = ema8 < ema13 < ema21 < ema34 < ema55

            prev_row = df.iloc[idx - 1] if idx > 0 else None

            # Manage open position -------------------------------------------------
            if position != 0:
                bars_in_trade += 1

                # Move to break-even once price moves 1R
                if not break_even:
                    if (position == 1 and row["high"] >= entry_price + (target_price - entry_price) / params.reward_r_multiple) or (
                        position == -1 and row["low"] <= entry_price - (entry_price - target_price) / params.reward_r_multiple
                    ):
                        stop_price = entry_price
                        break_even = True

                # Trail stop with EMA34 +/- atr_trail
                if break_even:
                    trail = ema34 - position * params.atr_trail_multiplier * atr
                    if position == 1:
                        stop_price = max(stop_price, trail)
                    else:
                        stop_price = min(stop_price, trail)

                exit_reason = None
                exit_price = None

                if position == 1 and row["low"] <= stop_price:
                    exit_price = stop_price
                    exit_reason = "stop"
                elif position == -1 and row["high"] >= stop_price:
                    exit_price = stop_price
                    exit_reason = "stop"

                if exit_price is None:
                    if position == 1 and row["high"] >= target_price:
                        exit_price = target_price
                        exit_reason = "target"
                    elif position == -1 and row["low"] <= target_price:
                        exit_price = target_price
                        exit_reason = "target"

                if exit_price is None and bars_in_trade >= params.time_stop_bars:
                    exit_price = row["close"]
                    exit_reason = "time"

                if exit_price is not None:
                    fee = abs(exit_price * qty) * params.taker_fee
                    pnl = (exit_price - entry_price) * qty * position
                    equity_net += pnl - fee
                    total_fees += fee

                    if trade_record:
                        trade_record.exit_time = ts
                        trade_record.exit_price = exit_price
                        trade_record.pnl = pnl
                        trade_record.fees += fee
                        trade_record.reason = exit_reason or ""
                        trade_record.pnl_r = pnl / risk_capital if risk_capital else 0.0
                        trades.append(trade_record)

                    position = 0
                    qty = 0.0
                    entry_price = 0.0
                    stop_price = 0.0
                    target_price = 0.0
                    break_even = False
                    bars_in_trade = 0
                    risk_capital = 0.0
                    atr_at_entry = 0.0
                    trade_record = None

            # Entry logic ----------------------------------------------------------
            if position == 0 and trades_today < params.max_trades_per_day and atr > 0:
                risk_pct = params.risk_per_trade
                if equity_net < 0.9 * high_water_mark:
                    risk_pct *= 0.5
                potential_risk = equity_net * risk_pct

                if long_trend and stacked_long and prev_row is not None:
                    pullback = prev_row["close"] < prev_row["ema8"] and row["low"] <= ema21 and row["close"] > ema8
                    if pullback:
                        recent_low = min_low_tracker.loc[ts]
                        stop_distance = max(
                            params.atr_stop_multiplier * atr,
                            row["close"] - min(recent_low, ema55),
                        )
                        if stop_distance > 0:
                            qty = potential_risk / stop_distance
                            if qty > 0:
                                entry_price = row["close"]
                                stop_price = entry_price - stop_distance
                                target_price = entry_price + params.reward_r_multiple * stop_distance
                                fee = entry_price * qty * params.taker_fee
                                equity_net -= fee
                                total_fees += fee

                                position = 1
                                bars_in_trade = 0
                                break_even = False
                                risk_capital = potential_risk
                                atr_at_entry = atr
                                trade_record = TradeRecord(
                                    direction=1,
                                    entry_time=ts,
                                    entry_price=entry_price,
                                    qty=qty,
                                    fees=fee,
                                    risk_capital=risk_capital,
                                )
                                trades_today += 1

                elif short_trend and stacked_short and prev_row is not None:
                    pullback = prev_row["close"] > prev_row["ema8"] and row["high"] >= ema21 and row["close"] < ema8
                    if pullback:
                        recent_high = max_high_tracker.loc[ts]
                        stop_distance = max(
                            params.atr_stop_multiplier * atr,
                            max(recent_high, ema55) - row["close"],
                        )
                        if stop_distance > 0:
                            qty = potential_risk / stop_distance
                            if qty > 0:
                                entry_price = row["close"]
                                stop_price = entry_price + stop_distance
                                target_price = entry_price - params.reward_r_multiple * stop_distance
                                fee = entry_price * qty * params.taker_fee
                                equity_net -= fee
                                total_fees += fee

                                position = -1
                                bars_in_trade = 0
                                break_even = False
                                risk_capital = potential_risk
                                atr_at_entry = atr
                                trade_record = TradeRecord(
                                    direction=-1,
                                    entry_time=ts,
                                    entry_price=entry_price,
                                    qty=qty,
                                    fees=fee,
                                    risk_capital=risk_capital,
                                )
                                trades_today += 1

            high_water_mark = max(high_water_mark, equity_net)
            mark_price = row["close"]
            unrealised = 0.0
            if position != 0 and qty > 0:
                unrealised = (mark_price - entry_price) * qty * position

            equity_net_curve.append(equity_net + unrealised)
            equity_gross_curve.append(equity_net + total_fees + unrealised)

        # Close any open position at end
        if position != 0 and qty > 0:
            final_ts = timestamps[-1]
            final_price = df.iloc[-1]["close"]
            fee = final_price * qty * params.taker_fee
            pnl = (final_price - entry_price) * qty * position
            equity_net += pnl - fee
            total_fees += fee
            if trade_record:
                trade_record.exit_time = final_ts
                trade_record.exit_price = final_price
                trade_record.pnl = pnl
                trade_record.fees += fee
                trade_record.reason = "final_close"
                trade_record.pnl_r = pnl / risk_capital if risk_capital else 0.0
                trades.append(trade_record)
            if equity_net_curve:
                equity_net_curve[-1] = equity_net
            if equity_gross_curve:
                equity_gross_curve[-1] = equity_net + total_fees

        equity_series_net = pd.Series(equity_net_curve, index=timestamps)
        equity_series_gross = pd.Series(equity_gross_curve, index=timestamps)

        total_return_net = equity_series_net.iloc[-1] / initial_capital - 1
        total_return_gross = equity_series_gross.iloc[-1] / initial_capital - 1

        prepared = df.copy()
        prepared["equity_net"] = equity_series_net
        prepared["equity_gross"] = equity_series_gross

        return {
            "trades": trades,
            "equity_net": equity_series_net,
            "equity_gross": equity_series_gross,
            "total_return_net": total_return_net,
            "total_return_gross": total_return_gross,
            "fees_paid": total_fees,
            "data": prepared,
        }
