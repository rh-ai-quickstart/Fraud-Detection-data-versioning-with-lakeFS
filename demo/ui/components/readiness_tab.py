from __future__ import annotations

from dataclasses import replace

import streamlit as st

from models import WorkflowStage
from services import EnvironmentConfigService, ReadinessService, WorkflowProgressService


class ReadinessTabComponent:
    def __init__(self, stage: WorkflowStage) -> None:
        self._stage = stage
        self._readiness_service = ReadinessService()

    def render(self) -> None:
        left, right = st.columns([2, 1])
        with left:
            st.markdown(f"### {self._stage.objective}")
        with right:
            st.metric("Stage Status", self._stage.status)

        self._render_form()


    def _render_form(self) -> None:
        st.markdown("#### Environment Readiness")
        env = EnvironmentConfigService.from_os_env()
        with st.form("readiness_form_impl"):
            c1, c2 = st.columns(2)
            with c1:
                lakefs_endpoint = st.text_input("LAKECTL_SERVER_ENDPOINT_URL", value=env.lakefs_endpoint or "http://lakefs:8000")
                lakefs_access_key = st.text_input("LAKECTL_CREDENTIALS_ACCESS_KEY_ID", value=env.lakefs_access_key)
                lakefs_secret_key = st.text_input("LAKECTL_CREDENTIALS_SECRET_ACCESS_KEY", value=env.lakefs_secret_key, type="password")
            with c2:
                aws_s3_endpoint = st.text_input("AWS_S3_ENDPOINT", value=env.aws_s3_endpoint or "http://minio:9000")
                aws_access_key = st.text_input("AWS_ACCESS_KEY_ID", value=env.aws_access_key)
                aws_secret_key = st.text_input("AWS_SECRET_ACCESS_KEY", value=env.aws_secret_key, type="password")
                lakefs_repo_name = st.text_input("LAKEFS_REPO_NAME", value=env.lakefs_repo_name)
                lakefs_region = st.text_input("LAKEFS_DEFAULT_REGION", value=env.lakefs_region)
            submitted = st.form_submit_button("Run Checks", use_container_width=True)

        if not submitted:
            return

        runtime_config = replace(
            env,
            lakefs_endpoint=lakefs_endpoint,
            lakefs_access_key=lakefs_access_key,
            lakefs_secret_key=lakefs_secret_key,
            aws_s3_endpoint=aws_s3_endpoint,
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            lakefs_repo_name=lakefs_repo_name,
            lakefs_region=lakefs_region,
        )
        checks, repositories = self._readiness_service.run_checks(runtime_config)
        passed = sum(1 for check in checks if check.passed)
        if passed == len(checks):
            WorkflowProgressService.mark_complete("readiness")
        st.success(f"Passed {passed}/{len(checks)} checks")
        for check in checks:
            icon = "✅" if check.passed else "❌"
            st.write(f"{icon} **{check.name}** - {check.detail}")

        if repositories:
            st.markdown("**Repositories discovered:**")
            st.write(", ".join(repositories))

