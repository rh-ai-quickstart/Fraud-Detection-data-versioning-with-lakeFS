from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TransactionFeatures:
    distance_from_last_transaction: float
    ratio_to_median_purchase_price: float
    used_chip: float
    used_pin_number: float
    online_order: float


@dataclass(frozen=True)
class InferencePlan:
    repository: str
    training_branch: str
    infer_url: str
    model_name: str
    threshold: float
    features: TransactionFeatures
    verify_tls: bool = False


@dataclass(frozen=True)
class InferenceResult:
    model_name: str
    infer_url: str
    raw_features: tuple[float, ...]
    scaled_features: tuple[float, ...]
    payload: dict
    score: float
    decision: str
    threshold: float
    auth_source: str
    log_lines: tuple[str, ...] = field(default_factory=tuple)


EXAMPLE_SCENARIOS: dict[str, tuple[str, TransactionFeatures]] = {
    "Sally's transaction": (
        "Example with moderate distance and ratio values.",
        TransactionFeatures(0.3111400080477545, 1.9459399775518593, 1.0, 0.0, 0.0),
    ),
    "Coffee purchase": (
        "Same location and price, chip + PIN, in-store purchase.",
        TransactionFeatures(0.0, 1.0, 1.0, 1.0, 0.0),
    ),
    "Fraudulent online purchase": (
        "Far from last transaction, no chip/PIN, online order.",
        TransactionFeatures(100.0, 1.2, 0.0, 0.0, 1.0),
    ),
}
