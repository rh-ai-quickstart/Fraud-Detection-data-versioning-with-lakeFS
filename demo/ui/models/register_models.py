from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RegisterModelPlan:
    model_name: str
    version_name: str
    description: str
    repository: str
    branch: str
    model_relative_path: str
    model_format_name: str
    model_format_version: str
    storage_key: str
    author: str


@dataclass(frozen=True)
class RegisterModelResult:
    model_name: str
    version_name: str
    registered_model_id: str
    model_version_id: str
    artifact_id: str
    storage_uri: str
    storage_path: str
    log_lines: tuple[str, ...] = field(default_factory=tuple)
