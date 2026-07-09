from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PublisherConfig:
    workdir: Path
    output_dir: Path | None = None
    github_mode: str = "pr-body-only"
    notion_mode: str = "dry-run"
    gdrive_wiki_mode: str = "dry-run"
    gdrive_wiki_root: Path | None = None
    notion_token: str = ""
    notion_database_id: str = ""
    commit_output: bool = False
    canonical_url: str = ""

    def __post_init__(self) -> None:
        self.workdir = Path(self.workdir).expanduser().resolve()
        if self.output_dir is not None:
            self.output_dir = Path(self.output_dir).expanduser().resolve()
        if self.gdrive_wiki_root is not None:
            self.gdrive_wiki_root = Path(self.gdrive_wiki_root).expanduser().resolve()

    def resolved_output_dir(self) -> Path:
        return self.output_dir or self.workdir / ".artifact-publisher"


def load_config(workdir: str | Path = ".", **overrides) -> PublisherConfig:
    gdrive_root = os.environ.get("GDRIVE_WIKI_ROOT")
    config = PublisherConfig(
        workdir=Path(workdir),
        gdrive_wiki_root=Path(gdrive_root).expanduser() if gdrive_root else None,
        notion_token=os.environ.get("NOTION_TOKEN", ""),
        notion_database_id=os.environ.get("NOTION_ARTIFACT_DB_ID", ""),
    )
    for key, value in overrides.items():
        if value is not None and hasattr(config, key):
            setattr(config, key, value)
    config.__post_init__()
    return config
