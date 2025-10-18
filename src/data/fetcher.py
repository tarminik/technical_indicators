import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
from binance.client import Client
from binance.helpers import convert_ts_str, interval_to_milliseconds
from tabulate import tabulate

from indicators import ta


class MarketDataFetcher:
    """Service for downloading market data (spot or futures) with optional indicators."""

    SUPPORTED_MARKETS = {"spot", "futures"}

    def __init__(
        self,
        pair: str = "DOGEUSDT",
        timeframe: str = Client.KLINE_INTERVAL_1DAY,
        start_date: str = "1 Jan, 1900",
        end_date: Optional[str] = "now",
        indicators: Optional[List[List]] = None,
        market: str = "spot",
        client: Optional[Client] = None,
    ):
        self.pair = pair
        self.timeframe = timeframe
        self.start_date = start_date
        self.end_date = end_date
        self.market = self._normalize_market(market)
        self.indicators = indicators or []
        self.ohlcv = pd.DataFrame()

        try:
            self.client = client or Client("_", "_")
        except Exception:
            print("\nCan not get data. Check your network connection.")
            sys.exit()

    def fetch(self) -> pd.DataFrame:
        klines = list(self._stream_klines())
        self.ohlcv = self._klines_to_dataframe(klines)

        if self.ohlcv.empty:
            print("No data received from Binance.")
            return self.ohlcv

        for indicator in self.indicators:
            self.add_indicator(indicator)

        return self.ohlcv

    @classmethod
    def _normalize_market(cls, market: str) -> str:
        value = (market or "spot").strip().lower()
        if not value or value == "spot":
            return "spot"
        if value in {"futures", "future", "f", "um", "usdt_futures", "usdt-futures"}:
            return "futures"
        raise ValueError(f"Unsupported market type: {market}")

    def _stream_klines(self) -> Iterable[List]:
        start_str = self._normalize_date(self.start_date)
        end_str = self._normalize_date(self.end_date)

        generator = self._klines_generator(start_str=start_str, end_str=end_str)
        total_estimate = self._estimate_total_candles(
            raw_start=self.start_date, raw_end=self.end_date
        )

        collected = 0
        last_percent = -1

        for kline in generator:
            collected += 1
            if total_estimate:
                percent = int(min(100, (collected / total_estimate) * 100))
                if percent >= last_percent + 5 or percent >= 100:
                    self._print_progress(percent, collected, total_estimate)
                    last_percent = percent
            elif collected % 200 == 0:
                self._print_progress(None, collected, None)

            yield kline

        if collected and total_estimate:
            self._print_progress(100, collected, total_estimate)
        elif collected and not total_estimate:
            self._print_progress(None, collected, None)

        if collected:
            print()

    def _klines_generator(self, start_str: Optional[str], end_str: Optional[str]):
        kwargs = {
            "symbol": self.pair,
            "interval": self.timeframe,
            "start_str": start_str,
            "end_str": end_str,
        }

        if self.market == "spot":
            return self.client.get_historical_klines_generator(**kwargs)
        if self.market == "futures":
            return self.client.futures_historical_klines_generator(**kwargs)

        raise ValueError(f"Unsupported market type: {self.market}")

    @staticmethod
    def _normalize_date(value: Optional[str]) -> Optional[str]:
        if value in (None, "", "now"):
            return None
        return value

    def _estimate_total_candles(
        self, raw_start: Optional[str], raw_end: Optional[str]
    ) -> Optional[int]:
        try:
            interval_ms = interval_to_milliseconds(self.timeframe)
        except Exception:
            interval_ms = None

        if not interval_ms:
            return None

        start_ts = self._to_milliseconds(raw_start)
        end_ts = self._to_milliseconds(raw_end)

        if start_ts is None:
            return None
        if end_ts is None:
            end_ts = int(pd.Timestamp.utcnow().timestamp() * 1000)
        if end_ts <= start_ts:
            return None

        total = (end_ts - start_ts) / interval_ms
        return max(1, int(total) + 1)

    @staticmethod
    def _to_milliseconds(value: Optional[str]) -> Optional[int]:
        if value in (None, ""):
            return None
        try:
            return convert_ts_str(value)
        except Exception:
            try:
                return int(pd.to_datetime(value).timestamp() * 1000)
            except Exception:
                return None

    @staticmethod
    def _print_progress(percent: Optional[int], count: int, total: Optional[int]) -> None:
        if percent is not None and total:
            percent = min(100, percent)
            message = f"Loading data: {percent:3d}% ({count}/{total})"
        else:
            message = f"Loading data: {count} klines fetched..."
        print(message, end="\r", flush=True)

    @staticmethod
    def _klines_to_dataframe(klines) -> pd.DataFrame:
        columns = [
            "time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
            "ignore",
        ]
        df = pd.DataFrame(klines, columns=columns)
        if df.empty:
            return pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])

        df = df.drop(
            columns=[
                "close_time",
                "quote_asset_volume",
                "number_of_trades",
                "taker_buy_base_asset_volume",
                "taker_buy_quote_asset_volume",
                "ignore",
            ],
            errors="ignore",
        )
        df["time"] = pd.to_datetime(df["time"], unit="ms")

        numeric_cols = ["open", "high", "low", "close", "volume"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

        return df.loc[:, ["time", "open", "high", "low", "close", "volume"]]

    def add_indicator(self, info: List):
        if not info:
            return

        name = str(info[0]).lower()

        if name == "sma":
            period = info[1]
            self.ohlcv[f"sma_{period}"] = ta.SMA(self.ohlcv, period)
        elif name == "smm":
            period = info[1]
            self.ohlcv[f"smm_{period}"] = ta.SMM(self.ohlcv, period)
        elif name == "ssma":
            period = info[1]
            self.ohlcv[f"ssma_{period}"] = ta.SSMA(self.ohlcv, period)
        elif name == "ema":
            period = info[1]
            self.ohlcv[f"ema_{period}"] = ta.EMA(self.ohlcv, period)
        elif name == "dema":
            period = info[1]
            self.ohlcv[f"dema_{period}"] = ta.DEMA(self.ohlcv, period)
        elif name == "tema":
            period = info[1]
            self.ohlcv[f"tema_{period}"] = ta.TEMA(self.ohlcv, period)
        elif name == "trima":
            period = info[1]
            self.ohlcv[f"trima_{period}"] = ta.TRIMA(self.ohlcv, period)
        elif name == "vama":
            period = info[1]
            self.ohlcv[f"vama_{period}"] = ta.VAMA(self.ohlcv, period)
        elif name == "wma":
            period = info[1]
            self.ohlcv[f"wma_{period}"] = ta.WMA(self.ohlcv, period)
        elif name == "smma":
            period = info[1]
            self.ohlcv[f"smma_{period}"] = ta.SMMA(self.ohlcv, period)
        elif name == "bbands":
            period = info[1]
            upper, middle, lower = ta.BBANDS(self.ohlcv, period)
            self.ohlcv[f"upper_bb_{period}"] = upper
            self.ohlcv[f"middle_bb_{period}"] = middle
            self.ohlcv[f"lower_bb_{period}"] = lower
        elif name == "macd":
            fast = info[1]
            slow = info[2]
            macd, signal, diff = ta.MACD(self.ohlcv, period_fast=fast, period_slow=slow)
            self.ohlcv[f"macd_{fast}_{slow}"] = macd
            self.ohlcv[f"macd_signal_{fast}_{slow}"] = signal
            self.ohlcv[f"macd_difference_{fast}_{slow}"] = diff
        elif name == "mom":
            period = info[1]
            self.ohlcv[f"mom_{period}"] = ta.MOM(self.ohlcv, period)
        elif name == "roc":
            period = info[1]
            self.ohlcv[f"roc_{period}"] = ta.ROC(self.ohlcv, period)
        elif name == "rsi":
            period = info[1]
            self.ohlcv[f"rsi_{period}"] = ta.RSI(self.ohlcv, period)
        elif name == "tr":
            period = info[1]
            self.ohlcv[f"tr_{period}"] = ta.TR(self.ohlcv, period)
        elif name == "atr":
            period = info[1]
            self.ohlcv[f"atr_{period}"] = ta.ATR(self.ohlcv, period)
        elif name == "volume":
            return
        elif name == "kc":
            period = info[1]
            upper, lower = ta.KC(self.ohlcv, period)
            self.ohlcv[f"kc_up_{period}"] = upper
            self.ohlcv[f"kc_down_{period}"] = lower
        elif name == "stoch":
            period = info[1]
            self.ohlcv[f"stoch_{period}"] = ta.STOCH(self.ohlcv, period)
        elif name == "williams":
            period = info[1]
            self.ohlcv[f"williams_{period}"] = ta.WILLIAMS(self.ohlcv, period)
        else:
            print("This indicator is not available yet")

    def beauty_print_data(self):
        if self.ohlcv.empty:
            print("No data loaded.")
            return
        print(tabulate(self.ohlcv, headers="keys", tablefmt="psql"))
        print(self.ohlcv.shape)

    def print_data(self):
        print(self.ohlcv)

    @staticmethod
    def _sanitize_token(raw_value) -> str:
        value = str(raw_value).strip()
        return re.sub(r"[^A-Za-z0-9._-]+", "_", value) or "unknown"

    @staticmethod
    def _format_timestamp(ts: pd.Timestamp) -> str:
        if pd.isna(ts):
            return "unknown"
        return ts.strftime("%Y-%m-%dT%H-%M-%S")

    def save_to_csv(self, directory: str = "data") -> Path:
        if self.ohlcv.empty:
            raise ValueError("No data available to save.")

        output_dir = Path(directory)
        output_dir.mkdir(parents=True, exist_ok=True)

        begin = self._format_timestamp(self.ohlcv["time"].iloc[0])
        end = self._format_timestamp(self.ohlcv["time"].iloc[-1])

        pair_token = self._sanitize_token(self.pair)
        timeframe_token = self._sanitize_token(self.timeframe)
        filename = f"{pair_token}-{begin}-{end}-{timeframe_token}.csv"
        filepath = output_dir / filename

        self.ohlcv.to_csv(filepath, index=False)
        return filepath
