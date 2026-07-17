from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class InferenceApiClient:
    infer_url: str
    token: str
    verify_tls: bool = False
    timeout_seconds: int = 10

    def infer(self, payload: dict[str, Any]) -> tuple[bool, str, list[float]]:
        if not self.infer_url:
            return False, "Inference URL is empty.", []
        if not self.token:
            return False, "Token missing. Run `oc whoami -t` first.", []

        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.post(
                self.infer_url,
                headers=headers,
                json=payload,
                verify=self.verify_tls,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            return False, f"Inference request failed: {exc}", []

        if not response.ok:
            return False, f"HTTP {response.status_code}: {response.text[:250]}", []

        response_dict = response.json()
        outputs = response_dict.get("outputs", [])
        if not outputs:
            return False, "No outputs field returned.", []

        data = outputs[0].get("data", [])
        if not isinstance(data, list):
            return False, "Invalid output data format.", []

        return True, "Inference call completed.", [float(v) for v in data]

