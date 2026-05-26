# Strategy Debugger CLI

Local offline strategy debugger for Hushine.

The default workspace includes:

- Binance USDT-M Futures 1m data for January 2025
- `BTCUSDT`, `ETHUSDT`, `BNBUSDT`, `SOLUSDT`, `XRPUSDT`
- a sample grid-style `strategy.py`
- a USDT futures wallet with `1000` initial balance
- a VSCode Debug configuration

## First Run

Clone this repository and run the bootstrap script.

macOS / Linux:

```bash
git clone git@github.com:hushine-tech/strategy-debugger-cli.git
cd strategy-debugger-cli
./init
```

Windows PowerShell:

```powershell
git clone git@github.com:hushine-tech/strategy-debugger-cli.git
cd strategy-debugger-cli
py init.py
```

Cross-platform explicit form:

```bash
python init.py
```

The script creates `~/hushine-debug-workspace`, installs dependencies into
`~/hushine-debug-workspace/.venv`, initializes the workspace, runs the default
demo, then prints the replay result.

## Debug In VSCode

Open the generated workspace:

```bash
cd ~/hushine-debug-workspace
code .
```

Set a breakpoint in `strategy.py`, then run `Hushine Local Replay` from the
VSCode Debug panel.

The generated `.vscode/launch.json` uses:

```text
${workspaceFolder}/.venv/bin/python
```

You do not need to manually select a Python interpreter.

## Change Strategy Code

Edit:

```text
~/hushine-debug-workspace/strategy.py
```

Then click Debug again in VSCode. The replay runs from the beginning each time.

## Change Data

Edit:

```text
~/hushine-debug-workspace/hushine-debug.yaml
```

Example:

```yaml
symbol: ETHUSDT
interval: 1m
start: "2025-01-01T00:00:00Z"
end: "2025-02-01T00:00:00Z"
download_if_missing: true
```

If the requested data is not available locally and `download_if_missing` is
`true`, the debugger downloads Binance futures data and prints progress in the
VSCode integrated terminal.

## Import A Debug Data Package

If the platform gives you a debug data package:

```bash
cd ~/hushine-debug-workspace
.venv/bin/hushine-debug import ~/Downloads/debug-package.zip
```

Then run `Hushine Local Replay` again from VSCode.

## Validate Strategy Code

```bash
cd ~/hushine-debug-workspace
.venv/bin/hushine-debug validate strategy.py
```

The validator blocks dangerous imports and unsupported strategy patterns before
you upload the strategy to the platform.

## Repair Managed Files

If managed templates are damaged:

```bash
cd ~/hushine-debug-workspace
.venv/bin/hushine-debug repair --dir .
```

This restores managed templates. It does not overwrite `strategy.py`,
`hushine-debug.yaml`, or `wallet.yaml`.

## Update The Tool

From the cloned repository:

```bash
cd strategy-debugger-cli
git pull
python init.py
```

`./init` is idempotent. It updates the venv and managed files without
overwriting your strategy.

## Remove The Tool

Remove the cloned repository and workspace:

```bash
rm -rf ~/hushine-debug-workspace
rm -rf strategy-debugger-cli
```
