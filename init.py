from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

STRATEGY_LIBRARY_PACKAGE = "hushine-strategy-library"


def _default_workspace() -> Path:
    return Path(os.environ.get("HUSHINE_DEBUG_WORKSPACE", Path.home() / "hushine-debug-workspace")).expanduser()


def _venv_python(workspace: Path) -> Path:
    if os.name == "nt":
        return workspace / ".venv" / "Scripts" / "python.exe"
    return workspace / ".venv" / "bin" / "python"


def _run(args: list[str | Path], *, cwd: Path | None = None) -> None:
    printable = " ".join(str(item) for item in args)
    print(f"$ {printable}", flush=True)
    subprocess.run([str(item) for item in args], cwd=cwd, check=True)


def _editable_requirement(source: str, package_name: str) -> str:
    if not source.startswith(("git+", "hg+", "svn+", "bzr+")):
        return source
    if "#egg=" in source or "&egg=" in source:
        return source
    separator = "&" if "#" in source else "#"
    return f"{source}{separator}egg={package_name}"


def _strategy_library_source(root: Path) -> str:
    configured = os.environ.get("HUSHINE_STRATEGY_LIBRARY_DIR")
    if configured:
        path = Path(configured).expanduser()
        if path.exists():
            return str(path)
    sibling = root.parent / "strategy-library"
    if sibling.exists():
        return str(sibling)
    source = os.environ.get(
        "HUSHINE_STRATEGY_LIBRARY_GIT",
        "git+https://github.com/hushine-tech/strategy-library.git",
    )
    return _editable_requirement(source, STRATEGY_LIBRARY_PACKAGE)


def bootstrap(workspace: Path) -> None:
    root = Path(__file__).resolve().parent
    if sys.version_info < (3, 11):
        raise SystemExit("Python 3.11+ is required")

    workspace.mkdir(parents=True, exist_ok=True)
    python = _venv_python(workspace)

    _run([sys.executable, "-m", "venv", workspace / ".venv"])
    _run([python, "-m", "pip", "install", "-U", "pip"])
    _run([python, "-m", "pip", "install", "-e", _strategy_library_source(root)])
    _run([python, "-m", "pip", "install", "-e", root])
    _run([python, "-m", "hushine_debugger.cli", "init", "--dir", workspace, "--with-demo"])
    _run([python, "-m", "hushine_debugger.cli", "replay"], cwd=workspace)

    print()
    print("Demo completed")
    print()
    print("Next:")
    print(f"1. cd {workspace}")
    print("2. Open this folder in VSCode")
    print("3. Open strategy.py and set breakpoints")
    print('4. Run "Hushine Local Replay" in VSCode Debug')
    print("5. Edit hushine-debug.yaml to change symbol, interval, or date range")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a local Hushine strategy debugger workspace.")
    parser.add_argument(
        "--workspace",
        default=str(_default_workspace()),
        help="Workspace directory. Defaults to HUSHINE_DEBUG_WORKSPACE or ~/hushine-debug-workspace.",
    )
    args = parser.parse_args()
    bootstrap(Path(args.workspace).expanduser())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
