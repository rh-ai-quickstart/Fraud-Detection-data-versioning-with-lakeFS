from __future__ import annotations

import pickle

import lakefs
from sklearn.preprocessing import StandardScaler

from services.config_service import EnvironmentConfig
from services.lakefs_repository_service import LakeFSRepositoryService


class ScalerArtifactService:
    @staticmethod
    def load_from_branch(repository: str, training_branch: str, config: EnvironmentConfig) -> StandardScaler:
        LakeFSRepositoryService.configure_sdk(config)
        LakeFSRepositoryService.ensure_repository_exists(repository, config)

        branch = lakefs.Repository(repository).branch(training_branch)
        try:
            with branch.object(path="artifact/scaler.pkl").reader("rb") as handle:
                scaler = pickle.load(handle)
        except Exception as exc:
            raise ValueError(
                f"Unable to load `artifact/scaler.pkl` from `{repository}/{training_branch}`. "
                "Run the Train tab first."
            ) from exc

        if not hasattr(scaler, "transform"):
            raise ValueError("Loaded scaler artifact is invalid.")
        return scaler
