import os
import subprocess
import sys
from pathlib import Path

from hushine_debugger.cli import main


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
    assert (workspace / "strategy.py.template").exists()
    assert (workspace / ".vscode" / "launch.json").exists()


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
