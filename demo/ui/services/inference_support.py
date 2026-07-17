from __future__ import annotations

from typing import Any


class InferencePayloadBuilder:
    @staticmethod
    def build_payload(scaled_features: list[float]) -> dict[str, Any]:
        return {
            "inputs": [
                {
                    "name": "dense_input",
                    "shape": [1, 5],
                    "datatype": "FP32",
                    "data": scaled_features,
                }
            ]
        }


class InferenceDecisionService:
    @staticmethod
    def classify(score: float, threshold: float) -> str:
        return "fraud" if score > threshold else "not fraud"
