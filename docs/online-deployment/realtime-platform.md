# 实时反诈平台上限方案落地说明

本目录对应完整实时系统，不是只为了展示的 Kafka/Flink 壳子。目标是形成从多源仿真、实时特征、图状态、风险评分、风险事件存储到 Vue 大屏的闭环。

## 当前已落地

- 多源交易仿真器：覆盖银行转账、钱包支付、商户收单、二维码支付和移动银行渠道。
- 多源主题输出：仿真器不只写交易流，还会同步生成账户画像、设备登录、黑名单更新和延迟标签事件。
- 欺诈剧本注入：覆盖分散汇入、试探后转移、循环转账、设备复用、IP 聚集、商户洗钱、跨渠道规避和突发交易。
- 实时特征引擎：维护账户、设备、IP、商户和图邻域状态。
- 多源特征融合：账户画像、设备登录挑战和黑名单状态已经进入实时特征，并参与风险评分和原因码输出。
- 图状态服务内核：维护动态邻接表，输出一跳邻居、二跳组件、风险邻居数和团伙编号。
- 图追溯证据：评分结果会携带图团伙编号和真实相关节点列表，风险事件入库时会同步写入关联边，用于大屏点击节点后的邻域追溯。
- 融合评分器：将 DGraph-Fin 账户模型先验、实时行为、图团伙和规则命中融合为风险分、风险等级和处置动作。账户模型先验默认加载 `data/runtime-artifacts/output/dgraph_fin/models` 下的 XGBoost 与 LightGBM 模型，并使用 DGraph-Fin 126 维图特征模型分作为交易两端账户风险先验；评分不使用仿真标签字段，`is_scripted_fraud` 只作为烟测评估真值保留。
- Kafka 本地链路命令：支持仿真交易进入 `transactions.raw`，特征消费者写入 `features.realtime`，评分消费者写入 `risk.scored`、`risk.alerts` 和 `risk.audit`。
- Kafka 多源汇合：特征消费者会按 `event_id` 汇合同批账户画像、设备登录、黑名单和交易事件，满足账户、设备、交易三类必要来源后再计算实时特征，避免跨主题乱序导致评分证据缺失。
- 本地 JSON Schema：`packages/schema/` 下维护交易、账户画像、设备登录、黑名单、延迟标签、实时特征和风险判定的字段契约。
- Schema Registry：Docker Compose 会启动 Schema Registry，并通过 `schema-init` 把本地 JSON Schema 注册到对应 Kafka subject。
- PostgreSQL 告警入库：高危风险事件会写入风险事件、原因、关联边、审计日志和待处置案件表。
- 实时大屏 API：提供 `/api/graph-stream`、`/api/graph-node-neighborhood`、`/api/audit-logs`、`/api/case-actions` 和 `/graph/node/{id}/features` 等接口，前端可直接读取统计、告警、图节点、图边、节点邻域、审计日志和处置记录。实时 API 会直接托管 `frontend/graph-stream/dist`，访问根路径即可打开 Vue 3D 大屏。
- 大屏数据契约：内置演示运行时已经按账户画像、设备登录、黑名单、交易的顺序摄入多源事件；数据库快照会聚合风险原因、关联节点和关联边后返回前端。
- Redis 实时榜单：评分消费者会维护 `top_risk_nodes`、`recent_alerts` 和 `community_risk_rank`，大屏优先读取这些实时榜单。
- Neo4j 异构图谱：评分消费者可写入 `Account`、`Device`、`IP`、`Merchant` 节点及转账、设备、IP、商户关系，用于追溯团伙关系。
- Flink 实时特征作业：`flink/jobs/realtime_features.py` 同时订阅 `transactions.raw`、`accounts.raw`、`devices.raw` 和 `blacklist.raw`，先按账户、设备、IP、商户和黑名单实体键分别维护状态，再按 `event_id` 汇合成完整特征；清洗交易输出到 `transactions.cleaned`，实时特征输出到 `features.realtime`。
- 应用目录：`apps/frontend`、`apps/simulator`、`apps/scoring-service` 和 `apps/graph-state-service` 标明平台服务边界，公共实现复用 `src/dgcheater/realtime`。
- 运行指标闭环：生产者、特征消费者和评分消费者会写入运行指标，大屏展示 Kafka 吞吐、Flink 估计延迟和模型平均评分耗时。

## 核心验收命令

```powershell
uv run dgcheater-realtime smoke --event-count 1000
uv run dgcheater-realtime multisource-smoke --event-count 500
uv run dgcheater-realtime multisource-score-smoke --event-count 1000
uv run dgcheater-realtime graph-trace-smoke --event-count 1000
uv run dgcheater-realtime dashboard-contract-smoke --event-count 1000
uv run dgcheater-realtime flink-local-smoke --event-count 1000
uv run dgcheater-realtime multisource-join-smoke --event-count 1000
uv run dgcheater-realtime validate-schemas --sample-count 500
uv run dgcheater-realtime dgraph-prior-smoke --event-count 80
```

这些命令分别覆盖核心评分、多源事件生成、多源状态入模、图追溯、大屏接口契约、Flink 状态逻辑、Schema 字段契约和 DGraph-Fin 账户先验。

## 一键启动基础设施

```powershell
uv run dev-system
```

该命令会启动 Kafka、Kafka UI、Flink、PostgreSQL、Redis、Neo4j、实时大屏 API、Flink 特征作业、评分消费者和仿真交易生产器。
默认特征后端是 Flink，不会启动 Python `feature-worker`，避免正式演示时混用两套特征来源。
启动器会等待 Flink 实时特征作业进入 RUNNING 且任务全部运行后再开始生产交易，并自动打开实时大屏页面。
如果 Windows 侧没有 `docker` 命令，但 WSL 中有 Docker，启动器会自动通过 WSL 执行 Docker Compose，并启动一个 WSL 保活进程，避免基础服务因为 WSL 空闲退出。
PostgreSQL 对宿主机映射到 `55432`，避免与 Windows 本机已有 PostgreSQL 的 `5432` 端口冲突。

如果只想用 Python 特征消费者做轻量调试：

```powershell
uv run dev-system --feature-backend python
```

如果只需要启动基础设施：

```powershell
uv run dev-system --infra-only
```

如果需要手动分开启动三个实时进程：

```powershell
uv run dgcheater-realtime feature-worker
uv run dgcheater-realtime scoring-worker
uv run dgcheater-realtime produce --event-count 400 --interval-ms 80
```

其中 `feature-worker` 会同时订阅 `transactions.raw`、`accounts.raw`、`devices.raw` 和 `blacklist.raw`，按 `event_id` 汇合必要来源后再把多源状态融合成 `features.realtime`。仿真生产器会先写账户画像、设备登录、黑名单和延迟标签，再写对应交易；消费者侧仍会做显式汇合，因此不依赖 Kafka 多主题之间的到达顺序。

如果要使用 Flink 替代 Python 特征消费者：

```powershell
uv run dgcheater-realtime submit-flink
uv run dgcheater-realtime scoring-worker
uv run dgcheater-realtime produce --event-count 400 --interval-ms 80
```

验收 Flink 真实链路时，应先停止本地 `feature-worker`，只保留 Flink 作业和 `scoring-worker`。这样 `features.realtime` 的来源才是 Flink，不会混入 Python 特征消费者。

真实端到端验收：

```powershell
uv run dgcheater-realtime e2e-check --event-count 200 --timeout-sec 120
```

该命令要求基础设施、实时 API、特征消费者和评分消费者已经启动。它会向 Kafka 写入一批带唯一 `event_id` 的多源事件，然后检查本次运行对应的 PostgreSQL 风险事件、风险原因、风险边、审计记录、处置记录、Redis 风险缓存、Neo4j 转账边和大屏快照。验收通过才说明当前链路不是只在本地函数里模拟。

默认连接：

- Kafka：`localhost:9094`
- PostgreSQL：`postgresql://dgcheater:dgcheater@localhost:55432/dgcheater`
- Redis：`redis://localhost:6379/0`
- Neo4j Bolt：`bolt://localhost:7687`
- 实时 API：`http://127.0.0.1:8060`
- Kafka UI：`http://127.0.0.1:8088`
- Flink UI：`http://127.0.0.1:8081`
- Neo4j：`http://127.0.0.1:7474`
- Schema Registry：`http://127.0.0.1:8085`

## 主题与存储

当前 Python 实时链路和 Flink 作业已经接到：

- Kafka 主题：`transactions.raw`、`transactions.cleaned`、`features.realtime`、`risk.scored`、`risk.alerts`、`risk.audit`
- 多源原始主题：`accounts.raw`、`devices.raw`、`blacklist.raw`、`labels.delayed`
- PostgreSQL：风险事件、风险原因、风险边、审计日志和处置记录
- Redis：高风险节点榜、近期告警队列和团伙风险榜
- Neo4j：账户转账边、账户设备边、账户 IP 边和账户商户边
- Flink：`transactions.raw`、`accounts.raw`、`devices.raw`、`blacklist.raw` 到 `transactions.cleaned` 和 `features.realtime` 的多源状态化特征作业
- 大屏指标：`streamMetrics.kafkaThroughput`、`streamMetrics.flinkLatencyMs`、`streamMetrics.modelLatencyMs`

## Redis 键

- `top_risk_nodes`：按风险分排序的账户节点。
- `recent_alerts`：最近 200 条高危及严重告警。
- `community_risk_rank`：按团伙最高风险排序的团伙编号。
- `risk_event:{event_id}`：单条风险事件的短期详情。

## Neo4j 图模型

- `(Account)-[:TRANSFERRED_TO]->(Account)`
- `(Account)-[:USED_DEVICE]->(Device)`
- `(Account)-[:USED_IP]->(IP)`
- `(Account)-[:PAID_MERCHANT]->(Merchant)`

这些关系由评分消费者按事件写入，风险分、风险等级、渠道、金额和时间戳会挂在转账边上。

## 运行指标

指标文件默认写入 `tmp/realtime/runtime-metrics.json`。字段含义：

- `produced_events`：仿真生产器写入 Kafka 的事件数。
- `feature_events`：特征消费者或 Flink 特征链路处理后的事件数。
- `scored_events`：评分消费者完成风险判定的事件数。
- `alert_events`：高危及严重风险事件数。
- `scoring_latency_ms_avg`：模型评分平均耗时。
- `scoring_latency_ms_max`：模型评分最大耗时。

实时 API 会将这些字段转换为大屏使用的 Kafka 吞吐、Flink 估计延迟和模型耗时。
