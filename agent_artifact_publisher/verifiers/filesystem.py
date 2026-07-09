from __future__ import annotations

from pathlib import Path


def verify_file_contains(path: Path, required_text: list[str]) -> tuple[bool, str]:
    if not path.exists():
        return False, f"missing: {path}"
    content = path.read_text(encoding="utf-8")
    missing = [text for text in required_text if text not in content]
    if missing:
        return False, f"missing text: {missing}"
    return True, f"verified: {path}"
