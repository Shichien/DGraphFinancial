from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..core.config import APP_CONFIG


@dataclass(slots=True)
class DatasetSpec:
    key: str
    display_name: str
    problem_type: str
    format: str
    source_url: str
    default_path: Path | None
    download_required: bool
    login_required: bool
    notes: str


DATASET_SPECS: dict[str, DatasetSpec] = {
    "dgraph_fin": DatasetSpec(
        key="dgraph_fin",
        display_name="DGraph-Fin",
        problem_type="graph_binary_node_classification",
        format="npz_or_extracted_zip",
        source_url="https://dgraph.xinye.com/dataset",
        default_path=APP_CONFIG.dataset_path("dgraph_fin"),
        download_required=True,
        login_required=True,
        notes="Official base graph dataset. Loader accepts dgraphfin.npz or an extracted DGraphFin directory.",
    ),
    "dgraph_fin2": DatasetSpec(
        key="dgraph_fin2",
        display_name="DGraph-Fin2",
        problem_type="graph_temporal_node_classification",
        format="extracted_timestamp_pack_plus_base_npz",
        source_url="https://dgraph.xinye.com/dataset",
        default_path=APP_CONFIG.dataset_path("dgraph_fin2"),
        download_required=True,
        login_required=True,
        notes="Official temporal extension package. Requires dgraphfinv2 edge and node timestamp files plus base dgraphfin.npz from DGraph-Fin.",
    ),
    "ieee_cis": DatasetSpec(
        key="ieee_cis",
        display_name="IEEE-CIS Fraud Detection",
        problem_type="tabular_binary_classification",
        format="csv",
        source_url="https://www.kaggle.com/c/ieee-fraud-detection",
        default_path=APP_CONFIG.dataset_path("ieee_cis"),
        download_required=True,
        login_required=True,
        notes="Kaggle competition dataset focused on transaction fraud detection.",
    ),
    "elliptic_pp": DatasetSpec(
        key="elliptic_pp",
        display_name="Elliptic++",
        problem_type="graph_binary_node_classification",
        format="csv",
        source_url="https://github.com/git-disl/EllipticPlusPlus",
        default_path=APP_CONFIG.dataset_path("elliptic_pp"),
        download_required=True,
        login_required=False,
        notes="Public anti-money laundering graph benchmark derived from blockchain transaction data.",
    ),
    "ibm_aml": DatasetSpec(
        key="ibm_aml",
        display_name="IBM Synthetic AML",
        problem_type="tabular_or_graph_binary_classification",
        format="csv",
        source_url="https://research.ibm.com/publications/realistic-synthetic-financial-transactions-for-anti-money-laundering-models",
        default_path=APP_CONFIG.dataset_path("ibm_aml"),
        download_required=True,
        login_required=False,
        notes="Synthetic AML-style transaction data suitable for simulator and system-design sections.",
    ),
    "amlsim_sample": DatasetSpec(
        key="amlsim_sample",
        display_name="AMLSim Sample",
        problem_type="graph_binary_node_classification",
        format="csv",
        source_url="https://github.com/IBM/AMLSim",
        default_path=APP_CONFIG.dataset_path("amlsim_sample"),
        download_required=False,
        login_required=False,
        notes="Small built-in AMLSim sample output with account labels and transaction edges.",
    ),
}


def get_dataset_spec(dataset_key: str) -> DatasetSpec:
    try:
        return DATASET_SPECS[dataset_key]
    except KeyError as exc:
        valid = ", ".join(sorted(DATASET_SPECS))
        raise KeyError(f"Unknown dataset '{dataset_key}'. Valid options: {valid}") from exc
