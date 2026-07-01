from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
import os
import tomllib


CONFIG_ENV_VAR = "DGC_CONFIG_PATH"


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    data_root: Path
    output_dir: Path
    cache_dir: Path
    model_dir: Path
    metrics_dir: Path
    submission_dir: Path
    figure_dir: Path

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ProjectPaths":
        return cls(
            data_root=Path(data["data_root"]),
            output_dir=Path(data["output_dir"]),
            cache_dir=Path(data["cache_dir"]),
            model_dir=Path(data["model_dir"]),
            metrics_dir=Path(data["metrics_dir"]),
            submission_dir=Path(data["submission_dir"]),
            figure_dir=Path(data["figure_dir"]),
        )


@dataclass(frozen=True, slots=True)
class TrainingSettings:
    default_dataset: str
    seed: int
    valid_size: float
    use_cached_features: bool

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "TrainingSettings":
        return cls(
            default_dataset=str(data["default_dataset"]),
            seed=int(data["seed"]),
            valid_size=float(data["valid_size"]),
            use_cached_features=bool(data["use_cached_features"]),
        )


@dataclass(frozen=True, slots=True)
class ReportingSettings:
    metrics_path: Path
    output_path: Path
    importance_path: Path
    importance_output_path: Path
    top_feature_count: int

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ReportingSettings":
        return cls(
            metrics_path=Path(data["metrics_path"]),
            output_path=Path(data["output_path"]),
            importance_path=Path(data["importance_path"]),
            importance_output_path=Path(data["importance_output_path"]),
            top_feature_count=int(data["top_feature_count"]),
        )


@dataclass(frozen=True, slots=True)
class RiskLevel:
    level: str
    threshold: float
    action: str

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "RiskLevel":
        return cls(
            level=str(data["level"]),
            threshold=float(data["threshold"]),
            action=str(data["action"]),
        )


@dataclass(frozen=True, slots=True)
class LightGBMSettings:
    n_estimators: int
    learning_rate: float
    num_leaves: int
    subsample: float
    colsample_bytree: float
    reg_lambda: float
    n_jobs: int
    verbose: int

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "LightGBMSettings":
        return cls(
            n_estimators=int(data["n_estimators"]),
            learning_rate=float(data["learning_rate"]),
            num_leaves=int(data["num_leaves"]),
            subsample=float(data["subsample"]),
            colsample_bytree=float(data["colsample_bytree"]),
            reg_lambda=float(data["reg_lambda"]),
            n_jobs=int(data["n_jobs"]),
            verbose=int(data["verbose"]),
        )


@dataclass(frozen=True, slots=True)
class XGBoostSettings:
    n_estimators: int
    max_depth: int
    learning_rate: float
    subsample: float
    colsample_bytree: float
    tree_method: str
    n_jobs: int

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "XGBoostSettings":
        return cls(
            n_estimators=int(data["n_estimators"]),
            max_depth=int(data["max_depth"]),
            learning_rate=float(data["learning_rate"]),
            subsample=float(data["subsample"]),
            colsample_bytree=float(data["colsample_bytree"]),
            tree_method=str(data["tree_method"]),
            n_jobs=int(data["n_jobs"]),
        )


@dataclass(frozen=True, slots=True)
class BlendSettings:
    xgboost_weight: float
    lightgbm_weight: float

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "BlendSettings":
        return cls(
            xgboost_weight=float(data["xgboost_weight"]),
            lightgbm_weight=float(data["lightgbm_weight"]),
        )

    def describe(self) -> str:
        return f"{self.xgboost_weight:g} * xgboost + {self.lightgbm_weight:g} * lightgbm"


@dataclass(frozen=True, slots=True)
class ModelGroupSettings:
    lightgbm: LightGBMSettings
    xgboost: XGBoostSettings
    blend: BlendSettings

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ModelGroupSettings":
        return cls(
            lightgbm=LightGBMSettings.from_mapping(data["lightgbm"]),
            xgboost=XGBoostSettings.from_mapping(data["xgboost"]),
            blend=BlendSettings.from_mapping(data["blend"]),
        )


@dataclass(frozen=True, slots=True)
class ModelSettings:
    graph: ModelGroupSettings
    tabular: ModelGroupSettings

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ModelSettings":
        return cls(
            graph=ModelGroupSettings.from_mapping(data["graph"]),
            tabular=ModelGroupSettings.from_mapping(data["tabular"]),
        )


@dataclass(frozen=True, slots=True)
class AppConfig:
    paths: ProjectPaths
    datasets: dict[str, Path]
    training: TrainingSettings
    reporting: ReportingSettings
    risk_levels: tuple[RiskLevel, ...]
    models: ModelSettings

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "AppConfig":
        return cls(
            paths=ProjectPaths.from_mapping(data["paths"]),
            datasets={key: Path(value) for key, value in data["datasets"].items()},
            training=TrainingSettings.from_mapping(data["training"]),
            reporting=ReportingSettings.from_mapping(data["reporting"]),
            risk_levels=tuple(RiskLevel.from_mapping(item) for item in data["risk_levels"]),
            models=ModelSettings.from_mapping(data["models"]),
        )

    def dataset_path(self, dataset_key: str) -> Path:
        return self.datasets[dataset_key]


def _find_config_path(config_path: Path | str | None) -> Path:
    if config_path is not None:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(path)
        return path

    env_path = os.getenv(CONFIG_ENV_VAR)
    if env_path:
        path = Path(env_path)
        if not path.exists():
            raise FileNotFoundError(path)
        return path

    search_roots = (Path.cwd(), *Path.cwd().parents, Path(__file__).resolve().parents[2])
    for root in search_roots:
        candidate = root / "config.toml"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("config.toml")


@lru_cache(maxsize=4)
def load_app_config(config_path: Path | str | None = None) -> AppConfig:
    path = _find_config_path(config_path)
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    return AppConfig.from_mapping(data)


APP_CONFIG = load_app_config()
DEFAULT_DATA_ROOT = APP_CONFIG.paths.data_root
DEFAULT_DATA_PATH = APP_CONFIG.dataset_path(APP_CONFIG.training.default_dataset)
DEFAULT_OUTPUT_DIR = APP_CONFIG.paths.output_dir
DEFAULT_CACHE_DIR = APP_CONFIG.paths.cache_dir
DEFAULT_MODEL_DIR = APP_CONFIG.paths.model_dir
DEFAULT_METRICS_DIR = APP_CONFIG.paths.metrics_dir
DEFAULT_SUBMISSION_DIR = APP_CONFIG.paths.submission_dir
DEFAULT_FIGURE_DIR = APP_CONFIG.paths.figure_dir


@dataclass(slots=True)
class TrainingConfig:
    data_path: Path = DEFAULT_DATA_PATH
    output_dir: Path = DEFAULT_OUTPUT_DIR
    seed: int = APP_CONFIG.training.seed
    valid_size: float = APP_CONFIG.training.valid_size
    use_cached_features: bool = APP_CONFIG.training.use_cached_features
