from __future__ import annotations

from agent_artifact_publisher.config import load_config
from agent_artifact_publisher.orchestrator import publish_artifact


def publish_artifact_tool(
    workdir: str,
    title: str,
    artifact_type: str,
    project: str,
    summary: str,
    created_by_agent: str = "local-agent",
    dry_run: bool = True,
) -> dict:
    config = load_config(
        workdir,
        github_mode="pr-body-only",
        notion_mode="dry-run" if dry_run else "update",
        gdrive_wiki_mode="dry-run" if dry_run else "write",
    )
    artifact = publish_artifact(config, title, artifact_type, project, summary, created_by_agent)
    output = config.resolved_output_dir()
    return {
        "artifact_id": artifact.artifact_id,
        "status": str(artifact.overall_status()),
        "links": {
            "publish_report": str(output / "publish-report.md"),
            "install": str(output / "install.md"),
            "manifest": str(output / "artifact-manifest.json"),
            "links": str(output / "links.md"),
        },
    }
