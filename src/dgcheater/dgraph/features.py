from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np

from ..core.config import DEFAULT_CACHE_DIR
from .data import DGraphRawData


@dataclass(slots=True)
class FeatureBundle:
    features: np.ndarray
    feature_names: list[str]


FEATURE_CACHE_VERSION = "v3"


def feature_cache_path(cache_dir: Path, cache_key: str = "default") -> Path:
    return cache_dir / f"feature_bundle_{cache_key}_{FEATURE_CACHE_VERSION}.joblib"


def _safe_ratio(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    return (num / np.maximum(den, 1)).astype(np.float32)


def _neighbor_stat_features(
    x: np.ndarray,
    src: np.ndarray,
    dst: np.ndarray,
    degree: np.ndarray,
    base_dim: int | None = None,
) -> tuple[np.ndarray, list[str]]:
    feature_parts: list[np.ndarray] = []
    feature_names: list[str] = []
    base_dim = base_dim or x.shape[1]
    for idx in range(base_dim):
        values = x[:, idx].astype(np.float32)
        neighbor_sum = np.bincount(src, weights=values[dst], minlength=x.shape[0]) + np.bincount(
            dst, weights=values[src], minlength=x.shape[0]
        )
        neighbor_mean = _safe_ratio(neighbor_sum, degree)

        neighbor_max = np.full(x.shape[0], -np.inf, dtype=np.float32)
        np.maximum.at(neighbor_max, src, values[dst])
        np.maximum.at(neighbor_max, dst, values[src])
        neighbor_max[~np.isfinite(neighbor_max)] = 0.0

        neighbor_min = np.full(x.shape[0], np.inf, dtype=np.float32)
        np.minimum.at(neighbor_min, src, values[dst])
        np.minimum.at(neighbor_min, dst, values[src])
        neighbor_min[~np.isfinite(neighbor_min)] = 0.0

        feature_parts.append(np.stack([neighbor_max, neighbor_min, neighbor_mean], axis=1))
        feature_names.extend(
            [
                f"neighbor_feat_{idx}_max",
                f"neighbor_feat_{idx}_min",
                f"neighbor_feat_{idx}_mean",
            ]
        )

    return np.concatenate(feature_parts, axis=1).astype(np.float32), feature_names


def build_features(raw: DGraphRawData) -> FeatureBundle:
    x = raw.x
    y = raw.y
    src = raw.edge_index[:, 0]
    dst = raw.edge_index[:, 1]
    edge_type = raw.edge_type
    edge_ts = raw.edge_timestamp
    num_nodes = raw.num_nodes

    feature_parts: list[np.ndarray] = [x]
    feature_names = [f"node_feat_{idx}" for idx in range(x.shape[1])]

    base_dim = x.shape[1]
    missing_count = (x[:, :base_dim] == -1).sum(axis=1, keepdims=True).astype(np.float32)
    feature_parts.append(missing_count)
    feature_names.append("missing_value_count")

    in_degree = np.bincount(dst, minlength=num_nodes).astype(np.float32)
    out_degree = np.bincount(src, minlength=num_nodes).astype(np.float32)
    degree = in_degree + out_degree

    degree_features = np.stack(
        [
            in_degree,
            out_degree,
            degree,
            np.log1p(in_degree),
            np.log1p(out_degree),
            np.log1p(degree),
        ],
        axis=1,
    ).astype(np.float32)
    feature_parts.append(degree_features)
    feature_names.extend(
        [
            "in_degree",
            "out_degree",
            "total_degree",
            "log_in_degree",
            "log_out_degree",
            "log_total_degree",
        ]
    )

    num_edge_types = int(edge_type.max())
    type_out = np.zeros((num_nodes, num_edge_types), dtype=np.float32)
    type_in = np.zeros((num_nodes, num_edge_types), dtype=np.float32)
    for edge_value in range(1, num_edge_types + 1):
        mask = edge_type == edge_value
        type_out[:, edge_value - 1] = np.bincount(src[mask], minlength=num_nodes)
        type_in[:, edge_value - 1] = np.bincount(dst[mask], minlength=num_nodes)

    feature_parts.extend([type_out, type_in, type_out + type_in])
    feature_names.extend([f"edge_type_{idx}_out" for idx in range(1, num_edge_types + 1)])
    feature_names.extend([f"edge_type_{idx}_in" for idx in range(1, num_edge_types + 1)])
    feature_names.extend([f"edge_type_{idx}_total" for idx in range(1, num_edge_types + 1)])

    unique_type_features = np.stack(
        [
            (type_out > 0).sum(axis=1),
            (type_in > 0).sum(axis=1),
            ((type_out + type_in) > 0).sum(axis=1),
        ],
        axis=1,
    ).astype(np.float32)
    feature_parts.append(unique_type_features)
    feature_names.extend(
        [
            "unique_edge_type_out_count",
            "unique_edge_type_in_count",
            "unique_edge_type_total_count",
        ]
    )

    sum_out = np.bincount(src, weights=edge_ts, minlength=num_nodes).astype(np.float64)
    sum_in = np.bincount(dst, weights=edge_ts, minlength=num_nodes).astype(np.float64)
    mean_out = _safe_ratio(sum_out, out_degree)
    mean_in = _safe_ratio(sum_in, in_degree)
    mean_total = _safe_ratio(sum_out + sum_in, degree)

    min_ts = np.full(num_nodes, np.iinfo(np.int32).max, dtype=np.int32)
    max_ts = np.zeros(num_nodes, dtype=np.int32)
    np.minimum.at(min_ts, src, edge_ts)
    np.minimum.at(min_ts, dst, edge_ts)
    np.maximum.at(max_ts, src, edge_ts)
    np.maximum.at(max_ts, dst, edge_ts)
    min_ts = min_ts.astype(np.float32)
    min_ts[min_ts > 1e8] = 0.0
    max_ts = max_ts.astype(np.float32)
    time_span = (max_ts - min_ts).astype(np.float32)

    time_features = np.stack(
        [
            mean_out,
            mean_in,
            mean_total,
            min_ts,
            max_ts,
            time_span,
        ],
        axis=1,
    ).astype(np.float32)
    feature_parts.append(time_features)
    feature_names.extend(
        [
            "mean_out_timestamp",
            "mean_in_timestamp",
            "mean_total_timestamp",
            "min_timestamp",
            "max_timestamp",
            "timestamp_span",
        ]
    )

    label2 = (y == 2).astype(np.float32)
    label3 = (y == 3).astype(np.float32)
    neighbor_label2 = np.bincount(src, weights=label2[dst], minlength=num_nodes) + np.bincount(
        dst, weights=label2[src], minlength=num_nodes
    )
    neighbor_label3 = np.bincount(src, weights=label3[dst], minlength=num_nodes) + np.bincount(
        dst, weights=label3[src], minlength=num_nodes
    )
    label_stats = np.stack(
        [
            neighbor_label2.astype(np.float32),
            neighbor_label3.astype(np.float32),
            _safe_ratio(neighbor_label2, degree),
            _safe_ratio(neighbor_label3, degree),
        ],
        axis=1,
    ).astype(np.float32)
    feature_parts.append(label_stats)
    feature_names.extend(
        [
            "neighbor_label2_count",
            "neighbor_label3_count",
            "neighbor_label2_ratio",
            "neighbor_label3_ratio",
        ]
    )

    neighbor_stat_matrix, neighbor_stat_names = _neighbor_stat_features(x, src, dst, degree, base_dim=base_dim)
    feature_parts.append(neighbor_stat_matrix)
    feature_names.extend(neighbor_stat_names)

    features = np.concatenate(feature_parts, axis=1).astype(np.float32)
    return FeatureBundle(features=features, feature_names=feature_names)


def build_features_for_nodes(raw: DGraphRawData, nodes: np.ndarray) -> FeatureBundle:
    nodes = np.asarray(nodes, dtype=np.int64)
    x = raw.x
    y = raw.y
    src = raw.edge_index[:, 0]
    dst = raw.edge_index[:, 1]
    edge_type = raw.edge_type
    edge_ts = raw.edge_timestamp
    num_nodes = raw.num_nodes

    node_x = x[nodes].astype(np.float32)
    feature_parts: list[np.ndarray] = [node_x]
    feature_names = [f"node_feat_{idx}" for idx in range(x.shape[1])]

    base_dim = x.shape[1]
    missing_count = (node_x[:, :base_dim] == -1).sum(axis=1, keepdims=True).astype(np.float32)
    feature_parts.append(missing_count)
    feature_names.append("missing_value_count")

    in_degree = np.bincount(dst, minlength=num_nodes).astype(np.float32)
    out_degree = np.bincount(src, minlength=num_nodes).astype(np.float32)
    degree = in_degree + out_degree
    node_in = in_degree[nodes]
    node_out = out_degree[nodes]
    node_degree = degree[nodes]

    degree_features = np.stack(
        [
            node_in,
            node_out,
            node_degree,
            np.log1p(node_in),
            np.log1p(node_out),
            np.log1p(node_degree),
        ],
        axis=1,
    ).astype(np.float32)
    feature_parts.append(degree_features)
    feature_names.extend(
        [
            "in_degree",
            "out_degree",
            "total_degree",
            "log_in_degree",
            "log_out_degree",
            "log_total_degree",
        ]
    )

    num_edge_types = int(edge_type.max())
    type_out = np.zeros((nodes.shape[0], num_edge_types), dtype=np.float32)
    type_in = np.zeros((nodes.shape[0], num_edge_types), dtype=np.float32)
    for edge_value in range(1, num_edge_types + 1):
        mask = edge_type == edge_value
        out_counts = np.bincount(src[mask], minlength=num_nodes)
        in_counts = np.bincount(dst[mask], minlength=num_nodes)
        type_out[:, edge_value - 1] = out_counts[nodes]
        type_in[:, edge_value - 1] = in_counts[nodes]

    feature_parts.extend([type_out, type_in, type_out + type_in])
    feature_names.extend([f"edge_type_{idx}_out" for idx in range(1, num_edge_types + 1)])
    feature_names.extend([f"edge_type_{idx}_in" for idx in range(1, num_edge_types + 1)])
    feature_names.extend([f"edge_type_{idx}_total" for idx in range(1, num_edge_types + 1)])

    unique_type_features = np.stack(
        [
            (type_out > 0).sum(axis=1),
            (type_in > 0).sum(axis=1),
            ((type_out + type_in) > 0).sum(axis=1),
        ],
        axis=1,
    ).astype(np.float32)
    feature_parts.append(unique_type_features)
    feature_names.extend(
        [
            "unique_edge_type_out_count",
            "unique_edge_type_in_count",
            "unique_edge_type_total_count",
        ]
    )

    sum_out = np.bincount(src, weights=edge_ts, minlength=num_nodes).astype(np.float64)
    sum_in = np.bincount(dst, weights=edge_ts, minlength=num_nodes).astype(np.float64)
    mean_out = _safe_ratio(sum_out[nodes], node_out)
    mean_in = _safe_ratio(sum_in[nodes], node_in)
    mean_total = _safe_ratio(sum_out[nodes] + sum_in[nodes], node_degree)

    min_ts = np.full(num_nodes, np.iinfo(np.int32).max, dtype=np.int32)
    max_ts = np.zeros(num_nodes, dtype=np.int32)
    np.minimum.at(min_ts, src, edge_ts)
    np.minimum.at(min_ts, dst, edge_ts)
    np.maximum.at(max_ts, src, edge_ts)
    np.maximum.at(max_ts, dst, edge_ts)
    node_min_ts = min_ts[nodes].astype(np.float32)
    node_min_ts[node_min_ts > 1e8] = 0.0
    node_max_ts = max_ts[nodes].astype(np.float32)
    time_span = (node_max_ts - node_min_ts).astype(np.float32)

    time_features = np.stack(
        [
            mean_out,
            mean_in,
            mean_total,
            node_min_ts,
            node_max_ts,
            time_span,
        ],
        axis=1,
    ).astype(np.float32)
    feature_parts.append(time_features)
    feature_names.extend(
        [
            "mean_out_timestamp",
            "mean_in_timestamp",
            "mean_total_timestamp",
            "min_timestamp",
            "max_timestamp",
            "timestamp_span",
        ]
    )

    label2 = (y == 2).astype(np.float32)
    label3 = (y == 3).astype(np.float32)
    neighbor_label2 = np.bincount(src, weights=label2[dst], minlength=num_nodes) + np.bincount(
        dst, weights=label2[src], minlength=num_nodes
    )
    neighbor_label3 = np.bincount(src, weights=label3[dst], minlength=num_nodes) + np.bincount(
        dst, weights=label3[src], minlength=num_nodes
    )
    label_stats = np.stack(
        [
            neighbor_label2[nodes].astype(np.float32),
            neighbor_label3[nodes].astype(np.float32),
            _safe_ratio(neighbor_label2[nodes], node_degree),
            _safe_ratio(neighbor_label3[nodes], node_degree),
        ],
        axis=1,
    ).astype(np.float32)
    feature_parts.append(label_stats)
    feature_names.extend(
        [
            "neighbor_label2_count",
            "neighbor_label3_count",
            "neighbor_label2_ratio",
            "neighbor_label3_ratio",
        ]
    )

    neighbor_parts: list[np.ndarray] = []
    neighbor_names: list[str] = []
    for idx in range(base_dim):
        values = x[:, idx].astype(np.float32)
        neighbor_sum = np.bincount(src, weights=values[dst], minlength=num_nodes) + np.bincount(
            dst, weights=values[src], minlength=num_nodes
        )
        neighbor_mean = _safe_ratio(neighbor_sum[nodes], node_degree)

        neighbor_max = np.full(num_nodes, -np.inf, dtype=np.float32)
        np.maximum.at(neighbor_max, src, values[dst])
        np.maximum.at(neighbor_max, dst, values[src])
        node_neighbor_max = neighbor_max[nodes]
        node_neighbor_max[~np.isfinite(node_neighbor_max)] = 0.0

        neighbor_min = np.full(num_nodes, np.inf, dtype=np.float32)
        np.minimum.at(neighbor_min, src, values[dst])
        np.minimum.at(neighbor_min, dst, values[src])
        node_neighbor_min = neighbor_min[nodes]
        node_neighbor_min[~np.isfinite(node_neighbor_min)] = 0.0

        neighbor_parts.append(np.stack([node_neighbor_max, node_neighbor_min, neighbor_mean], axis=1))
        neighbor_names.extend(
            [
                f"neighbor_feat_{idx}_max",
                f"neighbor_feat_{idx}_min",
                f"neighbor_feat_{idx}_mean",
            ]
        )

    feature_parts.append(np.concatenate(neighbor_parts, axis=1).astype(np.float32))
    feature_names.extend(neighbor_names)

    features = np.concatenate(feature_parts, axis=1).astype(np.float32)
    return FeatureBundle(features=features, feature_names=feature_names)


def get_or_create_feature_cache(
    raw: DGraphRawData,
    cache_dir: Path | None = None,
    cache_key: str = "default",
) -> FeatureBundle:
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = feature_cache_path(cache_dir, cache_key)
    if cache_file.exists():
        return joblib.load(cache_file)
    bundle = build_features(raw)
    joblib.dump(bundle, cache_file)
    return bundle
