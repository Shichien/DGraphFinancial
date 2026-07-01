# 模型评分服务

本目录是实时评分服务边界。当前可执行实现位于 `src/dgcheater/realtime`：

- Kafka worker：`uv run dgcheater-realtime scoring-worker`
- 实时离线模型训练：`uv run dgcheater-realtime train-realtime-model`
- 评分逻辑：`dgcheater.realtime.scoring.FusionRiskScorer`

评分 worker 默认加载 `data/runtime-artifacts/output/realtime/models` 下的 XGBoost 和 LightGBM 实时模型包；需要临时切换模型时，可通过 `DG_REALTIME_MODEL_DIR` 指定模型目录。
