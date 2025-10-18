from __future__ import annotations

import pandas as pd

from .base import Strategy


class BuyAndHoldStrategy(Strategy):
    """Simple baseline: stay long after the first candle."""

    def __init__(self):
        super().__init__(name="Buy & Hold")

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["signal"] = 1 if not df.empty else 0
        return df
