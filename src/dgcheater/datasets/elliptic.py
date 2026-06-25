from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..dgraph.data import DGraphRawData
from .common import ensure_zip_extracted, find_first_existing_path


def resolve_elliptic_pp_dir(input_path: Path) -> Path:
    expected_files = [
        "wallets_features.csv",
        "wallets_classes.csv",
        "AddrAddr_edgelist.csv",
    ]
    if input_path.is_file() and input_path.suffix.lower() == ".zip":
        return ensure_zip_extracted(input_path, expected_files)
    if input_path.is_dir():
        zip_candidates = [
            input_path / "drive-download-20260529T023527Z-3-001.zip",
            input_path / "drive-download-20260529T023527Z-3-002.zip",
        ]
        found_zip = any(candidate.exists() for candidate in zip_candidates)
        if found_zip:
            for candidate, files in [
                (zip_candidates[0], ["wallets_features.csv", "wallets_classes.csv"]),
                (zip_candidates[1], ["AddrAddr_edgelist.csv"]),
            ]:
                if candidate.exists():
                    ensure_zip_extracted(candidate, files)
            return input_path
        return input_path
    raise FileNotFoundError(f"Could not resolve EllipticPlusPlus dataset from {input_path}")


def load_elliptic_pp_dataset(path: Path) -> DGraphRawData:
    dataset_dir = resolve_elliptic_pp_dir(path)
    zip1_dir = dataset_dir / "drive-download-20260529T023527Z-3-001"
    zip2_dir = dataset_dir / "drive-download-20260529T023527Z-3-002"

    wallets_features_path = find_first_existing_path(
        [
            dataset_dir / "wallets_features.csv",
            zip1_dir / "wallets_features.csv",
        ]
    )
    wallets_classes_path = find_first_existing_path(
        [
            dataset_dir / "wallets_classes.csv",
            zip1_dir / "wallets_classes.csv",
        ]
    )
    addr_addr_path = find_first_existing_path(
        [
            dataset_dir / "AddrAddr_edgelist.csv",
            zip2_dir / "AddrAddr_edgelist.csv",
        ]
    )
    if wallets_features_path is None or wallets_classes_path is None or addr_addr_path is None:
        raise FileNotFoundError("EllipticPlusPlus requires wallets_features.csv, wallets_classes.csv and AddrAddr_edgelist.csv.")

    wallets_features = pd.read_csv(wallets_features_path)
    wallets_classes = pd.read_csv(wallets_classes_path)
    addr_edges = pd.read_csv(addr_addr_path)

    aggregation_map = {
        column: "max"
        for column in wallets_features.columns
        if column not in {"address", "Time step"}
    }
    aggregation_map["Time step"] = "max"
    aggregated_features = wallets_features.groupby("address", sort=False, as_index=False).agg(aggregation_map)
    merged = aggregated_features.merge(wallets_classes, on="address", how="inner", copy=False)
    merged = merged.drop_duplicates(subset="address", keep="first").reset_index(drop=True)

    feature_frame = merged.drop(columns=["address", "class", "Time step"]).astype(np.float32)
    x = feature_frame.to_numpy(dtype=np.float32)

    raw_class = merged["class"].to_numpy(dtype=np.int64)
    y = np.full(raw_class.shape[0], 3, dtype=np.int64)
    y[raw_class == 1] = 1
    y[raw_class == 2] = 0

    address_ids = merged["address"].tolist()
    id_to_pos = {address: idx for idx, address in enumerate(address_ids)}

    src = addr_edges["input_address"].map(id_to_pos)
    dst = addr_edges["output_address"].map(id_to_pos)
    valid_mask = src.notna() & dst.notna()
    src_idx = src[valid_mask].to_numpy(dtype=np.int64)
    dst_idx = dst[valid_mask].to_numpy(dtype=np.int64)
    edge_index = np.stack([src_idx, dst_idx], axis=1)
    edge_type = np.ones(edge_index.shape[0], dtype=np.int32)

    edge_timestamp = np.zeros(edge_index.shape[0], dtype=np.int32)

    time_step = merged["Time step"].to_numpy(dtype=np.int64)
    labeled_mask = y != 3
    labeled_time = time_step[labeled_mask]
    cutoff = int(np.quantile(labeled_time, 0.8))
    train_idx = np.flatnonzero((y != 3) & (time_step <= cutoff)).astype(np.int64)
    valid_idx = np.flatnonzero((y != 3) & (time_step > cutoff)).astype(np.int64)
    test_idx = valid_idx.copy()

    if np.unique(y[train_idx]).shape[0] < 2 or np.unique(y[valid_idx]).shape[0] < 2:
        raise ValueError("EllipticPlusPlus time split produced a single-class train or test partition.")

    return DGraphRawData(
        x=x,
        y=y,
        edge_index=edge_index,
        edge_type=edge_type,
        edge_timestamp=edge_timestamp,
        train_idx=train_idx,
        test_idx=test_idx,
        valid_idx=valid_idx,
    )
