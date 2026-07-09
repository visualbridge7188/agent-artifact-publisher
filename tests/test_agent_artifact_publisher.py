import json
from pathlib import Path

from agent_artifact_publisher.config import PublisherConfig, load_config
from agent_artifact_publisher.model import Artifact, InstallInfo, PublishStatus, PublishTarget
from agent_artifact_publisher.scanner import scan_workdir
from agent_artifact_publisher.renderer import render_all
from agent_artifact_publisher.publishers.gdrive_wiki import publish_gdrive_wiki
from agent_artifact_publisher.publishers.github import prepare_github_publish
from agent_artifact_publisher.publishers.notion import build_notion_payload, prepare_notion_dry_run, publish_notion_page
from agent_artifact_publisher.orchestrator import publish_artifact
from agent_artifact_publisher.mcp.tools import publish_artifact_tool


def test_artifact_manifest_and_partial_status():
    artifact = Artifact(
        artifact_id="skill-demo-2026-07-09",
        title="Demo Skill",
        artifact_type="skill",
        project="AI Agent Operations",
        summary="Demo summary",
        workdir=".",
        created_by_agent="codex",
        install=InstallInfo(mode="skill", install_command="install", use_command="use"),
    )
    artifact.targets.append(PublishTarget(target="github", mode="pr-body-only", status=PublishStatus.VERIFIED))
    artifact.targets.append(PublishTarget(target="notion", mode="update", status=PublishStatus.FAILED, error="401"))
    manifest = artifact.to_manifest()
    assert manifest["artifact_id"] == "skill-demo-2026-07-09"
    assert manifest["install"]["mode"] == "skill"
    assert manifest["status"] == "partial"


def test_config_env_and_safe_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("GDRIVE_WIKI_ROOT", str(tmp_path / "Wiki"))
    config = load_config(workdir=tmp_path)
    assert config.gdrive_wiki_root == tmp_path / "Wiki"
    assert config.github_mode == "pr-body-only"
    assert config.notion_mode == "dry-run"
    assert config.commit_output is False


def test_scan_detects_skill_and_readme(tmp_path):
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    skill_dir = tmp_path / "skills" / "demo-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: demo-skill\ndescription: Use when testing.\n---\n", encoding="utf-8")
    result = scan_workdir(tmp_path)
    assert "README.md" in result.candidate_files
    assert "skills/demo-skill/SKILL.md" in result.candidate_files
    assert result.detected_type == "skill"


def test_render_all_contains_links_and_install_sections(tmp_path):
    artifact = Artifact(
        artifact_id="demo",
        title="Demo Skill",
        artifact_type="skill",
        project="Ops",
        summary="Demo summary",
        workdir=str(tmp_path),
        created_by_agent="codex",
        install=InstallInfo(mode="skill", install_command="install", use_command="use", smoke_test_command="test"),
    )
    artifact.targets.append(PublishTarget(target="github", mode="pr-body-only", url_or_path="https://github.com/x/y", status=PublishStatus.VERIFIED))
    rendered = render_all(artifact)
    assert "install" in rendered
    assert "links" in rendered
    assert "https://github.com/x/y" in rendered["publish-report"]
    assert "Smoke test" in rendered["install"]


def test_gdrive_wiki_writes_and_verifies(tmp_path):
    artifact = Artifact("demo-artifact", "Demo Artifact", "skill", "Ops", "Demo summary", str(tmp_path), "codex")
    target = publish_gdrive_wiki(artifact, root=tmp_path / "Wiki", content="# Demo Artifact\n\n## 사용법\nUse it")
    assert target.status == PublishStatus.VERIFIED
    assert (tmp_path / "Wiki" / "Ops" / "skill" / "demo-artifact.md").exists()


def test_publish_artifact_dry_run_creates_manifest_reports_and_links(tmp_path):
    workdir = tmp_path / "work"
    workdir.mkdir()
    (workdir / "README.md").write_text("# Demo\n", encoding="utf-8")
    config = PublisherConfig(workdir=workdir, gdrive_wiki_mode="dry-run", github_mode="pr-body-only", notion_mode="dry-run")
    result = publish_artifact(config, title="Demo", artifact_type="skill", project="Ops", summary="Summary", created_by_agent="codex")
    output = workdir / ".artifact-publisher"
    assert (output / "artifact-manifest.json").exists()
    assert (output / "publish-report.md").exists()
    assert (output / "install.md").exists()
    assert (output / "links.md").exists()
    manifest = json.loads((output / "artifact-manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifact_id"] == result.artifact_id


def test_github_pr_mode_uses_runner_and_records_url(tmp_path):
    artifact = Artifact("demo", "Demo", "skill", "Ops", "Summary", str(tmp_path), "codex")
    calls = []

    def fake_runner(command, cwd):
        calls.append((command, cwd))
        if command[:3] == ["gh", "pr", "create"]:
            return 0, "https://github.com/org/repo/pull/7\n", ""
        return 0, "", ""

    target = prepare_github_publish(artifact, mode="pr", pr_body="## Summary", output_dir=tmp_path / "github", runner=fake_runner)
    assert target.status == PublishStatus.VERIFIED
    assert target.url_or_path == "https://github.com/org/repo/pull/7"
    assert any(call[0][:3] == ["gh", "pr", "create"] for call in calls)


def test_github_pr_mode_fails_safely_without_gh(tmp_path):
    artifact = Artifact("demo", "Demo", "skill", "Ops", "Summary", str(tmp_path), "codex")

    def missing_runner(command, cwd):
        return 127, "", "gh missing"

    target = prepare_github_publish(artifact, mode="pr", pr_body="## Summary", output_dir=tmp_path / "github", runner=missing_runner)
    assert target.status == PublishStatus.FAILED
    assert target.error
    assert (tmp_path / "github" / "pr-body.md").exists()


def test_notion_payload_uses_existing_schema_fields_only():
    artifact = Artifact("demo", "Demo", "skill", "Ops", "Summary", ".", "codex")
    payload = build_notion_payload(
        artifact,
        database_id="db123",
        body="# Demo\n\n## Usage\nUse it",
        schema={"Title": "title", "URL": "url", "description": "rich_text", "stats": "status"},
        canonical_url="https://github.com/org/repo",
    )
    assert payload["parent"] == {"database_id": "db123"}
    assert set(payload["properties"]) == {"Title", "URL", "description", "stats"}
    assert payload["properties"]["URL"]["url"] == "https://github.com/org/repo"
    assert payload["children"]


def test_notion_update_uses_http_client_and_readback():
    artifact = Artifact("demo", "Demo", "skill", "Ops", "Summary", ".", "codex")
    requests = []

    def fake_http(method, url, headers, payload=None):
        requests.append((method, url, payload))
        if method == "POST":
            return 200, {"id": "page123", "url": "https://notion.so/page123"}
        if method == "GET":
            return 200, {"id": "page123", "url": "https://notion.so/page123"}
        return 500, {"message": "unexpected"}

    target = publish_notion_page(
        artifact,
        mode="create",
        token="secret",
        database_id="db123",
        body="# Demo",
        schema={"Title": "title", "URL": "url", "description": "rich_text"},
        canonical_url="https://github.com/org/repo",
        http_client=fake_http,
    )
    assert target.status == PublishStatus.VERIFIED
    assert target.url_or_path == "https://notion.so/page123"
    assert requests[0][0] == "POST"
    assert requests[1][0] == "GET"


def test_publish_artifact_marks_missing_gdrive_root_failed(tmp_path):
    workdir = tmp_path / "work"
    workdir.mkdir()
    config = PublisherConfig(workdir=workdir, gdrive_wiki_mode="write", github_mode="pr-body-only", notion_mode="dry-run")
    result = publish_artifact(config, title="Demo", artifact_type="skill", project="Ops", summary="Summary", created_by_agent="codex")
    gdrive = [target for target in result.targets if target.target == "gdrive_wiki"][0]
    assert gdrive.status == PublishStatus.FAILED
    assert "GDRIVE_WIKI_ROOT" in gdrive.error


def test_publish_artifact_tool_returns_links(tmp_path):
    result = publish_artifact_tool(
        workdir=str(tmp_path),
        title="Demo",
        artifact_type="skill",
        project="Ops",
        summary="Summary",
        created_by_agent="codex",
        dry_run=True,
    )
    assert result["status"] in {"draft", "partial", "verified", "not_checked"}
    assert "publish_report" in result["links"]
    assert "install" in result["links"]
