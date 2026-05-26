from __future__ import annotations

from pathlib import Path

import pandas as pd

from hushine_strategy import MarketData


def _matching_klines(section_path: Path, *, symbol: str, market: str, interval: str) -> pd.DataFrame | None:
    frames = []
    for path in section_path.rglob("*.parquet"):
        frames.append(pd.read_parquet(path))
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    df = df[
        (df["symbol"].str.upper() == symbol.upper())
        & (df["market"].str.lower() == market.lower())
        & (df["interval"].astype(str) == interval)
    ].sort_values("timestamp")
    return df if not df.empty else None


def _load_files(root: Path, files: tuple[str, ...], *, symbol: str, market: str, interval: str) -> pd.DataFrame | None:
    frames = []
    for rel in files:
        path = root / rel
        if not path.exists():
            raise FileNotFoundError(f"configured data file does not exist: {rel}")
        frames.append(pd.read_parquet(path))
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    df = df[
        (df["symbol"].str.upper() == symbol.upper())
        & (df["market"].str.lower() == market.lower())
        & (df["interval"].astype(str) == interval)
    ].sort_values("timestamp")
    return df if not df.empty else None


def _apply_time_filter(df: pd.DataFrame, *, start_time_ms: int | None, end_time_ms: int | None) -> pd.DataFrame:
    if start_time_ms is not None:
        df = df[df["timestamp"] >= start_time_ms]
    if end_time_ms is not None:
        df = df[df["timestamp"] < end_time_ms]
    return df


def load_klines(
    root: str | Path,
    *,
    symbol: str,
    market: str,
    interval: str,
    data_source_order: tuple[str, ...] = ("bundled", "imports", "cache"),
    data_files: tuple[str, ...] = (),
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
) -> list[MarketData]:
    base = Path(root) / "data"
    workspace = Path(root)
    if data_files:
        df = _load_files(workspace, data_files, symbol=symbol, market=market, interval=interval)
        if df is None:
            raise FileNotFoundError(f"configured data files do not contain {market} {symbol} {interval}")
        df = _apply_time_filter(df, start_time_ms=start_time_ms, end_time_ms=end_time_ms)
        if df.empty:
            raise FileNotFoundError(f"configured data files have no rows in requested time range for {market} {symbol} {interval}")
        return _rows_to_market_data(df)
    checked: list[str] = []
    for section in data_source_order:
        section_name = str(section).strip()
        if not section_name:
            continue
        checked.append(section_name)
        df = _matching_klines(base / section_name, symbol=symbol, market=market, interval=interval)
        if df is not None:
            df = _apply_time_filter(df, start_time_ms=start_time_ms, end_time_ms=end_time_ms)
            if df.empty:
                continue
            break
    else:
        locations = ", ".join(f"data/{section}" for section in checked or data_source_order)
        raise FileNotFoundError(f"no kline data for {market} {symbol} {interval} in {locations}")
    return _rows_to_market_data(df)


def _rows_to_market_data(df: pd.DataFrame) -> list[MarketData]:
    return [
        MarketData(
            symbol=str(row.symbol).upper(),
            price=float(row.close),
            timestamp=int(row.timestamp),
            market=str(row.market).lower(),
            interval=str(row.interval),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
        )
        for row in df.itertuples(index=False)
    ]
