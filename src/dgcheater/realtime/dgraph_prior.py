from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Any
import warnings

import joblib
import numpy as np

from ..core.config import APP_CONFIG
from ..datasets.dgraph import load_dgraph_fin_dataset
from ..dgraph.features import build_features_for_nodes
from ..models.training import _build_known_label_neighbor_features


@dataclass(slots=True)
class DGraphPriorMetadata:
    model_name: str
    dataset_key: str
    node_count: int
    feature_count: int
    valid_auc: float
    xgboost_weight: float
    lightgbm_weight: float
    cache_path: str


class DGraphAccountPrior:
    def __init__(self, scores: np.ndarray, metadata: DGraphPriorMetadata) -> None:
        if scores.ndim != 1 or scores.size == 0:
            raise ValueError("DGraph 账户先验分必须是一维非空数组。")
        self.scores = scores.astype(np.float32, copy=False)
        self.metadata = metadata

    @classmethod
    def load(cls, repo_root: Path | None = None, node_count: int | None = None) -> "DGraphAccountPrior":
        root = repo_root or Path(__file__).resolve().parents[3]
        requested_node_count = node_count or int(os.getenv("DG_DGRAPH_PRIOR_NODE_COUNT", "12000"))
        if requested_node_count <= 0:
            raise ValueError("DG_DGRAPH_PRIOR_NODE_COUNT 必须大于 0。")
        cache_path = _cache_path(root, requested_node_count)
        if cache_path.exists():
            payload = joblib.load(cache_path)
            return cls(
                scores=np.asarray(payload["scores"], dtype=np.float32),
                metadata=DGraphPriorMetadata(**payload["metadata"]),
            )
        return cls._build(root=root, requested_node_count=requested_node_count, cache_path=cache_path)

    @classmethod
    def _build(cls, *, root: Path, requested_node_count: int, cache_path: Path) -> "DGraphAccountPrior":
        raw = load_dgraph_fin_dataset(_resolve_path(root, APP_CONFIG.dataset_path("dgraph_fin")))
        node_count = min(requested_node_count, raw.num_nodes)
        nodes = np.arange(node_count, dtype=np.int64)
        bundle = build_features_for_nodes(raw, nodes)
        label_features = _build_known_label_neighbor_features(raw.edge_index, raw.train_idx, raw.y, raw.num_nodes)[nodes]
        score_matrix = np.concatenate([bundle.features, label_features], axis=1)

        model_dir = _resolve_path(root, APP_CONFIG.paths.output_dir) / "dgraph_fin" / "models"
        xgb_path = model_dir / "xgboost.joblib"
        lgb_path = model_dir / "lightgbm_aux.joblib"
        missing = [path for path in (xgb_path, lgb_path) if not path.exists()]
        if missing:
            raise FileNotFoundError("DGraph 模型文件缺失：" + ", ".join(str(path) for path in missing))

        xgb_model = joblib.load(xgb_path)
        lgb_model = joblib.load(lgb_path)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            xgb_score = xgb_model.predict_proba(score_matrix)[:, 1]
            lgb_score = lgb_model.predict_proba(score_matrix)[:, 1]
        blend = APP_CONFIG.models.graph.blend
        scores = (
            blend.xgboost_weight * xgb_score.astype(np.float32)
            + blend.lightgbm_weight * lgb_score.astype(np.float32)
        ).astype(np.float32)

        metadata = DGraphPriorMetadata(
            model_name="dgraph_fin_xgboost_lightgbm_account_prior",
            dataset_key="dgraph_fin",
            node_count=int(node_count),
            feature_count=int(score_matrix.shape[1]),
            valid_auc=_read_valid_auc(root),
            xgboost_weight=float(blend.xgboost_weight),
            lightgbm_weight=float(blend.lightgbm_weight),
            cache_path=str(cache_path),
        )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"scores": scores, "metadata": asdict(metadata)}, cache_path)
        return cls(scores=scores, metadata=metadata)

    def score_account(self, account_id: int) -> tuple[float, int]:
        dgraph_node_id = int(account_id) % int(self.scores.size)
        return float(self.scores[dgraph_node_id]), dgraph_node_id


def _cache_path(root: Path, node_count: int) -> Path:
    return _resolve_path(root, APP_CONFIG.paths.output_dir) / "realtime" / f"dgraph_account_prior_{node_count}.joblib"


def _resolve_path(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _read_valid_auc(root: Path) -> float:
    metrics_path = _resolve_path(root, APP_CONFIG.paths.output_dir) / "dgraph_fin" / "metrics" / "xgboost_metrics.json"
    if not metrics_path.exists():
        return 0.0
    data: dict[str, Any] = json.loads(metrics_path.read_text(encoding="utf-8"))
    return float(data.get("valid_auc", 0.0))
