from dataclasses import dataclass

@dataclass(frozen=True)
class WorkflowStage:
    stage_id: str
    tab_label: str
    objective: str
    status: str


@dataclass(frozen=True)
class ReadinessCheckResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class WorkflowPrerequisiteCheck:
    name: str
    passed: bool
    detail: str
    stage_id: str
