from __future__ import annotations

import argparse

from agent_artifact_publisher.config import load_config
from agent_artifact_publisher.orchestrator import publish_artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish AI agent work artifacts")
    parser.add_argument("--workdir", default=".")
    parser.add_argument("--title", required=True)
    parser.add_argument("--artifact-type", default="other")
    parser.add_argument("--project", default="AI Agent Operations")
    parser.add_argument("--summary", default="AI agent work artifact")
    parser.add_argument("--created-by-agent", default="local-agent")
    parser.add_argument("--github", dest="github_mode", default=None)
    parser.add_argument("--notion", dest="notion_mode", default=None)
    parser.add_argument("--gdrive-wiki", dest="gdrive_wiki_mode", default=None)
    parser.add_argument("--canonical-url", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(
        args.workdir,
        github_mode=args.github_mode,
        notion_mode=args.notion_mode,
        gdrive_wiki_mode=args.gdrive_wiki_mode,
        canonical_url=args.canonical_url,
    )
    artifact = publish_artifact(config, args.title, args.artifact_type, args.project, args.summary, args.created_by_agent)
    print(config.resolved_output_dir() / "publish-report.md")
    return 0 if str(artifact.overall_status()) != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
