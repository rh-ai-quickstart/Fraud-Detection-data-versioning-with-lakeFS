from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class LakeFSApiClient:
    endpoint_url: str
    timeout_seconds: int = 5

    def healthcheck(self) -> tuple[bool, str]:
        if not self.endpoint_url:
            return False, "LAKECTL_SERVER_ENDPOINT_URL is empty."

        url = f"{self.endpoint_url.rstrip('/')}/api/v1/healthcheck"
        try:
            response = requests.get(url, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            return False, f"Healthcheck request failed: {exc}"

        if response.ok:
            return True, f"HTTP {response.status_code} from {url}"
        return False, f"HTTP {response.status_code} from {url}"

    def list_repositories(self, access_key: str, secret_key: str) -> tuple[bool, str, list[str]]:
        if not self.endpoint_url:
            return False, "Missing endpoint URL", []
        if not access_key or not secret_key:
            return False, "Missing lakeFS access/secret key", []

        url = f"{self.endpoint_url.rstrip('/')}/api/v1/repositories"
        try:
            response = requests.get(url, auth=(access_key, secret_key), timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            return False, f"Repository request failed: {exc}", []

        if not response.ok:
            return False, f"HTTP {response.status_code} while listing repositories", []

        payload: dict[str, Any] = response.json() if response.content else {}
        results = payload.get("results", [])
        repo_ids = [repo.get("id", "<unknown>") for repo in results if isinstance(repo, dict)]
        return True, f"Fetched {len(repo_ids)} repositories", repo_ids

