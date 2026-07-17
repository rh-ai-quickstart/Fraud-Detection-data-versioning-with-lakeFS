from __future__ import annotations

from clients import LakeFSApiClient
from models import ReadinessCheckResult
from services.config_service import EnvironmentConfig


class ReadinessService:
    def run_checks(self, config: EnvironmentConfig) -> tuple[list[ReadinessCheckResult], list[str]]:
        checks = [
            ReadinessCheckResult(
                "LAKECTL_SERVER_ENDPOINT_URL",
                bool(config.lakefs_endpoint),
                "Configured" if config.lakefs_endpoint else "Missing",
            ),
            ReadinessCheckResult(
                "LAKECTL_CREDENTIALS_ACCESS_KEY_ID",
                bool(config.lakefs_access_key),
                "Configured" if config.lakefs_access_key else "Missing",
            ),
            ReadinessCheckResult(
                "LAKECTL_CREDENTIALS_SECRET_ACCESS_KEY",
                bool(config.lakefs_secret_key),
                "Configured" if config.lakefs_secret_key else "Missing",
            ),
            ReadinessCheckResult(
                "AWS_S3_ENDPOINT",
                bool(config.aws_s3_endpoint),
                "Configured" if config.aws_s3_endpoint else "Missing",
            ),
            ReadinessCheckResult(
                "AWS_ACCESS_KEY_ID",
                bool(config.aws_access_key),
                "Configured" if config.aws_access_key else "Missing",
            ),
        ]

        repositories: list[str] = []
        if config.lakefs_endpoint:
            client = LakeFSApiClient(config.lakefs_endpoint)
            ok, detail = client.healthcheck()
            checks.append(ReadinessCheckResult("lakeFS /healthcheck", ok, detail))

            repos_ok, repos_detail, repositories = client.list_repositories(
                access_key=config.lakefs_access_key,
                secret_key=config.lakefs_secret_key,
            )
            checks.append(ReadinessCheckResult("lakeFS repositories", repos_ok, repos_detail))

        return checks, repositories

