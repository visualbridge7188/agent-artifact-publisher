from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ScanResult:
    workdir: Path
    candidate_files: list[str] = field(default_factory=list)
    detected_type: str = "other"
    git_branch: str = ""
    git_remote: str = ""
    changed_files: list[str] = field(default_factory=list)


def _run_git(workdir: Path, args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=workdir, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def scan_workdir(workdir: Path) -> ScanResult:
    root = workdir.expanduser().resolve()
    result = ScanResult(workdir=root)
    for relative in ["README.md", "pyproject.toml", "package.json"]:
        if (root / relative).exists():
            result.candidate_files.append(relative)
    for skill_file in root.glob("skills/*/SKILL.md"):
        result.candidate_files.append(str(skill_file.relative_to(root)))
        result.detected_type = "skill"
    result.git_branch = _run_git(root, ["branch", "--show-current"])
    result.git_remote = _run_git(root, ["remote", "get-url", "origin"])
    status = _run_git(root, ["status", "--short"])
    result.changed_files = [line[3:] for line in status.splitlines() if len(line) > 3]
    return result
