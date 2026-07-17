from __future__ import annotations

from collections.abc import Callable

from models.training_models import TrainingPlan, TrainingResult
from services.config_service import EnvironmentConfig
from services.training_execution_service import TrainingExecutionService


class TrainingService:
    def __init__(self, execution_service: TrainingExecutionService | None = None) -> None:
        self._execution_service = execution_service or TrainingExecutionService()

    @staticmethod
    def build_plan(
        repository: str,
        main_branch: str,
        training_branch: str,
        epochs: int,
        threshold: float,
        class_weighting: bool,
        train_path: str,
        validate_path: str,
        test_path: str,
    ) -> TrainingPlan:
        return TrainingPlan(
            repository=repository.strip(),
            main_branch=main_branch.strip(),
            training_branch=training_branch.strip(),
            epochs=epochs,
            threshold=threshold,
            class_weighting=class_weighting,
            train_path=train_path.strip(),
            validate_path=validate_path.strip(),
            test_path=test_path.strip(),
        )

    def run_training(
        self,
        plan: TrainingPlan,
        config: EnvironmentConfig,
        on_log: Callable[[str], None] | None = None,
    ) -> TrainingResult:
        return self._execution_service.run(plan, config, on_log=on_log)
