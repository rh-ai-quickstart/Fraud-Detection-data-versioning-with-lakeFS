from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import lakefs

from clients.lakefs_s3_client import LakeFSS3Client
from models.model_registry_models import SaveModelPlan, SaveModelResult
from services.config_service import EnvironmentConfig
from services.lakefs_repository_service import LakeFSRepositoryService


class ModelRegistryExecutionService:
    def run(
        self,
        plan: SaveModelPlan,
        config: EnvironmentConfig,
        on_log: Callable[[str], None] | None = None,
    ) -> SaveModelResult:
        logs: list[str] = []

        def log(message: str) -> None:
            logs.append(message)
            if on_log:
                on_log(message)

        repository = plan.repository.strip()
        LakeFSRepositoryService.configure_sdk(config)
        LakeFSRepositoryService.ensure_repository_exists(repository, config)

        branch_prefix = f"{plan.branch}/{plan.s3_prefix}"
        s3_client = LakeFSS3Client(replace(config, lakefs_repo_name=repository))

        objects_before = tuple(s3_client.list_objects(branch_prefix))
        log(f"Objects under `{branch_prefix}` before upload: {len(objects_before)}")
        for key in objects_before:
            log(f"  - {key}")

        uploaded_keys = s3_client.upload_directory(plan.local_model_dir, branch_prefix)
        if not uploaded_keys:
            raise ValueError(
                f"No files uploaded from `{plan.local_model_dir}`. "
                "Run training first to create `models/fraud/1/model.onnx`."
            )

        for key in uploaded_keys:
            log(f"Uploaded local file to `s3://{repository}/{key}`")

        objects_after = tuple(s3_client.list_objects(branch_prefix))
        log(f"Objects under `{branch_prefix}` after upload: {len(objects_after)}")

        try:
            branch = lakefs.Repository(repository).branch(plan.branch)
            ref = branch.commit(message=plan.commit_message)
            commit = ref.get_commit()
            commit_id = str(getattr(commit, "id", "") or getattr(commit, "commit_id", "") or commit)
        except Exception as exc:
            raise ValueError(f"Model upload succeeded but lakeFS commit failed: {exc}") from exc

        log(f"Committed branch `{plan.branch}` with message `{plan.commit_message}`.")

        return SaveModelResult(
            repository=repository,
            branch=plan.branch,
            files_uploaded=len(uploaded_keys),
            objects_before=objects_before,
            objects_after=objects_after,
            commit_id=commit_id,
            commit_message=plan.commit_message,
            log_lines=tuple(logs),
        )
