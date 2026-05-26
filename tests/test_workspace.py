from pathlib import Path

from hushine_debugger.init_workspace import init_workspace
from hushine_debugger.integrity import check_workspace_integrity, repair_workspace


def test_init_writes_template_without_strategy_py(tmp_path: Path):
    init_workspace(tmp_path)
    assert (tmp_path / "strategy.py.template").exists()
    assert not (tmp_path / "strategy.py").exists()
    assert (tmp_path / ".hushine" / "manifest.lock").exists()


def test_integrity_detects_managed_file_change(tmp_path: Path):
    init_workspace(tmp_path)
    template = tmp_path / "strategy.py.template"
    template.write_text(template.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    result = check_workspace_integrity(tmp_path)
    assert result.ok is False
    assert "strategy.py.template" in result.changed_files


def test_integrity_allows_user_config_changes(tmp_path: Path):
    init_workspace(tmp_path)
    (tmp_path / "hushine-debug.yaml").write_text("symbol: ETHUSDT\n", encoding="utf-8")
    (tmp_path / "wallet.yaml").write_text("initial_balance: 5000.0\n", encoding="utf-8")

    result = check_workspace_integrity(tmp_path)

    assert result.ok is True
    assert result.changed_files == []


def test_repair_restores_managed_file_without_touching_strategy(tmp_path: Path):
    init_workspace(tmp_path)
    strategy = tmp_path / "strategy.py"
    strategy.write_text("class MyStrategy:\n    INPUTS = []\n", encoding="utf-8")
    (tmp_path / "strategy.py.template").write_text("broken", encoding="utf-8")
    repair_workspace(tmp_path)
    assert "broken" not in (tmp_path / "strategy.py.template").read_text(encoding="utf-8")
    assert strategy.read_text(encoding="utf-8").startswith("class MyStrategy")


def test_repair_does_not_overwrite_user_config(tmp_path: Path):
    init_workspace(tmp_path)
    config = tmp_path / "hushine-debug.yaml"
    wallet = tmp_path / "wallet.yaml"
    config.write_text("symbol: ETHUSDT\n", encoding="utf-8")
    wallet.write_text("initial_balance: 5000.0\n", encoding="utf-8")

    repair_workspace(tmp_path)

    assert config.read_text(encoding="utf-8") == "symbol: ETHUSDT\n"
    assert wallet.read_text(encoding="utf-8") == "initial_balance: 5000.0\n"
