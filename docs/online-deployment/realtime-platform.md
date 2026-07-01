# 实时反诈平台上限方案落地说明

本目录对应完整实时系统，不是只为了展示的 Kafka/Flink 壳子。目标是形成从多源仿真、实时特征、图状态、风险评分、风险事件存储到 Vue 大屏的闭环。

官方规则中安全合规、模型迭代和性能稳定性三块补强说明见 [评审补强说明](competition-hardening.md)。该文档用于答辩时解释当前系统如何覆盖方向一的高分项，以及哪些能力是本地演示已落地、哪些能力是生产部署设计。

## 当前已落地

- 多源交易仿真器：覆盖银行转账、钱包支付、商户收单、二维码支付和移动银行渠道。
- 多源主题输出：仿真器不只写交易流，还会同步生成账户画像、设备登录、黑名单更新和延迟标签事件。
- 欺诈剧本注入：覆盖分散汇入、试探后转移、循环转账、设备复用、IP 聚集、商户洗钱、跨渠道规避和突发交易。
- 实时特征引擎：维护账户、设备、IP、商户和图邻域状态。
- 多源特征融合：账户画像、设备登录挑战和黑名单状态已经进入实时特征，并参与风险评分和原因码输出。
- 图状态服务内核：维护动态邻接表，输出一跳邻居、二跳组件、风险邻居数和团伙编号。
- 图追溯证据：评分结果会携带图团伙编号和真实相关节点列表，风险事件入库时会同步写入关联边，用于大屏点击节点后的邻域追溯。
- 融合评分器：将 DGraph-Fin 账户模型先验、实时行为、图团伙和规则命中融合为风险分、风险等级和处置动作。账户模型先验加载 `output/dgraph_fin/models` 下的 XGBoost 与 LightGBM 模型，并使用 DGraph-Fin 126 维图特征模型分作为交易两端账户风险先验；评分不使用仿真标签字段，`is_scripted_fraud` 只作为烟测评估真值保留。
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

## 本地烟测

```powershell
uv run dgcheater-realtime smoke --event-count 1000 --output-path output/realtime/smoke.json
```

输出内容包括风险等级分布、高危以上告警数量和样例告警。该命令不依赖 Docker，先用于验证核心业务链路。

多源仿真验收：

```powershell
uv run dgcheater-realtime multisource-smoke --event-count 500
```

该命令会验证仿真器是否同时产生交易、账户画像、设备登录、黑名单和延迟标签事件，并输出各欺诈剧本命中数量。

多源评分验收：

```powershell
uv run dgcheater-realtime multisource-score-smoke --event-count 1000
```

该命令不依赖 Docker，会按真实顺序摄入账户画像、设备登录和黑名单状态，再将交易转成实时特征并评分，用于验证多源状态确实进入模型证据。

图追溯验收：

```powershell
uv run dgcheater-realtime graph-trace-smoke --event-count 1000
```

该命令不依赖 Docker，会检查高危告警是否携带团伙编号、相关节点列表和图邻域证据，用于验证点击节点追溯不是只返回交易两端。

大屏接口契约验收：

```powershell
uv run dgcheater-realtime dashboard-contract-smoke --event-count 1000
```

该命令不依赖 Docker，会检查大屏快照是否携带原因码、相关节点和关联边，并验证数据库快照行转换后仍能保留风险原因和团伙追溯字段。

Flink 多源状态逻辑验收：

```powershell
uv run dgcheater-realtime flink-local-smoke --event-count 1000
```

该命令不启动 Flink 集群，但会直接调用 PyFlink 作业中的状态处理函数，按账户画像、设备登录、黑名单、交易的顺序喂入同批多源事件，验证输出的 `features.realtime` 是否包含历史风险、登录挑战和黑名单命中特征。命令还会构造两个账户复用同一设备、IP 和商户的事件，断言第二条事件能看到跨账户累计状态，用于证明 Flink 作业不是单账户局部状态或单交易流批处理。

Kafka 多源汇合验收：

```powershell
uv run dgcheater-realtime multisource-join-smoke --event-count 1000
```

该命令不依赖 Kafka 集群，会直接验证特征消费者中的多源汇合逻辑，确认同一个 `event_id` 的交易、账户画像、设备登录和可选黑名单被汇合后再输出实时特征。

本地 Schema 验收：

```powershell
uv run dgcheater-realtime validate-schemas --sample-count 500
```

该命令会用标准库校验生成样本是否符合 `packages/schema/` 下的本地 JSON Schema，覆盖必填字段、类型、枚举、数值范围和额外字段约束。

DGraph 账户先验验收：

```powershell
uv run dgcheater-realtime dgraph-prior-smoke --event-count 80
```

该命令会验证实时评分是否真正携带 DGraph-Fin 模型先验，输出源账户模型分、目标账户模型分、DGraph 节点映射、126 维特征数和 DGraph 验证 AUC。

旧版实时仿真模型训练命令保留用于对照：

```powershell
uv run dgcheater-realtime train-realtime-model --event-count 20000
```

该命令会基于实时特征清单训练 XGBoost 与 LightGBM 模型包，输出到 `output/realtime/models`。当前主链路已经改为加载 DGraph-Fin 账户模型先验，该旧命令只作为对照实验保留。

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
uv run dgcheater-realtime produce --event-count 20000 --interval-ms 80
```

其中 `feature-worker` 会同时订阅 `transactions.raw`、`accounts.raw`、`devices.raw` 和 `blacklist.raw`，按 `event_id` 汇合必要来源后再把多源状态融合成 `features.realtime`。仿真生产器会先写账户画像、设备登录、黑名单和延迟标签，再写对应交易；消费者侧仍会做显式汇合，因此不依赖 Kafka 多主题之间的到达顺序。

如果要使用 Flink 替代 Python 特征消费者：

```powershell
uv run dgcheater-realtime submit-flink
uv run dgcheater-realtime scoring-worker
uv run dgcheater-realtime produce --event-count 20000 --interval-ms 80
```

验收 Flink 真实链路时，应先停止本地 `feature-worker`，只保留 Flink 作业和 `scoring-worker`。这样 `features.realtime` 的来源才是 Flink，不会混入 Python 特征消费者。

真实端到端验收：

```powershell
uv run dgcheater-realtime e2e-check --event-count 200 --timeout-sec 120
```

该命令要求基础设施、实时 API、特征消费者和评分消费者已经启动。它会向 Kafka 写入一批带唯一 `event_id` 的多源事件，然后检查本次运行对应的 PostgreSQL 风险事件、风险原因、风险边、审计记录、处置记录、Redis 风险缓存、Neo4j 转账边和大屏快照。验收通过才说明当前链路不是只在本地函数里模拟。

注意不要让 Windows 和 WSL 共用同一个 `.venv`。如果需要分别在两侧验证，建议显式设置隔离环境：

```powershell
$env:UV_PROJECT_ENVIRONMENT=".venv-e2e-win"
uv run dgcheater-realtime smoke --event-count 1000
```

```bash
UV_PROJECT_ENVIRONMENT=.venv-e2e-wsl uv run dgcheater-realtime smoke --event-count 1000
```

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

Flink 作业当前已经修正以下问题：

- 提交脚本显式连接 `flink-jobmanager:8081`，并指定 Python 解释器。
- 提交脚本会清理代理环境变量，避免容器访问内部服务名时走宿主代理。
- 状态函数改为 Flink 要求的键控处理函数。
- 状态键已经拆成账户、设备、IP、商户、黑名单实体键和事件汇合键，避免并行状态下设备复用、IP 聚集、商户集中度被账户分区切碎。
- 状态描述器使用 PyFlink 的显式字符串类型。
- Python 算子输出显式声明字符串类型，避免 Kafka Sink 收到字节数组。

下一阶段继续补：

- Flink 端到端验证：当前作业已覆盖多源输入、账户画像、设备登录、黑名单、账户窗口、设备账户集合、IP 账户集合、商户入账窗口、图邻域、窗口金额、交易次数、对手方数量、最近交易间隔和渠道切换；本轮已在 WSL Docker 中提交并保持 RUNNING，JobID 为 `6f24656e24e9afa924f035181b7b5dcf`，任务数 14/14 RUNNING，并验证唯一事件 `920001` 同时写入 `transactions.cleaned` 和 `features.realtime`。
- Python 实时端到端验证：当前已经通过 Kafka 生产、Python 特征消费者、评分消费者、PostgreSQL、Redis、Neo4j 和实时 API 的真实链路验收。
- Vue 大屏：复用当前 3D 点云图谱，继续加强 Kafka 吞吐、Flink 延迟、模型耗时和审计记录的展示。

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

指标文件默认写入 `output/realtime/runtime-metrics.json`。字段含义：

- `produced_events`：仿真生产器写入 Kafka 的事件数。
- `feature_events`：特征消费者或 Flink 特征链路处理后的事件数。
- `scored_events`：评分消费者完成风险判定的事件数。
- `alert_events`：高危及严重风险事件数。
- `scoring_latency_ms_avg`：模型评分平均耗时。
- `scoring_latency_ms_max`：模型评分最大耗时。

实时 API 会将这些字段转换为大屏使用的 Kafka 吞吐、Flink 估计延迟和模型耗时。

## 已验证项

- 隔离环境编译检查通过：

```powershell
$env:UV_PROJECT_ENVIRONMENT=".venv-e2e-win"
uv run python -m py_compile src\dgcheater\realtime\schemas.py src\dgcheater\realtime\simulator.py src\dgcheater\realtime\kafka_runtime.py
```

- 核心评分烟测通过：

```powershell
$env:UV_PROJECT_ENVIRONMENT=".venv-e2e-win"
uv run dgcheater-realtime smoke --event-count 1000
```

本次烟测输出 1000 条事件，低危 982 条，中危 17 条，高危 1 条。

- 多源仿真验证通过：500 条交易同步生成 500 条账户画像、500 条设备登录、141 条黑名单和 141 条延迟标签事件，覆盖 8 类欺诈剧本。

- 本地 Schema 验证通过：500 条交易样本、500 条账户画像样本、500 条设备登录样本、141 条黑名单样本和 141 条延迟标签样本全部通过字段契约校验。

- 多源评分验证通过：1000 条事件中，黑名单特征命中 277 次，登录挑战特征命中 41 次，历史高风险账户命中 314 次，输出高危 9 条。

- 图追溯验证通过：1000 条事件中输出高危 9 条，高危告警平均关联节点数 4.0，最大关联节点数 7，样例告警包含 `community_id`、`related_nodes` 和图邻域证据字段。

- 大屏契约验证通过：1000 条事件生成 80 条窗口事件，80 条均带原因码，38 条带超过交易双方的相关节点，前端图谱返回 87 条关联边；数据库事件转换样例保留 2 个原因码、4 个相关节点和 3 条图边。

- Flink 多源状态逻辑验证通过：500 条多源事件通过 PyFlink 状态函数生成 500 条清洗交易和 500 条实时特征；500 条特征带账户画像历史风险，27 条命中登录挑战，140 条命中黑名单；额外构造的跨账户共享设备、IP 和商户场景验证通过，第二条事件看到 `device_account_count=4`、`ip_account_count=4` 和 `merchant_in_amount=30000.0`。

- Kafka 多源汇合验证通过：1000 条多源事件通过特征消费者汇合逻辑生成 1000 条实时特征，待处理事件清零；1000 条特征带账户画像历史风险，41 条命中登录挑战，277 条命中黑名单。

- 真实端到端验收通过：`uv run dgcheater-realtime e2e-check --event-count 200 --timeout-sec 120` 输出 `ok: true`；本次 200 条事件中，PostgreSQL 写入 172 条风险事件、224 条原因记录、187 条关联边、172 条审计记录和 172 条处置记录，Redis 捕获 173 条本次风险事件，Neo4j 写入 173 条本次转账边，大屏快照返回 238 条总事件、161 个可见节点、172 条可见边和 80 条最近事件。

- Flink 真实端到端验收通过：停止 Python `feature-worker` 后，保留 Flink 作业和 `scoring-worker`，执行 `uv run dgcheater-realtime e2e-check --event-count 200 --timeout-sec 180` 输出 `ok: true`；本次 200 条事件中，PostgreSQL 写入 171 条风险事件、178 条原因记录、169 条关联边、171 条审计记录和 171 条处置记录，Redis 捕获 172 条本次风险事件，Neo4j 写入 172 条本次转账边，大屏快照返回 2093 条总事件、153 个可见节点、159 条可见边和 80 条最近事件。验收时未运行 Python `feature-worker`，`features.realtime` 由 Flink 作业产生。

- Vue 大屏托管验证通过：实时 API 临时端口返回 Vue `index.html`，根路径状态码 200，页面包含 `id="app"`，同一服务的 `/api/graph-stream` 返回 2121 条总事件、152 个可见节点和 159 条可见边。

- 审计与处置接口验证通过：`POST /api/case-actions` 可写入案件处置动作并同步追加 `case_action_recorded` 审计日志，HTTP 验证返回 `confirmed_fraud` 处置状态，`GET /api/case-actions` 可读取处置记录。
