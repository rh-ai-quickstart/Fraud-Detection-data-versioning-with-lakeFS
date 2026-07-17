from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


@dataclass
class KubernetesClient:
    api_server: str = ""
    token: str = ""
    namespace: str = ""
    ca_cert_path: Path = Path("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
    verify_tls: bool = True
    timeout_seconds: int = 30

    @classmethod
    def from_service_account(cls, token: str) -> KubernetesClient:
        namespace_path = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")
        namespace = (
            namespace_path.read_text(encoding="utf-8").strip()
            if namespace_path.exists()
            else os.getenv("OPENSHIFT_NAMESPACE", os.getenv("DEPLOY_NAMESPACE", ""))
        )
        host = os.getenv("KUBERNETES_SERVICE_HOST", "")
        port = os.getenv("KUBERNETES_SERVICE_PORT", "443")
        api_server = os.getenv("KUBERNETES_API_URL", f"https://{host}:{port}" if host else "")
        verify_tls = cls._should_verify_tls()
        return cls(api_server=api_server, token=token, namespace=namespace, verify_tls=verify_tls)

    @staticmethod
    def _should_verify_tls() -> bool:
        ca_path = Path("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
        return ca_path.exists()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _verify(self) -> bool | str:
        if not self.verify_tls:
            return False
        return str(self.ca_cert_path) if self.ca_cert_path.exists() else False

    def get_custom_resource(
        self,
        group: str,
        version: str,
        plural: str,
        name: str,
        namespace: str | None = None,
    ) -> tuple[bool, str, dict[str, Any] | None]:
        if not self.api_server:
            return False, "Kubernetes API server is not configured in this environment.", None

        ns = namespace or self.namespace
        url = f"{self.api_server}/apis/{group}/{version}/namespaces/{ns}/{plural}/{name}"
        try:
            response = requests.get(
                url,
                headers=self._headers(),
                verify=self._verify(),
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            return False, f"Kubernetes GET failed: {exc}", None

        if response.status_code == 404:
            return False, "Resource not found.", None
        if not response.ok:
            return False, f"HTTP {response.status_code}: {response.text[:250]}", None
        return True, "Resource fetched.", response.json()

    def apply_custom_resource(
        self,
        group: str,
        version: str,
        plural: str,
        body: dict[str, Any],
        namespace: str | None = None,
    ) -> tuple[bool, str, dict[str, Any] | None]:
        if not self.api_server:
            return False, "Kubernetes API server is not configured in this environment.", None

        metadata = body.get("metadata", {})
        name = metadata.get("name", "")
        if not name:
            return False, "Resource metadata.name is required.", None

        ns = namespace or metadata.get("namespace") or self.namespace
        if not ns:
            return False, "Namespace is required to apply the resource.", None

        ok, message, existing = self.get_custom_resource(group, version, plural, name, namespace=ns)
        if ok and existing:
            return self._patch_custom_resource(group, version, plural, name, body, ns)

        url = f"{self.api_server}/apis/{group}/{version}/namespaces/{ns}/{plural}"
        try:
            response = requests.post(
                url,
                headers=self._headers(),
                json=body,
                verify=self._verify(),
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            return False, f"Kubernetes POST failed: {exc}", None

        if not response.ok:
            return False, f"HTTP {response.status_code}: {response.text[:250]}", None
        return True, f"Created `{plural}/{name}`.", response.json()

    def _patch_custom_resource(
        self,
        group: str,
        version: str,
        plural: str,
        name: str,
        body: dict[str, Any],
        namespace: str,
    ) -> tuple[bool, str, dict[str, Any] | None]:
        url = f"{self.api_server}/apis/{group}/{version}/namespaces/{namespace}/{plural}/{name}"
        patch_body = {
            "spec": body.get("spec", {}),
            "metadata": {
                "annotations": body.get("metadata", {}).get("annotations", {}),
                "labels": body.get("metadata", {}).get("labels", {}),
            },
        }
        headers = self._headers()
        headers["Content-Type"] = "application/merge-patch+json"
        try:
            response = requests.patch(
                url,
                headers=headers,
                data=json.dumps(patch_body),
                verify=self._verify(),
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            return False, f"Kubernetes PATCH failed: {exc}", None

        if not response.ok:
            return False, f"HTTP {response.status_code}: {response.text[:250]}", None
        return True, f"Updated `{plural}/{name}`.", response.json()

    @staticmethod
    def inference_service_ready(resource: dict[str, Any]) -> tuple[bool, str]:
        conditions = resource.get("status", {}).get("conditions", [])
        for condition in conditions:
            if condition.get("type") == "Ready":
                status = condition.get("status", "Unknown")
                message = condition.get("message", "No status message.")
                return status == "True", message
        return False, "InferenceService Ready condition not reported yet."

    def api_group_available(self, group: str, version: str) -> tuple[bool, str]:
        if not self.api_server:
            return False, "Kubernetes API server is not configured in this environment."

        url = f"{self.api_server}/apis/{group}/{version}"
        try:
            response = requests.get(
                url,
                headers=self._headers(),
                verify=self._verify(),
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            return False, f"Kubernetes API discovery failed: {exc}"

        if response.status_code == 404:
            return False, f"API group `{group}/{version}` is not registered on this cluster."
        if not response.ok:
            return False, f"HTTP {response.status_code}: {response.text[:250]}"
        return True, f"API group `{group}/{version}` is available."
