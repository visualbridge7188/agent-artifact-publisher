from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class PublishStatus(StrEnum):
    DRAFT = "draft"
    VERIFIED = "verified"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_CHECKED = "not_checked"


@dataclass
class Verification:
    command_or_check: str
    result: str = "not_run"
    evidence: str = ""
    notes: str = ""


@dataclass
class InstallInfo:
    mode: str = "manual"
    install_command: str = ""
    use_command: str = ""
    smoke_test_command: str = ""
    uninstall_command: str = ""
    rollback_command: str = ""
    local_link: str = ""


@dataclass
class PublishTarget:
    target: str
    mode: str
    destination: str = ""
    url_or_path: str = ""
    status: PublishStatus = PublishStatus.NOT_CHECKED
    error: str = ""


@dataclass
class Artifact:
    artifact_id: str
    title: str
    artifact_type: str
    project: str
    summary: str
    workdir: str
    created_by_agent: str
    status: PublishStatus = PublishStatus.DRAFT
    install: InstallInfo = field(default_factory=InstallInfo)
    targets: list[PublishTarget] = field(default_factory=list)
    verification: list[Verification] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)

    def overall_status(self) -> PublishStatus:
        if not self.targets:
            return PublishStatus.DRAFT
        statuses = [target.status for target in self.targets if target.status != PublishStatus.SKIPPED]
        if not statuses:
            return PublishStatus.SKIPPED
        if all(status == PublishStatus.VERIFIED for status in statuses):
            return PublishStatus.VERIFIED
        if any(status == PublishStatus.VERIFIED for status in statuses):
            return PublishStatus.PARTIAL
        if any(status == PublishStatus.FAILED for status in statuses):
            return PublishStatus.FAILED
        return PublishStatus.NOT_CHECKED

    def to_manifest(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = str(self.overall_status())
        data["targets"] = [asdict(target) | {"status": str(target.status)} for target in self.targets]
        return data
