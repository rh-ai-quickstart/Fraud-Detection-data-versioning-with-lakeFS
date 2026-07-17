from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from clients.codeflare_client import CodeFlareClient
from clients.kubernetes_client import KubernetesClient
from clients.openshift_client import OpenShiftClient
from models.distributed_models import DistributedJobStatus, DistributedTrainingPlan, DistributedTrainingResult
from services.config_service import EnvironmentConfig
from services.distributed_execution_service import DistributedTrainingExecutionService


class DistributedTrainingService:
    DEFAULT_CLUSTER_NAME = "raycluster-cpu"
    DEFAULT_NAMESPACE = "fraud-detection"
    DEFAULT_NUM_WORKERS = 2
    DEFAULT_WORKER_CPU_REQUESTS = 1
    DEFAULT_WORKER_CPU_LIMITS = 4
    DEFAULT_WORKER_MEMORY_LIMITS_GI = 4
    DEFAULT_IMAGE = "quay.io/modh/ray:2.35.0-py39-cu121"
    DEFAULT_SCRIPT_NAME = "train_tf_cpu_lakefs.py"

    def __init__(self, execution_service: DistributedTrainingExecutionService | None = None) -> None:
        self._execution_service = execution_service or DistributedTrainingExecutionService()

    @classmethod
    def scripts_dir(cls) -> Path:
        candidate = Path(__file__).resolve().parents[2] / "scripts"
        if candidate.is_dir():
            return candidate
        container_candidate = Path("/app/scripts")
        if container_candidate.is_dir():
            return container_candidate
        raise ValueError(
            f"Training scripts directory was not found. Expected `{candidate}` or `{container_candidate}`."
        )

    @staticmethod
    def build_plan(
        cluster_name: str,
        namespace: str,
        training_branch: str,
        num_workers: int,
        worker_cpu_requests: int,
        worker_cpu_limits: int,
        worker_memory_limits_gi: int,
        image: str,
        script_name: str,
        scripts_dir: str | None = None,
        cluster_ready_timeout_seconds: int = 600,
    ) -> DistributedTrainingPlan:
        resolved_scripts_dir = scripts_dir or str(DistributedTrainingService.scripts_dir())
        return DistributedTrainingPlan(
            cluster_name=cluster_name.strip(),
            namespace=namespace.strip(),
            training_branch=training_branch.strip(),
            num_workers=num_workers,
            worker_cpu_requests=worker_cpu_requests,
            worker_cpu_limits=worker_cpu_limits,
            worker_memory_limits_gi=worker_memory_limits_gi,
            image=image.strip(),
            script_name=script_name.strip(),
            scripts_dir=resolved_scripts_dir,
            cluster_ready_timeout_seconds=cluster_ready_timeout_seconds,
        )

    @staticmethod
    def cluster_preview(plan: DistributedTrainingPlan) -> str:
        return (
            "Cluster(ClusterConfiguration("
            f"name='{plan.cluster_name}', "
            "head_extended_resource_requests={'nvidia.com/gpu': 0}, "
            "worker_extended_resource_requests={'nvidia.com/gpu': 0}, "
            f"num_workers={plan.num_workers}, "
            f"worker_cpu_requests={plan.worker_cpu_requests}, "
            f"worker_cpu_limits={plan.worker_cpu_limits}, "
            "worker_memory_requests=2, "
            f"worker_memory_limits={plan.worker_memory_limits_gi}, "
            f"image='{plan.image}'"
            "))"
        )

    @staticmethod
    def build_lakefs_s3_env(config: EnvironmentConfig) -> dict[str, str]:
        """Credentials and endpoint for lakeFS S3 gateway access inside Ray workers."""
        return {
            "AWS_ACCESS_KEY_ID": config.lakefs_access_key,
            "AWS_SECRET_ACCESS_KEY": config.lakefs_secret_key,
            "AWS_S3_ENDPOINT": config.lakefs_endpoint,
            "AWS_DEFAULT_REGION": config.lakefs_region,
            "AWS_S3_BUCKET": config.lakefs_repo_name,
        }

    @staticmethod
    def build_runtime_env(plan: DistributedTrainingPlan, config: EnvironmentConfig) -> dict[str, object]:
        branch = plan.training_branch
        lakefs_env = DistributedTrainingService.build_lakefs_s3_env(config)
        return {
            "working_dir": plan.scripts_dir,
            "excludes": [],
            "pip": str(Path(plan.scripts_dir) / "requirements.txt"),
            "env_vars": {
                **lakefs_env,
                "PIPELINE_ARTIFACTS_ENDPOINT_URL": config.pipeline_artifacts_endpoint_url,
                "PIPELINE_ARTIFACTS_ACCESS_KEY_ID": config.pipeline_artifacts_access_key_id,
                "PIPELINE_ARTIFACTS_SECRET_ACCESS_KEY": config.pipeline_artifacts_secret_access_key,
                "PIPELINE_ARTIFACTS_S3_BUCKET": config.pipeline_artifacts_s3_bucket,
                "NUM_WORKERS": str(plan.num_workers),
                "TRAIN_DATA": f"{branch}/data/train.csv",
                "VALIDATE_DATA": f"{branch}/data/validate.csv",
                "MODEL_OUTPUT": f"{branch}/models/fraud/1/",
            },
        }

    @staticmethod
    def runtime_env_preview(plan: DistributedTrainingPlan, config: EnvironmentConfig) -> dict[str, object]:
        return DistributedTrainingService.build_runtime_env(plan, config)

    def submit_job(
        self,
        plan: DistributedTrainingPlan,
        config: EnvironmentConfig,
        on_log: Callable[[str], None] | None = None,
    ) -> DistributedTrainingResult:
        if not Path(plan.scripts_dir).is_dir():
            raise ValueError(f"Scripts directory `{plan.scripts_dir}` does not exist.")
        script_path = Path(plan.scripts_dir) / plan.script_name
        if not script_path.is_file():
            raise ValueError(f"Training script `{script_path}` was not found.")

        missing = [
            name
            for name, value in (
                ("LAKECTL_SERVER_ENDPOINT_URL", config.lakefs_endpoint),
                ("LAKECTL_CREDENTIALS_ACCESS_KEY_ID", config.lakefs_access_key),
                ("LAKECTL_CREDENTIALS_SECRET_ACCESS_KEY", config.lakefs_secret_key),
                ("LAKEFS_REPO_NAME", config.lakefs_repo_name),
                ("PIPELINE_ARTIFACTS_ENDPOINT_URL", config.pipeline_artifacts_endpoint_url),
                ("PIPELINE_ARTIFACTS_S3_BUCKET", config.pipeline_artifacts_s3_bucket),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                f"Missing environment configuration for distributed training: {', '.join(missing)}."
            )

        platform_ok, platform_message = self.check_platform(plan.namespace)
        if not platform_ok:
            raise ValueError(platform_message)

        runtime_env = self.build_runtime_env(plan, config)
        return self._execution_service.run(plan, runtime_env, on_log=on_log)

    def refresh_job_status(
        self,
        plan: DistributedTrainingPlan,
        submission_id: str,
    ) -> tuple[str, tuple[str, ...]]:
        return self._execution_service.get_job_status(plan, submission_id)

    def poll_job(
        self,
        plan: DistributedTrainingPlan,
        submission_id: str,
        interval_seconds: int = DistributedTrainingExecutionService.DEFAULT_POLL_INTERVAL_SECONDS,
        on_update: Callable[[DistributedJobStatus], None] | None = None,
    ) -> DistributedJobStatus:
        return self._execution_service.poll_job(
            plan=plan,
            submission_id=submission_id,
            interval_seconds=interval_seconds,
            on_update=on_update,
        )

    @staticmethod
    def is_terminal_job_status(status: str) -> bool:
        normalized = DistributedTrainingExecutionService._normalize_job_status(status)
        return normalized in DistributedTrainingExecutionService.TERMINAL_JOB_STATUSES

    def check_platform(self, namespace: str) -> tuple[bool, str]:
        token_ok, token_or_message = OpenShiftClient.current_token()
        if not token_ok:
            return False, token_or_message

        auth_ok, auth_message = CodeFlareClient.configure_authentication()
        if not auth_ok:
            return False, auth_message

        k8s = KubernetesClient.from_service_account(token_or_message)
        ray_ok, ray_detail = k8s.api_group_available("ray.io", "v1")
        if not ray_ok:
            return False, (
                "RayCluster API is not available. Enable OpenShift AI distributed workloads "
                "(codeflare, ray, kueue) by upgrading the admin chart, then wait for the "
                "kuberay-operator pods to become Ready. "
                f"Details: {ray_detail}"
            )

        kueue_ok, kueue_detail = k8s.api_group_available("kueue.x-k8s.io", "v1beta1")
        target_namespace = namespace.strip() or k8s.namespace
        if not kueue_ok:
            return True, (
                f"{auth_message} Ray API is available for namespace `{target_namespace}`. "
                f"Kueue is not registered ({kueue_detail}); queue admission may be unavailable."
            )

        return True, (
            f"{auth_message} Ray and Kueue APIs are available for namespace `{target_namespace}`."
        )
