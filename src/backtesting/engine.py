from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from strategies.base import Strategy
from config import FEE_CONFIG
@dataclass
class BacktestResult:
    strategy_name: str
    dataset: Optional[Path]
    total_return_net: float
    total_return_gross: float
    buy_and_hold_return: float
    annual_return: Optional[float]
    max_drawdown: Optional[float]
    sharpe_ratio: Optional[float]
    trades: int
    fees_paid: float
    equity_curve_net: pd.Series
    equity_curve_gross: pd.Series
    signals: pd.DataFrame
    trades_log: List = field(default_factory=list)
    summary: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy_name,
            "dataset": str(self.dataset) if self.dataset else None,
            "total_return_net": self.total_return_net,
            "total_return_gross": self.total_return_gross,
            "buy_and_hold_return": self.buy_and_hold_return,
            "annual_return": self.annual_return,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "trades": self.trades,
            "fees_paid": self.fees_paid,
        }


def _run_advanced_backtest(
    data: pd.DataFrame,
    strategy: Strategy,
    dataset: Optional[Path],
    initial_capital: float,
) -> BacktestResult:
    sim_output = strategy.simulate(data.copy(), initial_capital=initial_capital)
    equity_net: pd.Series = sim_output["equity_net"]
    equity_gross: pd.Series = sim_output["equity_gross"]
    trades_log = sim_output.get("trades", [])
    fees_paid = sim_output.get("fees_paid", 0.0)
    total_return_net = sim_output.get("total_return_net", 0.0)
    total_return_gross = sim_output.get("total_return_gross", 0.0)
    prepared_data: pd.DataFrame = sim_output.get("data")
    summary = sim_output.get("summary")

    if prepared_data is None or prepared_data.empty:
        raise ValueError("Prepared data is empty after indicator calculation.")

    buy_hold_returns = prepared_data["close"].pct_change().fillna(0)
    buy_hold_curve = (1 + buy_hold_returns).cumprod() * initial_capital
    buy_and_hold_return = buy_hold_curve.iloc[-1] / initial_capital - 1 if not buy_hold_curve.empty else 0.0

    periods_per_year = _infer_periods_per_year(prepared_data)
    returns = equity_net.pct_change()
    returns = returns.replace([np.inf, -np.inf], np.nan).fillna(0)
    sharpe_ratio = _compute_sharpe_ratio(returns, periods_per_year)
    annual_return = _annualize_return(total_return_net, len(equity_net), periods_per_year)
    max_drawdown = _compute_max_drawdown(equity_net)

    signals = pd.DataFrame(
        {
            "equity_net": equity_net,
            "equity_gross": equity_gross,
        }
    )

    return BacktestResult(
        strategy_name=strategy.name,
        dataset=dataset,
        total_return_net=total_return_net,
        total_return_gross=total_return_gross,
        buy_and_hold_return=buy_and_hold_return,
        annual_return=annual_return,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe_ratio,
        trades=len(trades_log),
        fees_paid=fees_paid,
        equity_curve_net=equity_net,
        equity_curve_gross=equity_gross,
        signals=signals,
        trades_log=trades_log,
        summary=summary,
    )


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time")
    return df.reset_index(drop=True)


def run_backtest(
    data: pd.DataFrame,
    strategy: Strategy,
    dataset: Optional[Path] = None,
    initial_capital: float = 1_000.0,
    fee_rate: Optional[float] = None,
) -> BacktestResult:
    if hasattr(strategy, "simulate") and callable(getattr(strategy, "simulate")):
        return _run_advanced_backtest(
            data=data,
            strategy=strategy,
            dataset=dataset,
            initial_capital=initial_capital,
        )

    if data.empty:
        raise ValueError("Input data is empty.")
    if "close" not in data.columns:
        raise ValueError("Data must include a 'close' column.")

    df = strategy.generate_signals(data.copy())
    if "signal" not in df.columns:
        raise ValueError("Strategy must create a 'signal' column.")

    df["signal"] = df["signal"].ffill().fillna(0).clip(-1, 1)

    df["position"] = df["signal"]
    df["returns"] = df["close"].pct_change().fillna(0)

    df["strategy_returns_gross"] = df["returns"] * df["position"]

    applied_fee = fee_rate if fee_rate is not None else FEE_CONFIG.get_rate()
    turnover = df["position"].diff().abs()
    turnover.iloc[0] = abs(df["position"].iloc[0])
    turnover = turnover.fillna(0)
    df["fees_rate"] = turnover * applied_fee
    df["strategy_returns_net"] = df["strategy_returns_gross"] - df["fees_rate"]

    equity_curve_gross = (1 + df["strategy_returns_gross"]).cumprod() * initial_capital
    equity_curve_net = (1 + df["strategy_returns_net"]).cumprod() * initial_capital
    buy_and_hold_curve = (1 + df["returns"]).cumprod() * initial_capital

    total_return_gross = equity_curve_gross.iloc[-1] / initial_capital - 1
    total_return_net = equity_curve_net.iloc[-1] / initial_capital - 1
    buy_and_hold_return = buy_and_hold_curve.iloc[-1] / initial_capital - 1

    fees_paid = (equity_curve_gross - equity_curve_net).iloc[-1]

    max_drawdown = _compute_max_drawdown(equity_curve_net)
    periods_per_year = _infer_periods_per_year(df)
    annual_return = _annualize_return(total_return_net, len(df), periods_per_year)
    sharpe_ratio = _compute_sharpe_ratio(df["strategy_returns_net"], periods_per_year)

    trades = int(turnover.sum())

    signals = df[
        [
            "time",
            "close",
            "position",
            "returns",
            "strategy_returns_gross",
            "strategy_returns_net",
            "fees_rate",
        ]
        + [
            col
            for col in df.columns
            if col
            not in {
                "time",
                "close",
                "position",
                "returns",
                "strategy_returns_gross",
                "strategy_returns_net",
                "fees_rate",
                "signal",
            }
        ]
    ].copy()
    signals["signal"] = df["signal"]

    return BacktestResult(
        strategy_name=strategy.name,
        dataset=dataset,
        total_return_net=total_return_net,
        total_return_gross=total_return_gross,
        buy_and_hold_return=buy_and_hold_return,
        annual_return=annual_return,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe_ratio,
        trades=trades,
        fees_paid=fees_paid,
        equity_curve_net=equity_curve_net,
        equity_curve_gross=equity_curve_gross,
        signals=signals,
        trades_log=[],
    )


def run_backtests_on_directory(
    directory: Path,
    strategy: Strategy,
    pattern: str = "*.csv",
    initial_capital: float = 1_000.0,
    fee_rate: Optional[float] = None,
) -> List[BacktestResult]:
    paths = sorted(directory.glob(pattern))
    results: List[BacktestResult] = []
    for path in paths:
        df = load_dataset(path)
        results.append(
            run_backtest(
                df,
                strategy,
                dataset=path,
                initial_capital=initial_capital,
                fee_rate=fee_rate,
            )
        )
    return results


def _compute_max_drawdown(equity_curve: pd.Series) -> Optional[float]:
    if equity_curve.empty:
        return None
    running_max = equity_curve.cummax()
    drawdowns = equity_curve / running_max - 1
    return float(drawdowns.min())


def _infer_periods_per_year(df: pd.DataFrame) -> Optional[float]:
    if "time" in df.columns:
        times = pd.to_datetime(df["time"])
    elif isinstance(df.index, pd.DatetimeIndex):
        times = df.index.to_series()
    else:
        return None

    diffs = times.diff().dropna()
    if diffs.empty:
        return None

    median_seconds = diffs.dt.total_seconds().median()
    if median_seconds is None or median_seconds <= 0:
        return None

    seconds_per_year = 365.25 * 24 * 60 * 60
    return seconds_per_year / median_seconds


def _annualize_return(total_return: float, periods: int, periods_per_year: Optional[float]) -> Optional[float]:
    if periods_per_year is None or periods <= 0:
        return None
    compounded = (1 + total_return) ** (periods_per_year / periods) - 1
    return float(compounded)


def _compute_sharpe_ratio(returns: pd.Series, periods_per_year: Optional[float]) -> Optional[float]:
    if periods_per_year is None or returns.empty:
        return None
    std = returns.std(ddof=0)
    if std == 0 or pd.isna(std):
        return None
    mean = returns.mean()
    return float((mean / std) * sqrt(periods_per_year))
