from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TrainingPlan:
    repository: str
    main_branch: str
    training_branch: str
    epochs: int
    threshold: float
    class_weighting: bool
    train_path: str
    validate_path: str
    test_path: str


@dataclass(frozen=True)
class TrainingResult:
    accuracy: float
    precision: float
    recall: float
    epochs: int
    training_seconds: float
    model_path: str
    repository: str
    training_branch: str
    train_s3_uri: str
    validate_s3_uri: str
    test_s3_uri: str
    log_lines: tuple[str, ...] = field(default_factory=tuple)
