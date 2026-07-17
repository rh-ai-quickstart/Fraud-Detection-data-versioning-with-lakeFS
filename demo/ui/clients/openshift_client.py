from __future__ import annotations

import os
from pathlib import Path
import subprocess


class OpenShiftClient:
    SERVICE_ACCOUNT_TOKEN_PATH = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")

    @staticmethod
    def service_account_token() -> tuple[bool, str]:
        token_path = OpenShiftClient.SERVICE_ACCOUNT_TOKEN_PATH
        if not token_path.exists():
            return False, "Service account token is not mounted in this pod."
        token = token_path.read_text(encoding="utf-8").strip()
        if not token:
            return False, "Service account token file is empty."
        return True, token

    @staticmethod
    def current_token() -> tuple[bool, str]:
        env_token = os.getenv("INFERENCE_BEARER_TOKEN", "").strip()
        if env_token:
            return True, env_token

        ok, token_or_message = OpenShiftClient.service_account_token()
        if ok:
            return True, token_or_message

        try:
            completed = subprocess.run(
                ["oc", "whoami", "-t"],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return False, token_or_message
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else "unknown error"
            return False, f"Failed to fetch token: {stderr}"

        token = completed.stdout.strip()
        if not token:
            return False, "Token command succeeded but returned empty output."
        return True, token

    @staticmethod
    def token_source() -> str:
        if os.getenv("INFERENCE_BEARER_TOKEN", "").strip():
            return "INFERENCE_BEARER_TOKEN"
        if OpenShiftClient.SERVICE_ACCOUNT_TOKEN_PATH.exists():
            return "service account"
        return "oc whoami -t"

