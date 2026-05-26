from __future__ import annotations

from pathlib import Path

import pandas as pd

from hushine_debugger.demo_data import DEFAULT_INTERVAL, DEFAULT_MARKET, DEFAULT_SYMBOLS
from hushine_debugger.downloader.binance_futures import download_klines


START_MS = 1735689600000
END_MS = 1738368000000
EXPECTED_BARS = 44_640


def _asset_root() -> Path:
    return Path(__file__).resolve().parents[1] / "src" / "hushine_debugger" / "assets" / "default_data"


def main() -> int:
    root = _asset_root() / "binance" / DEFAULT_MARKET / DEFAULT_INTERVAL
    for symbol in DEFAULT_SYMBOLS:
        print(f"Downloading {symbol} {DEFAULT_MARKET} {DEFAULT_INTERVAL} 2025-01", flush=True)
        events = []
        frame = download_klines(
            symbol=symbol,
            interval=DEFAULT_INTERVAL,
            start_ms=START_MS,
            end_ms=END_MS,
            on_progress=events.append,
        )
        if len(frame) != EXPECTED_BARS:
            raise SystemExit(f"{symbol}: expected {EXPECTED_BARS} bars, got {len(frame)}")
        timestamps = frame["timestamp"].astype(int)
        if int(timestamps.min()) != START_MS:
            raise SystemExit(f"{symbol}: unexpected first timestamp {int(timestamps.min())}")
        if int(timestamps.max()) != END_MS - 60_000:
            raise SystemExit(f"{symbol}: unexpected last timestamp {int(timestamps.max())}")
        target = root / symbol / "klines.parquet"
        target.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(target, index=False, compression="zstd")
        print(f"Wrote {target} ({len(frame)} bars)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
