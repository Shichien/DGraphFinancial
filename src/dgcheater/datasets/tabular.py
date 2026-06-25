from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .common import TabularDataset, ensure_zip_extracted


def resolve_ieee_cis_dir(input_path: Path) -> Path:
    expected_files = [
        "train_transaction.csv",
        "train_identity.csv",
        "test_transaction.csv",
        "test_identity.csv",
        "sample_submission.csv",
    ]
    if input_path.is_file() and input_path.suffix.lower() == ".zip":
        return ensure_zip_extracted(input_path, expected_files)
    if input_path.is_dir():
        zip_candidate = input_path / "ieee-fraud-detection.zip"
        if zip_candidate.exists():
            return ensure_zip_extracted(zip_candidate, expected_files)
        return input_path
    raise FileNotFoundError(f"Could not resolve IEEE-CIS dataset from {input_path}")


def factorize_mixed_columns(frame: pd.DataFrame) -> pd.DataFrame:
    transformed = frame.copy()
    for column in transformed.columns:
        series = transformed[column]
        if pd.api.types.is_numeric_dtype(series):
            transformed[column] = series.fillna(-1)
            continue

        filled = series.astype("string").fillna("<NA>")
        codes, _ = pd.factorize(filled, sort=True)
        transformed[column] = codes.astype(np.int32)
    return transformed


def build_tabular_dataset_from_csv(
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    label_column: str,
) -> TabularDataset:
    feature_names = [col for col in train_frame.columns if col != label_column]
    x = pd.concat([train_frame[feature_names], test_frame[feature_names]], axis=0, ignore_index=True).to_numpy(dtype=np.float32)
    y = pd.concat([train_frame[label_column], pd.Series([-100] * len(test_frame))], axis=0, ignore_index=True).to_numpy(dtype=np.int64)
    train_idx = np.arange(len(train_frame), dtype=np.int64)
    test_idx = np.arange(len(train_frame), len(train_frame) + len(test_frame), dtype=np.int64)
    return TabularDataset(
        x=x,
        y=y,
        train_idx=train_idx,
        test_idx=test_idx,
        feature_names=feature_names,
    )


def load_ieee_cis_dataset(path: Path) -> TabularDataset:
    dataset_dir = resolve_ieee_cis_dir(path)

    train_transaction = pd.read_csv(dataset_dir / "train_transaction.csv")
    train_identity = pd.read_csv(dataset_dir / "train_identity.csv")
    test_transaction = pd.read_csv(dataset_dir / "test_transaction.csv")
    test_identity = pd.read_csv(dataset_dir / "test_identity.csv")

    train_frame = train_transaction.merge(train_identity, on="TransactionID", how="left", copy=False)
    test_frame = test_transaction.merge(test_identity, on="TransactionID", how="left", copy=False)

    test_ids = test_frame["TransactionID"].to_numpy(dtype=np.int64)

    drop_columns = ["TransactionID", "isFraud"]
    train_features = train_frame.drop(columns=drop_columns)
    test_features = test_frame.drop(columns=["TransactionID"])
    combined_features = pd.concat([train_features, test_features], axis=0, ignore_index=True)
    combined_features = factorize_mixed_columns(combined_features)

    split_point = len(train_features)
    encoded_train = combined_features.iloc[:split_point].reset_index(drop=True)
    encoded_test = combined_features.iloc[split_point:].reset_index(drop=True)

    dataset = build_tabular_dataset_from_csv(
        train_frame=pd.concat([encoded_train, train_frame["isFraud"].reset_index(drop=True)], axis=1),
        test_frame=encoded_test,
        label_column="isFraud",
    )
    sorted_train_idx = train_frame["TransactionDT"].sort_values(kind="mergesort").index.to_numpy(dtype=np.int64)
    valid_start = int(len(sorted_train_idx) * 0.9)
    dataset.train_idx = sorted_train_idx[:valid_start]
    dataset.valid_idx = sorted_train_idx[valid_start:]
    dataset.test_ids = test_ids
    dataset.submission_id_column = "TransactionID"
    dataset.submission_target_column = "isFraud"
    return dataset
