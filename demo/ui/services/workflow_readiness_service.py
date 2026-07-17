from __future__ import annotations

import lakefs

from clients import InferenceApiClient, KubernetesClient, ModelRegistryApiClient, OpenShiftClient
from clients.lakefs_s3_client import LakeFSS3Client
from models.workflow_models import WorkflowPrerequisiteCheck
from services.config_service import EnvironmentConfig
from services.deploy_execution_service import DeployExecutionService
from services.lakefs_repository_service import LakeFSRepositoryService


class WorkflowReadinessService:
    def evaluate_inference_prerequisites(
        self,
        repository: str,
        branch: str,
        model_relative_path: str,
        infer_url: str,
        config: EnvironmentConfig,
    ) -> list[WorkflowPrerequisiteCheck]:
        checks: list[WorkflowPrerequisiteCheck] = []
        checks.append(self._check_scaler_artifact(repository, branch, config))
        checks.append(self._check_model_artifact(repository, branch, model_relative_path, config))
        checks.append(self._check_registered_model(config))
        checks.append(self._check_deployed_service(config))
        checks.append(self._check_inference_endpoint(infer_url, config))
        return checks

    @staticmethod
    def _check_scaler_artifact(repository: str, branch: str, config: EnvironmentConfig) -> WorkflowPrerequisiteCheck:
        try:
            LakeFSRepositoryService.configure_sdk(config)
            LakeFSRepositoryService.ensure_repository_exists(repository, config)
            with lakefs.Repository(repository).branch(branch).object(path="artifact/scaler.pkl").reader("rb"):
                pass
            return WorkflowPrerequisiteCheck(
                name="Training scaler artifact",
                passed=True,
                detail=f"Found `{repository}/{branch}/artifact/scaler.pkl`.",
                stage_id="train",
            )
        except Exception as exc:
            return WorkflowPrerequisiteCheck(
                name="Training scaler artifact",
                passed=False,
                detail=f"Missing scaler on `{repository}/{branch}`: {exc}",
                stage_id="train",
            )

    @staticmethod
    def _check_model_artifact(
        repository: str,
        branch: str,
        model_relative_path: str,
        config: EnvironmentConfig,
    ) -> WorkflowPrerequisiteCheck:
        key = f"{branch}/{model_relative_path.strip().strip('/')}"
        s3_client = LakeFSS3Client(config)
        objects = s3_client.list_objects(key)
        if objects:
            return WorkflowPrerequisiteCheck(
                name="Saved model artifact",
                passed=True,
                detail=f"Found lakeFS object `{key}`.",
                stage_id="save",
            )
        return WorkflowPrerequisiteCheck(
            name="Saved model artifact",
            passed=False,
            detail=f"Model object `{key}` was not found in lakeFS.",
            stage_id="save",
        )

    @staticmethod
    def _check_registered_model(config: EnvironmentConfig) -> WorkflowPrerequisiteCheck:
        if not config.model_registry_url:
            return WorkflowPrerequisiteCheck(
                name="Model Registry registration",
                passed=False,
                detail="MODEL_REGISTRY_URL is not configured.",
                stage_id="register",
            )

        token_ok, token_or_message = OpenShiftClient.current_token()
        token = token_or_message if token_ok else ""
        client = ModelRegistryApiClient(base_url=config.model_registry_url, token=token)
        ok, message, models = client.list_registered_models()
        if not ok:
            return WorkflowPrerequisiteCheck(
                name="Model Registry registration",
                passed=False,
                detail=message,
                stage_id="register",
            )

        model = ModelRegistryApiClient.find_registered_model(models, config.inference_model_name)
        if model:
            return WorkflowPrerequisiteCheck(
                name="Model Registry registration",
                passed=True,
                detail=f"Registered model `{config.inference_model_name}` exists (id={model.get('id')}).",
                stage_id="register",
            )
        return WorkflowPrerequisiteCheck(
            name="Model Registry registration",
            passed=False,
            detail=f"Registered model `{config.inference_model_name}` was not found.",
            stage_id="register",
        )

    @staticmethod
    def _check_deployed_service(config: EnvironmentConfig) -> WorkflowPrerequisiteCheck:
        token_ok, token_or_message = OpenShiftClient.current_token()
        if not token_ok:
            return WorkflowPrerequisiteCheck(
                name="Deployed InferenceService",
                passed=False,
                detail=token_or_message,
                stage_id="deploy",
            )

        k8s = KubernetesClient.from_service_account(token_or_message)
        namespace = config.deploy_namespace or k8s.namespace
        if not namespace:
            return WorkflowPrerequisiteCheck(
                name="Deployed InferenceService",
                passed=False,
                detail="Deploy namespace is not configured.",
                stage_id="deploy",
            )

        ok, message, resource = k8s.get_custom_resource(
            DeployExecutionService.KSERVE_GROUP,
            DeployExecutionService.KSERVE_VERSION,
            DeployExecutionService.KSERVE_PLURAL,
            config.inference_model_name,
            namespace=namespace,
        )
        if not ok or not resource:
            return WorkflowPrerequisiteCheck(
                name="Deployed InferenceService",
                passed=False,
                detail=f"InferenceService `{config.inference_model_name}` not found in `{namespace}`.",
                stage_id="deploy",
            )

        ready, ready_message = KubernetesClient.inference_service_ready(resource)
        return WorkflowPrerequisiteCheck(
            name="Deployed InferenceService",
            passed=ready,
            detail=ready_message,
            stage_id="deploy",
        )

    @staticmethod
    def _check_inference_endpoint(infer_url: str, config: EnvironmentConfig) -> WorkflowPrerequisiteCheck:
        if not infer_url:
            return WorkflowPrerequisiteCheck(
                name="Inference endpoint",
                passed=False,
                detail="Inference URL is empty.",
                stage_id="inference",
            )

        token_ok, token_or_message = OpenShiftClient.current_token()
        if not token_ok:
            return WorkflowPrerequisiteCheck(
                name="Inference endpoint",
                passed=False,
                detail=token_or_message,
                stage_id="inference",
            )

        probe_payload = {
            "inputs": [{
                "name": "dense_input",
                "shape": [1, 5],
                "datatype": "FP32",
                "data": [0.0, 0.0, 0.0, 0.0, 0.0],
            }]
        }
        client = InferenceApiClient(infer_url=infer_url, token=token_or_message, timeout_seconds=5)
        ok, message, _ = client.infer(probe_payload)
        return WorkflowPrerequisiteCheck(
            name="Inference endpoint",
            passed=ok,
            detail=message,
            stage_id="inference",
        )
