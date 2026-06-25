from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(slots=True)
class DGraphRawData:
    x: np.ndarray
    y: np.ndarray
    edge_index: np.ndarray
    edge_type: np.ndarray
    edge_timestamp: np.ndarray
    train_idx: np.ndarray
    test_idx: np.ndarray
    valid_idx: np.ndarray | None = None
    node_timestamp: np.ndarray | None = None

    @property
    def num_nodes(self) -> int:
        return int(self.x.shape[0])


def _normalize_index_array(index_values: np.ndarray, num_nodes: int) -> np.ndarray:
    flat_values = np.asarray(index_values).reshape(-1)
    if flat_values.dtype == np.bool_:
        if flat_values.shape[0] != num_nodes:
            raise ValueError("Boolean split mask length does not match number of nodes.")
        return np.flatnonzero(flat_values).astype(np.int64)
    return flat_values.astype(np.int64)


def _resolve_split_indices(arrays: np.lib.npyio.NpzFile, num_nodes: int) -> tuple[np.ndarray, np.ndarray]:
    train_idx = _normalize_index_array(arrays["train_mask"], num_nodes)
    test_idx = _normalize_index_array(arrays["test_mask"], num_nodes)
    if "valid_mask" not in arrays:
        return train_idx, test_idx

    valid_idx = _normalize_index_array(arrays["valid_mask"], num_nodes)
    merged_train_idx = np.concatenate([train_idx, valid_idx]).astype(np.int64)
    return merged_train_idx, test_idx


def load_raw_data(
    data_path: Path,
    edge_timestamp_override: np.ndarray | None = None,
    node_timestamp: np.ndarray | None = None,
) -> DGraphRawData:
    arrays = np.load(data_path)
    num_nodes = int(arrays["x"].shape[0])
    train_idx, test_idx = _resolve_split_indices(arrays, num_nodes)
    edge_timestamp = edge_timestamp_override if edge_timestamp_override is not None else arrays["edge_timestamp"]
    return DGraphRawData(
        x=arrays["x"].astype(np.float32),
        y=arrays["y"].reshape(-1).astype(np.int64),
        edge_index=arrays["edge_index"].astype(np.int64),
        edge_type=arrays["edge_type"].reshape(-1).astype(np.int32),
        edge_timestamp=np.asarray(edge_timestamp).reshape(-1).astype(np.int32),
        train_idx=train_idx,
        test_idx=test_idx,
        node_timestamp=None if node_timestamp is None else np.asarray(node_timestamp).reshape(-1).astype(np.int32),
    )
