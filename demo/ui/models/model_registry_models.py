from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SaveModelPlan:
    local_model_dir: str
    repository: str
    branch: str
    commit_message: str
    s3_prefix: str = "models"


@dataclass(frozen=True)
class SaveModelResult:
    repository: str
    branch: str
    files_uploaded: int
    objects_before: tuple[str, ...]
    objects_after: tuple[str, ...]
    commit_id: str
    commit_message: str
    log_lines: tuple[str, ...] = field(default_factory=tuple)
