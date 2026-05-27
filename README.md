# Strategy Debugger CLI

Hushine 本地策略调试工具。它不连接平台、不需要 Docker、不需要证书，适合用户在本机快速写策略、打断点、跑离线回放。

默认工作区包含：

- Binance USDT-M Futures 2025 年 1 月 1m K 线数据
- 内置 symbol：`BTCUSDT`、`ETHUSDT`、`BNBUSDT`、`SOLUSDT`、`XRPUSDT`
- 默认钱包：`1000 USDT`
- 示例策略：`strategy.py`
- VSCode Debug 配置：`Hushine Local Replay`

## 一次性跑通

前置条件：

- uv
- Git
- Python 由 uv 自动准备，不需要用户手动创建 venv
- VSCode（只有需要断点调试时才需要）

安装 uv：

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS / Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

确认安装完成：

```bash
uv --version
```

### 1. 拉代码

```bash
git clone git@github.com:hushine-tech/strategy-debugger-cli.git
cd strategy-debugger-cli
```

### 2. 初始化并运行默认 demo

所有平台统一使用 uv：

```bash
uv run --no-project --python 3.13 python init.py
```

也可以指定工作区目录：

```bash
uv run --no-project --python 3.13 python init.py --workspace ~/hushine-debug-workspace
```

脚本会自动完成：

1. 创建 `~/hushine-debug-workspace`
2. 通过 `uv run` 启动初始化脚本，再用 `uv venv` 创建 `~/hushine-debug-workspace/.venv`
3. 通过 `uv pip install` 安装 CLI 和依赖
4. 生成 `strategy.py`
5. 复制内置 demo 数据
6. 运行默认 `BTCUSDT futures 1m` 回测
7. 输出进度、成交数量、盈亏和收益率

正常输出会包含类似内容：

```text
Running backtest BTCUSDT futures 1m
Progress: 10% (4464/44640 bars)
...
Progress: 100% (44640/44640 bars)
Backtest completed
Bars processed: 44640
Orders filled: 215
Initial balance: 1000.00 USDT
Final equity: 1012.35 USDT
PnL: +12.35 USDT
Return: +1.23%
```

## 在 VSCode 中调试

打开生成的工作区：

```bash
cd ~/hushine-debug-workspace
code .
```

Windows PowerShell:

```powershell
cd $HOME\hushine-debug-workspace
code .
```

Windows Git Bash:

```bash
cd ~/hushine-debug-workspace
code .
```

然后：

1. 打开 `strategy.py`
2. 在策略代码里打断点
3. 打开 VSCode 左侧 `Run and Debug`
4. 选择 `Hushine Local Replay`
5. 点击 Debug

生成的 `.vscode/launch.json` 会固定使用当前工作区的虚拟环境：

macOS / Linux:

```text
${workspaceFolder}/.venv/bin/python
```

Windows:

```text
${workspaceFolder}/.venv/Scripts/python.exe
```

所以即使 VSCode 状态栏显示的不是 `.venv`，点击 `Hushine Local Replay` 时也会用工作区内的虚拟环境运行。

## 修改策略

用户只需要改这个文件：

```text
~/hushine-debug-workspace/strategy.py
```

再次点击 VSCode Debug，回测会从头重新运行。

`strategy.py.template` 是模板文件，不建议直接修改。重新初始化不会覆盖已有的 `strategy.py`。

## 替换数据

有两种方式。

### 方式一：直接改配置，让 CLI 自动下载

修改：

```text
~/hushine-debug-workspace/hushine-debug.yaml
```

例如切换成 `ETHUSDT`：

```yaml
symbol: ETHUSDT
interval: 1m
start: "2025-01-01T00:00:00Z"
end: "2025-02-01T00:00:00Z"
download_if_missing: true
```

如果本地已经有数据，会直接运行。  
如果本地没有数据，CLI 会自动从 Binance Futures 下载，并在终端显示下载进度。

### 方式二：从平台下载 debug package

在 Hushine 后台的 Account Detail -> Local Debug 中选择：

1. Symbol
2. Interval
3. Initial balance
4. Start / End

然后点击 `Generate Debug Package` 下载 zip 包。

导入到本地工作区：

macOS / Linux:

```bash
cd ~/hushine-debug-workspace
.venv/bin/hushine-debug import ~/Downloads/debug-package.zip
.venv/bin/hushine-debug replay
```

Windows PowerShell:

```powershell
cd $HOME\hushine-debug-workspace
.\.venv\Scripts\hushine-debug import $HOME\Downloads\debug-package.zip
.\.venv\Scripts\hushine-debug replay
```

Windows Git Bash:

```bash
cd ~/hushine-debug-workspace
./.venv/Scripts/hushine-debug import ~/Downloads/debug-package.zip
./.venv/Scripts/hushine-debug replay
```

导入后也可以直接在 VSCode 里点击 `Hushine Local Replay`。

### 导入 ETH / 其他币种后修改策略

`hushine-debug import` 会更新 `hushine-debug.yaml` 和本地数据，但不会覆盖用户自己的 `strategy.py`。

如果下载的是 `ETHUSDT`，需要打开 `strategy.py`，把模板顶部的常量改成和数据包一致：

```python
class MyStrategy:
    MARKET = "futures"
    SYMBOL = "ETHUSDT"
    INTERVAL = "1m"
```

模板后面已经统一使用这三个常量：

```python
INPUTS = [
    {"market": MARKET, "symbol": SYMBOL, "interval": INTERVAL},
]

tick = data.market[self.MARKET].symbol[self.SYMBOL].interval[self.INTERVAL]

return OrderDecision(symbol=self.SYMBOL, side="LONG", qty=self.order_qty, market=self.MARKET)
```

所以正常情况下只需要改 `SYMBOL`。如果你下载的是不同 interval，例如 `5m`，再同步改 `INTERVAL`。如果 `strategy.py` 里还有手写的 `"BTCUSDT"`，也要一并替换，否则 replay 读的是 ETH 数据，策略却在等 BTC tick，断点可能进不到预期分支。

## 常用命令

### 运行回测

macOS / Linux:

```bash
cd ~/hushine-debug-workspace
.venv/bin/hushine-debug replay
```

Windows PowerShell:

```powershell
cd $HOME\hushine-debug-workspace
.\.venv\Scripts\hushine-debug replay
```

Windows Git Bash:

```bash
cd ~/hushine-debug-workspace
./.venv/Scripts/hushine-debug replay
```

### 校验策略

macOS / Linux:

```bash
.venv/bin/hushine-debug validate strategy.py
```

Windows PowerShell:

```powershell
.\.venv\Scripts\hushine-debug validate strategy.py
```

Windows Git Bash:

```bash
./.venv/Scripts/hushine-debug validate strategy.py
```

校验会拦截危险 import 和不支持的策略写法。

### 修复模板文件

macOS / Linux:

```bash
.venv/bin/hushine-debug repair --dir .
```

Windows PowerShell:

```powershell
.\.venv\Scripts\hushine-debug repair --dir .
```

Windows Git Bash:

```bash
./.venv/Scripts/hushine-debug repair --dir .
```

它会恢复受管理模板文件，不会覆盖：

- `strategy.py`
- `hushine-debug.yaml`
- `wallet.yaml`

## 更新工具

在 CLI 仓库目录执行：

```bash
git pull
uv run --no-project --python 3.13 python init.py
```

Windows:

```powershell
git pull
uv run --no-project --python 3.13 python init.py
```

初始化脚本是幂等的，会通过 `uv` 更新工作区虚拟环境和模板，不会覆盖已有 `strategy.py`。

如果本机还没有安装 `uv`，先执行：

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS / Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

如果之前初始化失败留下了半成品虚拟环境，可以只删除工作区里的 `.venv` 后重新运行：

macOS / Linux:

```bash
rm -rf ~/hushine-debug-workspace/.venv
uv run --no-project --python 3.13 python init.py
```

Windows PowerShell:

```powershell
Remove-Item -Recurse -Force "$HOME\hushine-debug-workspace\.venv"
uv run --no-project --python 3.13 python init.py
```

## 删除工具

删除工作区和仓库即可：

macOS / Linux:

```bash
rm -rf ~/hushine-debug-workspace
rm -rf strategy-debugger-cli
```

Windows PowerShell:

```powershell
Remove-Item -Recurse -Force $HOME\hushine-debug-workspace
Remove-Item -Recurse -Force .\strategy-debugger-cli
```

## 常见问题

### `Editable must refer to a local directory, not a Git URL`

这是旧版本初始化脚本的问题：它把远程 `strategy-library` Git URL 当成 editable 依赖安装了，而 `uv` 只允许本地目录使用 editable。

先更新 CLI 仓库，再删除半成品 `.venv` 后重新初始化：

```bash
git pull
rm -rf ~/hushine-debug-workspace/.venv
uv run --no-project --python 3.13 python init.py
```

Windows Git Bash:

```bash
git pull
rm -rf ~/hushine-debug-workspace/.venv
uv run --no-project --python 3.13 python init.py
```

### VSCode: `Couldn't spawn debuggee: [WinError 2]`

这通常是旧版 `.vscode/launch.json` 在 Windows 下解释器路径不正确。更新 CLI 后，在工作区修复模板：

Windows Git Bash:

```bash
cd ~/strategy-debugger-cli
git pull
cd ~/hushine-debug-workspace
.venv/Scripts/hushine-debug repair --dir .
```

然后重新打开 VSCode，选择 `Hushine Local Replay` 再点 Debug。
