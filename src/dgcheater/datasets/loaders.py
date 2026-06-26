from __future__ import annotations

from pathlib import Path

from ..dgraph.data import DGraphRawData, load_raw_data
from .amlsim import load_amlsim_sample_dataset
from .common import TabularDataset
from .dgraph import load_dgraph_fin2_dataset, load_dgraph_fin_dataset
from .elliptic import load_elliptic_pp_dataset
from .registry import DatasetSpec
from .tabular import build_tabular_dataset_from_csv, load_ieee_cis_dataset


def load_dataset_from_spec(spec: DatasetSpec, data_path: Path | None = None) -> DGraphRawData | TabularDataset:
    path = data_path or spec.default_path
    if path is None:
        raise FileNotFoundError(f"{spec.display_name} has no local default path configured.")

    if spec.key == "dgraph_fin":
        return load_dgraph_fin_dataset(path)
    if spec.key == "dgraph_fin2":
        return load_dgraph_fin2_dataset(path)
    if spec.key == "ieee_cis":
        return load_ieee_cis_dataset(path)
    if spec.key == "elliptic_pp":
        return load_elliptic_pp_dataset(path)
    if spec.key == "amlsim_sample":
        return load_amlsim_sample_dataset(path)

    raise NotImplementedError(
        f"{spec.display_name} is registered but not yet locally materialized. "
        f"Expected format: {spec.format}. Source: {spec.source_url}"
    )


__all__ = [
    "TabularDataset",
    "build_tabular_dataset_from_csv",
    "load_dataset_from_spec",
    "load_dgraph_fin_dataset",
    "load_dgraph_fin2_dataset",
    "load_ieee_cis_dataset",
    "load_elliptic_pp_dataset",
    "load_amlsim_sample_dataset",
]
