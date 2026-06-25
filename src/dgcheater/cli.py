from __future__ import annotations

from pathlib import Path

import typer

from .core.config import APP_CONFIG, DEFAULT_OUTPUT_DIR
from .dashboard.builder import build_showcase_dashboard
from .datasets.registry import DATASET_SPECS, get_dataset_spec
from .dgraph.features import build_features, get_or_create_feature_cache
from .models.training import fit_lightgbm_baseline, fit_tabular_blend, fit_xgboost, fit_xgboost_without_label_neighbors
from .datasets.loaders import TabularDataset, load_dataset_from_spec
from .reporting.metrics import build_feature_importance_markdown, build_metrics_summary
from .streaming.prototype import result_to_json, run_streaming_prototype

app = typer.Typer(no_args_is_help=True)


@app.command()
def train(
    dataset: str = typer.Option(APP_CONFIG.training.default_dataset),
    data_path: Path | None = typer.Option(None, file_okay=True, dir_okay=True),
    output_dir: Path = typer.Option(DEFAULT_OUTPUT_DIR),
    seed: int = typer.Option(APP_CONFIG.training.seed),
    valid_size: float = typer.Option(APP_CONFIG.training.valid_size, min=0.05, max=0.4),
) -> None:
    """Train the default competition model and generate submission."""
    spec = get_dataset_spec(dataset)
    raw = load_dataset_from_spec(spec, data_path or spec.default_path)
    if isinstance(raw, TabularDataset):
        result = fit_tabular_blend(
            raw.x,
            raw.feature_names,
            raw.y,
            raw.train_idx,
            raw.test_idx,
            output_dir=output_dir,
            dataset_key=spec.key,
            valid_idx=raw.valid_idx,
            test_ids=raw.test_ids,
            submission_id_column=raw.submission_id_column or "id",
            submission_target_column=raw.submission_target_column or "target",
            seed=seed,
            valid_size=valid_size,
        )
        typer.echo(f"XGBoost+LightGBM valid AUC: {result.valid_auc:.6f}")
        typer.echo(f"Saved submission to {result.submission_path}")
        return

    bundle = (
        get_or_create_feature_cache(raw, APP_CONFIG.paths.cache_dir, cache_key=spec.key)
        if APP_CONFIG.training.use_cached_features
        else build_features(raw)
    )
    baseline_auc = fit_lightgbm_baseline(
        bundle.features,
        raw.y,
        raw.train_idx,
        valid_idx=raw.valid_idx,
        seed=seed,
        valid_size=valid_size,
    )
    if spec.key == "elliptic_pp":
        result = fit_xgboost_without_label_neighbors(
            bundle.features,
            bundle.feature_names,
            raw.y,
            raw.train_idx,
            raw.test_idx,
            output_dir=output_dir,
            dataset_key=spec.key,
            valid_idx=raw.valid_idx,
            seed=seed,
            valid_size=valid_size,
        )
        typer.echo(f"LightGBM valid AUC: {baseline_auc:.6f}")
        typer.echo(f"Blend valid AUC: {result.valid_auc:.6f}")
        typer.echo(f"Saved submission to {result.submission_path}")
        return

    result = fit_xgboost(
        bundle.features,
        bundle.feature_names,
        raw.edge_index,
        raw.y,
        raw.train_idx,
        raw.test_idx,
        output_dir=output_dir,
        dataset_key=spec.key,
        valid_idx=raw.valid_idx,
        seed=seed,
        valid_size=valid_size,
    )
    typer.echo(f"LightGBM valid AUC: {baseline_auc:.6f}")
    typer.echo(f"Blend valid AUC: {result.valid_auc:.6f}")
    typer.echo(f"Saved submission to {result.submission_path}")


@app.command("list-datasets")
def list_datasets() -> None:
    """List registered public datasets and local availability notes."""
    for spec in DATASET_SPECS.values():
        typer.echo(f"{spec.key}: {spec.display_name}")
        typer.echo(f"  problem_type: {spec.problem_type}")
        typer.echo(f"  source: {spec.source_url}")
        typer.echo(f"  default_path: {spec.default_path}")
        typer.echo(f"  login_required: {spec.login_required}")
        typer.echo(f"  notes: {spec.notes}")


@app.command("report-metrics")
def report_metrics(
    metrics_path: Path = typer.Option(APP_CONFIG.reporting.metrics_path, exists=True),
    output_path: Path = typer.Option(APP_CONFIG.reporting.output_path),
    importance_path: Path = typer.Option(APP_CONFIG.reporting.importance_path, exists=True),
    importance_output_path: Path = typer.Option(APP_CONFIG.reporting.importance_output_path),
) -> None:
    """Generate a markdown summary from the latest metrics file."""
    build_metrics_summary(metrics_path, output_path)
    build_feature_importance_markdown(importance_path, importance_output_path, top_k=APP_CONFIG.reporting.top_feature_count)
    typer.echo(f"Saved summary to {output_path}")


@app.command("build-dashboard")
def build_dashboard(
    output_path: Path = typer.Option(APP_CONFIG.dashboard.output_path),
    output_dir: Path = typer.Option(DEFAULT_OUTPUT_DIR),
) -> None:
    """Build a self-contained showcase dashboard for experiments and datasets."""
    result = build_showcase_dashboard(output_path=output_path, output_dir=output_dir)
    typer.echo(f"Saved dashboard to {result}")


@app.command("stream-prototype")
def stream_prototype(
    dataset: str = typer.Option(APP_CONFIG.streaming.prototype.dataset),
    data_path: Path | None = typer.Option(None, file_okay=True, dir_okay=True),
    output_dir: Path = typer.Option(DEFAULT_OUTPUT_DIR),
    event_count: int = typer.Option(APP_CONFIG.streaming.prototype.event_count, min=100, max=200_000),
    trace_top_k: int = typer.Option(APP_CONFIG.streaming.prototype.trace_top_k, min=1, max=200),
    seed: int = typer.Option(APP_CONFIG.training.seed),
) -> None:
    """Replay graph transactions, score risks, trace rings and measure latency."""
    spec = get_dataset_spec(dataset)
    raw = load_dataset_from_spec(spec, data_path or spec.default_path)
    if isinstance(raw, TabularDataset):
        raise typer.BadParameter("stream-prototype currently requires a graph dataset.")
    result = run_streaming_prototype(
        raw,
        dataset_key=spec.key,
        output_dir=output_dir,
        event_count=event_count,
        trace_top_k=trace_top_k,
        seed=seed,
    )
    typer.echo(result_to_json(result))


if __name__ == "__main__":
    app()
