from __future__ import annotations

from components import (
    DeployTabComponent,
    DistributedTabComponent,
    HeaderComponent,
    InferenceTabComponent,
    ModelRegistryTabComponent,
    ReadinessTabComponent,
    RegisterTabComponent,
    SidebarComponent,
    ThemeComponent,
    TrainingTabComponent,
)
from services import WorkflowService

import streamlit as st


class StreamlitApp:
    def __init__(self) -> None:
        self._stages = WorkflowService.stages()

    def run(self) -> None:
        st.set_page_config(page_title="Fraud Detection Workflow Studio", page_icon=":bar_chart:", layout="wide")
        ThemeComponent.render()
        HeaderComponent.render()

        selected_index = SidebarComponent.render(self._stages)
        stage = self._stages[selected_index]

        component = {
            "readiness": ReadinessTabComponent,
            "train": TrainingTabComponent,
            "save": ModelRegistryTabComponent,
            "register": RegisterTabComponent,
            "deploy": DeployTabComponent,
            "inference": InferenceTabComponent,
            "distributed": DistributedTabComponent,
        }[stage.stage_id]
        component(stage).render()


def main() -> None:
    StreamlitApp().run()


if __name__ == "__main__":
    main()
