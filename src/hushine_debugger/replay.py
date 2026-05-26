from __future__ import annotations

from pathlib import Path

from hushine_strategy.notifier import LocalNotifier
from hushine_strategy.replay.engine import ReplayConfig, ReplayResult, run_replay
from hushine_strategy.wallet.futures import FuturesWallet

from hushine_debugger.config import load_config, load_initial_balance
from hushine_debugger.data.parquet_store import DataCoverageError, load_klines
from hushine_debugger.downloader.binance_futures import download_klines, interval_to_ms, save_to_cache
from hushine_debugger.integrity import check_workspace_integrity


def _load_or_download_klines(workspace: Path, cfg):
    try:
        interval_ms = interval_to_ms(cfg.interval) if cfg.start_time_ms is not None and cfg.end_time_ms is not None else None
        return load_klines(
            workspace,
            symbol=cfg.symbol,
            market=cfg.market,
            interval=cfg.interval,
            data_source_order=cfg.data_source_order,
            data_files=cfg.data_files,
            start_time_ms=cfg.start_time_ms,
            end_time_ms=cfg.end_time_ms,
            interval_ms=interval_ms,
        )
    except (FileNotFoundError, DataCoverageError):
        if cfg.data_files or not cfg.download_if_missing:
            raise
        if cfg.exchange != "binance" or cfg.market != "futures":
            raise
        if cfg.start_time_ms is None or cfg.end_time_ms is None:
            raise FileNotFoundError("missing local data and config start/end are required for download")
        print(f"Local data missing, downloading {cfg.symbol} {cfg.market} {cfg.interval}...", flush=True)

        def report_progress(event) -> None:
            print(
                f"Downloaded {event.downloaded_bars}/{event.expected_bars} bars ({event.percent:.1f}%)",
                flush=True,
            )

        frame = download_klines(
            symbol=cfg.symbol,
            interval=cfg.interval,
            start_ms=cfg.start_time_ms,
            end_ms=cfg.end_time_ms,
            on_progress=report_progress,
        )
        if frame.empty:
            raise FileNotFoundError(f"download returned no kline data for {cfg.market} {cfg.symbol} {cfg.interval}")
        save_to_cache(workspace, frame, symbol=cfg.symbol, interval=cfg.interval)
        print("Download completed, replay starting...", flush=True)
        return load_klines(
            workspace,
            symbol=cfg.symbol,
            market=cfg.market,
            interval=cfg.interval,
            data_source_order=("cache",),
            start_time_ms=cfg.start_time_ms,
            end_time_ms=cfg.end_time_ms,
            interval_ms=interval_to_ms(cfg.interval),
        )


def replay_workspace(root: str | Path = ".") -> ReplayResult:
    workspace = Path(root)
    integrity = check_workspace_integrity(workspace)
    if not integrity.ok:
        changed = ", ".join(integrity.changed_files + integrity.missing_files)
        raise RuntimeError(f"workspace managed files changed: {changed}")
    cfg = load_config(workspace)
    strategy_path = workspace / cfg.strategy_file
    if not strategy_path.exists():
        raise FileNotFoundError("strategy.py not found; copy strategy.py.template to strategy.py first")
    ticks = _load_or_download_klines(workspace, cfg)
    wallet = FuturesWallet(initial_balance=load_initial_balance(workspace))
    return run_replay(
        ReplayConfig(
            strategy_code=strategy_path.read_text(encoding="utf-8"),
            ticks=ticks,
            wallet=wallet,
            strategy_path=str(strategy_path),
            notifier=LocalNotifier(workspace / "logs" / "notifications.log"),
        )
    )
