from dataclasses import replace
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from backtesting.engine import load_dataset, run_backtest
from strategies import (
    BuyAndHoldStrategy,
    MovingAverageCrossStrategy,
    MTFTrendBreakoutStrategy,
    Strategy,
    StrategyParams,
    VWAPZScoreParams,
    VWAPZScoreStrategy,
    EMARibbonStrategy,
    EMARibbonParams,
    DailyTrendBreakoutStrategy,
    DailyBreakoutParams,
    DCAStrategy,
    DCAParams,
)
from optimization import grid_search


def choose_dataset(base_dir: Path) -> Path:
    files = sorted(base_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"Directory {base_dir} does not contain CSV datasets.")

    print("Available datasets:")
    for idx, path in enumerate(files, start=1):
        print(f"  {idx}. {path.name}")

    while True:
        choice = input("Select dataset by number or enter a custom path: ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                return files[idx]
            print("Invalid number, try again.")
            continue
        custom_path = Path(choice)
        if custom_path.exists():
            return custom_path
        print("File not found, try again.")


def choose_strategy():
    print("\nStrategies:")
    print("  1. Buy & Hold")
    print("  2. Moving Average Crossover")
    print("  3. MTF Trend Breakout")
    print("  4. VWAP Z-Score Mean Reversion")
    print("  5. EMA Ribbon Pullback")
    print("  6. Daily Trend Breakout")
    print("  7. DCA Strategy")

    while True:
        choice = input("Select strategy [1]: ").strip() or "1"
        if choice == "1":
            return BuyAndHoldStrategy(), None
        if choice == "2":
            fast = _ask_int("Fast MA period", default=12)
            slow = _ask_int("Slow MA period", default=26)
            return MovingAverageCrossStrategy(fast_period=fast, slow_period=slow), None
        if choice == "3":
            if _ask_yes_no("Run parameter optimization for MTF Trend Breakout? [y/N]: "):
                return None, optimize_mtf_trend
            donchian = _ask_choice("Donchian lookback", options=[20, 24], default=20)
            atr_mult = _ask_choice_float("ATR stop multiplier", options=[1.25, 1.5, 1.75], default=1.5)
            vol_threshold = _ask_choice_float(
                "Volatility threshold (ATR/Price)",
                options=[0.006, 0.008, 0.010],
                default=0.008,
            )
            time_stop = _ask_choice("Time stop (M15 bars)", options=[16, 24, 32], default=24)
            params = StrategyParams(
                donchian_period=donchian,
                atr_multiplier=atr_mult,
                volatility_threshold=vol_threshold,
                time_stop_bars=time_stop,
            )
            return MTFTrendBreakoutStrategy(params=params), None
        if choice == "4":
            if _ask_yes_no("Run parameter optimization for VWAP Z-Score? [y/N]: "):
                return None, optimize_vwap_zscore
            z_entry = _ask_choice_float("Z-entry threshold", options=[1.5, 2.0, 2.5], default=2.0)
            z_step = _ask_choice_float("Z-step spacing", options=[0.5, 0.75, 1.0], default=0.5)
            max_steps = _ask_choice("Max steps", options=[2, 3], default=3)
            std_window = _ask_choice("Std window (minutes)", options=[20, 30, 45], default=30)
            time_stop = _ask_choice("Time stop (minutes)", options=[60, 90, 120], default=90)
            params = VWAPZScoreParams(
                z_entry=z_entry,
                z_step=z_step,
                max_steps=max_steps,
                std_window=std_window,
                time_stop_minutes=time_stop,
            )
            print("Hint: use the 1-minute dataset and ensure funding CSV is available at data/funding_BTCUSDT_USDT.csv.")
            return VWAPZScoreStrategy(params=params), None
        if choice == "5":
            if _ask_yes_no("Run parameter optimization for EMA Ribbon? [y/N]: "):
                return None, optimize_ema_ribbon
            atr_stop = _ask_choice_float("ATR stop multiplier", options=[1.0, 1.2, 1.5], default=1.2)
            atr_trail = _ask_choice_float("ATR trail multiplier", options=[0.5, 0.8, 1.0], default=0.8)
            reward = _ask_choice_float("Reward multiple", options=[1.5, 1.8, 2.0], default=1.8)
            max_trades = _ask_choice("Max trades per day", options=[4, 6, 8], default=6)
            params = EMARibbonParams(
                atr_stop_multiplier=atr_stop,
                atr_trail_multiplier=atr_trail,
                reward_r_multiple=reward,
                max_trades_per_day=max_trades,
            )
            print("Hint: use the 15-minute dataset for EMA ribbon strategy.")
            return EMARibbonStrategy(params=params), None
        if choice == "6":
            if _ask_yes_no("Run parameter optimization for Daily Trend Breakout? [y/N]: "):
                return None, optimize_daily_breakout
            breakout = _ask_choice("Breakout lookback", options=[40, 50, 60], default=50)
            exit_lb = _ask_choice("Exit lookback", options=[10, 20, 30], default=20)
            atr_mult = _ask_choice_float("ATR position multiplier", options=[1.5, 2.0, 2.5], default=2.0)
            params = DailyBreakoutParams(
                breakout_lookback=breakout,
                exit_lookback=exit_lb,
                atr_position_multiplier=atr_mult,
            )
            print("Hint: use the daily dataset (1d) for this strategy.")
            return DailyTrendBreakoutStrategy(params=params), None
        if choice == "7":
            contribution = _ask_choice_float("Monthly contribution (USD)", options=[500, 1000, 1500], default=1000.0)
            params = DCAParams(contribution_usd=contribution)
            print("Hint: DCA работает на любом таймфрейме; для чистого месячного графика выберите daily CSV.")
            return DCAStrategy(params=params), None
        print("Unknown strategy, try again.")


def _ask_int(prompt: str, default: int) -> int:
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        if not raw:
            return default
        if raw.isdigit():
            return int(raw)
        try:
            return int(raw)
        except ValueError:
            print("Please enter a valid integer.")


def _ask_choice(prompt: str, options, default):
    opts = ", ".join(str(opt) for opt in options)
    while True:
        raw = input(f"{prompt} ({opts}) [{default}]: ").strip()
        if not raw:
            return default
        try:
            value = int(raw)
            if value in options:
                return value
        except ValueError:
            pass
        print(f"Please choose one of: {opts}")


def _ask_choice_float(prompt: str, options, default):
    opts = ", ".join(f"{opt:.3f}" if isinstance(opt, float) else str(opt) for opt in options)
    while True:
        raw = input(f"{prompt} ({opts}) [{default}]: ").strip()
        if not raw:
            return default
        try:
            value = float(raw)
            if value in options:
                return value
        except ValueError:
            pass
        print(f"Please choose one of: {opts}")


def _ask_yes_no(prompt: str, default: bool = False) -> bool:
    raw = input(prompt).strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes"}


def format_percent(value) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100: .2f}%"


def main():
    base_dir = Path("data")
    dataset_path = choose_dataset(base_dir)
    strategy, optimizer = choose_strategy()

    df = load_dataset(dataset_path)
    if optimizer:
        optimizer(df, dataset_path)
        return

    result = run_backtest(df, strategy, dataset=dataset_path)

    print("\n=== Backtest Summary ===")
    print(f"Strategy        : {result.strategy_name}")
    print(f"Dataset         : {dataset_path}")
    print(f"Net Return      : {format_percent(result.total_return_net)}")
    print(f"Gross Return    : {format_percent(result.total_return_gross)}")
    print(f"Buy & Hold      : {format_percent(result.buy_and_hold_return)}")
    print(f"Annual Return   : {format_percent(result.annual_return)}")
    print(f"Max Drawdown    : {format_percent(result.max_drawdown)}")
    print(f"Sharpe Ratio    : {result.sharpe_ratio if result.sharpe_ratio is not None else 'n/a'}")
    print(f"Trades Executed : {result.trades}")
    print(f"Fees Paid       : {result.fees_paid:,.2f}")
    print(f"Final Equity    : {result.equity_curve_net.iloc[-1]:,.2f}")
    if result.trades_log:
        print(f"Completed Trades: {len(result.trades_log)}")

    show_equity_chart(result)


def show_equity_chart(result):
    df = pd.DataFrame(
        {
            "Equity (Net)": result.equity_curve_net,
            "Equity (Gross)": result.equity_curve_gross,
        }
    ).dropna(how="all")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Equity (Net)"],
            name="Equity (Net)",
            line=dict(color="#1f77b4"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Equity (Gross)"],
            name="Equity (Gross)",
            line=dict(color="#ff7f0e", dash="dash"),
        )
    )
    fig.update_layout(
        title=f"Equity Curve — {result.strategy_name}",
        xaxis_title="Time",
        yaxis_title="Equity",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    try:
        fig.show()
    except PermissionError:
        output = f"equity_curve_{result.strategy_name.replace(' ', '_').lower()}.html"
        fig.write_html(output)
        print(f"Plotly display blocked; saved equity curve to {output}")

    summary = getattr(result, "summary", None)
    if summary:
        invested = summary.get("total_invested")
        if invested is not None:
            print(f"Total invested: {invested:,.2f} USD")


def display_optimization_results(entries, strategy_name: str, dataset_path: Path, top_n: int = 5):
    if not entries:
        print("No parameter combinations evaluated.")
        return

    print(f"\nOptimization results for {strategy_name} on {dataset_path}:")
    print(f"Tested {len(entries)} combinations; showing top {min(top_n, len(entries))}.")

    header = f"{'Rank':>4}  {'Net%':>8}  {'Sharpe':>8}  {'MaxDD%':>8}  {'Trades':>6}  Params"
    print(header)
    print("-" * len(header))

    for idx, entry in enumerate(entries[:top_n], start=1):
        result = entry.result
        params_str = ", ".join(f"{k}={v}" for k, v in entry.params.items())
        max_dd = result.max_drawdown * 100 if result.max_drawdown is not None else float("nan")
        sharpe = result.sharpe_ratio if result.sharpe_ratio is not None else float("nan")
        print(
            f"{idx:>4}  {result.total_return_net * 100:>8.2f}  {sharpe:>8.2f}  {max_dd:>8.2f}  {result.trades:>6}  {params_str}"
        )

    best = entries[0]
    print("\nBest parameters:")
    for k, v in best.params.items():
        print(f"  {k}: {v}")
    print(f"Net return: {best.result.total_return_net * 100:.2f}%  |  Sharpe: {best.result.sharpe_ratio}")
    show_equity_chart(best.result)


def optimize_mtf_trend(data: pd.DataFrame, dataset_path: Path):
    base_params = StrategyParams()
    param_grid = {
        "donchian_period": [20, 24],
        "atr_multiplier": [1.25, 1.5, 1.75],
        "volatility_threshold": [0.006, 0.008, 0.01],
        "time_stop_bars": [16, 24, 32],
    }

    entries = grid_search(
        data,
        param_grid,
        params_factory=lambda overrides: replace(base_params, **overrides),
        strategy_factory=lambda params: MTFTrendBreakoutStrategy(params=params),
        dataset=dataset_path,
    )
    display_optimization_results(entries, "MTF Trend Breakout", dataset_path)


def optimize_vwap_zscore(data: pd.DataFrame, dataset_path: Path):
    base_params = VWAPZScoreParams()
    param_grid = {
        "z_entry": [1.5, 2.0, 2.5],
        "z_step": [0.5, 0.75, 1.0],
        "max_steps": [2, 3],
        "std_window": [20, 30, 45],
        "time_stop_minutes": [60, 90, 120],
    }

    entries = grid_search(
        data,
        param_grid,
        params_factory=lambda overrides: replace(base_params, **overrides),
        strategy_factory=lambda params: VWAPZScoreStrategy(params=params),
        dataset=dataset_path,
    )
    display_optimization_results(entries, "VWAP Z-Score Mean Reversion", dataset_path)


def optimize_ema_ribbon(data: pd.DataFrame, dataset_path: Path):
    base_params = EMARibbonParams()
    param_grid = {
        "atr_stop_multiplier": [1.0, 1.2, 1.5],
        "atr_trail_multiplier": [0.5, 0.8, 1.0],
        "reward_r_multiple": [1.5, 1.8, 2.0],
        "max_trades_per_day": [4, 6, 8],
    }

    entries = grid_search(
        data,
        param_grid,
        params_factory=lambda overrides: replace(base_params, **overrides),
        strategy_factory=lambda params: EMARibbonStrategy(params=params),
        dataset=dataset_path,
    )
    display_optimization_results(entries, "EMA Ribbon Pullback", dataset_path)


def optimize_daily_breakout(data: pd.DataFrame, dataset_path: Path):
    base_params = DailyBreakoutParams()
    param_grid = {
        "breakout_lookback": [40, 50, 60],
        "exit_lookback": [10, 20, 30],
        "atr_position_multiplier": [1.5, 2.0, 2.5],
    }

    entries = grid_search(
        data,
        param_grid,
        params_factory=lambda overrides: replace(base_params, **overrides),
        strategy_factory=lambda params: DailyTrendBreakoutStrategy(params=params),
        dataset=dataset_path,
    )
    display_optimization_results(entries, "Daily Trend Breakout", dataset_path)


if __name__ == "__main__":
    main()
