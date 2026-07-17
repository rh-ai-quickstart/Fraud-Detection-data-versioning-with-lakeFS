from __future__ import annotations

import streamlit as st

from models import WorkflowStage
from services import DistributedTrainingService, EnvironmentConfigService, WorkflowProgressService


class DistributedTabComponent:
    def __init__(self, stage: WorkflowStage) -> None:
        self._stage = stage
        self._distributed_service = DistributedTrainingService()

    def render(self) -> None:
        env = EnvironmentConfigService.from_os_env()
        if st.session_state.get("distributed_last_error"):
            st.error(st.session_state["distributed_last_error"])

        left, right = st.columns([2, 1])
        with left:
            st.markdown(f"### {self._stage.objective}")
            st.caption(
                "Create or connect to a Ray cluster with CodeFlare, preview the runtime environment, "
                "and submit distributed training to lakeFS."
            )
        with right:
            status = "Complete" if WorkflowProgressService.is_complete("distributed") else self._stage.status
            st.metric("Stage Status", status)

        namespace = env.deploy_namespace or DistributedTrainingService.DEFAULT_NAMESPACE
        platform_ok, platform_message = self._distributed_service.check_platform(namespace)
        if platform_ok:
            st.success(platform_message)
        else:
            st.warning(platform_message)
            st.markdown(
                "Enable distributed workloads with:\n"
                "```bash\n"
                "cd deploy\n"
                "make deploy-admin\n"
                "oc get pods -n redhat-ods-applications | egrep 'kuberay|codeflare|kueue'\n"
                "make deploy\n"
                "```"
            )

        st.markdown("#### CodeFlare + Ray Job Planner")
        with st.form("distributed_form_impl"):
            cluster_name = st.text_input("Cluster name", value=DistributedTrainingService.DEFAULT_CLUSTER_NAME)
            namespace = st.text_input("OpenShift namespace", value=namespace)
            training_branch = st.text_input("Training branch", value="train01")
            num_workers = st.number_input(
                "Worker count",
                min_value=1,
                max_value=16,
                value=DistributedTrainingService.DEFAULT_NUM_WORKERS,
                step=1,
            )

            action_col1, action_col2 = st.columns(2)
            with action_col1:
                preview_submitted = st.form_submit_button("Preview Job Spec", use_container_width=True)
            with action_col2:
                submit_submitted = st.form_submit_button(
                    "Submit Distributed Job",
                    use_container_width=True,
                    type="primary",
                )

        if not preview_submitted and not submit_submitted:
            self._render_active_job(env, namespace)
            return

        st.session_state.pop("distributed_last_error", None)
        plan = self._distributed_service.build_plan(
            cluster_name=cluster_name,
            namespace=namespace,
            training_branch=training_branch,
            num_workers=int(num_workers),
            worker_cpu_requests=DistributedTrainingService.DEFAULT_WORKER_CPU_REQUESTS,
            worker_cpu_limits=DistributedTrainingService.DEFAULT_WORKER_CPU_LIMITS,
            worker_memory_limits_gi=DistributedTrainingService.DEFAULT_WORKER_MEMORY_LIMITS_GI,
            image=DistributedTrainingService.DEFAULT_IMAGE,
            script_name=DistributedTrainingService.DEFAULT_SCRIPT_NAME,
        )

        cluster_preview = self._distributed_service.cluster_preview(plan)
        runtime_env = self._distributed_service.runtime_env_preview(plan, env)

        with st.expander("Job spec preview", expanded=preview_submitted and not submit_submitted):
            st.caption(f"Target namespace: `{namespace}` | scripts: `{plan.scripts_dir}`")
            st.code(cluster_preview, language="python")
            st.code(str(runtime_env), language="python")
            st.info(
                f"Submit plan: `client.submit_job(entrypoint='python {plan.script_name}', runtime_env=runtime_env)`"
            )

        if preview_submitted and not submit_submitted:
            st.success("Distributed training spec generated.")
            return

        log_lines: list[str] = []
        with st.status("Submitting distributed training job...", expanded=True) as status:
            try:
                result = self._distributed_service.submit_job(
                    plan=plan,
                    config=env,
                    on_log=lambda message: log_lines.append(message),
                )
            except Exception as exc:
                error_message = str(exc)
                st.session_state["distributed_last_error"] = error_message
                status.update(label="Job submission failed", state="error")
                st.error(error_message)
                if log_lines:
                    st.markdown("**Submission log before failure**")
                    st.code("\n".join(log_lines))
                st.stop()

            status.update(label="Job submitted", state="complete")

        final_status = self._poll_job_progress(plan, result.submission_id, log_lines)

        st.session_state.pop("distributed_last_error", None)
        WorkflowProgressService.mark_complete(
            "distributed",
            {
                "submission_id": result.submission_id,
                "cluster_name": result.cluster_name,
                "namespace": result.namespace,
                "training_branch": plan.training_branch,
                "job_status": final_status.status,
                "dashboard_url": result.dashboard_url,
            },
        )
        st.session_state["distributed_job_status"] = final_status.status
        st.session_state["distributed_job_log_tail"] = final_status.log_tail

        st.markdown("#### Submission Result")
        st.write(f"Cluster: `{result.cluster_name}` in `{result.namespace}`")
        st.write(f"Entrypoint: `{result.entrypoint}`")
        st.write(f"Submission id: `{result.submission_id}`")
        if result.dashboard_url:
            st.caption(f"Ray dashboard (in-cluster): `{result.dashboard_url}`")

        if final_status.status == "SUCCEEDED":
            st.success("Distributed training job succeeded.")
        elif final_status.status == "FAILED":
            st.error("Distributed training job failed.")
        elif final_status.status == "STOPPED":
            st.warning("Distributed training job was stopped.")
        else:
            st.info(f"Latest job status: `{final_status.status}`")

        if log_lines:
            with st.expander("Submission log", expanded=False):
                st.code("\n".join(log_lines))
        if final_status.log_tail:
            with st.expander("Recent job logs", expanded=final_status.status != "SUCCEEDED"):
                st.code("\n".join(final_status.log_tail))

    def _poll_job_progress(self, plan, submission_id: str, log_lines: list[str]):
        log_view = st.empty()
        with st.status("Monitoring distributed training job (polling every 5s)...", expanded=True) as monitor_status:
            try:
                def on_poll(snapshot) -> None:
                    monitor_status.update(label=f"Ray job status: {snapshot.status}")
                    log_lines.append(f"Polled status: {snapshot.status}")
                    if snapshot.log_tail:
                        log_view.code("\n".join(snapshot.log_tail))

                final_status = self._distributed_service.poll_job(
                    plan=plan,
                    submission_id=submission_id,
                    on_update=on_poll,
                )
            except Exception as exc:
                monitor_status.update(label="Job monitoring failed", state="error")
                st.error(str(exc))
                st.stop()

            if final_status.status == "SUCCEEDED":
                monitor_status.update(label="Distributed training succeeded", state="complete")
            elif final_status.status in {"FAILED", "STOPPED"}:
                monitor_status.update(label=f"Distributed training {final_status.status.lower()}", state="error")
            else:
                monitor_status.update(label=f"Monitoring ended with status: {final_status.status}", state="complete")

        return final_status

    def _build_plan_from_metadata(self, metadata: dict, namespace: str):
        return self._distributed_service.build_plan(
            cluster_name=metadata.get("cluster_name", DistributedTrainingService.DEFAULT_CLUSTER_NAME),
            namespace=metadata.get("namespace", namespace),
            training_branch=metadata.get("training_branch", "train01"),
            num_workers=DistributedTrainingService.DEFAULT_NUM_WORKERS,
            worker_cpu_requests=DistributedTrainingService.DEFAULT_WORKER_CPU_REQUESTS,
            worker_cpu_limits=DistributedTrainingService.DEFAULT_WORKER_CPU_LIMITS,
            worker_memory_limits_gi=DistributedTrainingService.DEFAULT_WORKER_MEMORY_LIMITS_GI,
            image=DistributedTrainingService.DEFAULT_IMAGE,
            script_name=DistributedTrainingService.DEFAULT_SCRIPT_NAME,
        )

    def _render_active_job(self, env, namespace: str) -> None:
        metadata = WorkflowProgressService.metadata("distributed")
        submission_id = metadata.get("submission_id")
        if not submission_id:
            return

        st.markdown("#### Active Distributed Job")
        st.write(f"Submission id: `{submission_id}`")
        status = st.session_state.get("distributed_job_status", metadata.get("job_status", "UNKNOWN"))
        st.write(f"Latest status: `{status}`")

        plan = self._build_plan_from_metadata(metadata, namespace)
        action_col1, action_col2 = st.columns(2)
        with action_col1:
            refresh_clicked = st.button("Refresh job status", key="distributed_refresh_job")
        with action_col2:
            resume_clicked = (
                st.button("Resume monitoring", key="distributed_resume_monitoring")
                if not DistributedTrainingService.is_terminal_job_status(status)
                else False
            )

        if refresh_clicked:
            try:
                refreshed_status, log_tail = self._distributed_service.refresh_job_status(plan, submission_id)
                st.session_state["distributed_job_status"] = refreshed_status
                st.session_state["distributed_job_log_tail"] = log_tail
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        if resume_clicked:
            poll_logs: list[str] = []
            final_status = self._poll_job_progress(plan, submission_id, poll_logs)
            st.session_state["distributed_job_status"] = final_status.status
            st.session_state["distributed_job_log_tail"] = final_status.log_tail
            WorkflowProgressService.mark_complete(
                "distributed",
                {**metadata, "job_status": final_status.status},
            )
            st.rerun()

        log_tail = st.session_state.get("distributed_job_log_tail", ())
        if log_tail:
            with st.expander("Recent job logs", expanded=True):
                st.code("\n".join(log_tail))
