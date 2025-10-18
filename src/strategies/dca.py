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

        purchases: List[PurchaseRecord] = []
        equity_curve = []
        timestamps = []

        for ts, row in df.iterrows():
            price = row.get("contribution_price")
            if not pd.isna(price):
                usd = params.contribution_usd
                quantity = usd / price
                fee = usd * params.maker_fee  # assume maker execution
                total_invested += usd
                total_fees += fee
                total_quantity += quantity

                purchases.append(
                    PurchaseRecord(
                        time=ts,
                        price=price,
                        quantity=quantity,
                        fee=fee,
                        cumulative_quantity=total_quantity,
                        cumulative_invested=total_invested,
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
