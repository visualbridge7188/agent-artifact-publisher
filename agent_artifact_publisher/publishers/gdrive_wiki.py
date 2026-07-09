from __future__ import annotations

from pathlib import Path

from agent_artifact_publisher.model import Artifact, PublishStatus, PublishTarget
from agent_artifact_publisher.verifiers.filesystem import verify_file_contains


def publish_gdrive_wiki(artifact: Artifact, root: Path, content: str) -> PublishTarget:
    destination_dir = Path(root).expanduser().resolve() / artifact.project / artifact.artifact_type
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{artifact.artifact_id}.md"
    destination.write_text(content, encoding="utf-8")
    ok, evidence = verify_file_contains(destination, [artifact.title])
    target = PublishTarget(
        target="gdrive_wiki",
        mode="write",
        destination=str(destination),
        url_or_path=str(destination),
        status=PublishStatus.VERIFIED if ok else PublishStatus.FAILED,
        error="" if ok else evidence,
    )
    artifact.targets.append(target)
    return target
