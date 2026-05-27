from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

STRATEGY_LIBRARY_PACKAGE = "hushine-strategy-library"
UV_INSTALL_MESSAGE = """uv is required to initialize the Hushine debugger workspace.

Install uv first:
  Windows PowerShell:
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

  macOS/Linux:
    curl -LsSf https://astral.sh/uv/install.sh | sh

Then rerun:
  uv run --no-project --python 3.13 python init.py
"""


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


def _uv_executable() -> str:
    configured = os.environ.get("UV")
    if configured:
        resolved = shutil.which(configured)
        if resolved:
            return resolved
        path = Path(configured).expanduser()
        if path.exists():
            return str(path)
        raise SystemExit(f"UV={configured} was set but the executable was not found.")

    uv = shutil.which("uv")
    if uv:
        return uv
    raise SystemExit(UV_INSTALL_MESSAGE)


def _is_vcs_source(source: str) -> bool:
    return source.startswith(("git+", "hg+", "svn+", "bzr+"))


def _remove_egg_fragment(source: str) -> str:
    if "#" not in source:
        return source
    base, fragment = source.split("#", 1)
    parts = [part for part in fragment.split("&") if not part.startswith("egg=")]
    if not parts:
        return base
    return f"{base}#{'&'.join(parts)}"


def _direct_url_requirement(source: str, package_name: str) -> str:
    return f"{package_name} @ {_remove_egg_fragment(source)}"


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
    return source


def _strategy_library_install_args(root: Path) -> list[str]:
    source = _strategy_library_source(root)
    if _is_vcs_source(source):
        return [_direct_url_requirement(source, STRATEGY_LIBRARY_PACKAGE)]
    return ["-e", source]


def bootstrap(workspace: Path) -> None:
    root = Path(__file__).resolve().parent
    if sys.version_info < (3, 11):
        raise SystemExit("Python 3.11+ is required")

    workspace.mkdir(parents=True, exist_ok=True)
    uv = _uv_executable()
    python = _venv_python(workspace)

    _run([uv, "venv", "--python", sys.executable, workspace / ".venv"])
    _run([uv, "pip", "install", "--python", python, *_strategy_library_install_args(root), "-e", root])
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
