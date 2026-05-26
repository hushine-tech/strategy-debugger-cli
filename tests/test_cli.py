from hushine_debugger.cli import main


def test_version_command(capsys):
    code = main(["--version"])
    captured = capsys.readouterr()
    assert code == 0
    assert "hushine-debug 0.1.0" in captured.out
