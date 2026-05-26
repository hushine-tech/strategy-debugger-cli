from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataSlice:
    exchange: str
    market: str
    symbol: str
    interval: str
    path: str
