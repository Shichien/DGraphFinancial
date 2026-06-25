from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from ..core.config import APP_CONFIG, BlendSettings, ModelGroupSettings


@dataclass(slots=True)
class TrainingResult:
    model_name: str
    valid_auc: float
    train_size: int
    valid_size: int
    positive_ratio_train: float
    feature_count: int
    model_path: str
    aux_model_path: str
    submission_path: str
    metrics_path: str
    blend_rule: str


@dataclass(slots=True)
class TabularTrainingResult:
    model_name: str
    valid_auc: float
    train_size: int
    valid_size: int
    positive_ratio_train: float
    feature_count: int
    model_path: str
    aux_model_path: str
    submission_path: str
    metrics_path: str
    blend_rule: str


def _class_weight(y_train: np.ndarray) -> float:
    pos_count = float((y_train == 1).sum())
    neg_count = float((y_train == 0).sum())
    return neg_count / max(pos_count, 1.0)


def _make_lgb_classifier(settings: ModelGroupSettings, seed: int, scale_pos_weight: float) -> LGBMClassifier:
    lgb = settings.lightgbm
    return LGBMClassifier(
        n_estimators=lgb.n_estimators,
        learning_rate=lgb.learning_rate,
        num_leaves=lgb.num_leaves,
        subsample=lgb.subsample,
        colsample_bytree=lgb.colsample_bytree,
        objective="binary",
        random_state=seed,
        n_jobs=lgb.n_jobs,
        scale_pos_weight=scale_pos_weight,
        reg_lambda=lgb.reg_lambda,
        verbose=lgb.verbose,
    )


def _make_xgb_classifier(settings: ModelGroupSettings, seed: int, scale_pos_weight: float) -> XGBClassifier:
    xgb = settings.xgboost
    return XGBClassifier(
        n_estimators=xgb.n_estimators,
        max_depth=xgb.max_depth,
        learning_rate=xgb.learning_rate,
        subsample=xgb.subsample,
        colsample_bytree=xgb.colsample_bytree,
        objective="binary:logistic",
        eval_metric="auc",
        tree_method=xgb.tree_method,
        random_state=seed,
        n_jobs=xgb.n_jobs,
        scale_pos_weight=scale_pos_weight,
    )


def _blend_probabilities(xgb_prob: np.ndarray, lgb_prob: np.ndarray, settings: BlendSettings) -> np.ndarray:
    return settings.xgboost_weight * xgb_prob + settings.lightgbm_weight * lgb_prob


def _build_known_label_neighbor_features(
    edge_index: np.ndarray,
    known_nodes: np.ndarray,
    y: np.ndarray,
    num_nodes: int,
) -> np.ndarray:
    src = edge_index[:, 0]
    dst = edge_index[:, 1]

    known_mask = np.zeros(num_nodes, dtype=bool)
    known_mask[known_nodes] = True
    known_y = y.copy()
    known_y[~known_mask] = -100

    known_fraud = (known_y == 1).astype(np.float32)
    known_normal = (known_y == 0).astype(np.float32)

    fraud_neighbor_count = np.bincount(src, weights=known_fraud[dst], minlength=num_nodes) + np.bincount(
        dst, weights=known_fraud[src], minlength=num_nodes
    )
    normal_neighbor_count = np.bincount(src, weights=known_normal[dst], minlength=num_nodes) + np.bincount(
        dst, weights=known_normal[src], minlength=num_nodes
    )
    known_neighbor_count = fraud_neighbor_count + normal_neighbor_count
    fraud_neighbor_ratio = fraud_neighbor_count / np.maximum(known_neighbor_count, 1)
    normal_neighbor_ratio = normal_neighbor_count / np.maximum(known_neighbor_count, 1)

    return np.stack(
        [
            fraud_neighbor_count.astype(np.float32),
            normal_neighbor_count.astype(np.float32),
            known_neighbor_count.astype(np.float32),
            fraud_neighbor_ratio.astype(np.float32),
            normal_neighbor_ratio.astype(np.float32),
        ],
        axis=1,
    )


def fit_xgboost(
    features: np.ndarray,
    feature_names: list[str],
    edge_index: np.ndarray,
    y: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    output_dir: Path,
    dataset_key: str,
    valid_idx: np.ndarray | None = None,
    seed: int = APP_CONFIG.training.seed,
    valid_size: float = APP_CONFIG.training.valid_size,
) -> TrainingResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_output_dir = output_dir / dataset_key
    model_dir = dataset_output_dir / "models"
    metrics_dir = dataset_output_dir / "metrics"
    submission_dir = dataset_output_dir / "submissions"
    figure_dir = dataset_output_dir / "figures"
    model_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    submission_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    y_train = y[train_idx]
    if valid_idx is None:
        train_nodes, valid_nodes, y_tr, y_va = train_test_split(
            train_idx,
            y_train,
            test_size=valid_size,
            random_state=seed,
            stratify=y_train,
        )
    else:
        train_nodes = train_idx
        valid_nodes = valid_idx
        y_tr = y[train_nodes]
        y_va = y[valid_nodes]
    label_feature_names = [
        "known_fraud_neighbor_count",
        "known_normal_neighbor_count",
        "known_labeled_neighbor_count",
        "known_fraud_neighbor_ratio",
        "known_normal_neighbor_ratio",
    ]
    label_neighbor_features = _build_known_label_neighbor_features(edge_index, train_nodes, y, features.shape[0])
    augmented_features = np.concatenate([features, label_neighbor_features], axis=1)
    all_feature_names = feature_names + label_feature_names
    x_tr = augmented_features[train_nodes]
    x_va = augmented_features[valid_nodes]
    scale_pos_weight = _class_weight(y_tr)
    model_settings = APP_CONFIG.models.graph
    lgb_model = _make_lgb_classifier(model_settings, seed, scale_pos_weight)
    lgb_model.fit(x_tr, y_tr)
    lgb_valid_prob = lgb_model.predict_proba(x_va)[:, 1]
    model = _make_xgb_classifier(model_settings, seed, scale_pos_weight)
    model.fit(x_tr, y_tr)
    xgb_valid_prob = model.predict_proba(x_va)[:, 1]
    valid_prob = _blend_probabilities(xgb_valid_prob, lgb_valid_prob, model_settings.blend)
    valid_auc = float(roc_auc_score(y_va, valid_prob))

    full_train_label_features = _build_known_label_neighbor_features(edge_index, train_idx, y, features.shape[0])
    full_augmented_features = np.concatenate([features, full_train_label_features], axis=1)
    xgb_test_prob = model.predict_proba(full_augmented_features[test_idx])[:, 1]
    lgb_test_prob = lgb_model.predict_proba(full_augmented_features[test_idx])[:, 1]
    test_prob = _blend_probabilities(xgb_test_prob, lgb_test_prob, model_settings.blend)
    submission = np.stack([1.0 - test_prob, test_prob], axis=1).astype(np.float32)

    model_path = model_dir / "xgboost.joblib"
    aux_model_path = model_dir / "lightgbm_aux.joblib"
    submission_path = submission_dir / "submission.npy"
    metrics_path = metrics_dir / "xgboost_metrics.json"
    importance_path = figure_dir / "feature_importance.csv"
    joblib.dump(model, model_path)
    joblib.dump(lgb_model, aux_model_path)
    np.save(submission_path, submission)

    importance_frame = pd.DataFrame(
        {
            "feature": all_feature_names,
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)
    importance_frame.to_csv(importance_path, index=False, encoding="utf-8-sig")

    result = TrainingResult(
        model_name="xgboost_lightgbm_graph_blend",
        valid_auc=valid_auc,
        train_size=int(train_nodes.shape[0]),
        valid_size=int(valid_nodes.shape[0]),
        positive_ratio_train=float((y_tr == 1).mean()),
        feature_count=int(full_augmented_features.shape[1]),
        model_path=str(model_path),
        aux_model_path=str(aux_model_path),
        submission_path=str(submission_path),
        metrics_path=str(metrics_path),
        blend_rule=model_settings.blend.describe(),
    )
    metrics_path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
    return result


def fit_xgboost_without_label_neighbors(
    features: np.ndarray,
    feature_names: list[str],
    y: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    output_dir: Path,
    dataset_key: str,
    valid_idx: np.ndarray | None = None,
    seed: int = APP_CONFIG.training.seed,
    valid_size: float = APP_CONFIG.training.valid_size,
) -> TrainingResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_output_dir = output_dir / dataset_key
    model_dir = dataset_output_dir / "models"
    metrics_dir = dataset_output_dir / "metrics"
    submission_dir = dataset_output_dir / "submissions"
    figure_dir = dataset_output_dir / "figures"
    model_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    submission_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    x_train = features[train_idx]
    y_train = y[train_idx]
    if valid_idx is None:
        x_tr, x_va, y_tr, y_va = train_test_split(
            x_train,
            y_train,
            test_size=valid_size,
            random_state=seed,
            stratify=y_train,
        )
    else:
        x_tr = x_train
        y_tr = y_train
        x_va = features[valid_idx]
        y_va = y[valid_idx]
    scale_pos_weight = _class_weight(y_tr)
    model_settings = APP_CONFIG.models.graph
    lgb_model = _make_lgb_classifier(model_settings, seed, scale_pos_weight)
    lgb_model.fit(x_tr, y_tr)
    lgb_valid_prob = lgb_model.predict_proba(x_va)[:, 1]

    model = _make_xgb_classifier(model_settings, seed, scale_pos_weight)
    model.fit(x_tr, y_tr)
    xgb_valid_prob = model.predict_proba(x_va)[:, 1]
    valid_prob = _blend_probabilities(xgb_valid_prob, lgb_valid_prob, model_settings.blend)
    valid_auc = float(roc_auc_score(y_va, valid_prob))

    xgb_test_prob = model.predict_proba(features[test_idx])[:, 1]
    lgb_test_prob = lgb_model.predict_proba(features[test_idx])[:, 1]
    test_prob = _blend_probabilities(xgb_test_prob, lgb_test_prob, model_settings.blend)
    submission = np.stack([1.0 - test_prob, test_prob], axis=1).astype(np.float32)

    model_path = model_dir / "xgboost_no_label_neighbors.joblib"
    aux_model_path = model_dir / "lightgbm_no_label_neighbors.joblib"
    submission_path = submission_dir / "submission_no_label_neighbors.npy"
    metrics_path = metrics_dir / "xgboost_no_label_neighbors_metrics.json"
    importance_path = figure_dir / "feature_importance_no_label_neighbors.csv"
    joblib.dump(model, model_path)
    joblib.dump(lgb_model, aux_model_path)
    np.save(submission_path, submission)

    importance_frame = pd.DataFrame(
        {
            "feature": feature_names,
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)
    importance_frame.to_csv(importance_path, index=False, encoding="utf-8-sig")

    result = TrainingResult(
        model_name="xgboost_lightgbm_graph_blend_no_label_neighbors",
        valid_auc=valid_auc,
        train_size=int(x_tr.shape[0]),
        valid_size=int(x_va.shape[0]),
        positive_ratio_train=float((y_tr == 1).mean()),
        feature_count=int(features.shape[1]),
        model_path=str(model_path),
        aux_model_path=str(aux_model_path),
        submission_path=str(submission_path),
        metrics_path=str(metrics_path),
        blend_rule=model_settings.blend.describe(),
    )
    metrics_path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
    return result


def fit_lightgbm_baseline(
    features: np.ndarray,
    y: np.ndarray,
    train_idx: np.ndarray,
    valid_idx: np.ndarray | None = None,
    seed: int = APP_CONFIG.training.seed,
    valid_size: float = APP_CONFIG.training.valid_size,
) -> float:
    x_train = features[train_idx]
    y_train = y[train_idx]
    if valid_idx is None:
        x_tr, x_va, y_tr, y_va = train_test_split(
            x_train,
            y_train,
            test_size=valid_size,
            random_state=seed,
            stratify=y_train,
        )
    else:
        x_tr = x_train
        y_tr = y_train
        x_va = features[valid_idx]
        y_va = y[valid_idx]
    scale_pos_weight = _class_weight(y_tr)
    model = _make_lgb_classifier(APP_CONFIG.models.graph, seed, scale_pos_weight)
    model.fit(x_tr, y_tr)
    valid_prob = model.predict_proba(x_va)[:, 1]
    return float(roc_auc_score(y_va, valid_prob))


def fit_tabular_blend(
    features: np.ndarray,
    feature_names: list[str],
    y: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    output_dir: Path,
    dataset_key: str,
    valid_idx: np.ndarray | None = None,
    test_ids: np.ndarray | None = None,
    submission_id_column: str = "id",
    submission_target_column: str = "target",
    seed: int = APP_CONFIG.training.seed,
    valid_size: float = APP_CONFIG.training.valid_size,
) -> TabularTrainingResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_output_dir = output_dir / dataset_key
    model_dir = dataset_output_dir / "models"
    metrics_dir = dataset_output_dir / "metrics"
    submission_dir = dataset_output_dir / "submissions"
    figure_dir = dataset_output_dir / "figures"
    model_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    submission_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    if valid_idx is None:
        x_train = features[train_idx]
        y_train = y[train_idx]
        x_tr, x_va, y_tr, y_va = train_test_split(
            x_train,
            y_train,
            test_size=valid_size,
            random_state=seed,
            stratify=y_train,
        )
    else:
        x_tr = features[train_idx]
        y_tr = y[train_idx]
        x_va = features[valid_idx]
        y_va = y[valid_idx]
    scale_pos_weight = _class_weight(y_tr)
    model_settings = APP_CONFIG.models.tabular

    lgb_model = _make_lgb_classifier(model_settings, seed, scale_pos_weight)
    lgb_model.fit(x_tr, y_tr)
    lgb_valid_prob = lgb_model.predict_proba(x_va)[:, 1]

    xgb_model = _make_xgb_classifier(model_settings, seed, scale_pos_weight)
    xgb_model.fit(x_tr, y_tr)
    xgb_valid_prob = xgb_model.predict_proba(x_va)[:, 1]
    valid_prob = _blend_probabilities(xgb_valid_prob, lgb_valid_prob, model_settings.blend)
    valid_auc = float(roc_auc_score(y_va, valid_prob))

    x_test = features[test_idx]
    xgb_test_prob = xgb_model.predict_proba(x_test)[:, 1]
    lgb_test_prob = lgb_model.predict_proba(x_test)[:, 1]
    test_prob = _blend_probabilities(xgb_test_prob, lgb_test_prob, model_settings.blend)

    model_path = model_dir / "xgboost.joblib"
    aux_model_path = model_dir / "lightgbm_aux.joblib"
    metrics_path = metrics_dir / "xgboost_metrics.json"
    importance_path = figure_dir / "feature_importance.csv"
    submission_path = submission_dir / "submission.csv"
    joblib.dump(xgb_model, model_path)
    joblib.dump(lgb_model, aux_model_path)

    importance_frame = pd.DataFrame(
        {
            "feature": feature_names,
            "importance": xgb_model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)
    importance_frame.to_csv(importance_path, index=False, encoding="utf-8-sig")

    submission_frame = pd.DataFrame(
        {
            submission_id_column: test_ids if test_ids is not None else np.arange(len(test_idx), dtype=np.int64),
            submission_target_column: test_prob.astype(np.float32),
        }
    )
    submission_frame.to_csv(submission_path, index=False, encoding="utf-8")

    result = TabularTrainingResult(
        model_name="xgboost_lightgbm_tabular_blend",
        valid_auc=valid_auc,
        train_size=int(x_tr.shape[0]),
        valid_size=int(x_va.shape[0]),
        positive_ratio_train=float((y_tr == 1).mean()),
        feature_count=int(features.shape[1]),
        model_path=str(model_path),
        aux_model_path=str(aux_model_path),
        submission_path=str(submission_path),
        metrics_path=str(metrics_path),
        blend_rule=model_settings.blend.describe(),
    )
    metrics_path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
    return result
