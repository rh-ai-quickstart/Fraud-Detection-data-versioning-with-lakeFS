from __future__ import annotations

import tempfile
import urllib.request
from pathlib import Path


class TrainingDataClient:
    DATA_URLS = {
        "train.csv": "https://raw.githubusercontent.com/cfchase/fraud-detection/main/data/train.csv",
        "validate.csv": "https://raw.githubusercontent.com/cfchase/fraud-detection/main/data/validate.csv",
        "test.csv": "https://raw.githubusercontent.com/cfchase/fraud-detection/main/data/test.csv",
    }

    def download_datasets(self, target_dir: Path) -> dict[str, Path]:
        target_dir.mkdir(parents=True, exist_ok=True)
        downloaded: dict[str, Path] = {}
        for filename, url in self.DATA_URLS.items():
            destination = target_dir / filename
            urllib.request.urlretrieve(url, destination)
            downloaded[filename] = destination
        return downloaded

    @staticmethod
    def temp_dataset_dir() -> Path:
        return Path(tempfile.mkdtemp(prefix="fraud-training-data-"))
