from hushine_debugger.config import load_config


def test_load_config_parses_time_bool_and_single_source_order(tmp_path):
    (tmp_path / "hushine-debug.yaml").write_text(
        "strategy_file: strategy.py\n"
        "exchange: binance\n"
        "market: perpetual_futures\n"
        "symbol: ethusdt\n"
        "interval: 1m\n"
        "start: '2025-01-01T00:00:00Z'\n"
        "end: '2025-01-01T00:02:00Z'\n"
        "data_source_order: imports\n"
        "data_files:\n"
        "  - data/imports/debug.parquet\n"
        "download_if_missing: 'false'\n",
        encoding="utf-8",
    )

    cfg = load_config(tmp_path)

    assert cfg.symbol == "ETHUSDT"
    assert cfg.start_time_ms == 1735689600000
    assert cfg.end_time_ms == 1735689720000
    assert cfg.data_source_order == ("imports",)
    assert cfg.data_files == ("data/imports/debug.parquet",)
    assert cfg.download_if_missing is False
