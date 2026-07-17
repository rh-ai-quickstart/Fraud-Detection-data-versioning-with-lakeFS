from __future__ import annotations

import json

import streamlit as st

from models import WorkflowStage
from models.inference_models import EXAMPLE_SCENARIOS, InferenceResult, TransactionFeatures
from services import (
    EnvironmentConfigService,
    InferenceService,
    LakeFSRepositoryService,
    RegisterService,
    WorkflowProgressService,
    WorkflowReadinessService,
)


class InferenceTabComponent:
    DEFAULT_MODEL_PATH = RegisterService.DEFAULT_MODEL_PATH
    _FORM_INITIALIZED_KEY = "inference_form_initialized"
    _RESULT_KEY = "inference_last_result"
    _LOG_KEY = "inference_last_log_lines"
    _PREREQ_KEY = "inference_prerequisite_checks"

    def __init__(self, stage: WorkflowStage) -> None:
        self._stage = stage
        self._inference_service = InferenceService()
        self._workflow_readiness_service = WorkflowReadinessService()

    def render(self) -> None:
        env = EnvironmentConfigService.from_os_env()
        if st.session_state.get("inference_last_error"):
            st.error(st.session_state["inference_last_error"])

        left, right = st.columns([2, 1])
        with left:
            st.markdown(f"### {self._stage.objective}")
        with right:
            status = "Complete" if WorkflowProgressService.is_complete("inference") else self._stage.status
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

        default_infer_url = env.inference_url or (
            "http://fraud-detection-predictor.fraud-detection.svc.cluster.local"
            "/v2/models/fraud-detection/infer"
        )

        self._ensure_form_state(env, default_repo, default_infer_url)

        st.markdown("#### REST Inference")
        st.caption(
            "Loads the scaler from lakeFS, transforms transaction features, and calls the deployed "
            "KServe/OpenShift AI inference endpoint."
        )

        self._render_prerequisite_section(env)

        scenario_names = list(EXAMPLE_SCENARIOS.keys())
        if "inference_scenario" not in st.session_state:
            st.session_state["inference_scenario"] = scenario_names[0]

        st.selectbox(
            "Example scenario",
            scenario_names,
            key="inference_scenario",
            on_change=self._apply_selected_scenario,
        )
        scenario_description, _ = EXAMPLE_SCENARIOS[st.session_state["inference_scenario"]]
        st.caption(scenario_description)

        with st.form("inference_form_impl", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                infer_url = st.text_input("Inference URL", value=st.session_state["inference_infer_url"])
                model_name = st.text_input("Model name", value=st.session_state["inference_model_name"])
                repository = st.selectbox(
                    "Repository",
                    options=repo_options,
                    index=repo_options.index(st.session_state["inference_repository"])
                    if st.session_state["inference_repository"] in repo_options
                    else 0,
                )
                training_branch = st.text_input("Training branch", value=st.session_state["inference_training_branch"])
            with c2:
                distance = st.number_input(
                    "distance_from_last_transaction",
                    value=float(st.session_state["inference_distance"]),
                )
                ratio = st.number_input(
                    "ratio_to_median_purchase_price",
                    value=float(st.session_state["inference_ratio"]),
                )
                used_chip = st.selectbox(
                    "used_chip",
                    [0.0, 1.0],
                    index=int(st.session_state["inference_used_chip"]),
                )
                used_pin_number = st.selectbox(
                    "used_pin_number",
                    [0.0, 1.0],
                    index=int(st.session_state["inference_used_pin_number"]),
                )
                online_order = st.selectbox(
                    "online_order",
                    [0.0, 1.0],
                    index=int(st.session_state["inference_online_order"]),
                )

            threshold = st.slider(
                "Fraud threshold",
                0.50,
                0.99,
                float(st.session_state["inference_threshold"]),
                0.01,
            )
            submitted = st.form_submit_button("Run Inference", use_container_width=True, type="primary")

        if submitted:
            self._persist_form_state(
                infer_url=infer_url,
                model_name=model_name,
                repository=repository,
                training_branch=training_branch,
                distance=distance,
                ratio=ratio,
                used_chip=used_chip,
                used_pin_number=used_pin_number,
                online_order=online_order,
                threshold=threshold,
            )
            self._run_inference(
                env=env,
                infer_url=infer_url,
                model_name=model_name,
                repository=repository,
                training_branch=training_branch,
                distance=distance,
                ratio=ratio,
                used_chip=used_chip,
                used_pin_number=used_pin_number,
                online_order=online_order,
                threshold=threshold,
            )

        self._render_last_result()

    def _ensure_form_state(self, env, default_repo: str, default_infer_url: str) -> None:
        if st.session_state.get(self._FORM_INITIALIZED_KEY):
            return

        _, scenario_features = EXAMPLE_SCENARIOS[list(EXAMPLE_SCENARIOS.keys())[0]]
        st.session_state.update(
            {
                self._FORM_INITIALIZED_KEY: True,
                "inference_infer_url": default_infer_url,
                "inference_model_name": env.inference_model_name or "fraud-detection",
                "inference_repository": default_repo,
                "inference_training_branch": "train01",
                "inference_distance": float(scenario_features.distance_from_last_transaction),
                "inference_ratio": float(scenario_features.ratio_to_median_purchase_price),
                "inference_used_chip": int(scenario_features.used_chip),
                "inference_used_pin_number": int(scenario_features.used_pin_number),
                "inference_online_order": int(scenario_features.online_order),
                "inference_threshold": 0.95,
            }
        )

    @staticmethod
    def _apply_selected_scenario() -> None:
        _, features = EXAMPLE_SCENARIOS[st.session_state["inference_scenario"]]
        st.session_state["inference_distance"] = float(features.distance_from_last_transaction)
        st.session_state["inference_ratio"] = float(features.ratio_to_median_purchase_price)
        st.session_state["inference_used_chip"] = int(features.used_chip)
        st.session_state["inference_used_pin_number"] = int(features.used_pin_number)
        st.session_state["inference_online_order"] = int(features.online_order)

    @staticmethod
    def _persist_form_state(
        *,
        infer_url: str,
        model_name: str,
        repository: str,
        training_branch: str,
        distance: float,
        ratio: float,
        used_chip: float,
        used_pin_number: float,
        online_order: float,
        threshold: float,
    ) -> None:
        st.session_state.update(
            {
                "inference_infer_url": infer_url,
                "inference_model_name": model_name,
                "inference_repository": repository,
                "inference_training_branch": training_branch,
                "inference_distance": float(distance),
                "inference_ratio": float(ratio),
                "inference_used_chip": int(used_chip),
                "inference_used_pin_number": int(used_pin_number),
                "inference_online_order": int(online_order),
                "inference_threshold": float(threshold),
            }
        )

    def _render_prerequisite_section(self, env) -> None:
        refresh_col, _ = st.columns([1, 3])
        with refresh_col:
            refresh = st.button("Refresh prerequisite checks", key="inference_refresh_prereqs")

        if refresh or self._PREREQ_KEY not in st.session_state:
            st.session_state[self._PREREQ_KEY] = self._workflow_readiness_service.evaluate_inference_prerequisites(
                repository=st.session_state["inference_repository"],
                branch=st.session_state["inference_training_branch"],
                model_relative_path=self.DEFAULT_MODEL_PATH,
                infer_url=st.session_state["inference_infer_url"],
                config=env,
            )

        self._render_prerequisites(st.session_state[self._PREREQ_KEY])

    def _run_inference(
        self,
        *,
        env,
        infer_url: str,
        model_name: str,
        repository: str,
        training_branch: str,
        distance: float,
        ratio: float,
        used_chip: float,
        used_pin_number: float,
        online_order: float,
        threshold: float,
    ) -> None:
        prerequisite_checks = self._workflow_readiness_service.evaluate_inference_prerequisites(
            repository=repository,
            branch=training_branch,
            model_relative_path=self.DEFAULT_MODEL_PATH,
            infer_url=infer_url,
            config=env,
        )
        st.session_state[self._PREREQ_KEY] = prerequisite_checks

        if any(not check.passed for check in prerequisite_checks):
            st.session_state["inference_last_error"] = (
                "Inference blocked until train, save, register, deploy, and endpoint checks pass."
            )
            st.session_state.pop(self._RESULT_KEY, None)
            st.session_state.pop(self._LOG_KEY, None)
            return

        st.session_state.pop("inference_last_error", None)
        features = TransactionFeatures(
            distance_from_last_transaction=distance,
            ratio_to_median_purchase_price=ratio,
            used_chip=used_chip,
            used_pin_number=used_pin_number,
            online_order=online_order,
        )
        plan = self._inference_service.build_plan(
            repository=repository,
            training_branch=training_branch,
            infer_url=infer_url,
            model_name=model_name,
            threshold=threshold,
            features=features,
        )

        log_lines: list[str] = []
        with st.status("Running REST inference...", expanded=True) as status:
            try:
                result = self._inference_service.run_inference(
                    plan=plan,
                    config=env,
                    on_log=lambda message: log_lines.append(message),
                )
            except Exception as exc:
                error_message = str(exc)
                st.session_state["inference_last_error"] = error_message
                st.session_state.pop(self._RESULT_KEY, None)
                st.session_state.pop(self._LOG_KEY, None)
                status.update(label="Inference failed", state="error")
                st.error(error_message)
                if log_lines:
                    st.markdown("**Inference log before failure**")
                    st.code("\n".join(log_lines))
                return

            status.update(label="Inference complete", state="complete")

        WorkflowProgressService.mark_complete("inference", {"infer_url": result.infer_url})
        st.session_state[self._RESULT_KEY] = result
        st.session_state[self._LOG_KEY] = tuple(log_lines)

    def _render_last_result(self) -> None:
        result = st.session_state.get(self._RESULT_KEY)
        if not isinstance(result, InferenceResult):
            return

        log_lines = st.session_state.get(self._LOG_KEY, ())
        st.success(f"Prediction complete using auth from `{result.auth_source}`.")
        st.markdown("#### Inference Result")
        st.code(json.dumps(result.payload, indent=2), language="json")
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Model", result.model_name)
        mc2.metric("Fraud Probability", f"{result.score:.5f}")
        mc3.metric("Decision", result.decision.upper())
        st.caption(
            f"Raw features: {list(result.raw_features)} | "
            f"Scaled features: {[round(v, 5) for v in result.scaled_features]} | "
            f"Threshold: {result.threshold:.2f}"
        )
        if log_lines:
            with st.expander("Inference log", expanded=False):
                st.code("\n".join(log_lines))

    @staticmethod
    def _render_prerequisites(checks) -> None:
        st.markdown("#### Workflow Prerequisites")
        for check in checks:
            icon = "✅" if check.passed else "❌"
            st.write(f"{icon} **{check.name}** — {check.detail}")
