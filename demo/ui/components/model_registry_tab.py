from __future__ import annotations

import streamlit as st

from models import WorkflowStage
from services import EnvironmentConfigService, LakeFSRepositoryService, ModelRegistryService, WorkflowProgressService


class ModelRegistryTabComponent:
    DEFAULT_MODEL_DIR = "/app/models"
    DEFAULT_S3_PREFIX = "models"
    DEFAULT_COMMIT_MESSAGE = "Uploaded model artifacts"
    
    def __init__(self, stage: WorkflowStage) -> None:
        self._stage = stage
        self._model_registry_service = ModelRegistryService()

    def render(self) -> None:
        env = EnvironmentConfigService.from_os_env()
        if st.session_state.get("save_model_last_error"):
            st.error(st.session_state["save_model_last_error"])

        left, right = st.columns([2, 1])
        with left:
            st.markdown(f"### {self._stage.objective}")
            st.caption(
                "Uploads the trained `models/` directory to the branch namespace and commits the change."
            )
        with right:
            st.metric("Stage Status", self._stage.status)

        repos_ok, repos_detail, repositories = LakeFSRepositoryService.list_repository_names(env)
        if repos_ok and repositories:
            st.caption(f"lakeFS repositories available: {', '.join(repositories)}")
        elif not repos_ok:
            st.warning(f"Could not list lakeFS repositories: {repos_detail}")

        default_repo = env.lakefs_repo_name or "my-storage"
        repo_options = repositories or [default_repo]


        with st.form("model_registry_form_impl"):
            repository = st.selectbox("Repository", options=repo_options, index=repo_options.index(default_repo))
            branch = st.text_input("Branch", value="train01")
            submitted = st.form_submit_button("Upload and Commit Model", use_container_width=True, type="primary")

        if not submitted:
            return

        st.session_state.pop("save_model_last_error", None)
        plan = self._model_registry_service.build_plan(
            local_model_dir=self.DEFAULT_MODEL_DIR,
            repository=repository,
            branch=branch,
            commit_message=self.DEFAULT_COMMIT_MESSAGE,
            s3_prefix=self.DEFAULT_S3_PREFIX,
        )

        log_lines: list[str] = []
        with st.status("Uploading model artifacts to lakeFS...", expanded=True) as status:
            try:
                result = self._model_registry_service.save_model(
                    plan=plan,
                    config=env,
                    on_log=lambda message: log_lines.append(message),
                )
            except Exception as exc:
                error_message = str(exc)
                st.session_state["save_model_last_error"] = error_message
                status.update(label="Save model failed", state="error")
                st.error(error_message)
                if log_lines:
                    st.markdown("**Save model log before failure**")
                    st.code("\n".join(log_lines))
                st.stop()

            status.update(label="Model saved and committed", state="complete")

        st.session_state.pop("save_model_last_error", None)
        WorkflowProgressService.mark_complete(
            "save",
            {
                "repository": result.repository,
                "branch": result.branch,
                "commit_id": result.commit_id,
            },
        )
        st.success(f"Uploaded {result.files_uploaded} file(s) and committed branch `{result.branch}`.")
        st.markdown("#### lakeFS Objects")
        st.write("**Before upload**")
        st.code("\n".join(result.objects_before) or "(none)", language="text")
        st.write("**After upload**")
        st.code("\n".join(result.objects_after), language="text")
        st.caption(f"Commit: `{result.commit_id}` | Message: `{result.commit_message}`")
        if log_lines:
            with st.expander("Save model log", expanded=False):
                st.code("\n".join(log_lines))
