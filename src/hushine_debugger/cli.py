from __future__ import annotations

import argparse
from collections.abc import Sequence

from hushine_debugger import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hushine-debug")
    parser.add_argument("--version", action="store_true")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("init")
    sub.add_parser("replay")
    sub.add_parser("validate")
    sub.add_parser("import")
    sub.add_parser("repair")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"hushine-debug {__version__}")
        return 0
    if not args.command:
        parser.print_help()
        return 2
    raise SystemExit(f"command {args.command!r} is not implemented")
