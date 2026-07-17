from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class ModelRegistryApiClient:
    base_url: str
    token: str = ""
    verify_tls: bool = False
    timeout_seconds: int = 30

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _url(self, path: str) -> str:
        base = self.base_url.rstrip("/")
        return f"{base}/api/model_registry/v1alpha3/{path.lstrip('/')}"

    def list_registered_models(self) -> tuple[bool, str, list[dict[str, Any]]]:
        return self._get_collection("registered_models")

    def list_model_versions(self) -> tuple[bool, str, list[dict[str, Any]]]:
        return self._get_collection("model_versions")

    def create_registered_model(self, payload: dict[str, Any]) -> tuple[bool, str, dict[str, Any] | None]:
        return self._post("registered_models", payload)

    def create_model_version(self, payload: dict[str, Any]) -> tuple[bool, str, dict[str, Any] | None]:
        return self._post("model_versions", payload)

    def create_model_artifact(self, model_version_id: str, payload: dict[str, Any]) -> tuple[bool, str, dict[str, Any] | None]:
        return self._post(f"model_versions/{model_version_id}/artifacts", payload)

    def _get_collection(self, resource: str) -> tuple[bool, str, list[dict[str, Any]]]:
        if not self.base_url:
            return False, "Model Registry URL is empty.", []

        try:
            response = requests.get(
                self._url(resource),
                headers=self._headers(),
                verify=self.verify_tls,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            return False, f"Model Registry request failed: {exc}", []

        if not response.ok:
            return False, f"HTTP {response.status_code}: {response.text[:250]}", []

        body = response.json()
        items = body.get("items", body if isinstance(body, list) else [])
        if not isinstance(items, list):
            return False, "Unexpected Model Registry list response.", []
        return True, f"Fetched {len(items)} {resource}.", items

    def _post(self, path: str, payload: dict[str, Any]) -> tuple[bool, str, dict[str, Any] | None]:
        if not self.base_url:
            return False, "Model Registry URL is empty.", None

        try:
            response = requests.post(
                self._url(path),
                headers=self._headers(),
                json=payload,
                verify=self.verify_tls,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            return False, f"Model Registry request failed: {exc}", None

        if not response.ok:
            return False, f"HTTP {response.status_code}: {response.text[:250]}", None

        try:
            return True, "Model Registry request completed.", response.json()
        except ValueError:
            return True, "Model Registry request completed.", None

    @staticmethod
    def find_registered_model(models: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
        for model in models:
            if model.get("name") == name:
                return model
        return None

    @staticmethod
    def find_model_version(versions: list[dict[str, Any]], registered_model_id: str, version_name: str) -> dict[str, Any] | None:
        for version in versions:
            model_id = str(version.get("registeredModelId") or version.get("registeredModelID") or "")
            if model_id == str(registered_model_id) and version.get("name") == version_name:
                return version
        return None
