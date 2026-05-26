from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from hushine_debugger.cli import main
from hushine_debugger.init_workspace import init_workspace
from hushine_debugger.integrity import check_workspace_integrity
from hushine_debugger.replay import replay_workspace


def _write_minimal_workspace(root: Path) -> None:
    init_workspace(root)
    (root / "strategy.py").write_text(
        (root / "strategy.py.template").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    data_dir = root / "data" / "bundled"
    df = pd.DataFrame(
        [
            {
                "timestamp": 1735689600000,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 10.0,
                "symbol": "BTCUSDT",
                "market": "futures",
                "interval": "1m",
            },
            {
                "timestamp": 1735689660000,
                "open": 99.0,
                "high": 100.0,
                "low": 98.0,
                "close": 99.0,
                "volume": 11.0,
                "symbol": "BTCUSDT",
                "market": "futures",
                "interval": "1m",
            },
        ]
    )
    df.to_parquet(data_dir / "binance_futures_1m_2025_01.parquet")


def test_replay_workspace_uses_strategy_and_local_parquet(tmp_path: Path):
    _write_minimal_workspace(tmp_path)
    result = replay_workspace(tmp_path)
    assert result.bars_processed == 2
    assert (tmp_path / "logs" / "notifications.log").exists()


def test_replay_command_outputs_summary(tmp_path: Path, monkeypatch, capsys):
    _write_minimal_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    code = main(["replay"])

    captured = capsys.readouterr()
    assert code == 0
    assert "bars_processed=2" in captured.out
    assert "orders_filled=" in captured.out


def test_replay_requires_user_strategy_file(tmp_path: Path):
    init_workspace(tmp_path)
    try:
        replay_workspace(tmp_path)
    except FileNotFoundError as exc:
        assert "copy strategy.py.template to strategy.py first" in str(exc)
    else:
        raise AssertionError("replay should require strategy.py")


def test_import_command_unpacks_debug_package(tmp_path: Path, monkeypatch, capsys):
    package_path = tmp_path / "debug-package.zip"
    _write_debug_package(
        package_path,
        manifest="exchange: binance\nmarket: futures\nsymbol: ETHUSDT\ninterval: 1m\n",
        wallet="market: futures\nasset: USDT\ninitial_balance: 2500\n",
        source=pd.DataFrame(
            [
                {
                    "timestamp_ms": 1735689600000,
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                    "volume": 10.0,
                    "symbol": "wrong",
                    "market": "wrong",
                    "interval": "wrong",
                }
            ]
        ),
    )
    workspace = tmp_path / "workspace"
    init_workspace(workspace)
    (workspace / "strategy.py").write_text("user strategy should survive\n", encoding="utf-8")
    monkeypatch.chdir(workspace)

    code = main(["import", str(package_path)])

    captured = capsys.readouterr()
    assert code == 0
    assert "imported ETHUSDT futures 1m" in captured.out
    assert (workspace / "strategy.py").read_text(encoding="utf-8") == "user strategy should survive\n"
    assert "symbol: ETHUSDT" in (workspace / "hushine-debug.yaml").read_text(encoding="utf-8")
    assert "data_source_order:\n- imports" in (workspace / "hushine-debug.yaml").read_text(encoding="utf-8")
    assert "data_files:" in (workspace / "hushine-debug.yaml").read_text(encoding="utf-8")
    assert "initial_balance: 2500" in (workspace / "wallet.yaml").read_text(encoding="utf-8")
    assert check_workspace_integrity(workspace).ok is True
    imported = pd.read_parquet(next((workspace / "data" / "imports").glob("*.parquet")))
    assert imported.iloc[0]["timestamp"] == 1735689600000
    assert imported.iloc[0]["symbol"] == "ETHUSDT"
    assert imported.iloc[0]["market"] == "futures"
    assert imported.iloc[0]["interval"] == "1m"


def test_replay_after_multiple_imports_uses_latest_package_file_only(tmp_path: Path, monkeypatch):
    first_package = tmp_path / "first.zip"
    second_package = tmp_path / "second.zip"
    _write_debug_package(
        first_package,
        manifest="exchange: binance\nmarket: futures\nsymbol: BTCUSDT\ninterval: 1m\n",
        wallet="market: futures\nasset: USDT\ninitial_balance: 1000\n",
        source=pd.DataFrame(
            [
                {"timestamp_ms": 1735689600000, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 10.0},
                {"timestamp_ms": 1735689660000, "open": 101.0, "high": 102.0, "low": 100.0, "close": 101.0, "volume": 11.0},
            ]
        ),
    )
    _write_debug_package(
        second_package,
        manifest="exchange: binance\nmarket: futures\nsymbol: BTCUSDT\ninterval: 1m\n",
        wallet="market: futures\nasset: USDT\ninitial_balance: 1000\n",
        source=pd.DataFrame(
            [
                {"timestamp_ms": 1735689720000, "open": 102.0, "high": 103.0, "low": 101.0, "close": 102.0, "volume": 12.0},
            ]
        ),
    )
    workspace = tmp_path / "workspace"
    init_workspace(workspace)
    (workspace / "strategy.py").write_text(
        "class MyStrategy:\n"
        "    INPUTS = [{'market': 'futures', 'symbol': 'BTCUSDT', 'interval': '1m'}]\n"
        "    def on_market_data(self, data, wallet):\n"
        "        return None\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(workspace)

    main(["import", str(first_package)])
    main(["import", str(second_package)])
    result = main(["replay"])

    assert result == 0
    replay = replay_workspace(workspace)
    assert replay.bars_processed == 1
    assert "data/imports/second.parquet" in (workspace / "hushine-debug.yaml").read_text(encoding="utf-8")


def test_replay_uses_first_matching_data_source_only(tmp_path: Path):
    init_workspace(tmp_path)
    (tmp_path / "strategy.py").write_text(
        "from hushine_strategy import OrderDecision\n\n"
        "class MyStrategy:\n"
        "    INPUTS = [{'market': 'futures', 'symbol': 'BTCUSDT', 'interval': '1m'}]\n"
        "    def on_market_data(self, data, wallet):\n"
        "        return None\n",
        encoding="utf-8",
    )
    (tmp_path / "hushine-debug.yaml").write_text(
        "strategy_file: strategy.py\nmarket: futures\nsymbol: BTCUSDT\ninterval: 1m\ndata_source_order:\n  - imports\n  - bundled\n",
        encoding="utf-8",
    )
    bundled = pd.DataFrame(
        [
            {
                "timestamp": 1735689600000,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 10.0,
                "symbol": "BTCUSDT",
                "market": "futures",
                "interval": "1m",
            }
        ]
    )
    imports = pd.concat([bundled, bundled.assign(timestamp=1735689660000)], ignore_index=True)
    bundled.to_parquet(tmp_path / "data" / "bundled" / "bundled.parquet")
    imports.to_parquet(tmp_path / "data" / "imports" / "imports.parquet")

    result = replay_workspace(tmp_path)

    assert result.bars_processed == 2


def test_replay_filters_configured_time_range(tmp_path: Path):
    init_workspace(tmp_path)
    (tmp_path / "strategy.py").write_text(
        "class MyStrategy:\n"
        "    INPUTS = [{'market': 'futures', 'symbol': 'BTCUSDT', 'interval': '1m'}]\n"
        "    def on_market_data(self, data, wallet):\n"
        "        return None\n",
        encoding="utf-8",
    )
    (tmp_path / "hushine-debug.yaml").write_text(
        "strategy_file: strategy.py\n"
        "market: futures\n"
        "symbol: BTCUSDT\n"
        "interval: 1m\n"
        "start: '2025-01-01T00:01:00Z'\n"
        "end: '2025-01-01T00:03:00Z'\n"
        "data_source_order:\n"
        "  - bundled\n",
        encoding="utf-8",
    )
    rows = []
    for i in range(4):
        rows.append(
            {
                "timestamp": 1735689600000 + i * 60_000,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 10.0,
                "symbol": "BTCUSDT",
                "market": "futures",
                "interval": "1m",
            }
        )
    pd.DataFrame(rows).to_parquet(tmp_path / "data" / "bundled" / "range.parquet")

    result = replay_workspace(tmp_path)

    assert result.bars_processed == 2


def _write_debug_package(package_path: Path, *, manifest: str, wallet: str, source: pd.DataFrame) -> None:
    parquet_path = package_path.parent / f"{package_path.stem}.parquet"
    source.to_parquet(parquet_path)
    with ZipFile(package_path, "w") as archive:
        archive.writestr("manifest.yaml", manifest)
        archive.writestr("wallet.yaml", wallet)
        archive.writestr(
            "strategy.py.template",
            (Path(__file__).parents[1] / "src" / "hushine_debugger" / "templates" / "strategy.py.template").read_text(
                encoding="utf-8"
            ),
        )
        archive.write(parquet_path, "data.parquet")
