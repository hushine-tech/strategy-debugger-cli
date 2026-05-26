# Strategy Debugger CLI 零门槛初始化与调试设计

## 背景

`strategy-debugger-cli` 现在已经具备 `init`、`replay`、`import`、`validate` 等基础命令，但第一次使用仍然需要用户理解 Python venv、pip 安装、VSCode 解释器选择和本地数据准备。目标是把这些步骤收敛成一个默认可运行的本地调试工作区：用户拉下代码后运行一次初始化命令，就能看到 demo 结果，并能直接在 VSCode 中点 Debug 断点调试。

## 目标

1. 用户 clone 仓库后运行 `./init`，自动完成本地 workspace 初始化、依赖安装、默认策略生成、默认 demo replay。
2. 默认内置 5 个 Binance USDT-M Futures 一个月 1m K 线数据：`BTCUSDT`、`ETHUSDT`、`BNBUSDT`、`SOLUSDT`、`XRPUSDT`。
3. VSCode 打开生成的 workspace 后，用户直接点击 Debug 配置即可运行 `strategy.py` 并命中断点。
4. 用户修改配置到本地没有的数据时，Debug 运行阶段自动下载 Binance futures 数据，并在 terminal 中输出下载进度。
5. 用户仍然可以通过后台下载 debug 数据包并使用 `hushine-debug import <package.zip>` 替换或补充本地数据。

## 非目标

1. 不在本阶段支持 Docker debugger runtime。
2. 不在本阶段支持现货数据、非 Binance 数据或 live 交易。
3. 不在本阶段实现复杂 GUI/TUI 管理界面。
4. 不允许初始化流程覆盖用户已有的 `strategy.py`。

## 用户流程

### 第一次使用

```bash
git clone git@github.com:hushine-tech/strategy-debugger-cli.git
cd strategy-debugger-cli
./init
```

`./init` 完成后输出 demo replay 结果和下一步指引：

```text
Demo completed
bars_processed=...
orders_filled=...

Next:
1. cd ~/hushine-debug-workspace
2. code .
3. Open strategy.py and set breakpoints
4. Run "Hushine Local Replay" in VSCode Debug
5. Edit hushine-debug.yaml to change symbol, interval, or date range
```

### VSCode 调试

初始化生成 `.vscode/launch.json`，固定使用 workspace 内的 Python：

```text
${workspaceFolder}/.venv/bin/python
```

Debug 配置运行：

```text
python -m hushine_debugger.cli replay
```

用户不需要手动选择解释器，也不需要手动执行 pip install。

### 替换或补充数据

用户有两种方式准备数据：

1. 修改 `hushine-debug.yaml`，让 CLI 自动下载公开 Binance futures 数据。
2. 从管理后台下载 debug 数据包，然后执行：

```bash
hushine-debug import ~/Downloads/debug-package.zip
```

## 组件设计

### `./init` bootstrap 脚本

仓库根目录新增可执行脚本 `init`。它负责：

1. 找到可用的 Python 3.11+。
2. 创建默认 workspace：`~/hushine-debug-workspace`。
3. 创建 workspace 内 `.venv`。
4. 使用 `.venv/bin/python -m pip` 安装当前 CLI 包和 `strategy-library`。
5. 调用 `hushine-debug init --dir ~/hushine-debug-workspace --with-demo`。
6. 进入 workspace 自动运行一次 demo replay。
7. 输出 demo 结果和下一步说明。

如果 workspace 已存在，`./init` 必须幂等：

1. 不覆盖 `strategy.py`。
2. 可更新 `.vscode/launch.json` 和受管理模板。
3. 可修复缺失的内置数据目录。
4. 遇到损坏的受管理文件时，提示用户执行 `hushine-debug repair` 或使用显式 `--repair`。

### `hushine-debug init`

CLI 的 `init` 命令继续保留，增加适合 bootstrap 调用的能力：

1. 生成目录结构：`data/bundled`、`data/imports`、`data/cache`、`logs`、`.vscode`。
2. 写入 `strategy.py.template`。
3. 当 `strategy.py` 不存在时，从模板复制一份。
4. 写入默认 `hushine-debug.yaml`，默认指向 `BTCUSDT futures 1m 2025-01-01T00:00:00Z` 到 `2025-02-01T00:00:00Z`。
5. 写入 `wallet.yaml`，默认 USDT futures 钱包余额 `1000`。
6. 安装或复制 bundled dataset。
7. 写入 `.hushine/manifest.lock`。

### bundled dataset

内置数据存储为 parquet，路径按现有数据加载规则组织：

```text
data/bundled/binance/futures/1m/BTCUSDT/klines.parquet
data/bundled/binance/futures/1m/ETHUSDT/klines.parquet
data/bundled/binance/futures/1m/BNBUSDT/klines.parquet
data/bundled/binance/futures/1m/SOLUSDT/klines.parquet
data/bundled/binance/futures/1m/XRPUSDT/klines.parquet
```

时间范围固定为 `2025-01-01T00:00:00Z` 到 `2025-02-01T00:00:00Z`，每个 symbol 理论 bars 数为 `44640`。打包前必须做覆盖率校验，缺失数据不能进入默认包。

### replay 自动下载

`replay` 加载数据顺序保持：

```yaml
data_source_order:
  - bundled
  - imports
  - cache
```

当目标配置在本地数据中缺失或覆盖不完整时：

1. 如果 `download_if_missing: false`，直接报错。
2. 如果 exchange 不是 `binance` 或 market 不是 `futures`，直接报错。
3. 如果缺少 start/end，直接报错。
4. 其他情况自动从 Binance futures REST 下载。
5. 下载时输出进度，至少包含 symbol、interval、已下载 bars、预计 bars、百分比。
6. 下载完成后保存到 `data/cache`，再重新走本地加载和覆盖校验。

### 下载进度

`download_klines` 增加可选进度回调，不改变测试注入的 HTTP session 接口。回调事件包含：

```text
symbol
interval
start_ms
end_ms
cursor_ms
downloaded_bars
expected_bars
percent
```

CLI 默认把进度输出到 stdout，VSCode integrated terminal 可以直接看到。

### 完整性检查

继续使用 `.hushine/manifest.lock` 保护受管理文件。用户可自由修改：

1. `strategy.py`
2. `hushine-debug.yaml`
3. `wallet.yaml`
4. `data/imports`
5. `data/cache`
6. `logs`

不允许用户修改后继续运行的受管理文件包括：

1. `strategy.py.template`
2. CLI 内置模板文件
3. 以后加入的基础运行脚本

## 错误处理

1. Python 版本低于 3.11：`./init` 直接失败并提示安装 Python 3.11+。
2. pip 安装失败：输出失败命令和下一步排查建议。
3. demo replay 失败：保留 workspace，不删除现场，输出日志路径。
4. Binance 下载失败：输出 HTTP 错误或网络错误，不吞掉异常。
5. 数据下载后覆盖仍不完整：明确输出缺失区间，不继续 replay。
6. `strategy.py` 不存在：`init` 自动创建；`replay` 单独执行时提示重新运行 `hushine-debug init`。

## 测试计划

1. 单元测试：
   - `init_workspace` 自动生成 `strategy.py`。
   - `.vscode/launch.json` 指向 `${workspaceFolder}/.venv/bin/python`。
   - `download_klines` 进度回调按分页触发。
   - bundled 数据路径可被 `load_klines` 读取。
2. CLI 测试：
   - `hushine-debug init --dir <tmp>` 后可直接 `hushine-debug replay`。
   - 修改配置到 mock 缺失数据后会触发下载逻辑。
   - `download_if_missing: false` 时缺数据报错。
3. 端到端测试：
   - 在临时目录执行 `./init --workspace <tmp>`。
   - 验证 `.venv/bin/python -m hushine_debugger.cli replay` 成功。
   - 验证输出包含 `bars_processed` 和 `orders_filled`。
4. 手工验证：
   - 用 VSCode 打开生成 workspace。
   - 在 `strategy.py` 设置断点。
   - 点击 `Hushine Local Replay`，确认断点命中。

## 验收标准

1. 新用户 clone 仓库后只需要执行一次 `./init`，即可看到成功的 demo replay 输出。
2. `~/hushine-debug-workspace` 中已经有可编辑的 `strategy.py`。
3. VSCode 打开 workspace 后，不选择解释器也能直接 Debug。
4. 默认 5 个 futures symbol 的 `2025-01` 一个月数据都能被本地 replay 读取。
5. 修改到本地没有的数据时，Debug 输出下载进度，下载完成后继续 replay。
6. 用户已有 `strategy.py` 不会被任何 init/repair 流程覆盖。
