"""Dataset registry and dataset-specific loaders."""

from .loaders import TabularDataset, load_dataset_from_spec
from .registry import DATASET_SPECS, DatasetSpec, get_dataset_spec

__all__ = [
    "DATASET_SPECS",
    "DatasetSpec",
    "TabularDataset",
    "get_dataset_spec",
    "load_dataset_from_spec",
]
