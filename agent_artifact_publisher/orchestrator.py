from __future__ import annotations

import json
from pathlib import Path

from agent_artifact_publisher.config import PublisherConfig
from agent_artifact_publisher.model import Artifact, InstallInfo
from agent_artifact_publisher.publishers.gdrive_wiki import publish_gdrive_wiki
from agent_artifact_publisher.publishers.github import prepare_github_publish
from agent_artifact_publisher.publishers.notion import prepare_notion_dry_run, publish_notion_page
from agent_artifact_publisher.renderer import render_all


def _slug(text: str) -> str:
    normalized = text.lower().replace("_", "-").replace("/", "-")
    return "-".join(part.strip("-.,:;()[]{}") for part in normalized.split() if part.strip("-.,:;()[]{}")) or "artifact"


def publish_artifact(
    config: PublisherConfig,
    title: str,
    artifact_type: str,
    project: str,
    summary: str,
    created_by_agent: str = "local-agent",
) -> Artifact:
    artifact_id = f"{artifact_type}-{_slug(title)}"
    output = config.resolved_output_dir()
    output.mkdir(parents=True, exist_ok=True)
    artifact = Artifact(
        artifact_id=artifact_id,
        title=title,
        artifact_type=artifact_type,
        project=project,
        summary=summary,
        workdir=str(config.workdir),
        created_by_agent=created_by_agent,
        install=InstallInfo(
            mode=artifact_type,
            install_command="See project README or generated install guide.",
            use_command=f"Use {title} according to the generated Wiki/Notion guide.",
            smoke_test_command="artifact-publish --dry-run --workdir .",
            uninstall_command="Remove copied artifact files or revert the related commit.",
            rollback_command="Revert the generated commit or restore the previous artifact version.",
            local_link=str(output / "install.md"),
        ),
    )
    rendered = render_all(artifact)
    prepare_github_publish(artifact, config.github_mode, rendered["pr-body"], output / "github")
    if config.notion_mode in {"create", "update"}:
        publish_notion_page(
            artifact,
            mode=config.notion_mode,
            token=config.notion_token,
            database_id=config.notion_database_id,
            body=rendered["notion-page"],
            schema={"Title": "title", "URL": "url", "description": "rich_text", "stats": "status"},
            canonical_url="",
        )
    else:
        prepare_notion_dry_run(artifact, rendered["notion-page"], output / "notion")
    if config.gdrive_wiki_mode == "write" and config.gdrive_wiki_root:
        publish_gdrive_wiki(artifact, config.gdrive_wiki_root, rendered["wiki-guide"])
    elif config.gdrive_wiki_mode == "write":
        from agent_artifact_publisher.model import PublishStatus, PublishTarget

        artifact.targets.append(PublishTarget(target="gdrive_wiki", mode="write", status=PublishStatus.FAILED, error="Missing GDRIVE_WIKI_ROOT"))
    rendered = render_all(artifact)
    (output / "publish-report.md").write_text(rendered["publish-report"], encoding="utf-8")
    (output / "install.md").write_text(rendered["install"], encoding="utf-8")
    (output / "links.md").write_text(rendered["links"], encoding="utf-8")
    (output / "artifact-manifest.json").write_text(json.dumps(artifact.to_manifest(), ensure_ascii=False, indent=2), encoding="utf-8")
    return artifact
