import json
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hushine_debugger.cli import main


def _load_repo_init_script():
    script = Path(__file__).resolve().parents[1] / "init.py"
    spec = importlib.util.spec_from_file_location("hushine_debugger_repo_init", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_version_command(capsys):
    code = main(["--version"])
    captured = capsys.readouterr()
    assert code == 0
    assert "hushine-debug 0.1.0" in captured.out


def test_init_command_creates_workspace(tmp_path, capsys):
    workspace = tmp_path / "debug-workspace"
    code = main(["init", "--dir", str(workspace)])
    captured = capsys.readouterr()
    assert code == 0
    assert f"initialized {workspace}" in captured.out
    assert (workspace / "strategy.py").exists()
    assert (workspace / "strategy.py.template").exists()
    assert (workspace / ".vscode" / "launch.json").exists()
    launch = json.loads((workspace / ".vscode" / "launch.json").read_text(encoding="utf-8"))
    config = launch["configurations"][0]
    assert config["python"] == "${workspaceFolder}/.venv/bin/python"
    assert config["module"] == "hushine_debugger.cli"
    assert config["args"] == ["replay"]
    assert (workspace / "data" / "bundled").exists()


def test_init_command_with_demo_prints_ready_message(tmp_path, capsys):
    workspace = tmp_path / "debug-workspace"

    code = main(["init", "--dir", str(workspace), "--with-demo"])

    captured = capsys.readouterr()
    assert code == 0
    assert f"initialized {workspace}" in captured.out
    assert "demo workspace ready" in captured.out


def test_repair_command_restores_workspace(tmp_path, capsys):
    workspace = tmp_path / "debug-workspace"
    main(["init", "--dir", str(workspace)])
    (workspace / "wallet.yaml").write_text("initial_balance: 5000.0\n", encoding="utf-8")
    (workspace / "strategy.py.template").write_text("broken", encoding="utf-8")

    code = main(["repair", "--dir", str(workspace)])

    captured = capsys.readouterr()
    assert code == 0
    assert f"repaired {workspace}" in captured.out
    assert "broken" not in (workspace / "strategy.py.template").read_text(encoding="utf-8")
    assert "initial_balance: 5000.0" in (workspace / "wallet.yaml").read_text(encoding="utf-8")


def test_validate_command_accepts_clean_strategy(tmp_path, capsys):
    strategy = tmp_path / "strategy.py"
    strategy.write_text(
        """
from hushine_strategy import OrderDecision

class MyStrategy:
    INPUTS = [{"market": "futures", "symbol": "BTCUSDT", "interval": "1m"}]

    def on_market_data(self, data, wallet):
        return None
""",
        encoding="utf-8",
    )

    code = main(["validate", str(strategy)])

    captured = capsys.readouterr()
    assert code == 0
    assert "validation ok" in captured.out


def test_validate_command_rejects_forbidden_import(tmp_path, capsys):
    strategy = tmp_path / "strategy.py"
    strategy.write_text(
        """
import requests

class MyStrategy:
    INPUTS = [{"market": "futures", "symbol": "BTCUSDT", "interval": "1m"}]

    def on_market_data(self, data, wallet):
        return None
""",
        encoding="utf-8",
    )

    code = main(["validate", str(strategy)])

    captured = capsys.readouterr()
    assert code == 1
    assert "forbidden_import" in captured.out
    assert "requests" in captured.out


def test_module_entrypoint_creates_workspace(tmp_path):
    workspace = tmp_path / "module-workspace"
    env = dict(os.environ)
    repo_root = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = str(repo_root / "src")
    result = subprocess.run(
        [sys.executable, "-m", "hushine_debugger.cli", "init", "--dir", str(workspace)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    assert f"initialized {workspace}" in result.stdout
    assert (workspace / "hushine-debug.yaml").exists()


def test_repo_init_script_exists():
    script = Path(__file__).resolve().parents[1] / "init"

    assert script.exists()
    text = script.read_text(encoding="utf-8")
    assert "init.py" in text
    assert "uv" in text
    assert "--no-project" in text


def test_cross_platform_init_py_exists():
    script = Path(__file__).resolve().parents[1] / "init.py"

    assert script.exists()
    text = script.read_text(encoding="utf-8")
    assert "os.name == \"nt\"" in text
    assert "\"Scripts\"" in text
    assert "\"bin\"" in text
    assert "\"hushine_debugger.cli\"" in text
    assert "Demo completed" in text
    assert "uv" in text


def test_init_py_git_strategy_library_source_defaults_to_github(tmp_path, monkeypatch):
    init_script = _load_repo_init_script()
    root = tmp_path / "strategy-debugger-cli"
    root.mkdir()
    monkeypatch.delenv("HUSHINE_STRATEGY_LIBRARY_DIR", raising=False)
    monkeypatch.delenv("HUSHINE_STRATEGY_LIBRARY_GIT", raising=False)

    source = init_script._strategy_library_source(root)

    assert source == "git+https://github.com/hushine-tech/strategy-library.git"


def test_init_py_preserves_configured_git_fragment_for_direct_url_install(tmp_path, monkeypatch):
    init_script = _load_repo_init_script()
    root = tmp_path / "strategy-debugger-cli"
    root.mkdir()
    monkeypatch.delenv("HUSHINE_STRATEGY_LIBRARY_DIR", raising=False)
    monkeypatch.setenv(
        "HUSHINE_STRATEGY_LIBRARY_GIT",
        "git+https://example.invalid/strategy-library.git#subdirectory=python",
    )

    args = init_script._strategy_library_install_args(root)

    assert args == [
        "hushine-strategy-library @ git+https://example.invalid/strategy-library.git#subdirectory=python",
    ]


def test_init_py_installs_git_strategy_library_without_editable_flag(tmp_path, monkeypatch):
    init_script = _load_repo_init_script()
    root = tmp_path / "strategy-debugger-cli"
    root.mkdir()
    monkeypatch.delenv("HUSHINE_STRATEGY_LIBRARY_DIR", raising=False)
    monkeypatch.delenv("HUSHINE_STRATEGY_LIBRARY_GIT", raising=False)

    args = init_script._strategy_library_install_args(root)

    assert args == [
        "hushine-strategy-library @ git+https://github.com/hushine-tech/strategy-library.git",
    ]


def test_init_py_requires_uv(monkeypatch):
    init_script = _load_repo_init_script()
    monkeypatch.delenv("UV", raising=False)
    monkeypatch.setattr(init_script.shutil, "which", lambda _name: None)

    with pytest.raises(SystemExit) as exc:
        init_script._uv_executable()

    assert "uv is required" in str(exc.value)


def test_bootstrap_uses_uv_for_environment_install(tmp_path, monkeypatch):
    init_script = _load_repo_init_script()
    calls = []
    workspace = tmp_path / "workspace"
    root = Path(init_script.__file__).resolve().parent

    monkeypatch.setattr(init_script, "_uv_executable", lambda: "uv")
    monkeypatch.setattr(init_script, "_strategy_library_source", lambda _root: "strategy-library-source")

    def fake_run(args, *, cwd=None):
        calls.append(([str(item) for item in args], cwd))

    monkeypatch.setattr(init_script, "_run", fake_run)

    init_script.bootstrap(workspace)

    assert calls[0][0] == ["uv", "venv", "--python", sys.executable, str(workspace / ".venv")]
    assert calls[1][0] == [
        "uv",
        "pip",
        "install",
        "--python",
        str(init_script._venv_python(workspace)),
        "-e",
        "strategy-library-source",
        "-e",
        str(root),
    ]
    assert calls[2][0] == [
        str(init_script._venv_python(workspace)),
        "-m",
        "hushine_debugger.cli",
        "init",
        "--dir",
        str(workspace),
        "--with-demo",
    ]
    assert calls[3][0] == [
        str(init_script._venv_python(workspace)),
        "-m",
        "hushine_debugger.cli",
        "replay",
    ]
    assert calls[3][1] == workspace
