from __future__ import annotations

import streamlit as st

from models import WorkflowStage


class ThemeComponent:
    @staticmethod
    def render() -> None:
        st.markdown(
            """
            <style>
              .stApp {
                background: radial-gradient(circle at top right, #13253f 0%, #0f172a 40%, #020617 100%);
              }
              .hero {
                padding: 1.1rem 1.4rem;
                border-radius: 14px;
                background: linear-gradient(135deg, rgba(14,165,233,0.16), rgba(168,85,247,0.20));
                border: 1px solid rgba(148,163,184,0.35);
                margin-bottom: 1rem;
              }
              .hero h1, .hero p { color: #e2e8f0; margin: 0; }
              .hero p { margin-top: 0.45rem; }
              .pill {
                display: inline-block;
                font-size: 0.80rem;
                padding: 0.35rem 0.60rem;
                border-radius: 999px;
                margin-right: 0.45rem;
                margin-top: 0.7rem;
                color: #e2e8f0;
                background: rgba(15, 23, 42, 0.60);
                border: 1px solid rgba(148, 163, 184, 0.35);
              }
              .section-card {
                background: rgba(15, 23, 42, 0.65);
                border: 1px solid rgba(51, 65, 85, 0.85);
                border-radius: 12px;
                padding: 0.9rem 1rem;
                margin-bottom: 0.7rem;
              }
              .section-card h4 { margin: 0 0 0.4rem 0; color: #cbd5e1; }
              .section-card p { margin: 0; color: #94a3b8; font-size: 0.92rem; }
            </style>
            """,
            unsafe_allow_html=True,
        )


class HeaderComponent:
    @staticmethod
    def render() -> None:
        st.markdown(
            """
            <div class="hero">
              <h1>Fraud Detection Workflow Studio</h1>
            </div>
            """,
            unsafe_allow_html=True,
        )


class SidebarComponent:
    @staticmethod
    def render(stages: list[WorkflowStage]) -> int:
        from services.workflow_progress_service import WorkflowProgressService

        with st.sidebar:
            st.subheader("Workflow Navigator")
            progress = WorkflowProgressService.progress_fraction()
            st.progress(progress, text=f"Workflow progress: {int(progress * 100)}%")
            st.markdown("---")

            selected_index = st.radio(
                "Stage",
                options=range(len(stages)),
                format_func=lambda i: stages[i].tab_label,
                key="stage_selector",
            )

            selected_stage = stages[selected_index]
            if selected_stage.stage_id != "distributed":
                complete = WorkflowProgressService.is_complete(selected_stage.stage_id)
                marker = "✅" if complete else "⬜"
                st.markdown(f"{marker} **{selected_stage.tab_label}**")
                st.caption(selected_stage.objective)

            return selected_index




