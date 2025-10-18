from __future__ import annotations

import pandas as pd

from .base import Strategy


class MovingAverageCrossStrategy(Strategy):
    """Enter long when the fast MA crosses above the slow MA, exit when it crosses below."""

    def __init__(self, fast_period: int = 12, slow_period: int = 26):
        if fast_period <= 0 or slow_period <= 0:
            raise ValueError("Periods must be positive integers.")
        if fast_period >= slow_period:
            raise ValueError("Fast period must be smaller than slow period.")
        self.fast_period = fast_period
        self.slow_period = slow_period
        super().__init__(name=f"MA Cross {fast_period}/{slow_period}")

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        if df.empty:
            df["signal"] = 0
            return df

        df["fast_ma"] = df["close"].rolling(self.fast_period).mean()
        df["slow_ma"] = df["close"].rolling(self.slow_period).mean()

        df["signal"] = 0
        crossover_up = df["fast_ma"] > df["slow_ma"]
        crossover_down = df["fast_ma"] < df["slow_ma"]
        df.loc[crossover_up, "signal"] = 1
        df.loc[crossover_down, "signal"] = -1

        df["signal"] = df["signal"].shift(1).fillna(0)
        df.loc[df["fast_ma"].isna() | df["slow_ma"].isna(), "signal"] = 0

        return df
