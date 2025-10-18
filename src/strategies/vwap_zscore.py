from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import pandas as pd

from config import FEE_CONFIG
from .base import Strategy


def compute_daily_vwap(df: pd.DataFrame) -> pd.Series:
    day = df.index.date
    pv = (df["close"] * df["volume"]).groupby(day).cumsum()
    vol = df["volume"].groupby(day).cumsum().replace(0, np.nan)
    return pv / vol


def load_funding(path: str) -> pd.DataFrame:
    funding = pd.read_csv(path)
    if "fundingTime" not in funding.columns:
        raise ValueError("Funding CSV must contain 'fundingTime' column.")
    funding["fundingTime"] = pd.to_datetime(funding["fundingTime"], utc=True, format="mixed").dt.tz_convert(None)
    funding = funding.sort_values("fundingTime").set_index("fundingTime")
    funding = funding.rename(columns={"fundingRate": "funding_rate"})
    return funding[["funding_rate"]]


@dataclass
class VWAPZScoreParams:
    z_entry: float = 2.0
    z_step: float = 0.5
    max_steps: int = 3
    std_window: int = 30  # minutes
    time_stop_minutes: int = 90
    catastrophic_sigma: float = 3.5
    risk_per_trade: float = 0.004
    funding_threshold: float = 0.0005  # 0.05%
    maker_fee: float = field(default_factory=lambda: FEE_CONFIG.maker_fee)
    taker_fee: float = field(default_factory=lambda: FEE_CONFIG.taker_fee)
    funding_path: str = "data/funding_BTCUSDT_USDT.csv"


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
    steps_filled: int = 0
    risk_capital: float = 0.0


class VWAPZScoreStrategy(Strategy):
    """VWAP z-score mean-reversion strategy with laddered entries and funding filter."""

    def __init__(self, params: Optional[VWAPZScoreParams] = None):
        self.params = params or VWAPZScoreParams()
        self._funding = load_funding(self.params.funding_path)
        super().__init__(name="VWAP Z-Score Mean Reversion")

    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        if "time" not in df.columns:
            raise ValueError("Dataset must contain 'time' column.")
        df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time").set_index("time")

        df["vwap"] = compute_daily_vwap(df)
        df["sigma"] = df["close"].rolling(window=self.params.std_window).std(ddof=0)
        df["zscore"] = (df["close"] - df["vwap"]) / df["sigma"]

        funding = self._funding.reindex(df.index, method="ffill").fillna(0.0)
        df = df.join(funding, how="left")
        df["funding_rate"] = df["funding_rate"].fillna(0.0)

        df = df.dropna(subset=["vwap", "sigma", "zscore"])
        df = df.replace([np.inf, -np.inf], np.nan).dropna()
        return df

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

        position = 0  # -1 short, +1 long
        steps_filled = 0
        qty_total = 0.0
        avg_entry = 0.0
        risk_capital = 0.0
        stop_distance = 0.0
        stop_price = 0.0
        trade_start_time: Optional[pd.Timestamp] = None
        sigma_entry = 0.0
        time_in_position = 0
        high_water_mark = equity_net

        trade_record: Optional[TradeRecord] = None
        trades: List[TradeRecord] = []

        for ts, row in df.iterrows():
            timestamps.append(ts)

            price = row["close"]
            vwap = row["vwap"]
            sigma = row["sigma"]
            zscore = row["zscore"]
            funding_rate = row["funding_rate"]

            # Manage existing position ----------------------------------------------
            if position != 0:
                time_in_position += 1
                exit_reason = None
                exit_price = None

                if position == 1:
                    # Catastrophic stop first
                    if row["low"] <= stop_price:
                        exit_price = stop_price
                        exit_reason = "stop"
                    elif row["high"] >= vwap:
                        exit_price = vwap
                        exit_reason = "vwap"
                else:
                    if row["high"] >= stop_price:
                        exit_price = stop_price
                        exit_reason = "stop"
                    elif row["low"] <= vwap:
                        exit_price = vwap
                        exit_reason = "vwap"

                if exit_price is None and time_in_position >= params.time_stop_minutes:
                    exit_price = price
                    exit_reason = "time"

                if exit_price is not None:
                    fee = abs(exit_price * qty_total) * params.taker_fee
                    pnl = (exit_price - avg_entry) * qty_total * position
                    equity_net += pnl - fee
                    total_fees += fee

                    if trade_record:
                        trade_record.exit_time = ts
                        trade_record.exit_price = exit_price
                        trade_record.qty_exit = qty_total
                        trade_record.pnl = pnl
                        trade_record.fees += fee
                        trade_record.reason = exit_reason or ""
                        trade_record.pnl_r = pnl / risk_capital if risk_capital else 0.0
                        trades.append(trade_record)

                    position = 0
                    steps_filled = 0
                    qty_total = 0.0
                    avg_entry = 0.0
                    risk_capital = 0.0
                    stop_distance = 0.0
                    stop_price = 0.0
                    sigma_entry = 0.0
                    time_in_position = 0
                    trade_start_time = None
                    trade_record = None
                else:
                    # Ladder additional steps if deeper signal
                    desired_steps = steps_filled
                    if position == 1 and zscore <= -params.z_entry:
                        desired_steps = min(
                            params.max_steps,
                            int((abs(zscore) - params.z_entry) // params.z_step) + 1,
                        )
                    elif position == -1 and zscore >= params.z_entry:
                        desired_steps = min(
                            params.max_steps,
                            int((abs(zscore) - params.z_entry) // params.z_step) + 1,
                        )

                    while steps_filled < desired_steps and sigma_entry > 0:
                        qty_step = risk_capital / (stop_distance * params.max_steps)
                        if qty_step <= 0:
                            break
                        fee = abs(price * qty_step) * params.maker_fee
                        total_fees += fee
                        equity_net -= fee
                        prev_qty = qty_total
                        qty_total += qty_step
                        avg_entry = (
                            (avg_entry * prev_qty + price * qty_step) / qty_total if prev_qty > 0 else price
                        )
                        stop_price = avg_entry - position * stop_distance
                        steps_filled += 1
                        if trade_record:
                            trade_record.qty_initial = qty_total
                            trade_record.fees += fee
                            trade_record.steps_filled = steps_filled

            # No position or after exit: check for new entries ----------------------
            if position == 0:
                direction = 0
                desired_steps = 0
                if sigma > 0:
                    if zscore <= -params.z_entry and funding_rate <= params.funding_threshold:
                        direction = 1
                        desired_steps = min(
                            params.max_steps,
                            int((abs(zscore) - params.z_entry) // params.z_step) + 1,
                        )
                    elif zscore >= params.z_entry and funding_rate >= -params.funding_threshold:
                        direction = -1
                        desired_steps = min(
                            params.max_steps,
                            int((abs(zscore) - params.z_entry) // params.z_step) + 1,
                        )

                if direction != 0 and desired_steps > 0:
                    risk_pct = params.risk_per_trade
                    if equity_net < 0.9 * high_water_mark:
                        risk_pct *= 0.5
                    risk_capital = equity_net * risk_pct
                    stop_distance = params.catastrophic_sigma * sigma
                    if risk_capital > 0 and stop_distance > 0:
                        qty_step = risk_capital / (stop_distance * params.max_steps)
                        if qty_step > 0:
                            steps_filled = 0
                            qty_total = 0.0
                            avg_entry = 0.0
                            total_fee_entry = 0.0

                            for _ in range(desired_steps):
                                fee = abs(price * qty_step) * params.maker_fee
                                total_fees += fee
                                total_fee_entry += fee
                                equity_net -= fee
                                prev_qty = qty_total
                                qty_total += qty_step
                                avg_entry = (
                                    (avg_entry * prev_qty + price * qty_step) / qty_total if prev_qty > 0 else price
                                )
                                steps_filled += 1
                            position = direction
                            sigma_entry = sigma
                            stop_price = avg_entry - position * stop_distance
                            trade_start_time = ts
                            time_in_position = 0
                            trade_record = TradeRecord(
                                direction=direction,
                                entry_time=ts,
                                entry_price=avg_entry,
                                qty_initial=qty_total,
                                fees=total_fee_entry,
                                steps_filled=steps_filled,
                                risk_capital=risk_capital,
                            )

            high_water_mark = max(high_water_mark, equity_net)
            unrealised = 0.0
            if position != 0 and qty_total > 0:
                unrealised = (price - avg_entry) * qty_total * position

            equity_net_curve.append(equity_net + unrealised)
            equity_gross_curve.append(equity_net + total_fees + unrealised)

        # Force exit at final price if still in trade
        if position != 0 and qty_total > 0:
            final_ts = timestamps[-1]
            final_price = df.iloc[-1]["close"]
            fee = abs(final_price * qty_total) * params.taker_fee
            pnl = (final_price - avg_entry) * qty_total * position
            equity_net += pnl - fee
            total_fees += fee
            if trade_record:
                trade_record.exit_time = final_ts
                trade_record.exit_price = final_price
                trade_record.qty_exit = qty_total
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
