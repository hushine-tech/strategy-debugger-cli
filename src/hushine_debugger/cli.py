from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from hushine_debugger import __version__
from hushine_debugger.init_workspace import init_workspace
from hushine_debugger.integrity import repair_workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hushine-debug")
    parser.add_argument("--version", action="store_true")
    sub = parser.add_subparsers(dest="command")
    init = sub.add_parser("init")
    init.add_argument("--dir", default="hushine-debug-workspace")
    init.add_argument("--with-demo", action="store_true")
    sub.add_parser("replay")
    validate = sub.add_parser("validate")
    validate.add_argument("strategy_file", nargs="?", default="strategy.py")
    import_cmd = sub.add_parser("import")
    import_cmd.add_argument("package", nargs="?")
    repair = sub.add_parser("repair")
    repair.add_argument("--dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"hushine-debug {__version__}")
        return 0
    if args.command == "init":
        init_workspace(Path(args.dir))
        print(f"initialized {args.dir}")
        if args.with_demo:
            print("demo workspace ready")
        return 0
    if args.command == "repair":
        repair_workspace(Path(args.dir))
        print(f"repaired {args.dir}")
        return 0
    if args.command == "replay":
        from hushine_debugger.replay import replay_workspace

        result = replay_workspace(Path("."))
        print("Backtest completed")
        print(f"Bars processed: {result.bars_processed}")
        print(f"Orders filled: {result.orders_filled}")
        print(f"Initial balance: {result.initial_balance:.2f} USDT")
        print(f"Final equity: {result.final_equity:.2f} USDT")
        print(f"PnL: {result.pnl:+.2f} USDT")
        print(f"Return: {result.return_pct:+.2f}%")
        print(f"bars_processed={result.bars_processed} orders_filled={result.orders_filled}")
        return 0
    if args.command == "import":
        if not args.package:
            raise SystemExit("debug package path is required")
        from hushine_debugger.import_package import import_debug_package

        result = import_debug_package(args.package, Path("."))
        print(f"imported {result.symbol} {result.market} {result.interval} -> {result.parquet_path}")
        return 0
    if args.command == "validate":
        from hushine_strategy.validator import validate_strategy_code

        strategy_path = Path(args.strategy_file)
        result = validate_strategy_code(strategy_path.read_text(encoding="utf-8"))
        if result.ok:
            print("validation ok")
            return 0
        for issue in result.issues:
            where = f":{issue.line}" if issue.line else ""
            detail = issue.module or issue.symbol
            suffix = f" ({detail})" if detail else ""
            print(f"{issue.code}{where}: {issue.message}{suffix}")
        return 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
