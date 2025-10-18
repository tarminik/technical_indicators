from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from config import FEE_CONFIG
from .base import Strategy


@dataclass
class DCAParams:
    contribution_usd: float = 1000.0
    frequency: str = "MS"  # month start
    buy_on_red: bool = False
    ma_period: Optional[int] = None
    ma_condition: str = "below"  # 'below' or 'above'
    ma_timeframe: str = "daily"  # 'daily' or 'weekly200'
    carry_over: bool = True
    maker_fee: float = FEE_CONFIG.maker_fee
    taker_fee: float = FEE_CONFIG.taker_fee


@dataclass
class PurchaseRecord:
    time: pd.Timestamp
    price: float
    quantity: float
    fee: float
    cumulative_quantity: float
    cumulative_invested: float
    invested_usd: float


class DCAStrategy(Strategy):
    """Simple dollar-cost averaging strategy."""

    def __init__(self, params: Optional[DCAParams] = None):
        self.params = params or DCAParams()
        super().__init__(name="DCA Strategy")

    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        if "time" not in df.columns:
            raise ValueError("Dataset must contain 'time' column.")
        df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time").set_index("time")
        if self.params.ma_period:
            period = self.params.ma_period
            if self.params.ma_timeframe == "weekly200":
                weekly_close = df["close"].resample("W-SUN").last()
                weekly_ma = weekly_close.rolling(window=period).mean()
                df[f"ma_{period}w"] = weekly_ma.reindex(df.index, method="ffill")
            else:
                df[f"ma_{period}"] = df["close"].rolling(window=period).mean()
        return df

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError("Use simulate() for execution-driven strategy.")

    def simulate(self, data: pd.DataFrame, initial_capital: float = 0.0):
        df = self.prepare_data(data)
        params = self.params

        freq = params.frequency.upper()
        if freq == "M":
            freq = "ME"
        contributions = df.resample(freq, label="left", closed="left").first().dropna(subset=["close"])
        contribution_prices = contributions["close"]
        df["contribution_price"] = contribution_prices

        total_invested = 0.0
        total_fees = 0.0
        total_quantity = 0.0
        pending_usd = 0.0
        skipped_periods = 0
        contributions_made = 0

        purchases: List[PurchaseRecord] = []
        equity_curve = []
        timestamps = []

        for ts, row in df.iterrows():
            price = row.get("contribution_price")
            if not pd.isna(price):
                pending_usd += params.contribution_usd
                if not params.carry_over:
                    pending_usd = params.contribution_usd
                contributions_made += 1

                can_buy = price > 0
                if params.buy_on_red:
                    can_buy = can_buy and (row["close"] < row["open"])

                if can_buy and params.ma_period:
                    ma_col = f"ma_{params.ma_period}"
                    if params.ma_timeframe == "weekly200":
                        ma_col = f"ma_{params.ma_period}w"
                    ma_value = row.get(ma_col)
                    if pd.isna(ma_value):
                        can_buy = False
                    else:
                        if params.ma_condition == "below":
                            can_buy = can_buy and (row["close"] <= ma_value)
                        elif params.ma_condition == "above":
                            can_buy = can_buy and (row["close"] >= ma_value)

                if not can_buy:
                    skipped_periods += 1
                else:
                    usd_to_invest = pending_usd if params.carry_over else params.contribution_usd
                    if usd_to_invest > 0 and price > 0:
                        quantity = usd_to_invest / price
                        if quantity <= 0:
                            continue
                        fee = usd_to_invest * params.maker_fee  # assume maker execution
                        total_invested += usd_to_invest
                        total_fees += fee
                        total_quantity += quantity
                        pending_usd -= usd_to_invest
                        if pending_usd < 0:
                            pending_usd = 0.0

                        purchases.append(
                            PurchaseRecord(
                                time=ts,
                                price=price,
                                quantity=quantity,
                                fee=fee,
                                cumulative_quantity=total_quantity,
                                cumulative_invested=total_invested,
                                invested_usd=usd_to_invest,
                            )
                        )

            market_value = total_quantity * row["close"]
            equity_curve.append(market_value)
            timestamps.append(ts)

        equity_series = pd.Series(equity_curve, index=timestamps)
        net_return = (equity_series.iloc[-1] - total_invested) / total_invested if total_invested > 0 else 0.0

        summary = {
            "total_invested": total_invested,
            "final_market_value": equity_series.iloc[-1],
            "total_quantity": total_quantity,
            "average_price": total_invested / total_quantity if total_quantity > 0 else 0.0,
            "total_fees": total_fees,
            "net_return": net_return,
            "pending_usd": pending_usd,
            "contributions": contributions_made,
            "skipped_periods": skipped_periods,
        }

        prepared = df.copy()
        prepared["equity_net"] = equity_series

        return {
            "trades": purchases,
            "equity_net": equity_series,
            "equity_gross": equity_series + total_fees,
            "total_return_net": net_return,
            "total_return_gross": (equity_series.iloc[-1] + total_fees - total_invested) / total_invested if total_invested else 0.0,
            "fees_paid": total_fees,
            "data": prepared,
            "summary": summary,
        }
