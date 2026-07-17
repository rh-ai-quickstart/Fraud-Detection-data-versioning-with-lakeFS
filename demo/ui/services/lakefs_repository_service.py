from __future__ import annotations

import os

from clients import LakeFSApiClient
from services.config_service import EnvironmentConfig


class LakeFSRepositoryService:
    @staticmethod
    def configure_sdk(config: EnvironmentConfig) -> None:
        if config.lakefs_endpoint:
            os.environ["LAKECTL_SERVER_ENDPOINT_URL"] = config.lakefs_endpoint
        if config.lakefs_access_key:
            os.environ["LAKECTL_CREDENTIALS_ACCESS_KEY_ID"] = config.lakefs_access_key
        if config.lakefs_secret_key:
            os.environ["LAKECTL_CREDENTIALS_SECRET_ACCESS_KEY"] = config.lakefs_secret_key

    @staticmethod
    def list_repository_names(config: EnvironmentConfig) -> tuple[bool, str, list[str]]:
        client = LakeFSApiClient(config.lakefs_endpoint)
        return client.list_repositories(
            access_key=config.lakefs_access_key,
            secret_key=config.lakefs_secret_key,
        )

    @staticmethod
    def ensure_repository_exists(repository: str, config: EnvironmentConfig) -> list[str]:
        ok, detail, repositories = LakeFSRepositoryService.list_repository_names(config)
        if not ok:
            raise ValueError(f"Unable to list lakeFS repositories: {detail}")

        if repository not in repositories:
            available = ", ".join(repositories) if repositories else "none"
            raise ValueError(
                f"lakeFS repository '{repository}' does not exist. "
                f"Available repositories: {available}. "
                f"Use the repository configured in Helm (`LAKEFS_REPO_NAME`, typically `my-storage`)."
            )
        return repositories
