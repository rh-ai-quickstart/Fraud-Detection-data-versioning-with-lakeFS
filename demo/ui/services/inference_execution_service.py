from __future__ import annotations

from collections.abc import Callable
from typing import Any

from clients import InferenceApiClient, OpenShiftClient
from models.inference_models import InferencePlan, InferenceResult, TransactionFeatures
from services.config_service import EnvironmentConfig
from services.inference_support import InferenceDecisionService, InferencePayloadBuilder
from services.scaler_artifact_service import ScalerArtifactService


class InferenceExecutionService:
    def __init__(self, scaler_service: ScalerArtifactService | None = None) -> None:
        self._scaler_service = scaler_service or ScalerArtifactService()

    def run(
        self,
        plan: InferencePlan,
        config: EnvironmentConfig,
        on_log: Callable[[str], None] | None = None,
    ) -> InferenceResult:
        logs: list[str] = []

        def log(message: str) -> None:
            logs.append(message)
            if on_log:
                on_log(message)

        if not plan.infer_url:
            raise ValueError("Inference URL is empty. Set INFERENCE_URL in the deployment environment.")

        scaler = self._scaler_service.load_from_branch(plan.repository, plan.training_branch, config)
        log(f"Loaded scaler from `{plan.repository}/{plan.training_branch}/artifact/scaler.pkl`.")

        raw_features = self._feature_list(plan.features)
        scaled_features = scaler.transform([raw_features]).tolist()[0]
        log(f"Transformed features: {raw_features} -> {[round(v, 5) for v in scaled_features]}")

        payload = InferencePayloadBuilder.build_payload(scaled_features)
        token_ok, token_or_message = OpenShiftClient.current_token()
        if not token_ok:
            raise ValueError(token_or_message)

        auth_source = OpenShiftClient.token_source()
        log(f"Using auth token from {auth_source}.")

        client = InferenceApiClient(
            infer_url=plan.infer_url,
            token=token_or_message,
            verify_tls=plan.verify_tls,
        )
        call_ok, call_message, outputs = client.infer(payload)
        if not call_ok or not outputs:
            raise ValueError(call_message)

        score = float(outputs[0])
        decision = InferenceDecisionService.classify(score, plan.threshold)
        log(call_message)
        log(f"Prediction score={score:.5f}, threshold={plan.threshold:.2f}, decision={decision}")

        return InferenceResult(
            model_name=plan.model_name,
            infer_url=plan.infer_url,
            raw_features=tuple(raw_features),
            scaled_features=tuple(float(v) for v in scaled_features),
            payload=payload,
            score=score,
            decision=decision,
            threshold=plan.threshold,
            auth_source=auth_source,
            log_lines=tuple(logs),
        )

    @staticmethod
    def _feature_list(features: TransactionFeatures) -> list[float]:
        return [
            features.distance_from_last_transaction,
            features.ratio_to_median_purchase_price,
            features.used_chip,
            features.used_pin_number,
            features.online_order,
        ]
