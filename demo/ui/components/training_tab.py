from __future__ import annotations

import streamlit as st

from models import WorkflowStage
from services import EnvironmentConfigService, LakeFSRepositoryService, TrainingService, WorkflowProgressService


class TrainingTabComponent:
    def __init__(self, stage: WorkflowStage) -> None:
        self._stage = stage
        self._training_service = TrainingService()

    def render(self) -> None:
        env = EnvironmentConfigService.from_os_env()
        if st.session_state.get("training_last_error"):
            st.error(st.session_state["training_last_error"])

        left, right = st.columns([2, 1])
        with left:
            st.markdown(f"### {self._stage.objective}")
            st.caption(
                "Download data.csv, upload to a branch specified (train01), train, export ONNX model to models/fraud-detection.onnx, and evaluate."
            )
        with right:
            st.metric("Stage Status", self._stage.status)

        repos_ok, repos_detail, repositories = LakeFSRepositoryService.list_repository_names(env)
        if repos_ok and repositories:
            st.caption(f"lakeFS repositories available: {', '.join(repositories)}")
        elif not repos_ok:
            st.warning(f"Could not list lakeFS repositories: {repos_detail}")

        st.markdown("#### Training Run Configuration")
        st.caption(
            "Download data, upload to a branch, train, export ONNX, and evaluate."
        )
        default_repo = env.lakefs_repo_name or "my-storage"
        repo_options = repositories or [default_repo]
        if default_repo not in repo_options:
            repo_options = [default_repo, *repo_options]

        with st.form("training_form_impl"):
            repository = st.selectbox("Repository", options=repo_options, index=repo_options.index(default_repo))
            training_branch = st.text_input("Training Branch", value="train01")
            epochs = st.number_input("Epochs", min_value=1, max_value=200, value=2, step=1)
            submitted = st.form_submit_button("Start Training", use_container_width=True, type="primary")

        if not submitted:
            return

        st.session_state.pop("training_last_error", None)
        plan = self._training_service.build_plan(
            repository=repository,
            main_branch="main",
            training_branch=training_branch,
            epochs=epochs,
            threshold=0.95,
            train_path="data/train.csv",
            class_weighting=True,
            validate_path="data/validate.csv",
            test_path="data/test.csv",
        )

        log_lines: list[str] = []
        with st.status("Training fraud detection model...", expanded=True) as status:
            try:
                result = self._training_service.run_training(
                    plan=plan,
                    config=env,
                    on_log=lambda message: log_lines.append(message),
                )
            except Exception as exc:
                error_message = str(exc)
                st.session_state["training_last_error"] = error_message
                status.update(label="Training failed", state="error")
                st.error(error_message)
                if log_lines:
                    st.markdown("**Training log before failure**")
                    st.code("\n".join(log_lines))
                st.stop()

            status.update(label="Training complete", state="complete")

        st.session_state.pop("training_last_error", None)
        WorkflowProgressService.mark_complete(
            "train",
            {
                "repository": result.repository,
                "training_branch": result.training_branch,
                "model_path": result.model_path,
            },
        )
        st.success("Model trained and evaluated successfully.")
        st.markdown("#### Training Results")
        st.info(
            f"Datasets: `{result.train_s3_uri}`, `{result.validate_s3_uri}`, `{result.test_s3_uri}`"
        )
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Accuracy", f"{result.accuracy:.2f}%")
        mc2.metric("Precision", f"{result.precision:.4f}")
        mc3.metric("Recall", f"{result.recall:.4f}")
        mc4.metric("Epochs", str(result.epochs))
        st.caption(
            f"Branch `{result.training_branch}` in `{result.repository}` | "
            f"Training time: {result.training_seconds:.1f}s | "
            f"Model: `{result.model_path}`"
        )
        if log_lines:
            with st.expander("Training log", expanded=False):
                st.code("\n".join(log_lines))
