from __future__ import annotations

from dataclasses import replace

import streamlit as st

from clients import ModelRegistryApiClient, OpenShiftClient
from models import WorkflowStage
from services import (
    EnvironmentConfigService,
    LakeFSRepositoryService,
    RegisterService,
    WorkflowProgressService,
)


class RegisterTabComponent:
    DEFAULT_MODEL_PATH = RegisterService.DEFAULT_MODEL_PATH
    DEFAULT_REPOSITORY_NAME = "my-storage"
    DEFAULT_DATA_CONNECTION_KEY = "my-storage"
    DEFAULT_MODEL_FORMAT_NAME = "onnx"
    DEFAULT_MODEL_FORMAT_VERSION = "1"
    DEFAULT_AUTHOR = "fraud-detection-studio"
    DEFAULT_DESCRIPTION = "Fraud detection ONNX model versioned in lakeFS."

    def __init__(self, stage: WorkflowStage) -> None:
        self._stage = stage
        self._register_service = RegisterService()

    def render(self) -> None:
        env = EnvironmentConfigService.from_os_env()
        if st.session_state.get("register_last_error"):
            st.error(st.session_state["register_last_error"])

        left, right = st.columns([2, 1])
        with left:
            st.markdown(f"### {self._stage.objective}")
            st.caption("Registers the committed lakeFS ONNX artifact in OpenShift AI Model Registry.")
        with right:
            status = "Complete" if WorkflowProgressService.is_complete("register") else self._stage.status
            st.metric("Stage Status", status)

        repos_ok, repos_detail, repositories = LakeFSRepositoryService.list_repository_names(env)
        if repos_ok and repositories:
            st.caption(f"lakeFS repositories available: {', '.join(repositories)}")
        elif not repos_ok:
            st.warning(f"Could not list lakeFS repositories: {repos_detail}")

        default_repo = env.lakefs_repo_name or "my-storage"
        repo_options = repositories or [default_repo]
        if default_repo not in repo_options:
            repo_options = [default_repo, *repo_options]

        self._render_registry_connectivity(env.model_registry_url)

        with st.form("register_model_form"):
            model_name = st.text_input("Registered model name", value=env.inference_model_name or "fraud-detection")
            version_name = st.text_input("Version name", value="1.0.0")
            branch = st.text_input("Branch", value="train01")
            submitted = st.form_submit_button("Register Model", use_container_width=True, type="primary")

        if not submitted:
            return

        st.session_state.pop("register_last_error", None)
        config = replace(env, model_registry_url=env.model_registry_url.strip())

        plan = self._register_service.build_plan(
            model_name=model_name,
            version_name=version_name,
            description=self.DEFAULT_DESCRIPTION,
            repository=self.DEFAULT_REPOSITORY_NAME,
            branch=branch,
            model_relative_path=self.DEFAULT_MODEL_PATH,
            model_format_name=self.DEFAULT_MODEL_FORMAT_NAME,
            model_format_version=self.DEFAULT_MODEL_FORMAT_VERSION,
            storage_key=env.data_connection_key or self.DEFAULT_DATA_CONNECTION_KEY,
            author=self.DEFAULT_AUTHOR,
        )

        log_lines: list[str] = []
        with st.status("Registering model in OpenShift AI Model Registry...", expanded=True) as status:
            try:
                result = self._register_service.register_model(
                    plan=plan,
                    config=config,
                    on_log=lambda message: log_lines.append(message),
                )
            except Exception as exc:
                error_message = str(exc)
                st.session_state["register_last_error"] = error_message
                status.update(label="Registration failed", state="error")
                st.error(error_message)
                if log_lines:
                    st.code("\n".join(log_lines))
                st.stop()

            status.update(label="Model registered", state="complete")

        WorkflowProgressService.mark_complete(
            "register",
            {
                "model_name": result.model_name,
                "version_name": result.version_name,
                "storage_uri": result.storage_uri,
            },
        )
        st.success(f"Registered `{result.model_name}` version `{result.version_name}`.")
        st.markdown("#### Registration Result")
        st.write(f"Registered model id: `{result.registered_model_id}`")
        st.write(f"Model version id: `{result.model_version_id}`")
        st.write(f"Artifact id: `{result.artifact_id}`")
        st.write(f"Storage URI: `{result.storage_uri}`")
        if log_lines:
            with st.expander("Registration log", expanded=False):
                st.code("\n".join(log_lines))

    @staticmethod
    def _render_registry_connectivity(registry_url: str) -> None:
        if not registry_url:
            st.warning("MODEL_REGISTRY_URL is not configured.")
            return

        token_ok, token_or_message = OpenShiftClient.current_token()
        token = token_or_message if token_ok else ""
        client = ModelRegistryApiClient(base_url=registry_url, token=token)
        ok, message, _ = client.list_registered_models()
        if ok:
            st.caption(f"Model Registry reachable at `{registry_url}`.")
            return

        st.error(message)
        st.info(
            "Use the in-cluster service name created by the admin chart, for example "
            "`http://lakefs-model-registry.rhoai-model-registries.svc:8080`. "
            "Ensure `make deploy-admin` completed successfully."
        )
