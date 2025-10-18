from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

import pandas as pd

from backtesting.engine import BacktestResult, run_backtest


@dataclass
class OptimizationEntry:
    params: Dict[str, Any]
    result: BacktestResult

    @property
    def net_return(self) -> float:
        return self.result.total_return_net

    @property
    def sharpe(self) -> Optional[float]:
        return self.result.sharpe_ratio

    @property
    def max_drawdown(self) -> Optional[float]:
        return self.result.max_drawdown

    @property
    def trades(self) -> int:
        return self.result.trades


def grid_search(
    data: pd.DataFrame,
    param_grid: Dict[str, Iterable[Any]],
    params_factory: Callable[[Dict[str, Any]], Any],
    strategy_factory: Callable[[Any], Any],
    initial_capital: float = 1_000.0,
    dataset: Optional[Path] = None,
) -> List[OptimizationEntry]:
    keys = list(param_grid.keys())
    values = [list(param_grid[key]) for key in keys]
    entries: List[OptimizationEntry] = []

    for combination in product(*values):
        overrides = dict(zip(keys, combination))
        params = params_factory(overrides)
        strategy = strategy_factory(params)
        result = run_backtest(data, strategy, dataset=dataset, initial_capital=initial_capital)
        entries.append(OptimizationEntry(params=overrides, result=result))

    entries.sort(key=lambda entry: entry.net_return, reverse=True)
    return entries
