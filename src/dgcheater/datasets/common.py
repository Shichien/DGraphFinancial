from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import zipfile

import numpy as np


@dataclass(slots=True)
class TabularDataset:
    x: np.ndarray
    y: np.ndarray
    train_idx: np.ndarray
    test_idx: np.ndarray
    feature_names: list[str]
    valid_idx: np.ndarray | None = None
    test_ids: np.ndarray | None = None
    submission_id_column: str | None = None
    submission_target_column: str | None = None


def find_first_existing_path(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def ensure_zip_extracted(zip_path: Path, expected_files: list[str]) -> Path:
    extract_dir = zip_path.parent / zip_path.stem
    if all((extract_dir / name).exists() for name in expected_files):
        return extract_dir

    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_dir)
    return extract_dir
