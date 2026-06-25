from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..dgraph.data import DGraphRawData


def load_amlsim_sample_dataset(sample_dir: Path) -> DGraphRawData:
    accounts = pd.read_csv(sample_dir / "accounts.csv")
    transactions = pd.read_csv(sample_dir / "tx.csv")

    account_ids = accounts["ACCOUNT_ID"].to_numpy(dtype=np.int64)
    id_to_pos = {acc_id: idx for idx, acc_id in enumerate(account_ids.tolist())}

    base_numeric = accounts[["init_balance", "start", "end", "modelID"]].to_numpy(dtype=np.float32)
    business_flag = (accounts["business"] == "I").astype(np.float32).to_numpy().reshape(-1, 1)
    suspicious_flag = accounts["suspicious"].astype(str).str.lower().eq("true").astype(np.float32).to_numpy().reshape(-1, 1)
    x = np.concatenate([base_numeric, business_flag, suspicious_flag], axis=1).astype(np.float32)

    y = accounts["isFraud"].astype(str).str.lower().eq("true").astype(np.int64).to_numpy()

    src = transactions["ACCOUNT_ID"].map(id_to_pos).to_numpy(dtype=np.int64)
    dst = transactions["COUNTER_PARTY_ACCOUNT_NUM"].map(id_to_pos).to_numpy(dtype=np.int64)
    edge_index = np.stack([src, dst], axis=1)

    tx_type_codes = pd.Categorical(transactions["TXN_SOURCE_TYPE_CODE"])
    edge_type = tx_type_codes.codes.astype(np.int32) + 1
    edge_timestamp = transactions["start"].to_numpy(dtype=np.int32)

    rng = np.random.default_rng(42)
    fraud_idx = np.where(y == 1)[0]
    normal_idx = np.where(y == 0)[0]
    rng.shuffle(fraud_idx)
    rng.shuffle(normal_idx)
    train_fraud = fraud_idx[: max(1, int(len(fraud_idx) * 0.7))]
    test_fraud = fraud_idx[max(1, int(len(fraud_idx) * 0.7)) :]
    train_normal = normal_idx[: max(1, int(len(normal_idx) * 0.7))]
    test_normal = normal_idx[max(1, int(len(normal_idx) * 0.7)) :]
    train_idx = np.concatenate([train_fraud, train_normal]).astype(np.int64)
    test_idx = np.concatenate([test_fraud, test_normal]).astype(np.int64)

    return DGraphRawData(
        x=x,
        y=y,
        edge_index=edge_index,
        edge_type=edge_type,
        edge_timestamp=edge_timestamp,
        train_idx=train_idx,
        test_idx=test_idx,
    )
