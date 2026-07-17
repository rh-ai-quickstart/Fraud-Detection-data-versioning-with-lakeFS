from __future__ import annotations

from collections.abc import Callable

from clients import KubernetesClient, OpenShiftClient
from models.deploy_models import DeployModelPlan, DeployModelResult
from services.config_service import EnvironmentConfig


class DeployExecutionService:
    KSERVE_GROUP = "serving.kserve.io"
    KSERVE_VERSION = "v1beta1"
    KSERVE_PLURAL = "inferenceservices"
    SERVING_RUNTIME_VERSION = "v1alpha1"
    SERVING_RUNTIME_PLURAL = "servingruntimes"
    DEFAULT_SERVING_RUNTIME_IMAGE = (
        "registry.redhat.io/rhoai/odh-openvino-model-server-rhel9"
        "@sha256:1ab58519c50e2c3a9ebf0fee6d0708b1b5a0ae972aefcc722d87b2f62239a033"
    )

    def run(
        self,
        plan: DeployModelPlan,
        config: EnvironmentConfig,
        on_log: Callable[[str], None] | None = None,
    ) -> DeployModelResult:
        logs: list[str] = []

        def log(message: str) -> None:
            logs.append(message)
            if on_log:
                on_log(message)

        token_ok, token_or_message = OpenShiftClient.current_token()
        if not token_ok:
            raise ValueError(token_or_message)

        k8s = KubernetesClient.from_service_account(token_or_message)
        namespace = plan.namespace or k8s.namespace
        if not namespace:
            raise ValueError("Deploy namespace is empty. Set DEPLOY_NAMESPACE or run inside a Kubernetes pod.")

        self._ensure_serving_runtime(k8s, plan, namespace, log)

        storage_path = self._storage_path(plan)
        body = self._build_inference_service(plan, namespace, storage_path)
        log(f"Applying InferenceService `{plan.inference_service_name}` in `{namespace}`.")
        log(f"Runtime: `{plan.serving_runtime_name}` | storage `{storage_path}` via `{plan.storage_key}`.")

        ok, message, resource = k8s.apply_custom_resource(
            self.KSERVE_GROUP,
            self.KSERVE_VERSION,
            self.KSERVE_PLURAL,
            body,
            namespace=namespace,
        )
        if not ok or not resource:
            raise ValueError(message)
        log(message)

        ready, ready_message = KubernetesClient.inference_service_ready(resource)
        log(f"Ready status: {ready_message}")

        predictor_service = f"{plan.inference_service_name}-predictor"
        infer_url = (
            config.inference_url
            or f"http://{predictor_service}.{namespace}.svc.cluster.local/v2/models/{plan.inference_service_name}/infer"
        )

        return DeployModelResult(
            inference_service_name=plan.inference_service_name,
            namespace=namespace,
            storage_path=storage_path,
            predictor_service=predictor_service,
            infer_url=infer_url,
            ready=ready,
            status_message=ready_message,
            log_lines=tuple(logs),
        )

    def _ensure_serving_runtime(
        self,
        k8s: KubernetesClient,
        plan: DeployModelPlan,
        namespace: str,
        log: Callable[[str], None],
    ) -> None:
        runtime_name = plan.serving_runtime_name
        ok, message, existing = k8s.get_custom_resource(
            self.KSERVE_GROUP,
            self.SERVING_RUNTIME_VERSION,
            self.SERVING_RUNTIME_PLURAL,
            runtime_name,
            namespace=namespace,
        )
        if ok and existing:
            log(f"ServingRuntime `{runtime_name}` already exists in `{namespace}`.")
            return

        log(f"Creating ServingRuntime `{runtime_name}` for ONNX models in `{namespace}`.")
        body = self._build_serving_runtime(runtime_name, namespace)
        ok, message, _ = k8s.apply_custom_resource(
            self.KSERVE_GROUP,
            self.SERVING_RUNTIME_VERSION,
            self.SERVING_RUNTIME_PLURAL,
            body,
            namespace=namespace,
        )
        if not ok:
            raise ValueError(message)
        log(message)

    @staticmethod
    def _storage_path(plan: DeployModelPlan) -> str:
        relative = plan.model_relative_path.strip().strip("/")
        # OVMS expects /mnt/models/<version>/model.onnx, so point at the parent directory.
        if "/" in relative:
            model_dir = relative.rsplit("/", 2)[0]
        else:
            model_dir = relative
        return f"{plan.branch.strip()}/{model_dir}/"

    @staticmethod
    def _build_inference_service(plan: DeployModelPlan, namespace: str, storage_path: str) -> dict:
        return {
            "apiVersion": f"{DeployExecutionService.KSERVE_GROUP}/{DeployExecutionService.KSERVE_VERSION}",
            "kind": "InferenceService",
            "metadata": {
                "name": plan.inference_service_name,
                "namespace": namespace,
                "labels": {
                    "app.kubernetes.io/part-of": "fraud-detection-studio",
                },
                "annotations": {
                    "openshift.io/display-name": plan.inference_service_name,
                },
            },
            "spec": {
                "predictor": {
                    "serviceAccountName": plan.service_account_name,
                    "model": {
                        "runtime": plan.serving_runtime_name,
                        "modelFormat": {
                            "name": plan.model_format_name,
                            "version": "1",
                        },
                        "protocolVersion": "v2",
                        "storage": {
                            "key": plan.storage_key,
                            "path": storage_path,
                        },
                        "resources": {
                            "requests": {"cpu": "100m", "memory": "512Mi"},
                            "limits": {"cpu": "1", "memory": "1Gi"},
                        },
                    },
                },
            },
        }

    @classmethod
    def _build_serving_runtime(cls, runtime_name: str, namespace: str) -> dict:
        return {
            "apiVersion": f"{cls.KSERVE_GROUP}/{cls.SERVING_RUNTIME_VERSION}",
            "kind": "ServingRuntime",
            "metadata": {
                "name": runtime_name,
                "namespace": namespace,
                "labels": {
                    "opendatahub.io/dashboard": "true",
                    "app.kubernetes.io/part-of": "fraud-detection-studio",
                },
                "annotations": {
                    "opendatahub.io/runtime-version": "v2026.1.0",
                    "openshift.io/display-name": "OpenVINO Model Server",
                },
            },
            "spec": {
                "annotations": {
                    "opendatahub.io/kserve-runtime": "ovms",
                    "prometheus.io/path": "/metrics",
                    "prometheus.io/port": "8888",
                },
                "containers": [
                    {
                        "name": "kserve-container",
                        "image": cls.DEFAULT_SERVING_RUNTIME_IMAGE,
                        "args": [
                            "--model_name={{.Name}}",
                            "--port=8001",
                            "--rest_port=8888",
                            "--model_path=/mnt/models",
                            "--file_system_poll_wait_seconds=0",
                            "--metrics_enable",
                        ],
                        "ports": [{"containerPort": 8888, "protocol": "TCP"}],
                    }
                ],
                "multiModel": False,
                "protocolVersions": ["v2", "grpc-v2"],
                "supportedModelFormats": [
                    {"autoSelect": True, "name": "openvino_ir", "version": "opset13"},
                    {"name": "onnx", "version": "1"},
                    {"autoSelect": True, "name": "tensorflow", "version": "1"},
                    {"autoSelect": True, "name": "tensorflow", "version": "2"},
                    {"autoSelect": True, "name": "paddle", "version": "2"},
                    {"autoSelect": True, "name": "pytorch", "version": "2"},
                ],
            },
        }
