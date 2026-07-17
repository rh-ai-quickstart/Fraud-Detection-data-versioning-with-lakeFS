from __future__ import annotations

import streamlit as st

from models import WorkflowStage
from services import (
    DeployService,
    EnvironmentConfigService,
    LakeFSRepositoryService,
    WorkflowProgressService,
)


class DeployTabComponent:
    DEFAULT_MODEL_PATH = DeployService.DEFAULT_MODEL_PATH
    DEFAULT_REPOSITORY_NAME = "my-storage"
    DEFAULT_SERVICE_ACCOUNT_NAME = "lakefs-sa"
    DEFAULT_NAMESPACE = "fraud-detection"
    DEFAULT_INFERENCE_MODEL_NAME = "fraud-detection"
    DEFAULT_DATA_CONNECTION_KEY = "my-storage"  
    DEFAULT_MODEL_FORMAT_NAME = "onnx"
    DEFAULT_SERVING_RUNTIME_NAME = "kserve-ovms"

    def __init__(self, stage: WorkflowStage) -> None:
        self._stage = stage
        self._deploy_service = DeployService()

    def render(self) -> None:
        env = EnvironmentConfigService.from_os_env()
        if st.session_state.get("deploy_last_error"):
            st.error(st.session_state["deploy_last_error"])

        left, right = st.columns([2, 1])
        with left:
            st.markdown(f"### {self._stage.objective}")
            st.caption("Creates or updates a KServe InferenceService backed by the lakeFS model path.")
        with right:
            status = "Complete" if WorkflowProgressService.is_complete("deploy") else self._stage.status
            st.metric("Stage Status", status)

        st.markdown("#### Model Serving Deployment")
        st.caption(
            "Deploys an InferenceService that serves the ONNX model from the registered lakeFS storage path."
        )

        repos_ok, repos_detail, repositories = LakeFSRepositoryService.list_repository_names(env)
        if repos_ok and repositories:
            st.caption(f"lakeFS repositories available: {', '.join(repositories)}")
        elif not repos_ok:
            st.warning(f"Could not list lakeFS repositories: {repos_detail}")

        default_repo = env.lakefs_repo_name or "my-storage"
        repo_options = repositories or [default_repo]
        if default_repo not in repo_options:
            repo_options = [default_repo, *repo_options]

        default_namespace = env.deploy_namespace or self.DEFAULT_NAMESPACE

        default_service_account = env.inference_service_account or self.DEFAULT_SERVICE_ACCOUNT_NAME

        with st.form("deploy_model_form"):
            branch = st.text_input("Branch", value="train01")
            submitted = st.form_submit_button("Deploy Model", use_container_width=True, type="primary")

        if not submitted:
            return

        st.session_state.pop("deploy_last_error", None)
        plan = self._deploy_service.build_plan(
            inference_service_name=env.inference_model_name or self.DEFAULT_INFERENCE_MODEL_NAME,
            namespace=default_namespace,
            repository=self.DEFAULT_REPOSITORY_NAME,
            branch=branch,
            model_relative_path=self.DEFAULT_MODEL_PATH,
            storage_key=env.data_connection_key or self.DEFAULT_DATA_CONNECTION_KEY,
            service_account_name=default_service_account,
            model_format_name=self.DEFAULT_MODEL_FORMAT_NAME,
            serving_runtime_name=self.DEFAULT_SERVING_RUNTIME_NAME,
        )

        log_lines: list[str] = []
        with st.status("Deploying InferenceService...", expanded=True) as status:
            try:
                result = self._deploy_service.deploy_model(
                    plan=plan,
                    config=env,
                    on_log=lambda message: log_lines.append(message),
                )
            except Exception as exc:
                error_message = str(exc)
                st.session_state["deploy_last_error"] = error_message
                status.update(label="Deployment failed", state="error")
                st.error(error_message)
                if log_lines:
                    st.code("\n".join(log_lines))
                st.stop()

            status.update(label="Deployment submitted", state="complete")

        WorkflowProgressService.mark_complete(
            "deploy",
            {
                "inference_service_name": result.inference_service_name,
                "infer_url": result.infer_url,
                "ready": result.ready,
            },
        )
        if result.ready:
            st.success(f"InferenceService `{result.inference_service_name}` is Ready.")
        else:
            st.warning(
                f"InferenceService `{result.inference_service_name}` was applied but is not Ready yet: "
                f"{result.status_message}"
            )

        st.markdown("#### Deployment Result")
        st.write(f"Predictor service: `{result.predictor_service}`")
        st.write(f"Storage path: `{result.storage_path}`")
        st.write(f"Inference URL: `{result.infer_url}`")
        if log_lines:
            with st.expander("Deployment log", expanded=False):
                st.code("\n".join(log_lines))
