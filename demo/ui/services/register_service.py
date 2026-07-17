from __future__ import annotations

from collections.abc import Callable

from models.register_models import RegisterModelPlan, RegisterModelResult
from services.config_service import EnvironmentConfig
from services.register_execution_service import RegisterExecutionService


class RegisterService:
    DEFAULT_MODEL_PATH = "models/fraud/1/model.onnx"

    def __init__(self, execution_service: RegisterExecutionService | None = None) -> None:
        self._execution_service = execution_service or RegisterExecutionService()

    @staticmethod
    def build_plan(
        model_name: str,
        version_name: str,
        description: str,
        repository: str,
        branch: str,
        model_relative_path: str,
        model_format_name: str,
        model_format_version: str,
        storage_key: str,
        author: str,
    ) -> RegisterModelPlan:
        return RegisterModelPlan(
            model_name=model_name.strip(),
            version_name=version_name.strip(),
            description=description.strip(),
            repository=repository.strip(),
            branch=branch.strip(),
            model_relative_path=model_relative_path.strip().strip("/"),
            model_format_name=model_format_name.strip(),
            model_format_version=model_format_version.strip(),
            storage_key=storage_key.strip(),
            author=author.strip() or "fraud-detection-studio",
        )

    def register_model(
        self,
        plan: RegisterModelPlan,
        config: EnvironmentConfig,
        on_log: Callable[[str], None] | None = None,
    ) -> RegisterModelResult:
        return self._execution_service.run(plan, config, on_log=on_log)
