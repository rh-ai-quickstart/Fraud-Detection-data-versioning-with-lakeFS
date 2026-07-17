from __future__ import annotations

import os
from pathlib import Path

from clients.openshift_client import OpenShiftClient


class CodeFlareClient:
    SERVICE_ACCOUNT_TOKEN_PATH = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
    SERVICE_ACCOUNT_CA_PATH = Path("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
    WORKBENCH_CA_CERT_PATH = Path("/etc/pki/tls/custom-certs/ca-bundle.crt")

    @classmethod
    def configure_authentication(cls) -> tuple[bool, str]:
        try:
            import codeflare_sdk.common.kubernetes_cluster.auth as cf_auth
            from kubernetes import client, config
        except ImportError:
            return False, "codeflare-sdk or the Kubernetes client is not installed."

        if cls._in_cluster():
            return cls._configure_in_cluster(cf_auth, client, config)

        kubeconfig = Path.home() / ".kube" / "config"
        if kubeconfig.is_file():
            return cls._configure_kubeconfig(cf_auth, client, config, kubeconfig)

        return cls._configure_token_auth()

    @classmethod
    def _configure_in_cluster(cls, cf_auth, client, config) -> tuple[bool, str]:
        try:
            config.load_incluster_config()
        except config.ConfigException as exc:
            return False, f"Failed to load in-cluster Kubernetes config: {exc}"

        api = client.ApiClient()
        skip_tls = cls._should_skip_tls()
        cls._apply_tls_configuration(api.configuration, skip_tls=skip_tls)
        cf_auth.api_client = api
        cf_auth.config_path = None

        tls_mode = "without TLS verification" if skip_tls else "with cluster CA verification"
        return True, f"Authenticated to in-cluster Kubernetes at `{api.configuration.host}` ({tls_mode})."

    @classmethod
    def _configure_kubeconfig(
        cls,
        cf_auth,
        client,
        config,
        kubeconfig: Path,
    ) -> tuple[bool, str]:
        try:
            config.load_kube_config(config_file=str(kubeconfig))
        except config.ConfigException as exc:
            return False, f"Failed to load kubeconfig: {exc}"

        api = client.ApiClient()
        cls._apply_tls_configuration(api.configuration, skip_tls=cls._should_skip_tls())
        cf_auth.api_client = api
        cf_auth.config_path = str(kubeconfig)
        return True, f"Authenticated using kubeconfig `{kubeconfig}`."

    @classmethod
    def _configure_token_auth(cls) -> tuple[bool, str]:
        from codeflare_sdk import TokenAuthentication

        server = cls._api_server_url()
        if not server:
            return False, "Kubernetes API server URL is not available in this environment."

        token_ok, token_or_message = OpenShiftClient.current_token()
        if not token_ok:
            return False, token_or_message

        skip_tls = cls._should_skip_tls()
        ca_cert_path = None if skip_tls else cls._ca_cert_path()
        auth = TokenAuthentication(
            token=token_or_message,
            server=server,
            skip_tls=skip_tls,
            ca_cert_path=ca_cert_path,
        )
        login_result = auth.login()
        if not login_result:
            return False, "CodeFlare Kubernetes authentication failed."
        return True, f"Authenticated to Kubernetes at `{server}`."

    @classmethod
    def _apply_tls_configuration(cls, configuration, skip_tls: bool) -> None:
        if skip_tls:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            configuration.verify_ssl = False
            configuration.ssl_ca_cert = None
            return

        ca_cert_path = cls._ca_cert_path()
        configuration.verify_ssl = True
        configuration.ssl_ca_cert = ca_cert_path

    @classmethod
    def _ca_cert_path(cls) -> str | None:
        if cls.SERVICE_ACCOUNT_CA_PATH.is_file():
            return str(cls.SERVICE_ACCOUNT_CA_PATH)
        if cls.WORKBENCH_CA_CERT_PATH.is_file():
            return str(cls.WORKBENCH_CA_CERT_PATH)
        explicit = os.getenv("CF_SDK_CA_CERT_PATH", "").strip()
        return explicit or None

    @classmethod
    def _should_skip_tls(cls) -> bool:
        env = os.getenv("CF_SDK_SKIP_TLS", "").strip().lower()
        if env in {"1", "true", "yes"}:
            return True
        if env in {"0", "false", "no"}:
            return False
        # OpenShift in-cluster API calls commonly fail strict verification with the SA CA bundle.
        return cls._in_cluster()

    @staticmethod
    def _in_cluster() -> bool:
        return "KUBERNETES_SERVICE_HOST" in os.environ and CodeFlareClient.SERVICE_ACCOUNT_TOKEN_PATH.is_file()

    @classmethod
    def in_cluster(cls) -> bool:
        return cls._in_cluster()

    @staticmethod
    def _api_server_url() -> str:
        explicit = os.getenv("KUBERNETES_API_URL", "").strip()
        if explicit:
            return explicit

        host = os.getenv("KUBERNETES_SERVICE_HOST", "").strip()
        port = os.getenv("KUBERNETES_SERVICE_PORT", "443").strip()
        if host:
            return f"https://{host}:{port}"
        return ""
