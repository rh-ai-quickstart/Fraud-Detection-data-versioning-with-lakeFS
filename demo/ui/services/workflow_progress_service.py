from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st


@dataclass(frozen=True)
class WorkflowStep:
    stage_id: str
    label: str
    required_for_inference: bool = True


class WorkflowProgressService:
    """Tracks workflow stage completion in Streamlit session state."""

    STEPS: tuple[WorkflowStep, ...] = (
        WorkflowStep("readiness", "0. Readiness"),
        WorkflowStep("train", "1. Train"),
        WorkflowStep("save", "2. Save to lakeFS"),
        WorkflowStep("register", "3. Register Model"),
        WorkflowStep("deploy", "4. Deploy Model"),
        WorkflowStep("inference", "5. REST Inference"),
    )

    _SESSION_KEY = "workflow_completed"

    @classmethod
    def mark_complete(cls, stage_id: str, metadata: dict[str, Any] | None = None) -> None:
        completed = dict(st.session_state.get(cls._SESSION_KEY, {}))
        completed[stage_id] = metadata or {}
        st.session_state[cls._SESSION_KEY] = completed

    @classmethod
    def is_complete(cls, stage_id: str) -> bool:
        return stage_id in st.session_state.get(cls._SESSION_KEY, {})

    @classmethod
    def metadata(cls, stage_id: str) -> dict[str, Any]:
        return dict(st.session_state.get(cls._SESSION_KEY, {}).get(stage_id, {}))

    @classmethod
    def completed_stage_ids(cls) -> tuple[str, ...]:
        return tuple(st.session_state.get(cls._SESSION_KEY, {}).keys())

    @classmethod
    def inference_prerequisites_met(cls) -> tuple[bool, tuple[str, ...]]:
        missing: list[str] = []
        for step in cls.STEPS:
            if not step.required_for_inference or step.stage_id == "inference":
                continue
            if not cls.is_complete(step.stage_id):
                missing.append(step.label)
        return not missing, tuple(missing)

    @classmethod
    def progress_fraction(cls) -> float:
        required = [step for step in cls.STEPS if step.required_for_inference]
        if not required:
            return 0.0
        done = sum(1 for step in required if cls.is_complete(step.stage_id))
        return done / len(required)
