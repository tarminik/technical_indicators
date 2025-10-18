from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from config import FEE_CONFIG
from indicators import ta
from .base import Strategy


def compute_donchian(high: pd.Series, low: pd.Series, period: int) -> pd.DataFrame:
    upper = high.rolling(period, min_periods=period).max()
    lower = low.rolling(period, min_periods=period).min()
    return pd.DataFrame({"donchian_high": upper, "donchian_low": lower})


def compute_vwap_day(df: pd.DataFrame) -> pd.Series:
    day = df.index.date
    pv = (df["close"] * df["volume"]).groupby(day).cumsum()
    vol = df["volume"].groupby(day).cumsum().replace(0, np.nan)
    vwap = pv / vol
    return vwap


def resample_h1(df: pd.DataFrame) -> pd.DataFrame:
    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    h1 = df.resample("1h", label="right", closed="right").agg(agg).dropna()
    return h1


@dataclass
class StrategyParams:
    donchian_period: int = 20
    atr_multiplier: float = 1.5
    volatility_threshold: float = 0.008  # 0.8%
    time_stop_bars: int = 24
    break_even_trigger: float = 1.0
    partial_take_profit: float = 1.5
    trail_multiplier: float = 1.5
    risk_per_trade: float = 0.006  # 0.6%
    partial_fraction: float = 0.5
    daily_loss_limit_r: float = 2.0
    weekly_loss_limit_r: float = 5.0
    maker_fee: float = field(default_factory=lambda: FEE_CONFIG.maker_fee)
    taker_fee: float = field(default_factory=lambda: FEE_CONFIG.taker_fee)


@dataclass
class TradeRecord:
    direction: int
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    qty_initial: float = 0.0
    qty_exit: float = 0.0
    pnl: float = 0.0
    pnl_r: float = 0.0
    fees: float = 0.0
    reason: str = ""
    partials: List[Dict] = field(default_factory=list)
    risk_capital: float = 0.0


class MTFTrendBreakoutStrategy(Strategy):
    """
    Multi-timeframe trend breakout strategy with VWAP support and ATR-based risk management.
    Funding filter is ignored (assumed zero).
    """

    def __init__(self, params: Optional[StrategyParams] = None):
        self.params = params or StrategyParams()
        super().__init__(name="MTF Trend Breakout")

    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time").set_index("time")

        h1 = resample_h1(df)
        h1["ema50"] = h1["close"].ewm(span=50, adjust=False).mean()
        h1["ema200"] = h1["close"].ewm(span=200, adjust=False).mean()
        atr_h1 = ta.ATR(h1.reset_index(), period=14)
        h1["atr14"] = atr_h1.values

        h1 = h1.replace([np.inf, -np.inf], np.nan).ffill()
        df = df.join(h1[["close", "ema50", "ema200", "atr14"]], how="left", rsuffix="_h1")
        df["atr_ratio_h1"] = df["atr14"] / df["close_h1"]

        don = compute_donchian(df["high"], df["low"], self.params.donchian_period)
        df = df.join(don)

        atr_m15 = ta.ATR(df.reset_index(), period=20)
        df["atr_m15"] = atr_m15.values
        df["vwap_daily"] = compute_vwap_day(df)

        df = df.replace([np.inf, -np.inf], np.nan).ffill()
        return df.dropna(subset=["close_h1", "ema50", "ema200", "atr14", "donchian_high", "donchian_low", "atr_m15"])

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError("Use simulate_trades for execution-driven strategy.")

    # Simulation / execution -------------------------------------------------
    def simulate(self, data: pd.DataFrame, initial_capital: float = 1_000.0):
        df = self.prepare_data(data)
        params = self.params

        equity_net = initial_capital
        equity_gross = initial_capital
        high_water_mark_net = equity_net
        total_fees = 0.0

        position = 0
        qty = 0.0
        entry_price = 0.0
        stop_price = 0.0
        trade_risk = 0.0
        bars_in_trade = 0
        break_even = False
        partial_taken = False
        trade_record: Optional[TradeRecord] = None
        trades: List[TradeRecord] = []

        daily_r = 0.0
        weekly_r = 0.0
        current_day = None
        current_week = None
        daily_paused_until = None
        weekly_paused_until = None

        equity_net_curve = []
        equity_gross_curve = []
        timestamps = []

        for ts, row in df.iterrows():
            timestamps.append(ts)

            day = ts.date()
            week = ts.isocalendar()[:2]

            if current_day != day:
                current_day = day
                daily_r = 0.0
                daily_paused_until = None

            if current_week != week:
                current_week = week
                weekly_r = 0.0
                weekly_paused_until = None

            # position management ------------------------------------------------
            if position != 0:
                bars_in_trade += 1
                atr = row["atr_m15"]
                move = (row["close"] - entry_price) * position

                # Break-even activation
                if not break_even and move >= params.break_even_trigger * atr:
                    stop_price = entry_price
                    break_even = True

                # Trailing stop after breakeven
                if break_even:
                    trail = row["close"] - position * params.trail_multiplier * atr
                    if position == 1:
                        stop_price = max(stop_price, trail)
                    else:
                        stop_price = min(stop_price, trail)

                exit_reason = None
                exit_price = None
                exit_qty = qty

                # Partial take profit
                if not partial_taken:
                    target_move = params.partial_take_profit * atr
                    if (position == 1 and row["high"] >= entry_price + target_move) or (
                        position == -1 and row["low"] <= entry_price - target_move
                    ):
                        target_price = entry_price + position * target_move
                        partial_qty = qty * params.partial_fraction
                        realised = (target_price - entry_price) * partial_qty * position
                        fee = abs(target_price * partial_qty) * params.taker_fee
                        equity_net += realised - fee
                        equity_gross += realised
                        total_fees += fee
                        partial_taken = True
                        if trade_record:
                            trade_record.partials.append(
                                {
                                    "time": ts,
                                    "price": target_price,
                                    "qty": partial_qty,
                                    "pnl": realised,
                                    "fee": fee,
                                }
                            )
                            trade_record.pnl += realised
                            trade_record.fees += fee
                            trade_record.qty_exit += partial_qty
                        qty -= partial_qty

                # Stop loss / trailing
                if position == 1 and row["low"] <= stop_price:
                    exit_price = stop_price
                    exit_reason = "stop"
                elif position == -1 and row["high"] >= stop_price:
                    exit_price = stop_price
                    exit_reason = "stop"

                # Time stop
                if exit_price is None and bars_in_trade >= params.time_stop_bars:
                    exit_price = row["close"]
                    exit_reason = "time"

                if exit_price is not None:
                    fee = abs(exit_price * qty) * params.taker_fee
                    pnl = (exit_price - entry_price) * qty * position
                    equity_net += pnl - fee
                    equity_gross += pnl
                    total_fees += fee

                    if trade_record:
                        trade_record.exit_time = ts
                        trade_record.exit_price = exit_price
                        trade_record.qty_exit += exit_qty
                        trade_record.pnl += pnl
                        trade_record.fees += fee
                        trade_record.reason = exit_reason
                        trade_record.pnl_r = trade_record.pnl / trade_record.risk_capital if trade_record.risk_capital else 0
                        trades.append(trade_record)

                        daily_r += trade_record.pnl_r
                        weekly_r += trade_record.pnl_r

                        if daily_r <= -params.daily_loss_limit_r:
                            daily_paused_until = day
                        if weekly_r <= -params.weekly_loss_limit_r:
                            weekly_paused_until = week

                    position = 0
                    qty = 0.0
                    bars_in_trade = 0
                    break_even = False
                    partial_taken = False
                    trade_record = None

            # Entry logic ---------------------------------------------------------
            can_trade = position == 0
            if can_trade:
                if daily_paused_until == day:
                    can_trade = False
                if weekly_paused_until == week:
                    can_trade = False

            if can_trade:
                long_mode = (
                    row["close_h1"] > row["ema200"]
                    and row["ema50"] > row["ema200"]
                    and row["atr_ratio_h1"] >= params.volatility_threshold
                )
                short_mode = (
                    row["close_h1"] < row["ema200"]
                    and row["ema50"] < row["ema200"]
                    and row["atr_ratio_h1"] >= params.volatility_threshold
                )

                atr = row["atr_m15"]
                if np.isnan(atr) or atr <= 0:
                    long_mode = short_mode = False

                entered = False
                direction = 0
                entry_signal_price = None

                if long_mode and row["close"] >= row["donchian_high"] and row["close"] >= row["vwap_daily"]:
                    direction = 1
                    entry_signal_price = row["close"]
                elif short_mode and row["close"] <= row["donchian_low"] and row["close"] <= row["vwap_daily"]:
                    direction = -1
                    entry_signal_price = row["close"]

                if direction != 0 and entry_signal_price is not None:
                    entry_price = entry_signal_price
                    stop_offset = params.atr_multiplier * atr
                    stop_price = entry_price - direction * stop_offset
                    trade_risk = stop_offset
                    if trade_risk <= 0:
                        continue

                    # Adaptive risk sizing based on drawdown
                    risk_pct = params.risk_per_trade
                    if equity_net < 0.9 * high_water_mark_net:
                        risk_pct *= 0.5

                    risk_capital = equity_net * risk_pct
                    qty = risk_capital / trade_risk
                    if qty <= 0:
                        continue

                    fee = abs(entry_price * qty) * params.maker_fee
                    equity_net -= fee
                    total_fees += fee

                    position = direction
                    bars_in_trade = 0
                    break_even = False
                    partial_taken = False

                    trade_record = TradeRecord(
                        direction=direction,
                        entry_time=ts,
                        entry_price=entry_price,
                        qty_initial=qty,
                    )
                    trade_record.fees += fee
                    trade_record.risk_capital = risk_capital
                    entered = True

            # Equity tracking ------------------------------------------------------
            high_water_mark_net = max(high_water_mark_net, equity_net)

            unrealised = 0.0
            if position != 0 and qty > 0:
                unrealised = (row["close"] - entry_price) * qty * position

            equity_net_curve.append(equity_net + unrealised)
            equity_gross_curve.append(equity_gross + unrealised)

        # Force exit at last bar if position remains
        if position != 0 and len(df) > 0:
            final_ts = timestamps[-1]
            final_close = df.iloc[-1]["close"]
            fee = abs(final_close * qty) * params.taker_fee
            pnl = (final_close - entry_price) * qty * position
            equity_net += pnl - fee
            equity_gross += pnl
            total_fees += fee
            if trade_record:
                trade_record.exit_time = final_ts
                trade_record.exit_price = final_close
                trade_record.qty_exit += qty
                trade_record.pnl += pnl
                trade_record.fees += fee
                trade_record.reason = "final_close"
                trade_record.pnl_r = trade_record.pnl / trade_record.risk_capital if trade_record.risk_capital else 0
                trades.append(trade_record)
            if equity_net_curve:
                equity_net_curve[-1] = equity_net
            if equity_gross_curve:
                equity_gross_curve[-1] = equity_gross

        equity_series_net = pd.Series(equity_net_curve, index=timestamps)
        equity_series_gross = pd.Series(equity_gross_curve, index=timestamps)

        total_return_net = equity_series_net.iloc[-1] / initial_capital - 1
        total_return_gross = equity_series_gross.iloc[-1] / initial_capital - 1

        return {
            "trades": trades,
            "equity_net": equity_series_net,
            "equity_gross": equity_series_gross,
            "total_return_net": total_return_net,
            "total_return_gross": total_return_gross,
            "fees_paid": total_fees,
            "data": df,
        }
