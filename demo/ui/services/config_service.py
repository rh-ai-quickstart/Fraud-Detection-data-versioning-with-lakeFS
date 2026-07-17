from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentConfig:
    lakefs_endpoint: str
    lakefs_access_key: str
    lakefs_secret_key: str
    aws_s3_endpoint: str
    aws_access_key: str
    aws_secret_key: str
    lakefs_repo_name: str
    lakefs_region: str
    inference_url: str
    inference_model_name: str
    inference_bearer_token: str
    model_registry_url: str
    model_registry_name: str
    data_connection_key: str
    deploy_namespace: str
    inference_service_account: str
    inference_port: int
    serving_runtime_name: str
    pipeline_artifacts_endpoint_url: str
    pipeline_artifacts_access_key_id: str
    pipeline_artifacts_secret_access_key: str
    pipeline_artifacts_s3_bucket: str


class EnvironmentConfigService:
    @staticmethod
    def from_os_env() -> EnvironmentConfig:
        return EnvironmentConfig(
            lakefs_endpoint=os.getenv("LAKECTL_SERVER_ENDPOINT_URL", ""),
            lakefs_access_key=os.getenv("LAKECTL_CREDENTIALS_ACCESS_KEY_ID", ""),
            lakefs_secret_key=os.getenv("LAKECTL_CREDENTIALS_SECRET_ACCESS_KEY", ""),
            aws_s3_endpoint=os.getenv("AWS_S3_ENDPOINT", ""),
            aws_access_key=os.getenv("AWS_ACCESS_KEY_ID", ""),
            aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
            lakefs_repo_name=os.getenv("LAKEFS_REPO_NAME", "my-storage"),
            lakefs_region=os.getenv("LAKEFS_DEFAULT_REGION", "us-east-1"),
            inference_url=os.getenv("INFERENCE_URL", ""),
            inference_model_name=os.getenv("INFERENCE_MODEL_NAME", "fraud-detection"),
            inference_bearer_token=os.getenv("INFERENCE_BEARER_TOKEN", ""),
            model_registry_url=os.getenv(
                "MODEL_REGISTRY_URL",
                "http://lakefs-model-registry.rhoai-model-registries.svc:8080",
            ),
            model_registry_name=os.getenv("MODEL_REGISTRY_NAME", "lakefs-model-registry"),
            data_connection_key=os.getenv("DATA_CONNECTION_KEY", "my-storage"),
            deploy_namespace=os.getenv("DEPLOY_NAMESPACE", os.getenv("OPENSHIFT_NAMESPACE", "")),
            inference_service_account=os.getenv("INFERENCE_SERVICE_ACCOUNT", ""),
            inference_port=int(os.getenv("INFERENCE_PORT", "80")),
            serving_runtime_name=os.getenv("SERVING_RUNTIME_NAME", "kserve-ovms"),
            pipeline_artifacts_endpoint_url=os.getenv("PIPELINE_ARTIFACTS_ENDPOINT_URL", os.getenv("AWS_S3_ENDPOINT", "")),
            pipeline_artifacts_access_key_id=os.getenv(
                "PIPELINE_ARTIFACTS_ACCESS_KEY_ID",
                os.getenv("MINIO_ACCESS_KEY", os.getenv("AWS_ACCESS_KEY_ID", "")),
            ),
            pipeline_artifacts_secret_access_key=os.getenv(
                "PIPELINE_ARTIFACTS_SECRET_ACCESS_KEY",
                os.getenv("MINIO_SECRET_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", "")),
            ),
            pipeline_artifacts_s3_bucket=os.getenv("PIPELINE_ARTIFACTS_S3_BUCKET", "pipeline-artifacts"),
        )

