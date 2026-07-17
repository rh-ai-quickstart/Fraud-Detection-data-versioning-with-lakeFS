from __future__ import annotations

from collections.abc import Callable

from clients import ModelRegistryApiClient, OpenShiftClient
from models.register_models import RegisterModelPlan, RegisterModelResult
from services.config_service import EnvironmentConfig


class RegisterExecutionService:
    @staticmethod
    def run(
        plan: RegisterModelPlan,
        config: EnvironmentConfig,
        on_log: Callable[[str], None] | None = None,
    ) -> RegisterModelResult:
        logs: list[str] = []

        def log(message: str) -> None:
            logs.append(message)
            if on_log:
                on_log(message)

        if not config.model_registry_url:
            raise ValueError("MODEL_REGISTRY_URL is not configured.")

        token_ok, token_or_message = OpenShiftClient.current_token()
        if not token_ok:
            raise ValueError(token_or_message)

        storage_path = RegisterExecutionService._storage_path(plan)
        storage_uri = RegisterExecutionService._storage_uri(plan)
        client = ModelRegistryApiClient(
            base_url=config.model_registry_url,
            token=token_or_message,
        )

        ok, message, models = client.list_registered_models()
        if not ok:
            raise ValueError(message)
        log(message)

        registered_model = ModelRegistryApiClient.find_registered_model(models, plan.model_name)
        if registered_model:
            registered_model_id = str(registered_model["id"])
            log(f"Reusing registered model `{plan.model_name}` (id={registered_model_id}).")
        else:
            ok, message, registered_model = client.create_registered_model(
                {
                    "name": plan.model_name,
                    "description": plan.description,
                    "owner": plan.author,
                    "state": "LIVE",
                }
            )
            if not ok or not registered_model:
                raise ValueError(message)
            registered_model_id = str(registered_model["id"])
            log(f"Created registered model `{plan.model_name}` (id={registered_model_id}).")

        ok, message, versions = client.list_model_versions()
        if not ok:
            raise ValueError(message)
        log(message)

        model_version = ModelRegistryApiClient.find_model_version(
            versions,
            registered_model_id,
            plan.version_name,
        )
        if model_version:
            model_version_id = str(model_version["id"])
            log(f"Reusing model version `{plan.version_name}` (id={model_version_id}).")
            artifact_id = "existing"
        else:
            ok, message, model_version = client.create_model_version(
                {
                    "name": plan.version_name,
                    "description": plan.description,
                    "author": plan.author,
                    "registeredModelId": registered_model_id,
                    "state": "LIVE",
                }
            )
            if not ok or not model_version:
                raise ValueError(message)
            model_version_id = str(model_version["id"])
            log(f"Created model version `{plan.version_name}` (id={model_version_id}).")

            ok, message, artifact = client.create_model_artifact(
                model_version_id,
                {
                    "modelVersionId": model_version_id,
                    "name": f"{plan.model_name}-artifact",
                    "description": plan.description,
                    "modelFormatName": plan.model_format_name,
                    "modelFormatVersion": plan.model_format_version,
                    "storageKey": plan.storage_key,
                    "storagePath": storage_path,
                    "uri": storage_uri,
                    "artifactType": "model-artifact",
                    "state": "LIVE",
                },
            )
            if not ok or not artifact:
                raise ValueError(message)
            artifact_id = str(artifact.get("id", "created"))
            log(f"Created model artifact pointing at `{storage_uri}`.")

        return RegisterModelResult(
            model_name=plan.model_name,
            version_name=plan.version_name,
            registered_model_id=registered_model_id,
            model_version_id=model_version_id,
            artifact_id=artifact_id,
            storage_uri=storage_uri,
            storage_path=storage_path,
            log_lines=tuple(logs),
        )

    @staticmethod
    def _storage_path(plan: RegisterModelPlan) -> str:
        relative = plan.model_relative_path.strip().strip("/")
        if "/" in relative:
            relative = relative.rsplit("/", 1)[0]
        return f"{plan.branch.strip()}/{relative}"

    @staticmethod
    def _storage_uri(plan: RegisterModelPlan) -> str:
        relative = plan.model_relative_path.strip().strip("/")
        return f"s3://{plan.repository.strip()}/{plan.branch.strip()}/{relative}"
