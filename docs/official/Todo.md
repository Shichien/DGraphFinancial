# Todo

本清单按赛题原文逐条补齐当前项目短板，优先做能运行、能展示、能写进报告的最小闭环，不把尚未实现的生产级能力包装成已经上线。

## P0 本轮必须补齐

- [x] 交易流仿真与回放
  - 基于本地 `DGraph-Fin` 或 `phase1` 图数据，按边时间戳抽样生成交易事件流。
  - 输出事件字段：事件序号、时间戳、源节点、目标节点、交易类型、源/目标标签、渠道、金额、设备指纹。
  - 验收：可通过 CLI 生成 `output/streaming/transaction_stream_sample.csv`。

- [x] 实时评分原型
  - 加载已训练 `XGBoost + LightGBM` 模型和特征缓存。
  - 对交易流中的源节点与目标节点进行单机在线式风险评分。
  - 输出风险分、风险等级、关键解释字段与是否命中欺诈标签。
  - 验收：可通过 CLI 生成 `output/streaming/risk_events.csv`。

- [x] 风险等级输出
  - 将模型概率映射为 `low`、`medium`、`high`、`critical` 四档。
  - 每条结果给出建议动作，如放行、二次验证、人工复核、冻结拦截。
  - 验收：结果文件中包含 `risk_score`、`risk_level`、`action`。

- [x] 团伙溯源轻量模块
  - 针对高风险事件抽取焦点节点的一跳邻域。
  - 统计高风险邻居数、欺诈邻居数、背景节点数、交易类型集中度、时间跨度。
  - 验收：生成 `output/streaming/ring_trace_summary.json`。

- [x] 性能测试实测
  - 对交易流回放进行单机压测。
  - 统计事件数、评分节点数、总耗时、吞吐、平均延迟、P95、P99。
  - 验收：生成 `output/streaming/performance_report.json` 和 Markdown 摘要。

## P1 本轮尽量补强

- [x] 报告与答辩材料同步
  - 把新增原型、风险等级、团伙溯源、性能实测写入 `docs`。
  - 如时间允许，同步到 Typst 报告。

- [x] 前端面板入口同步
  - 在已有 dashboard 中补充流式原型与性能实测卡片。
  - 验收：重新生成 `output/dashboard/index.html`。

## P2 后续扩展

- [x] Kafka 与 Flink 原型
  - 已新增 `deploy/streaming/docker-compose.yml`、Flink 作业、评分服务、Kafka producer 和 result consumer。
  - 当前机器未检测到 Docker，因此已完成静态验证和 Python 侧验证，实际 Compose 启动需等待 Docker 可用。

- [ ] 更大规模 AMLSim 数据生成
  - 当前先复用本地 DGraph-Fin 和 AMLSim sample。
  - 后续用 AMLSim 参数文件生成更大仿真样本，避免样例过小导致 AUC 不可用。

- [ ] 增量学习与模型版本切换
  - 当前先输出可复跑的离线再训练命令。
  - 后续补充样本回灌、模型注册、灰度发布与回滚记录。
