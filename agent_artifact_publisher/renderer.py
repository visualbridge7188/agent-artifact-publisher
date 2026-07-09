from __future__ import annotations

from agent_artifact_publisher.model import Artifact


def _target_lines(artifact: Artifact) -> str:
    if not artifact.targets:
        return "- No targets recorded"
    return "\n".join(f"- {target.target}: {target.url_or_path or target.destination or target.status}" for target in artifact.targets)


def render_publish_report(artifact: Artifact) -> str:
    return f"""# {artifact.title} Publish Report

## Status

- Overall: {artifact.overall_status()}
- Type: {artifact.artifact_type}
- Project: {artifact.project}

## Links

{_target_lines(artifact)}

## Local Install

- Install: `{artifact.install.install_command}`
- Use: `{artifact.install.use_command}`
- Local link: {artifact.install.local_link}

## Verification

"""


def render_install_guide(artifact: Artifact) -> str:
    return f"""# {artifact.title} Install Guide

## Install

```bash
{artifact.install.install_command}
```

## Use

```bash
{artifact.install.use_command}
```

## Smoke test

```bash
{artifact.install.smoke_test_command}
```

## Uninstall / Rollback

```bash
{artifact.install.uninstall_command or artifact.install.rollback_command}
```
"""


def render_wiki_guide(artifact: Artifact) -> str:
    return f"""# {artifact.title}

## 궁극 목적

{artifact.summary}

## 사용법

{artifact.install.use_command}

## 기반 레퍼런스

"""


def render_notion_page(artifact: Artifact) -> str:
    return f"""# {artifact.title}

## 한 줄 설명

{artifact.summary}

## 링크

{_target_lines(artifact)}

## 상태

{artifact.overall_status()}
"""


def render_pr_body(artifact: Artifact) -> str:
    return f"""## Summary

{artifact.summary}

## Verification

See `.artifact-publisher/publish-report.md`.
"""


def render_links(artifact: Artifact) -> str:
    return f"""# {artifact.title} Links

{_target_lines(artifact)}

- Local install: {artifact.install.local_link}
"""


def render_all(artifact: Artifact) -> dict[str, str]:
    return {
        "publish-report": render_publish_report(artifact),
        "install": render_install_guide(artifact),
        "wiki-guide": render_wiki_guide(artifact),
        "notion-page": render_notion_page(artifact),
        "pr-body": render_pr_body(artifact),
        "links": render_links(artifact),
    }
