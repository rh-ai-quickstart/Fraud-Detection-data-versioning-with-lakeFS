from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DeployModelPlan:
    inference_service_name: str
    namespace: str
    repository: str
    branch: str
    model_relative_path: str
    storage_key: str
    service_account_name: str
    model_format_name: str
    serving_runtime_name: str


@dataclass(frozen=True)
class DeployModelResult:
    inference_service_name: str
    namespace: str
    storage_path: str
    predictor_service: str
    infer_url: str
    ready: bool
    status_message: str
    log_lines: tuple[str, ...] = field(default_factory=tuple)
