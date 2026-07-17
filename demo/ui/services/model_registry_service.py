from __future__ import annotations

from collections.abc import Callable

from models.model_registry_models import SaveModelPlan, SaveModelResult
from services.config_service import EnvironmentConfig
from services.model_registry_execution_service import ModelRegistryExecutionService


class ModelRegistryService:
    def __init__(self, execution_service: ModelRegistryExecutionService | None = None) -> None:
        self._execution_service = execution_service or ModelRegistryExecutionService()

    @staticmethod
    def build_plan(
        local_model_dir: str,
        repository: str,
        branch: str,
        commit_message: str,
        s3_prefix: str = "models",
    ) -> SaveModelPlan:
        return SaveModelPlan(
            local_model_dir=local_model_dir.strip(),
            repository=repository.strip(),
            branch=branch.strip(),
            commit_message=commit_message.strip(),
            s3_prefix=s3_prefix.strip().strip("/"),
        )

    def save_model(
        self,
        plan: SaveModelPlan,
        config: EnvironmentConfig,
        on_log: Callable[[str], None] | None = None,
    ) -> SaveModelResult:
        return self._execution_service.run(plan, config, on_log=on_log)
