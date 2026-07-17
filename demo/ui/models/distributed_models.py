from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DistributedTrainingPlan:
    cluster_name: str
    namespace: str
    training_branch: str
    num_workers: int
    worker_cpu_requests: int
    worker_cpu_limits: int
    worker_memory_limits_gi: int
    image: str
    script_name: str
    scripts_dir: str
    cluster_ready_timeout_seconds: int = 600


@dataclass(frozen=True)
class DistributedTrainingResult:
    submission_id: str
    cluster_name: str
    namespace: str
    job_status: str
    entrypoint: str
    dashboard_url: str = ""
    log_lines: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DistributedJobStatus:
    submission_id: str
    status: str
    log_tail: tuple[str, ...]
    is_terminal: bool
