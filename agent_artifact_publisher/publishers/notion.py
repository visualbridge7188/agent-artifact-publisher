from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Callable, Mapping

from agent_artifact_publisher.model import Artifact, PublishStatus, PublishTarget

HttpClient = Callable[[str, str, Mapping[str, str], dict | None], tuple[int, dict]]


def _plain_blocks(markdown: str) -> list[dict]:
    blocks = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
        elif line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}})
        elif line.startswith("- "):
            blocks.append({"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
        else:
            blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}})
    return blocks[:100]


def build_notion_payload(
    artifact: Artifact,
    database_id: str,
    body: str,
    schema: Mapping[str, str],
    canonical_url: str = "",
) -> dict:
    properties: dict = {}
    if schema.get("Title") == "title":
        properties["Title"] = {"title": [{"type": "text", "text": {"content": artifact.title}}]}
    if schema.get("URL") == "url" and canonical_url:
        properties["URL"] = {"url": canonical_url}
    if schema.get("description") == "rich_text":
        properties["description"] = {"rich_text": [{"type": "text", "text": {"content": artifact.summary[:1900]}}]}
    if schema.get("stats") == "status":
        properties["stats"] = {"status": {"name": "Complete"}}
    return {"parent": {"database_id": database_id}, "properties": properties, "children": _plain_blocks(body)}


def _default_http_client(method: str, url: str, headers: Mapping[str, str], payload: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=dict(headers), method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except Exception as exc:
        return 0, {"message": str(exc)}


def prepare_notion_dry_run(artifact: Artifact, body: str, output_dir: Path | None = None) -> PublishTarget:
    output = output_dir or Path(artifact.workdir) / ".artifact-publisher" / "notion"
    output.mkdir(parents=True, exist_ok=True)
    page_path = output / "notion-page.md"
    page_path.write_text(body, encoding="utf-8")
    target = PublishTarget(target="notion", mode="dry-run", destination=str(page_path), url_or_path=str(page_path), status=PublishStatus.NOT_CHECKED)
    artifact.targets.append(target)
    return target


def publish_notion_page(
    artifact: Artifact,
    mode: str,
    token: str,
    database_id: str,
    body: str,
    schema: Mapping[str, str],
    canonical_url: str = "",
    http_client: HttpClient | None = None,
) -> PublishTarget:
    if mode in {"skip", "dry-run"}:
        return prepare_notion_dry_run(artifact, body)
    if not token or not database_id:
        target = PublishTarget(target="notion", mode=mode, status=PublishStatus.FAILED, error="Missing Notion token or database id")
        artifact.targets.append(target)
        return target

    client = http_client or _default_http_client
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    payload = build_notion_payload(artifact, database_id, body, schema, canonical_url)
    status, created = client("POST", "https://api.notion.com/v1/pages", headers, payload)
    page_id = created.get("id", "")
    page_url = created.get("url", "")
    if status < 200 or status >= 300 or not page_id:
        target = PublishTarget(target="notion", mode=mode, url_or_path=page_url, status=PublishStatus.FAILED, error=str(created))
        artifact.targets.append(target)
        return target
    read_status, readback = client("GET", f"https://api.notion.com/v1/pages/{page_id}", headers, None)
    verified_url = readback.get("url", page_url)
    ok = 200 <= read_status < 300 and bool(verified_url)
    target = PublishTarget(
        target="notion",
        mode=mode,
        destination=page_id,
        url_or_path=verified_url,
        status=PublishStatus.VERIFIED if ok else PublishStatus.FAILED,
        error="" if ok else str(readback),
    )
    artifact.targets.append(target)
    return target
