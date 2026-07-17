from __future__ import annotations

import os
from pathlib import Path

import boto3
import botocore

from services.config_service import EnvironmentConfig


class LakeFSS3Client:
    def __init__(self, config: EnvironmentConfig) -> None:
        if not all(
            [
                config.lakefs_access_key,
                config.lakefs_secret_key,
                config.lakefs_endpoint,
                config.lakefs_region,
                config.lakefs_repo_name,
            ]
        ):
            raise ValueError("lakeFS S3 connection settings are incomplete.")

        session = boto3.session.Session(
            aws_access_key_id=config.lakefs_access_key,
            aws_secret_access_key=config.lakefs_secret_key,
        )
        self._bucket = session.resource(
            "s3",
            config=botocore.client.Config(signature_version="s3v4"),
            endpoint_url=config.lakefs_endpoint,
            region_name=config.lakefs_region,
        ).Bucket(config.lakefs_repo_name)

    def list_objects(self, prefix: str) -> list[str]:
        keys: list[str] = []
        for obj in self._bucket.objects.filter(Prefix=prefix):
            keys.append(obj.key)
        return sorted(keys)

    def upload_directory(self, local_directory: str, s3_prefix: str) -> list[str]:
        local_root = Path(local_directory)
        if not local_root.is_dir():
            raise ValueError(f"Local model directory does not exist: {local_directory}")

        uploaded_keys: list[str] = []
        for root, _, files in os.walk(local_directory):
            for filename in files:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, local_directory)
                s3_key = os.path.join(s3_prefix, relative_path).replace("\\", "/")
                self._bucket.upload_file(file_path, s3_key)
                uploaded_keys.append(s3_key)
        return uploaded_keys
