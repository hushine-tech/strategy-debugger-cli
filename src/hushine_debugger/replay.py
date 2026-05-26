from __future__ import annotations

from pathlib import Path

from hushine_strategy.notifier import LocalNotifier
from hushine_strategy.replay.engine import ReplayConfig, ReplayResult, run_replay
from hushine_strategy.wallet.futures import FuturesWallet

from hushine_debugger.config import load_config, load_initial_balance
from hushine_debugger.data.parquet_store import load_klines
from hushine_debugger.integrity import check_workspace_integrity


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
    ticks = load_klines(
        workspace,
        symbol=cfg.symbol,
        market=cfg.market,
        interval=cfg.interval,
        data_source_order=cfg.data_source_order,
        data_files=cfg.data_files,
        start_time_ms=cfg.start_time_ms,
        end_time_ms=cfg.end_time_ms,
    )
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
