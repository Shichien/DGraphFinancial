# Streaming Prototype

本文档记录当前补齐的交易流仿真、在线评分、风险等级、团伙溯源与性能实测原型。

## 运行命令

```powershell
uv run dgcheater-train stream-prototype --dataset dgraph_fin --data-path data/DGraphFin/DGraphFin1 --event-count 5000 --trace-top-k 20
```

## 已生成产物

- `output/streaming/transaction_stream_sample.csv`
- `output/streaming/risk_events.csv`
- `output/streaming/ring_trace_summary.json`
- `output/streaming/performance_report.json`
- `output/streaming/performance_report.md`

## 原型能力

- 交易流仿真：从 DGraph-Fin 交易边按时间戳抽样回放，并补充渠道、金额和设备指纹模拟字段。
- 实时评分：加载已训练 `XGBoost + LightGBM` 融合模型，对事件两端节点进行微批风险评分。
- 风险等级：将风险分映射为 `low`、`medium`、`high`、`critical` 四档。
- 风控动作：按风险等级输出 `pass`、`step_up_verification`、`manual_review`、`freeze_and_manual_review`。
- 团伙溯源：对高风险事件抽取焦点节点一跳邻域，统计欺诈邻居、背景邻居、主导交易类型与时间跨度。
- 性能实测：记录单机微批回放吞吐、评分吞吐、平均延迟和 P95/P99 延迟。

## 本次实测结果

- 回放事件数：`5000`
- 评分唯一节点数：`9986`
- 总运行时间：`0.1130` 秒
- 模型评分时间：`0.0784` 秒
- 事件吞吐：`44231.03` events/second
- 纯评分吞吐：`127411.78` nodes/second
- 平均节点评分延迟：`0.0078` ms
- P95 节点评分延迟：`0.0078` ms
- P99 节点评分延迟：`0.0078` ms

## 风险等级分布

- `critical`: 80
- `high`: 760
- `medium`: 1117
- `low`: 3043

## 边界说明

当前实现是单机 CSV 回放与微批模型评分原型，不是完整 Kafka 和 Flink 生产部署。它的价值在于把原先只停留在设计里的实时识别、风险等级、团伙溯源和性能测试落成可运行证据。后续可以把当前 CSV 回放器替换为 Kafka producer，把窗口状态迁移到 Flink，把 `risk_events.csv` 的输出接入风控台。
