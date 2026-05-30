from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pandas as pd
import yaml

from hushine_debugger.init_workspace import init_workspace, write_manifest


DEFAULT_MARKET = "perpetual_futures"


@dataclass(frozen=True)
class ImportResult:
    parquet_path: Path
    symbol: str
    market: str
    interval: str


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "debug-package"


def _read_zip_text(archive: zipfile.ZipFile, name: str) -> str:
    with archive.open(name) as entry:
        return entry.read().decode("utf-8")


def _read_manifest(archive: zipfile.ZipFile) -> dict:
    if "manifest.yaml" not in archive.namelist():
        return {}
    return yaml.safe_load(_read_zip_text(archive, "manifest.yaml")) or {}


def _canonicalize_debug_parquet(raw: bytes, *, symbol: str, market: str, interval: str) -> pd.DataFrame:
    frame = pd.read_parquet(BytesIO(raw))
    if "timestamp_ms" in frame.columns and "timestamp" not in frame.columns:
        frame = frame.rename(columns={"timestamp_ms": "timestamp"})
    if "timestamp" not in frame.columns:
        raise ValueError("debug package data.parquet must include timestamp or timestamp_ms")
    for column in ("open", "high", "low", "close", "volume"):
        if column not in frame.columns:
            raise ValueError(f"debug package data.parquet must include {column}")
    frame = frame.copy()
    frame["symbol"] = symbol.upper()
    frame["market"] = market.lower()
    frame["interval"] = interval
    return frame[["timestamp", "open", "high", "low", "close", "volume", "symbol", "market", "interval"]]


def import_debug_package(package_path: str | Path, root: str | Path = ".") -> ImportResult:
    workspace = Path(root)
    init_workspace(workspace)
    package = Path(package_path)
    with zipfile.ZipFile(package) as archive:
        names = set(archive.namelist())
        if "data.parquet" not in names:
            raise ValueError("debug package is missing data.parquet")
        manifest = _read_manifest(archive)
        symbol = str(manifest.get("symbol") or "BTCUSDT").upper()
        market = str(manifest.get("market") or DEFAULT_MARKET).lower()
        interval = str(manifest.get("interval") or "1m")
        if "wallet.yaml" in names:
            (workspace / "wallet.yaml").write_text(_read_zip_text(archive, "wallet.yaml"), encoding="utf-8")
        if "strategy.py.template" in names:
            (workspace / "strategy.py.template").write_text(
                _read_zip_text(archive, "strategy.py.template"),
                encoding="utf-8",
            )
            write_manifest(workspace)
        config = {
            "strategy_file": "strategy.py",
            "strategy_profile": "debug-package-v1",
            "exchange": str(manifest.get("exchange") or "binance"),
            "market": market,
            "symbol": symbol,
            "interval": interval,
            "data_source_order": ["imports"],
            "download_if_missing": False,
        }
        raw = archive.read("data.parquet")
        frame = _canonicalize_debug_parquet(raw, symbol=symbol, market=market, interval=interval)
        imports_dir = workspace / "data" / "imports"
        imports_dir.mkdir(parents=True, exist_ok=True)
        output = imports_dir / f"{_safe_name(package.stem)}.parquet"
        frame.to_parquet(output, index=False)
        config["data_files"] = [str(output.relative_to(workspace))]
        (workspace / "hushine-debug.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        return ImportResult(parquet_path=output, symbol=symbol, market=market, interval=interval)
