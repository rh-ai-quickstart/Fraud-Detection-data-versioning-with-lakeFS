from __future__ import annotations

from collections.abc import Callable

from models.deploy_models import DeployModelPlan, DeployModelResult
from services.config_service import EnvironmentConfig
from services.deploy_execution_service import DeployExecutionService


class DeployService:
    DEFAULT_MODEL_PATH = "models/fraud/1/model.onnx"

    def __init__(self, execution_service: DeployExecutionService | None = None) -> None:
        self._execution_service = execution_service or DeployExecutionService()

    @staticmethod
    def build_plan(
        inference_service_name: str,
        namespace: str,
        repository: str,
        branch: str,
        model_relative_path: str,
        storage_key: str,
        service_account_name: str,
        model_format_name: str,
        serving_runtime_name: str,
    ) -> DeployModelPlan:
        return DeployModelPlan(
            inference_service_name=inference_service_name.strip(),
            namespace=namespace.strip(),
            repository=repository.strip(),
            branch=branch.strip(),
            model_relative_path=model_relative_path.strip().strip("/"),
            storage_key=storage_key.strip(),
            service_account_name=service_account_name.strip(),
            model_format_name=model_format_name.strip(),
            serving_runtime_name=serving_runtime_name.strip(),
        )

    def deploy_model(
        self,
        plan: DeployModelPlan,
        config: EnvironmentConfig,
        on_log: Callable[[str], None] | None = None,
    ) -> DeployModelResult:
        return self._execution_service.run(plan, config, on_log=on_log)
