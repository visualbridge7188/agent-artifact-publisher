from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Callable

from agent_artifact_publisher.model import Artifact, PublishStatus, PublishTarget

Runner = Callable[[list[str], Path], tuple[int, str, str]]


def _default_runner(command: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
        return completed.returncode, completed.stdout, completed.stderr
    except FileNotFoundError as exc:
        return 127, "", str(exc)


def _git_value(workdir: Path, args: list[str]) -> str:
    code, stdout, _ = _default_runner(["git", *args], workdir)
    return stdout.strip() if code == 0 else ""


def _parse_github_remote(remote: str) -> tuple[str, str] | None:
    patterns = [
        r"github\.com[:/]([^/]+)/([^/.]+)(?:\.git)?$",
        r"https://[^@]+@github\.com/([^/]+)/([^/.]+)(?:\.git)?$",
    ]
    for pattern in patterns:
        match = re.search(pattern, remote)
        if match:
            return match.group(1), match.group(2)
    return None


def _github_api(method: str, path: str, token: str, payload: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        "https://api.github.com" + path,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except Exception as exc:
        detail = getattr(exc, "read", lambda: b"")()
        text = detail.decode("utf-8", errors="ignore") if detail else str(exc)
        return getattr(exc, "code", 0) or 0, {"message": text}


def _create_pr_via_api(artifact: Artifact, pr_body: str, body_path: Path) -> tuple[bool, str, str]:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return False, "", "Missing GITHUB_TOKEN/GH_TOKEN"
    workdir = Path(artifact.workdir)
    remote = _git_value(workdir, ["remote", "get-url", "origin"])
    parsed = _parse_github_remote(remote)
    if not parsed:
        return False, "", "GitHub remote origin not found"
    owner, repo = parsed
    repo_path = f"/repos/{owner}/{repo}"
    status, repo_info = _github_api("GET", repo_path, token)
    if status != 200:
        return False, "", f"repo read failed: {repo_info}"
    base = repo_info.get("default_branch") or "main"
    status, ref_info = _github_api("GET", f"{repo_path}/git/ref/heads/{base}", token)
    if status != 200:
        return False, "", f"base ref read failed: {ref_info}"
    base_sha = ref_info.get("object", {}).get("sha")
    branch = f"artifact-publish/{artifact.artifact_id}"
    _github_api("POST", f"{repo_path}/git/refs", token, {"ref": f"refs/heads/{branch}", "sha": base_sha})
    file_path = ".artifact-publisher/github/pr-body.md"
    content = base64.b64encode(pr_body.encode("utf-8")).decode("ascii")
    status, put_info = _github_api(
        "PUT",
        f"{repo_path}/contents/{file_path}",
        token,
        {"message": f"docs: publish {artifact.title} artifact report", "content": content, "branch": branch},
    )
    if status not in {200, 201}:
        return False, "", f"content write failed: {put_info}"
    status, pr_info = _github_api(
        "POST",
        f"{repo_path}/pulls",
        token,
        {"title": f"Publish artifact: {artifact.title}", "head": branch, "base": base, "body": pr_body},
    )
    if status not in {200, 201}:
        return False, "", f"pr create failed: {pr_info}"
    return True, pr_info.get("html_url", ""), ""


def prepare_github_publish(
    artifact: Artifact,
    mode: str,
    pr_body: str,
    output_dir: Path | None = None,
    runner: Runner | None = None,
) -> PublishTarget:
    output = output_dir or Path(artifact.workdir) / ".artifact-publisher" / "github"
    output.mkdir(parents=True, exist_ok=True)
    body_path = output / "pr-body.md"
    body_path.write_text(pr_body, encoding="utf-8")

    if mode in {"skip", "dry-run"}:
        target = PublishTarget(target="github", mode=mode, destination=str(body_path), url_or_path=str(body_path), status=PublishStatus.SKIPPED)
        artifact.targets.append(target)
        return target

    if mode == "pr-body-only":
        target = PublishTarget(target="github", mode=mode, destination=str(body_path), url_or_path=str(body_path), status=PublishStatus.VERIFIED)
        artifact.targets.append(target)
        return target

    if mode in {"pr", "pr-api"}:
        run = runner or _default_runner
        if mode == "pr":
            command = ["gh", "pr", "create", "--fill", "--body-file", str(body_path)]
            code, stdout, stderr = run(command, Path(artifact.workdir))
            url = stdout.strip().splitlines()[-1] if stdout.strip() else ""
            if code == 0 and url.startswith("https://github.com/"):
                target = PublishTarget(target="github", mode=mode, destination=str(body_path), url_or_path=url, status=PublishStatus.VERIFIED)
                artifact.targets.append(target)
                return target
            if code != 127:
                target = PublishTarget(target="github", mode=mode, destination=str(body_path), url_or_path=str(body_path), status=PublishStatus.FAILED, error=stderr or stdout or f"gh exited {code}")
                artifact.targets.append(target)
                return target
        ok, url, error = _create_pr_via_api(artifact, pr_body, body_path)
        target = PublishTarget(
            target="github",
            mode="pr-api" if mode == "pr-api" else "pr",
            destination=str(body_path),
            url_or_path=url or str(body_path),
            status=PublishStatus.VERIFIED if ok else PublishStatus.FAILED,
            error=error,
        )
        artifact.targets.append(target)
        return target

    target = PublishTarget(target="github", mode=mode, destination=str(body_path), url_or_path=str(body_path), status=PublishStatus.FAILED, error=f"Unsupported github mode: {mode}")
    artifact.targets.append(target)
    return target
