from __future__ import annotations
import pickle
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import lakefs
import numpy as np
import onnx
import onnxruntime as rt
import pandas as pd

from clients.training_data_client import TrainingDataClient
from models.training_models import TrainingPlan, TrainingResult
from services.config_service import EnvironmentConfig
from services.lakefs_repository_service import LakeFSRepositoryService


class TrainingExecutionService:
    FEATURE_INDEXES = [1, 2, 4, 5, 6]
    LABEL_INDEXES = [7]

    def __init__(self, data_client: TrainingDataClient | None = None) -> None:
        self._data_client = data_client or TrainingDataClient()

    def run(self, plan: TrainingPlan, config: EnvironmentConfig, on_log: Callable[[str], None] | None = None) -> TrainingResult:
        import tensorflow as tf
        from sklearn.preprocessing import StandardScaler
        from sklearn.utils import class_weight
        tf.keras.backend.clear_session()
        logs: list[str] = []

        def log(message: str) -> None:
            logs.append(message)
            if on_log:
                on_log(message)

        if not all([config.lakefs_endpoint, config.lakefs_access_key, config.lakefs_secret_key, config.lakefs_repo_name]):
            raise ValueError("lakeFS environment variables are not fully configured.")

        repo_name = (plan.repository or config.lakefs_repo_name).strip()
        LakeFSRepositoryService.configure_sdk(config)
        available_repositories = LakeFSRepositoryService.ensure_repository_exists(repo_name, config)
        log(f"Verified lakeFS repository `{repo_name}` (available: {', '.join(available_repositories)}).")

        storage_options = self._storage_options(config)
        try:
            lakefs_repo = lakefs.Repository(repo_name)
            branch_training = lakefs_repo.branch(plan.training_branch).create(
                source_reference=plan.main_branch,
                exist_ok=True,
            )
        except Exception as exc:
            raise ValueError(
                f"Failed to access lakeFS repository '{repo_name}' on branch '{plan.training_branch}': {exc}"
            ) from exc
        log(f"Using lakeFS repository `{repo_name}` on branch `{plan.training_branch}`.")

        dataset_dir = self._data_client.temp_dataset_dir()
        try:
            local_files = self._data_client.download_datasets(dataset_dir)
            log("Downloaded training datasets from the public fraud-detection source.")

            for filename, local_path in local_files.items():
                object_path = self._object_path(plan.training_branch, f"data/{filename}")
                with open(local_path, "rb") as reader, branch_training.object(path=object_path).writer(
                    mode="wb",
                    metadata={"using": "fraud-detection-studio", "source": "Fraud Detection Demo"},
                ) as writer:
                    writer.write(reader.read())
                log(f"Uploaded `{object_path}` to branch `{plan.training_branch}`.")

            train_uri = self._s3_uri(repo_name, plan.training_branch, plan.train_path)
            validate_uri = self._s3_uri(repo_name, plan.training_branch, plan.validate_path)
            test_uri = self._s3_uri(repo_name, plan.training_branch, plan.test_path)

            df = pd.read_csv(train_uri, storage_options=storage_options)
            x_train = df.iloc[:, self.FEATURE_INDEXES].values
            y_train = df.iloc[:, self.LABEL_INDEXES].values

            df = pd.read_csv(validate_uri, storage_options=storage_options)
            x_val = df.iloc[:, self.FEATURE_INDEXES].values
            y_val = df.iloc[:, self.LABEL_INDEXES].values

            df = pd.read_csv(test_uri, storage_options=storage_options)
            x_test = df.iloc[:, self.FEATURE_INDEXES].values
            y_test = df.iloc[:, self.LABEL_INDEXES].values

            scaler = StandardScaler()
            x_train = scaler.fit_transform(x_train)
            x_val = scaler.transform(x_val)
            x_test = scaler.transform(x_test)

            with branch_training.object(path="artifact/test_data.pkl").writer("wb") as handle:
                pickle.dump((x_test, y_test), handle)
            with branch_training.object(path="artifact/scaler.pkl").writer("wb") as handle:
                pickle.dump(scaler, handle)
            log("Saved scaler and test artifacts to lakeFS.")

            class_weights: dict[int, float] | None = None
            if plan.class_weighting:
                weights = class_weight.compute_class_weight(
                    "balanced",
                    classes=np.unique(y_train),
                    y=y_train.ravel(),
                )
                class_weights = {index: weights[index] for index in range(len(weights))}

            model = self._build_model(len(self.FEATURE_INDEXES))
            log("Starting model training...")
            start = time.time()
            model.fit(
                x_train,
                y_train,
                epochs=plan.epochs,
                validation_data=(x_val, y_val),
                verbose=0,
                class_weight=class_weights,
            )
            elapsed = time.time() - start
            log(f"Training completed in {elapsed:.1f} seconds.")

            model_dir = Path("/app/models/fraud/1")
            model_dir.mkdir(parents=True, exist_ok=True)
            model_path = model_dir / "model.onnx"
            self._save_onnx_model(model, x_train.shape[1], model_path)
            log(f"Saved ONNX model to `{model_path}`.")

            metrics = self._evaluate(model_path, x_test, y_test, plan.threshold)
            log(
                f"Evaluation: accuracy={metrics['accuracy']:.2f}%, "
                f"precision={metrics['precision']:.4f}, recall={metrics['recall']:.4f}"
            )

            return TrainingResult(
                accuracy=metrics["accuracy"],
                precision=metrics["precision"],
                recall=metrics["recall"],
                epochs=plan.epochs,
                training_seconds=elapsed,
                model_path=str(model_path),
                repository=repo_name,
                training_branch=plan.training_branch,
                train_s3_uri=train_uri,
                validate_s3_uri=validate_uri,
                test_s3_uri=test_uri,
                log_lines=tuple(logs),
            )
        finally:
            for path in dataset_dir.glob("*"):
                path.unlink(missing_ok=True)
            dataset_dir.rmdir()

    @staticmethod
    def _storage_options(config: EnvironmentConfig) -> dict[str, Any]:
        return {
            "key": config.lakefs_access_key,
            "secret": config.lakefs_secret_key,
            "client_kwargs": {"endpoint_url": config.lakefs_endpoint},
        }

    @staticmethod
    def _object_path(training_branch: str, path: str) -> str:
        prefix = f"{training_branch}/"
        if path.startswith(prefix):
            return path[len(prefix) :]
        return path

    @staticmethod
    def _s3_uri(repository: str, training_branch: str, path: str) -> str:
        object_path = TrainingExecutionService._object_path(training_branch, path)
        if not object_path.startswith("data/"):
            object_path = TrainingExecutionService._object_path(training_branch, f"data/{Path(path).name}")
        return f"s3://{repository}/{training_branch}/{object_path}"

    @staticmethod
    def _build_model(input_dim: int) -> Sequential:
        from keras.models import Sequential
        from keras.layers import Activation, BatchNormalization, Dense, Dropout
        model = Sequential()
        model.add(Dense(32, activation="relu", input_dim=input_dim))
        model.add(Dropout(0.2))
        model.add(Dense(32))
        model.add(BatchNormalization())
        model.add(Activation("relu"))
        model.add(Dropout(0.2))
        model.add(Dense(32))
        model.add(BatchNormalization())
        model.add(Activation("relu"))
        model.add(Dropout(0.2))
        model.add(Dense(1, activation="sigmoid"))
        model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
        return model

    @staticmethod
    def _save_onnx_model(model: Sequential, input_dim: int, model_path: Path) -> None:
        import tensorflow as tf
        import tf2onnx
        @tf.function(input_signature=[tf.TensorSpec([None, input_dim], tf.float32, name="dense_input")])
        def model_fn(features: tf.Tensor) -> tf.Tensor:
            return model(features)

        model_proto, _ = tf2onnx.convert.from_function(
            model_fn,
            input_signature=[tf.TensorSpec([None, input_dim], tf.float32, name="dense_input")],
        )
        onnx.save(model_proto, str(model_path))

    @staticmethod
    def _evaluate(model_path: Path, x_test: np.ndarray, y_test: np.ndarray, threshold: float) -> dict[str, float]:
        from sklearn.metrics import precision_score, recall_score
        session = rt.InferenceSession(str(model_path), providers=rt.get_available_providers())
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        predictions = session.run([output_name], {input_name: x_test.astype(np.float32)})[0]
        predictions = np.squeeze(predictions)
        y_pred = np.where(predictions > threshold, 1, 0)
        y_true = y_test.squeeze()

        accuracy = float(np.equal(y_pred, y_true).mean() * 100)
        precision = float(precision_score(y_true, y_pred, zero_division=0))
        recall = float(recall_score(y_true, y_pred, zero_division=0))
        return {"accuracy": accuracy, "precision": precision, "recall": recall}
