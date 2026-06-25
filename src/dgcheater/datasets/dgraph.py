from __future__ import annotations

from pathlib import Path

import numpy as np

from ..core.config import APP_CONFIG
from ..dgraph.data import DGraphRawData, load_raw_data
from .common import ensure_zip_extracted, find_first_existing_path


def resolve_dgraph_fin_npz(input_path: Path) -> Path:
    candidates: list[Path] = []
    if input_path.is_file():
        if input_path.suffix.lower() == ".npz":
            return input_path
        if input_path.name.lower() == "dgraphfin.zip":
            extracted_dir = ensure_zip_extracted(input_path, ["dgraphfin.npz"])
            candidates.extend(
                [
                    extracted_dir / "dgraphfin.npz",
                    extracted_dir / "DGraphFin" / "dgraphfin.npz",
                ]
            )
        candidates.append(input_path.parent / "dgraphfin.npz")
    else:
        zip_candidate = input_path / "DGraphFin.zip"
        if zip_candidate.exists():
            extracted_dir = ensure_zip_extracted(zip_candidate, ["dgraphfin.npz"])
            candidates.extend(
                [
                    extracted_dir / "dgraphfin.npz",
                    extracted_dir / "DGraphFin" / "dgraphfin.npz",
                ]
            )
        candidates.extend(
            [
                input_path / "dgraphfin.npz",
                input_path / "DGraphFin" / "dgraphfin.npz",
                input_path / "raw" / "DGraphFin" / "dgraphfin.npz",
            ]
        )

    resolved = find_first_existing_path(candidates)
    if resolved is None:
        checked = "\n".join(str(path) for path in candidates)
        raise FileNotFoundError("Could not locate dgraphfin.npz. Checked:\n" f"{checked}")
    return resolved


def resolve_dgraph_fin2_dir(input_path: Path) -> Path:
    if input_path.is_dir():
        zip_candidate = input_path / "DGraphFin2.zip"
        if zip_candidate.exists():
            return ensure_zip_extracted(
                zip_candidate,
                ["dgraphfinv2_edge_timestamp.npy", "dgraphfinv2_node_timestamp.npy"],
            )
        return input_path
    if input_path.is_file() and input_path.suffix.lower() == ".zip":
        return ensure_zip_extracted(
            input_path,
            ["dgraphfinv2_edge_timestamp.npy", "dgraphfinv2_node_timestamp.npy"],
        )
    raise FileNotFoundError(f"Could not resolve extracted DGraph-Fin2 directory from {input_path}")


def load_dgraph_fin_dataset(path: Path) -> DGraphRawData:
    npz_path = resolve_dgraph_fin_npz(path)
    return load_raw_data(npz_path)


def load_dgraph_fin2_dataset(path: Path) -> DGraphRawData:
    fin2_dir = resolve_dgraph_fin2_dir(path)
    edge_ts_path = fin2_dir / "dgraphfinv2_edge_timestamp.npy"
    node_ts_path = fin2_dir / "dgraphfinv2_node_timestamp.npy"
    if not edge_ts_path.exists() or not node_ts_path.exists():
        raise FileNotFoundError(
            "DGraph-Fin2 extracted directory must contain dgraphfinv2_edge_timestamp.npy "
            "and dgraphfinv2_node_timestamp.npy."
        )

    base_candidates = [
        fin2_dir.parent / "DGraphFin.zip",
        fin2_dir.parent / "dgraphfin.npz",
        fin2_dir.parent / "dgraph_fin" / "dgraphfin.npz",
        fin2_dir.parent / "DGraphFin" / "dgraphfin.npz",
        fin2_dir.parent / "DGraphFin1" / "dgraphfin.npz",
        APP_CONFIG.dataset_path("dgraph_fin"),
        APP_CONFIG.dataset_path("dgraph_fin") / "dgraphfin.npz",
        APP_CONFIG.dataset_path("dgraph_fin").parent / "DGraphFin.zip",
    ]
    resolved_base_candidates: list[Path] = []
    for candidate in base_candidates:
        if candidate.name.lower() == "dgraphfin.zip" and candidate.exists():
            extracted_dir = ensure_zip_extracted(candidate, ["dgraphfin.npz"])
            resolved_base_candidates.extend(
                [
                    extracted_dir / "dgraphfin.npz",
                    extracted_dir / "DGraphFin" / "dgraphfin.npz",
                ]
            )
        else:
            resolved_base_candidates.append(candidate)
    base_npz_path = find_first_existing_path(resolved_base_candidates)
    if base_npz_path is None:
        checked = "\n".join(str(path) for path in resolved_base_candidates)
        raise FileNotFoundError(
            "DGraph-Fin2 requires the base DGraph-Fin graph file dgraphfin.npz. "
            "Please place it beside the extracted Fin2 folder or under one of these paths:\n"
            f"{checked}"
        )

    edge_timestamp = np.load(edge_ts_path, allow_pickle=True)
    node_timestamp = np.load(node_ts_path, allow_pickle=True)
    return load_raw_data(
        base_npz_path,
        edge_timestamp_override=edge_timestamp,
        node_timestamp=node_timestamp,
    )
