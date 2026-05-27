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

- Python 3.11+
- uv
- Git
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

macOS / Linux:

```bash
python init.py
```

Windows PowerShell:

```powershell
py init.py
```

也可以指定工作区目录：

```bash
python init.py --workspace ~/hushine-debug-workspace
```

脚本会自动完成：

1. 创建 `~/hushine-debug-workspace`
2. 通过 `uv venv` 创建 `~/hushine-debug-workspace/.venv`
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

导入后也可以直接在 VSCode 里点击 `Hushine Local Replay`。

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

### 校验策略

macOS / Linux:

```bash
.venv/bin/hushine-debug validate strategy.py
```

Windows PowerShell:

```powershell
.\.venv\Scripts\hushine-debug validate strategy.py
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

它会恢复受管理模板文件，不会覆盖：

- `strategy.py`
- `hushine-debug.yaml`
- `wallet.yaml`

## 更新工具

在 CLI 仓库目录执行：

```bash
git pull
python init.py
```

Windows:

```powershell
git pull
py init.py
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
python init.py
```

Windows PowerShell:

```powershell
Remove-Item -Recurse -Force $HOME\hushine-debug-workspace\.venv
py init.py
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
