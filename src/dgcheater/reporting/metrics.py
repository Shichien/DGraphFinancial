from __future__ import annotations

from pathlib import Path
import json

from ..core.config import APP_CONFIG


def build_metrics_summary(metrics_path: Path, output_path: Path) -> Path:
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    lines = [
        "# 训练结果摘要",
        "",
        f"- 模型: {metrics['model_name']}",
        f"- 验证 AUC: {metrics['valid_auc']:.6f}",
        f"- 训练样本数: {metrics['train_size']}",
        f"- 验证样本数: {metrics['valid_size']}",
        f"- 训练集正样本比例: {metrics['positive_ratio_train']:.6f}",
        f"- 特征数: {metrics['feature_count']}",
        f"- 模型文件: `{metrics['model_path']}`",
        f"- 辅助模型文件: `{metrics.get('aux_model_path', 'N/A')}`",
        f"- 提交文件: `{metrics['submission_path']}`",
        f"- 融合规则: `{metrics.get('blend_rule', 'N/A')}`",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def build_feature_importance_markdown(
    importance_path: Path,
    output_path: Path,
    top_k: int = APP_CONFIG.reporting.top_feature_count,
) -> Path:
    import csv

    rows: list[tuple[str, float]] = []
    with importance_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append((row["feature"], float(row["importance"])))

    lines = [
        "# 关键特征",
        "",
        "| 排名 | 特征 | 重要度 |",
        "| --- | --- | --- |",
    ]
    for idx, (name, importance) in enumerate(rows[:top_k], start=1):
        lines.append(f"| {idx} | {name} | {importance:.6f} |")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
