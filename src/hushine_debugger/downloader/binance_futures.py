from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

import pandas as pd
import requests


BASE_URL = "https://fapi.binance.com/fapi/v1/klines"
COLUMNS = ["timestamp", "open", "high", "low", "close", "volume", "symbol", "market", "interval"]


class HTTPSession(Protocol):
    def get(self, url: str, *, params: dict, timeout: int):
        ...


@dataclass(frozen=True)
class DownloadProgress:
    symbol: str
    interval: str
    start_ms: int
    end_ms: int
    cursor_ms: int
    downloaded_bars: int
    expected_bars: int
    percent: float


def interval_to_ms(interval: str) -> int:
    text = str(interval).strip()
    if len(text) < 2:
        raise ValueError(f"unsupported interval: {interval}")
    unit = text[-1]
    amount = int(text[:-1])
    scale = {
        "m": 60_000,
        "h": 60 * 60_000,
        "d": 24 * 60 * 60_000,
        "w": 7 * 24 * 60 * 60_000,
    }.get(unit)
    if scale is None:
        raise ValueError(f"unsupported interval: {interval}")
    return amount * scale


def parse_klines(raw: list[list], *, symbol: str, interval: str) -> pd.DataFrame:
    rows = []
    for item in raw:
        rows.append(
            {
                "timestamp": int(item[0]),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
                "symbol": symbol.upper(),
                "market": "futures",
                "interval": interval,
            }
        )
    return pd.DataFrame(rows, columns=COLUMNS)


def download_klines(
    *,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    session: HTTPSession | None = None,
    on_progress: Callable[[DownloadProgress], None] | None = None,
) -> pd.DataFrame:
    client = session or requests
    rows: list[pd.DataFrame] = []
    cursor = int(start_ms)
    step_ms = interval_to_ms(interval)
    expected_bars = max(0, (int(end_ms) - int(start_ms)) // step_ms)
    while cursor < int(end_ms):
        resp = client.get(
            BASE_URL,
            params={
                "symbol": symbol.upper(),
                "interval": interval,
                "startTime": cursor,
                "endTime": int(end_ms) - 1,
                "limit": 1500,
            },
            timeout=20,
        )
        resp.raise_for_status()
        raw = resp.json()
        if not raw:
            break
        frame = parse_klines(raw, symbol=symbol, interval=interval)
        rows.append(frame)
        next_cursor = int(frame["timestamp"].max()) + step_ms
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if on_progress is not None:
            downloaded_bars = sum(len(chunk) for chunk in rows)
            percent = 100.0 if expected_bars == 0 else min(100.0, round(downloaded_bars / expected_bars * 100, 1))
            on_progress(
                DownloadProgress(
                    symbol=symbol.upper(),
                    interval=interval,
                    start_ms=int(start_ms),
                    end_ms=int(end_ms),
                    cursor_ms=cursor,
                    downloaded_bars=downloaded_bars,
                    expected_bars=expected_bars,
                    percent=percent,
                )
            )
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    return pd.concat(rows, ignore_index=True).drop_duplicates(subset=["timestamp", "symbol", "market", "interval"])


def save_to_cache(root: str | Path, df: pd.DataFrame, *, symbol: str, interval: str) -> Path:
    target = Path(root) / "data" / "cache" / "binance" / "futures" / interval / symbol.upper()
    target.mkdir(parents=True, exist_ok=True)
    path = target / "klines.parquet"
    frames = [df]
    if path.exists():
        frames.append(pd.read_parquet(path))
    merged = pd.concat(frames, ignore_index=True)
    merged = (
        merged.drop_duplicates(subset=["timestamp", "symbol", "market", "interval"])
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    merged.to_parquet(path, index=False)
    return path
