from __future__ import annotations

from collections.abc import Callable
from typing import Any

from clients import InferenceApiClient
from models.inference_models import InferencePlan, InferenceResult, TransactionFeatures
from services.config_service import EnvironmentConfig
from services.inference_execution_service import InferenceExecutionService


class InferenceService:
    def __init__(self, execution_service: InferenceExecutionService | None = None) -> None:
        self._execution_service = execution_service or InferenceExecutionService()

    @staticmethod
    def build_plan(
        repository: str,
        training_branch: str,
        infer_url: str,
        model_name: str,
        threshold: float,
        features: TransactionFeatures,
        verify_tls: bool = False,
    ) -> InferencePlan:
        return InferencePlan(
            repository=repository.strip(),
            training_branch=training_branch.strip(),
            infer_url=infer_url.strip(),
            model_name=model_name.strip(),
            threshold=threshold,
            features=features,
            verify_tls=verify_tls,
        )

    def run_inference(
        self,
        plan: InferencePlan,
        config: EnvironmentConfig,
        on_log: Callable[[str], None] | None = None,
    ) -> InferenceResult:
        return self._execution_service.run(plan, config, on_log=on_log)

    @staticmethod
    def execute_remote_inference(infer_url: str, token: str, payload: dict[str, Any]) -> tuple[bool, str, list[float]]:
        client = InferenceApiClient(infer_url=infer_url, token=token)
        return client.infer(payload)
