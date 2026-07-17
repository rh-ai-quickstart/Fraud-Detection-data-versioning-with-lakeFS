from __future__ import annotations

import time
from collections.abc import Callable

from clients.codeflare_client import CodeFlareClient
from models.distributed_models import DistributedJobStatus, DistributedTrainingPlan, DistributedTrainingResult


class DistributedTrainingExecutionService:
    TERMINAL_JOB_STATUSES = frozenset({"SUCCEEDED", "FAILED", "STOPPED"})
    DEFAULT_POLL_INTERVAL_SECONDS = 5

    def run(
        self,
        plan: DistributedTrainingPlan,
        runtime_env: dict[str, object],
        on_log: Callable[[str], None] | None = None,
    ) -> DistributedTrainingResult:
        logs: list[str] = []

        def log(message: str) -> None:
            logs.append(message)
            if on_log:
                on_log(message)

        entrypoint = f"python {plan.script_name}"

        try:
            from codeflare_sdk import Cluster, ClusterConfiguration, get_cluster
        except ImportError as exc:
            raise ValueError(
                "codeflare-sdk is not installed. Add it to the UI image requirements to submit Ray jobs."
            ) from exc

        auth_ok, auth_message = CodeFlareClient.configure_authentication()
        if not auth_ok:
            raise ValueError(auth_message)
        log(auth_message)

        try:
            cluster = self._connect_or_create_cluster(plan, get_cluster, Cluster, ClusterConfiguration, log)
        except RuntimeError as exc:
            raise ValueError(self._format_cluster_error(exc, plan.namespace)) from exc
        if cluster is None:
            raise ValueError(
                f"Unable to connect to or create Ray cluster `{plan.cluster_name}` in `{plan.namespace}`."
            )

        log(f"Waiting for Ray cluster `{plan.cluster_name}` in `{plan.namespace}` to become ready...")
        cluster.wait_ready(timeout=plan.cluster_ready_timeout_seconds, dashboard_check=False)
        log("Ray cluster is ready.")

        job_client = self._job_submission_client(cluster, plan, log)
        log(f"Submitting job: `{entrypoint}`")
        submission_id = job_client.submit_job(entrypoint=entrypoint, runtime_env=runtime_env)
        log(f"Job submitted with id `{submission_id}`.")

        job_status = str(job_client.get_job_status(submission_id))
        log(f"Initial job status: {job_status}")

        return DistributedTrainingResult(
            submission_id=submission_id,
            cluster_name=plan.cluster_name,
            namespace=plan.namespace,
            job_status=job_status,
            entrypoint=entrypoint,
            dashboard_url=self._dashboard_url(plan),
            log_lines=tuple(logs),
        )

    @staticmethod
    def _connect_or_create_cluster(
        plan: DistributedTrainingPlan,
        get_cluster: Callable[..., object | None],
        cluster_cls: type,
        cluster_configuration_cls: type,
        log: Callable[[str], None],
    ) -> object | None:
        cluster = get_cluster(plan.cluster_name, namespace=plan.namespace)
        if cluster is not None:
            log(f"Connected to existing Ray cluster `{plan.cluster_name}` in `{plan.namespace}`.")
            return cluster

        log(
            f"Ray cluster `{plan.cluster_name}` was not found in `{plan.namespace}`. "
            "Creating a new cluster..."
        )
        cluster = cluster_cls(
            cluster_configuration_cls(
                name=plan.cluster_name,
                namespace=plan.namespace,
                head_extended_resource_requests={"nvidia.com/gpu": 0},
                worker_extended_resource_requests={"nvidia.com/gpu": 0},
                num_workers=plan.num_workers,
                worker_cpu_requests=plan.worker_cpu_requests,
                worker_cpu_limits=plan.worker_cpu_limits,
                worker_memory_requests=2,
                worker_memory_limits=plan.worker_memory_limits_gi,
                image=plan.image,
            )
        )
        cluster.apply(timeout=plan.cluster_ready_timeout_seconds)
        return cluster

    @staticmethod
    def _dashboard_url(plan: DistributedTrainingPlan) -> str:
        return (
            f"http://{plan.cluster_name}-head-svc.{plan.namespace}.svc.cluster.local:8265"
        )

    @classmethod
    def _job_submission_client(cls, cluster: object, plan: DistributedTrainingPlan, log: Callable[[str], None]) -> object:
        if not CodeFlareClient.in_cluster():
            log("Using CodeFlare dashboard route for job submission.")
            return cluster.job_client

        from ray.job_submission import JobSubmissionClient

        dashboard_url = cls._dashboard_url(plan)
        log(
            "No external Ray dashboard route detected; using in-cluster dashboard "
            f"at `{dashboard_url}`."
        )
        client = JobSubmissionClient(
            dashboard_url,
            headers=cluster._client_headers,
            verify=False,
        )
        cluster._job_submission_client = client
        return client

    def get_job_status(self, plan: DistributedTrainingPlan, submission_id: str) -> tuple[str, tuple[str, ...]]:
        from codeflare_sdk import get_cluster

        auth_ok, auth_message = CodeFlareClient.configure_authentication()
        if not auth_ok:
            raise ValueError(auth_message)

        cluster = get_cluster(plan.cluster_name, namespace=plan.namespace)
        if cluster is None:
            raise ValueError(f"Ray cluster `{plan.cluster_name}` was not found in `{plan.namespace}`.")

        job_client = self._job_submission_client(cluster, plan, lambda _message: None)
        status = str(job_client.get_job_status(submission_id))
        logs = job_client.get_job_logs(submission_id) or ""
        tail = logs.splitlines()[-40:]
        return status, tuple(tail)

    def poll_job(
        self,
        plan: DistributedTrainingPlan,
        submission_id: str,
        interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
        on_update: Callable[[DistributedJobStatus], None] | None = None,
    ) -> DistributedJobStatus:
        while True:
            status, log_tail = self.get_job_status(plan, submission_id)
            normalized_status = self._normalize_job_status(status)
            snapshot = DistributedJobStatus(
                submission_id=submission_id,
                status=normalized_status,
                log_tail=log_tail,
                is_terminal=normalized_status in self.TERMINAL_JOB_STATUSES,
            )
            if on_update:
                on_update(snapshot)
            if snapshot.is_terminal:
                return snapshot
            time.sleep(interval_seconds)

    @classmethod
    def _normalize_job_status(cls, status: str) -> str:
        normalized = status.strip().upper()
        if "." in normalized:
            normalized = normalized.rsplit(".", 1)[-1]
        return normalized

    @staticmethod
    def _format_cluster_error(exc: RuntimeError, namespace: str) -> str:
        message = str(exc)
        if "403" in message or "Forbidden" in message or "forbidden" in message:
            return (
                "The UI service account cannot access Ray resources in "
                f"`{namespace}`. Upgrade the Helm release to apply the Ray RBAC Role, "
                "then retry. Details: "
                f"{message}"
            )
        if "CustomResourceDefinition unavailable" in message or "404" in message:
            return (
                "The RayCluster API is not available in this OpenShift AI cluster. "
                "Run `make deploy-admin` to enable codeflare, ray, and kueue in the "
                "DataScienceCluster, wait for kuberay-operator pods to become Ready in "
                "`redhat-ods-applications`, then upgrade the fraud-detection release."
            )
        if "CERTIFICATE_VERIFY_FAILED" in message or "SSLError" in message:
            return (
                "Kubernetes TLS verification failed while connecting to the API server. "
                "The UI now skips in-cluster TLS verification by default; rebuild and "
                "redeploy the UI image, then retry. To force verification, set "
                "CF_SDK_SKIP_TLS=false in the UI deployment."
            )
        return message
