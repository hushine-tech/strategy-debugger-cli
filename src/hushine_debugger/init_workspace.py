from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from pathlib import Path


MANAGED_FILES = [
    "strategy.py.template",
]

REPAIRABLE_FILES = [
    *MANAGED_FILES,
    ".vscode/launch.json",
    ".idea-docs/pycharm.md",
]

USER_CONFIG_FILES = [
    "hushine-debug.yaml",
    "wallet.yaml",
]


def _template_bytes(name: str) -> bytes:
    template_name = name
    if name == ".vscode/launch.json":
        template_name = "vscode-launch.json"
    if name == ".idea-docs/pycharm.md":
        template_name = "pycharm.md"
    return (files("hushine_debugger.templates") / template_name).read_bytes()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_manifest(root: str | Path) -> None:
    path = Path(root)
    manifest: dict[str, str] = {}
    for rel in MANAGED_FILES:
        target = path / rel
        if target.exists():
            manifest[rel] = _sha256(target.read_bytes())
    lock = path / ".hushine" / "manifest.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps({"managed_files": manifest}, indent=2, sort_keys=True), encoding="utf-8")


def init_workspace(path: str | Path) -> None:
    root = Path(path)
    root.mkdir(parents=True, exist_ok=True)
    (root / "data" / "bundled").mkdir(parents=True, exist_ok=True)
    (root / "data" / "imports").mkdir(parents=True, exist_ok=True)
    (root / "data" / "cache").mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    for rel in REPAIRABLE_FILES:
        data = _template_bytes(rel)
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    for rel in USER_CONFIG_FILES:
        target = root / rel
        if not target.exists():
            data = _template_bytes(rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    write_manifest(root)
