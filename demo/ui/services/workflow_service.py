from __future__ import annotations

from models.workflow_models import WorkflowStage


class WorkflowService:
    @staticmethod
    def stages() -> list[WorkflowStage]:
        return [
            WorkflowStage(
                stage_id="readiness",
                tab_label="0. Readiness",
                objective="Validate lakeFS + OpenShift AI environment health.",
                status="Ready to start",
            ),
            WorkflowStage(
                stage_id="train",
                tab_label="1. Train",
                objective="Train the fraud model.",
                status="Experiment in progress",
            ),
            WorkflowStage(
                stage_id="save",
                tab_label="2. Save to lakeFS",
                objective="Upload Model to lakeFS.",
                status="Awaiting commit",
            ),
            WorkflowStage(
                stage_id="register",
                tab_label="3. Register Model",
                objective="Register Model to OpenShift AI Model Registry.",
                status="Awaiting registration",
            ),
            WorkflowStage(  
                stage_id="deploy",
                tab_label="4. Deploy Model",
                objective="Create Kserve InferenceService",
                status="Awaiting deployment",
            ),
            WorkflowStage(
                stage_id="inference",
                tab_label="5. REST Inference",
                objective="Submit inference payloads and evaluate fraud outcomes.",
                status="Endpoint configured",
            ),
            WorkflowStage(
                stage_id="distributed",
                tab_label="8. Distributed",
                objective="Submit CodeFlare + Ray distributed training to lakeFS.",
                status="Ready to submit",
            ),
        ]
