from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from binance.client import Client


def _to_ms(date_str: str) -> int:
    """Convert 'YYYY-MM-DD' or ISO date string to milliseconds UTC.

    This helper is forgiving: it will try pandas parsing if stdlib fails.
    """
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except Exception:
        ts = pd.to_datetime(date_str, utc=True)
        return int(ts.timestamp() * 1000)


@dataclass
class FundingFetcher:
    """Fetch historical futures funding rates (USDT- or COIN-margined)."""

    symbol: str
    start_date: str
    end_date: Optional[str] = None
    coin_margined: bool = False
    sleep_seconds: float = 0.2
    client: Optional[Client] = None

    def fetch(self) -> pd.DataFrame:
        client = self.client or Client("_", "_")
        api = (
            client.futures_coin_funding_rate
            if self.coin_margined
            else client.futures_funding_rate
        )

        start_ms = _to_ms(self.start_date)
        end_ms = _to_ms(self.end_date) if self.end_date else None

        rows = []
        while True:
            params = {"symbol": self.symbol, "startTime": start_ms, "limit": 1000}
            if end_ms:
                params["endTime"] = end_ms
            chunk = api(**params)
            if not chunk:
                break
            rows.extend(chunk)
            last_ms = chunk[-1]["fundingTime"]
            next_ms = last_ms + 1
            if end_ms and next_ms >= end_ms:
                break
            start_ms = next_ms
            time.sleep(self.sleep_seconds)

        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df["fundingTime"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True)
        df["fundingRate"] = df["fundingRate"].astype(float)
        return df[["symbol", "fundingTime", "fundingRate"]]


