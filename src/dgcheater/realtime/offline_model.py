from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from .feature_engine import RealtimeFeatureEngine
from .schemas import RealtimeFeatures
from .simulator import MultiSourceFraudSimulator, SimulatorConfig


REALTIME_MODEL_FEATURES = [
    "amount",
    "edge_type",
    "src_1m_count",
    "src_5m_amount",
    "src_10m_counterparty_count",
    "device_account_count",
    "ip_account_count",
    "merchant_in_amount",
    "src_out_degree",
    "dst_in_degree",
    "seconds_since_last_src_event",
    "channel_switch_count",
    "burst_score",
    "graph_neighbor_count",
    "graph_risky_neighbor_count",
    "graph_component_size",
    "historical_risk_score",
    "account_age_days",
    "recent_login_challenge_count",
    "blacklist_hit_count",
    "script_score",
]


@dataclass(slots=True)
class RealtimeModelMetadata:
    model_name: str
    feature_names: list[str]
    train_size: int
    valid_size: int
    valid_auc: float
    xgboost_weight: float
    lightgbm_weight: float


class RealtimeOfflineModel:
    def __init__(
        self,
        xgboost_model: Any,
        lightgbm_model: Any,
        metadata: RealtimeModelMetadata,
    ) -> None:
        self.xgboost_model = xgboost_model
        self.lightgbm_model = lightgbm_model
        self.metadata = metadata

    @classmethod
    def load(cls, model_dir: Path) -> "RealtimeOfflineModel":
        metadata_path = model_dir / "metadata.json"
        xgboost_path = model_dir / "xgboost.joblib"
        lightgbm_path = model_dir / "lightgbm_aux.joblib"
        missing = [path for path in (metadata_path, xgboost_path, lightgbm_path) if not path.exists()]
        if missing:
            joined = ", ".join(str(path) for path in missing)
            raise FileNotFoundError(f"实时离线模型文件缺失：{joined}")
        metadata_data = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata = RealtimeModelMetadata(
            model_name=str(metadata_data["model_name"]),
            feature_names=[str(item) for item in metadata_data["feature_names"]],
            train_size=int(metadata_data["train_size"]),
            valid_size=int(metadata_data["valid_size"]),
            valid_auc=float(metadata_data["valid_auc"]),
            xgboost_weight=float(metadata_data["xgboost_weight"]),
            lightgbm_weight=float(metadata_data["lightgbm_weight"]),
        )
        return cls(
            xgboost_model=joblib.load(xgboost_path),
            lightgbm_model=joblib.load(lightgbm_path),
            metadata=metadata,
        )

    def predict_score(self, features: RealtimeFeatures) -> float:
        frame = feature_frame(features, self.metadata.feature_names)
        xgb_score = float(self.xgboost_model.predict_proba(frame)[:, 1][0])
        lgb_score = float(self.lightgbm_model.predict_proba(frame)[:, 1][0])
        score = self.metadata.xgboost_weight * xgb_score + self.metadata.lightgbm_weight * lgb_score
        return max(0.0, min(score, 1.0))


def default_model_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or Path.cwd()
    return root / "data" / "runtime-artifacts" / "output" / "realtime" / "models"


def feature_vector(features: RealtimeFeatures, feature_names: list[str] | None = None) -> np.ndarray:
    payload = features.to_dict()
    names = feature_names or REALTIME_MODEL_FEATURES
    return np.asarray([float(payload[name]) for name in names], dtype=np.float32)


def feature_frame(features: RealtimeFeatures, feature_names: list[str] | None = None) -> pd.DataFrame:
    names = feature_names or REALTIME_MODEL_FEATURES
    vector = feature_vector(features, names).reshape(1, -1)
    return pd.DataFrame(vector, columns=names)


def build_training_matrix(event_count: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    simulator = MultiSourceFraudSimulator(SimulatorConfig(seed=seed))
    engine = RealtimeFeatureEngine()
    rows: list[np.ndarray] = []
    labels: list[int] = []
    for batch in simulator.multi_source_stream(event_count):
        engine.ingest_account(batch.account)
        engine.ingest_device(batch.device)
        if batch.blacklist is not None:
            engine.ingest_blacklist(batch.blacklist)
        features = engine.transform(batch.transaction)
        rows.append(feature_vector(features))
        labels.append(1 if batch.transaction.is_scripted_fraud else 0)
    return np.vstack(rows), np.asarray(labels, dtype=np.int32)


def train_realtime_offline_model(
    *,
    output_dir: Path,
    event_count: int = 20_000,
    seed: int = 42,
) -> RealtimeModelMetadata:
    if event_count < 1_000:
        raise ValueError("event_count 至少需要 1000，避免实时模型只记住少量样本。")
    output_dir.mkdir(parents=True, exist_ok=True)
    features, labels = build_training_matrix(event_count=event_count, seed=seed)
    x_train, x_valid, y_train, y_valid = train_test_split(
        features,
        labels,
        test_size=0.2,
        random_state=seed,
        stratify=labels,
    )
    positive = float((y_train == 1).sum())
    negative = float((y_train == 0).sum())
    scale_pos_weight = negative / max(positive, 1.0)
    xgb_model = XGBClassifier(
        n_estimators=220,
        max_depth=5,
        learning_rate=0.06,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="binary:logistic",
        eval_metric="auc",
        tree_method="hist",
        random_state=seed,
        n_jobs=4,
        scale_pos_weight=scale_pos_weight,
    )
    lgb_model = LGBMClassifier(
        n_estimators=260,
        learning_rate=0.05,
        num_leaves=63,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="binary",
        random_state=seed,
        n_jobs=4,
        scale_pos_weight=scale_pos_weight,
        reg_lambda=1.0,
        verbose=-1,
    )
    x_train_frame = pd.DataFrame(x_train, columns=REALTIME_MODEL_FEATURES)
    x_valid_frame = pd.DataFrame(x_valid, columns=REALTIME_MODEL_FEATURES)
    xgb_model.fit(x_train_frame, y_train)
    lgb_model.fit(x_train_frame, y_train)
    xgb_valid = xgb_model.predict_proba(x_valid_frame)[:, 1]
    lgb_valid = lgb_model.predict_proba(x_valid_frame)[:, 1]
    xgboost_weight = 0.75
    lightgbm_weight = 0.25
    blended = xgboost_weight * xgb_valid + lightgbm_weight * lgb_valid
    metadata = RealtimeModelMetadata(
        model_name="xgboost_lightgbm_realtime_feature_blend",
        feature_names=list(REALTIME_MODEL_FEATURES),
        train_size=int(x_train.shape[0]),
        valid_size=int(x_valid.shape[0]),
        valid_auc=float(roc_auc_score(y_valid, blended)),
        xgboost_weight=xgboost_weight,
        lightgbm_weight=lightgbm_weight,
    )
    joblib.dump(xgb_model, output_dir / "xgboost.joblib")
    joblib.dump(lgb_model, output_dir / "lightgbm_aux.joblib")
    (output_dir / "metadata.json").write_text(json.dumps(asdict(metadata), ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata
