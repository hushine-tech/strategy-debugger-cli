# Debugger CLI Zero-Friction Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a cloned `strategy-debugger-cli` repository initialize a complete local debug workspace, run a bundled demo, and support VSCode one-click replay debugging with automatic Binance futures data download when local data is missing.

**Architecture:** Add a repository-level `./init` bootstrap script for first-run setup, extend CLI workspace initialization to create runnable `strategy.py` and copy bundled data, and add progress reporting to the Binance futures downloader. Keep user-editable files (`strategy.py`, `hushine-debug.yaml`, `wallet.yaml`) separate from managed templates protected by the manifest.

**Tech Stack:** Python 3.11+, argparse, pandas/parquet/pyarrow, requests, VSCode debugpy launch configuration, pytest.

---

## File Structure

- Create `init`: repository bootstrap script that creates the workspace venv, installs local packages, initializes the workspace, and runs the demo.
- Create `src/hushine_debugger/demo_data.py`: copies packaged default parquet files into a workspace and exposes default symbol metadata.
- Create `scripts/build_default_data.py`: maintainer script to download and validate bundled demo data.
- Modify `src/hushine_debugger/init_workspace.py`: create `strategy.py` when missing, copy bundled data, and keep manifest behavior.
- Modify `src/hushine_debugger/cli.py`: add `init --with-demo`, `init --repair-managed`, clearer replay output, and demo run helper behavior.
- Modify `src/hushine_debugger/replay.py`: print download messages and pass progress callback to downloader.
- Modify `src/hushine_debugger/downloader/binance_futures.py`: add progress callback events without breaking injected test sessions.
- Modify `src/hushine_debugger/templates/vscode-launch.json`: pin the generated workspace interpreter to `.venv/bin/python`.
- Modify `README.md`: document clone/init/debug/import/update/remove flows.
- Modify tests under `tests/`: cover bootstrap assumptions, generated strategy, bundled data copy, downloader progress, and replay download output.
- Add bundled parquet files under `src/hushine_debugger/assets/default_data/binance/futures/1m/<SYMBOL>/klines.parquet`.

---

### Task 1: Workspace Init Becomes Runnable

**Files:**
- Modify: `src/hushine_debugger/init_workspace.py`
- Create: `src/hushine_debugger/demo_data.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_replay_cli.py`

- [ ] **Step 1: Write failing tests for generated `strategy.py` and bundled data copy**

Add assertions to `tests/test_cli.py::test_init_command_creates_workspace`:

```python
assert (workspace / "strategy.py").exists()
assert (workspace / "data" / "bundled").exists()
```

Add a new test in `tests/test_replay_cli.py`:

```python
def test_init_workspace_does_not_overwrite_user_strategy(tmp_path: Path):
    init_workspace(tmp_path)
    (tmp_path / "strategy.py").write_text("class MyStrategy:\n    pass\n", encoding="utf-8")

    init_workspace(tmp_path)

    assert (tmp_path / "strategy.py").read_text(encoding="utf-8") == "class MyStrategy:\n    pass\n"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest -q tests/test_cli.py::test_init_command_creates_workspace tests/test_replay_cli.py::test_init_workspace_does_not_overwrite_user_strategy
```

Expected before implementation: generated strategy assertion fails or new test fails if init overwrites.

- [ ] **Step 3: Implement minimal workspace generation**

Add `src/hushine_debugger/demo_data.py`:

```python
from __future__ import annotations

from importlib.resources import files
from pathlib import Path


DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT")
DEFAULT_EXCHANGE = "binance"
DEFAULT_MARKET = "futures"
DEFAULT_INTERVAL = "1m"


def copy_default_data(root: str | Path) -> None:
    target_root = Path(root) / "data" / "bundled" / DEFAULT_EXCHANGE / DEFAULT_MARKET / DEFAULT_INTERVAL
    package_root = files("hushine_debugger.assets.default_data") / DEFAULT_EXCHANGE / DEFAULT_MARKET / DEFAULT_INTERVAL
    for symbol in DEFAULT_SYMBOLS:
        source = package_root / symbol / "klines.parquet"
        if not source.is_file():
            continue
        target = target_root / symbol / "klines.parquet"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
```

Modify `init_workspace(path)`:

```python
from hushine_debugger.demo_data import copy_default_data

...
for rel in USER_CONFIG_FILES:
    ...
strategy_file = root / "strategy.py"
if not strategy_file.exists():
    strategy_file.write_bytes(_template_bytes("strategy.py.template"))
copy_default_data(root)
write_manifest(root)
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
pytest -q tests/test_cli.py::test_init_command_creates_workspace tests/test_replay_cli.py::test_init_workspace_does_not_overwrite_user_strategy
```

Expected: both tests pass.

---

### Task 2: Downloader Progress and Replay Output

**Files:**
- Modify: `src/hushine_debugger/downloader/binance_futures.py`
- Modify: `src/hushine_debugger/replay.py`
- Modify: `tests/test_downloader.py`
- Modify: `tests/test_replay_cli.py`

- [ ] **Step 1: Write failing downloader progress test**

Add to `tests/test_downloader.py`:

```python
def test_download_klines_reports_progress():
    session = _FakeSession()
    events = []
    df = download_klines(
        symbol="BTCUSDT",
        interval="1m",
        start_ms=1735689600000,
        end_ms=1735689720000,
        session=session,
        on_progress=events.append,
    )

    assert len(df) == 2
    assert events
    assert events[-1].downloaded_bars == 2
    assert events[-1].expected_bars == 2
    assert events[-1].percent == 100.0
```

- [ ] **Step 2: Implement progress event**

In `binance_futures.py`, add:

```python
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class DownloadProgress:
    symbol: str
    interval: str
    start_ms: int
    end_ms: int
    cursor_ms: int
    downloaded_bars: int
    expected_bars: int
    percent: float
```

Change `download_klines` signature:

```python
def download_klines(..., on_progress: Callable[[DownloadProgress], None] | None = None) -> pd.DataFrame:
```

After each fetched frame:

```python
downloaded = sum(len(frame) for frame in rows)
expected = max(0, (int(end_ms) - int(start_ms)) // step_ms)
percent = 100.0 if expected == 0 else min(100.0, round(downloaded / expected * 100, 1))
if on_progress is not None:
    on_progress(DownloadProgress(...))
```

- [ ] **Step 3: Add replay output test**

Update `tests/test_replay_cli.py::test_replay_downloads_missing_binance_futures_data` fake function to accept `on_progress=None` and emit an event-compatible object if provided. Assert captured stdout contains:

```python
assert "Local data missing, downloading BTCUSDT futures 1m" in captured.out
assert "Download completed" in captured.out
```

- [ ] **Step 4: Implement replay output**

In `replay.py`, before download:

```python
print(f"Local data missing, downloading {cfg.symbol} {cfg.market} {cfg.interval}...")
```

Add callback:

```python
def report_progress(event):
    print(f"Downloaded {event.downloaded_bars}/{event.expected_bars} bars ({event.percent:.1f}%)", flush=True)
```

Pass `on_progress=report_progress` and print `Download completed, replay starting...` after saving cache.

- [ ] **Step 5: Run focused tests**

Run:

```bash
pytest -q tests/test_downloader.py tests/test_replay_cli.py::test_replay_downloads_missing_binance_futures_data
```

Expected: pass.

---

### Task 3: VSCode One-Click Debug

**Files:**
- Modify: `src/hushine_debugger/templates/vscode-launch.json`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing launch config assertion**

In `tests/test_cli.py::test_init_command_creates_workspace`, load launch JSON and assert:

```python
import json
launch = json.loads((workspace / ".vscode" / "launch.json").read_text(encoding="utf-8"))
config = launch["configurations"][0]
assert config["python"] == "${workspaceFolder}/.venv/bin/python"
assert config["module"] == "hushine_debugger.cli"
assert config["args"] == ["replay"]
```

- [ ] **Step 2: Update template**

Change `src/hushine_debugger/templates/vscode-launch.json` to:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Hushine Local Replay",
      "type": "debugpy",
      "request": "launch",
      "python": "${workspaceFolder}/.venv/bin/python",
      "module": "hushine_debugger.cli",
      "args": ["replay"],
      "console": "integratedTerminal",
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  ]
}
```

- [ ] **Step 3: Run focused test**

Run:

```bash
pytest -q tests/test_cli.py::test_init_command_creates_workspace
```

Expected: pass.

---

### Task 4: Repository Bootstrap Script

**Files:**
- Create: `init`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add bootstrap script smoke test**

Add a test that asserts the script exists and contains the key operations:

```python
def test_repo_init_script_exists():
    script = Path(__file__).resolve().parents[1] / "init"
    text = script.read_text(encoding="utf-8")
    assert script.exists()
    assert "python -m venv" in text
    assert "pip install" in text
    assert "hushine_debugger.cli" in text
    assert "Demo completed" in text
```

- [ ] **Step 2: Create `init` script**

Create executable `init`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="${HUSHINE_DEBUG_WORKSPACE:-$HOME/hushine-debug-workspace}"
PYTHON_BIN="${PYTHON:-python3}"

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11+ is required")
PY

mkdir -p "$WORKSPACE"
"$PYTHON_BIN" -m venv "$WORKSPACE/.venv"
"$WORKSPACE/.venv/bin/python" -m pip install -U pip
"$WORKSPACE/.venv/bin/python" -m pip install -e "$ROOT_DIR/../strategy-library"
"$WORKSPACE/.venv/bin/python" -m pip install -e "$ROOT_DIR"
"$WORKSPACE/.venv/bin/python" -m hushine_debugger.cli init --dir "$WORKSPACE" --with-demo

(
  cd "$WORKSPACE"
  "$WORKSPACE/.venv/bin/python" -m hushine_debugger.cli replay
)

echo
echo "Demo completed"
echo
echo "Next:"
echo "1. cd $WORKSPACE"
echo "2. code ."
echo "3. Open strategy.py and set breakpoints"
echo "4. Run \"Hushine Local Replay\" in VSCode Debug"
echo "5. Edit hushine-debug.yaml to change symbol, interval, or date range"
```

- [ ] **Step 3: Make script executable and run smoke test**

Run:

```bash
chmod +x init
pytest -q tests/test_cli.py::test_repo_init_script_exists
```

Expected: pass.

---

### Task 5: Bundled Futures Demo Data

**Files:**
- Create: `scripts/build_default_data.py`
- Create: `src/hushine_debugger/assets/default_data/binance/futures/1m/*/klines.parquet`
- Modify: `tests/test_replay_cli.py`

- [ ] **Step 1: Add bundled data validation test**

Add to `tests/test_replay_cli.py`:

```python
def test_packaged_default_data_contains_required_symbols():
    from importlib.resources import files

    required = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
    root = files("hushine_debugger.assets.default_data") / "binance" / "futures" / "1m"
    for symbol in required:
        path = root / symbol / "klines.parquet"
        assert path.is_file(), symbol
        df = pd.read_parquet(path)
        assert len(df) == 44640
        assert df["timestamp"].min() == 1735689600000
        assert df["timestamp"].max() == 1738367940000
```

- [ ] **Step 2: Create maintainer data build script**

Create `scripts/build_default_data.py` that downloads the 5 symbols for January 2025, validates exactly 44,640 1m bars per symbol, and writes parquet files to package assets.

- [ ] **Step 3: Generate data files**

Run:

```bash
.venv/bin/python scripts/build_default_data.py
```

Expected: writes five `klines.parquet` files and prints validation summary.

- [ ] **Step 4: Run validation test**

Run:

```bash
pytest -q tests/test_replay_cli.py::test_packaged_default_data_contains_required_symbols
```

Expected: pass.

---

### Task 6: CLI Demo Flag and README

**Files:**
- Modify: `src/hushine_debugger/cli.py`
- Modify: `README.md`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add CLI `--with-demo` parser test**

Add a test that calls:

```python
code = main(["init", "--dir", str(workspace), "--with-demo"])
assert code == 0
assert "initialized" in captured.out
assert "demo workspace ready" in captured.out
```

- [ ] **Step 2: Implement `--with-demo` output**

Modify parser:

```python
init.add_argument("--with-demo", action="store_true")
```

Modify command:

```python
if args.command == "init":
    init_workspace(Path(args.dir))
    print(f"initialized {args.dir}")
    if args.with_demo:
        print("demo workspace ready")
    return 0
```

- [ ] **Step 3: Replace README**

Document:

```markdown
# Strategy Debugger CLI

## First run

```bash
git clone git@github.com:hushine-tech/strategy-debugger-cli.git
cd strategy-debugger-cli
./init
```

## Debug in VSCode

```bash
cd ~/hushine-debug-workspace
code .
```

Set a breakpoint in `strategy.py`, then run `Hushine Local Replay`.
```
```

- [ ] **Step 4: Run CLI tests**

Run:

```bash
pytest -q tests/test_cli.py
```

Expected: pass.

---

### Task 7: End-to-End Verification

**Files:**
- No planned source changes unless verification finds a defect.

- [ ] **Step 1: Run full test suite**

Run:

```bash
pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run isolated bootstrap smoke**

Run:

```bash
rm -rf /tmp/hushine-debug-workspace-smoke
HUSHINE_DEBUG_WORKSPACE=/tmp/hushine-debug-workspace-smoke ./init
```

Expected output includes `Demo completed`, `bars_processed=44640`, and `orders_filled=`.

- [ ] **Step 3: Verify direct module replay in generated workspace**

Run:

```bash
cd /tmp/hushine-debug-workspace-smoke
.venv/bin/python -m hushine_debugger.cli replay
```

Expected output includes `bars_processed=44640`.

- [ ] **Step 4: Check git status and commit implementation**

Run:

```bash
git status --short
git add init README.md scripts/build_default_data.py src tests
git commit -m "feat: add zero-friction debugger onboarding"
```

Expected: one implementation commit after tests pass.
