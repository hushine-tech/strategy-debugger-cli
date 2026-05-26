from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from hushine_debugger.init_workspace import REPAIRABLE_FILES, USER_CONFIG_FILES, _template_bytes


@dataclass(frozen=True)
class IntegrityResult:
    ok: bool
    changed_files: list[str]
    missing_files: list[str]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(root: Path) -> dict[str, str]:
    raw = json.loads((root / ".hushine" / "manifest.lock").read_text(encoding="utf-8"))
    return dict(raw["managed_files"])


def check_workspace_integrity(path: str | Path) -> IntegrityResult:
    root = Path(path)
    manifest = _manifest(root)
    changed: list[str] = []
    missing: list[str] = []
    for rel, expected in manifest.items():
        target = root / rel
        if not target.exists():
            missing.append(rel)
        elif _sha256(target) != expected:
            changed.append(rel)
    return IntegrityResult(ok=not changed and not missing, changed_files=changed, missing_files=missing)


def repair_workspace(path: str | Path) -> None:
    root = Path(path)
    for rel in REPAIRABLE_FILES:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_template_bytes(rel))
    for rel in USER_CONFIG_FILES:
        target = root / rel
        if not target.exists():
            target.write_bytes(_template_bytes(rel))
    from hushine_debugger.init_workspace import init_workspace

    init_workspace(root)
