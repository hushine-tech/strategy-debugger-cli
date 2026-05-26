from __future__ import annotations

from importlib.resources import files
from pathlib import Path


DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT")
DEFAULT_EXCHANGE = "binance"
DEFAULT_MARKET = "futures"
DEFAULT_INTERVAL = "1m"


def copy_default_data(root: str | Path) -> None:
    target_root = Path(root) / "data" / "bundled" / DEFAULT_EXCHANGE / DEFAULT_MARKET / DEFAULT_INTERVAL
    package_root = files("hushine_debugger.assets.default_data") / DEFAULT_EXCHANGE / DEFAULT_MARKET / DEFAULT_INTERVAL
    for symbol in DEFAULT_SYMBOLS:
        source = package_root / symbol / "klines.parquet"
        if not source.is_file():
            continue
        target = target_root / symbol / "klines.parquet"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
