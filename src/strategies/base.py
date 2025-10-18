from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd


class Strategy(ABC):
    """Abstract base class for trading strategies."""

    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Return a dataframe with a `signal` column (-1, 0, 1)."""
        raise NotImplementedError
