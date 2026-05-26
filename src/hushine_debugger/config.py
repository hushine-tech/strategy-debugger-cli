from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class DebugConfig:
    strategy_file: str
    exchange: str
    symbol: str
    market: str
    interval: str
    start: str | None
    end: str | None
    start_time_ms: int | None
    end_time_ms: int | None
    data_source_order: tuple[str, ...]
    data_files: tuple[str, ...]
    download_if_missing: bool


def _parse_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _parse_time_ms(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    normalized = text.replace("Z", "+00:00")
    return int(datetime.fromisoformat(normalized).timestamp() * 1000)


def _parse_data_source_order(value: Any) -> tuple[str, ...]:
    if value is None:
        return ("bundled", "imports", "cache")
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


def load_config(root: str | Path) -> DebugConfig:
    data = yaml.safe_load((Path(root) / "hushine-debug.yaml").read_text(encoding="utf-8")) or {}
    start = str(data["start"]) if data.get("start") else None
    end = str(data["end"]) if data.get("end") else None
    return DebugConfig(
        strategy_file=str(data.get("strategy_file") or "strategy.py"),
        exchange=str(data.get("exchange") or "binance").lower(),
        symbol=str(data.get("symbol") or "BTCUSDT").upper(),
        market=str(data.get("market") or "futures").lower(),
        interval=str(data.get("interval") or "1m"),
        start=start,
        end=end,
        start_time_ms=_parse_time_ms(start),
        end_time_ms=_parse_time_ms(end),
        data_source_order=_parse_data_source_order(data.get("data_source_order")),
        data_files=tuple(str(item) for item in data.get("data_files") or ()),
        download_if_missing=_parse_bool(data.get("download_if_missing"), True),
    )


def load_initial_balance(root: str | Path) -> float:
    data = yaml.safe_load((Path(root) / "wallet.yaml").read_text(encoding="utf-8")) or {}
    return float(data.get("initial_balance") or 1000.0)
