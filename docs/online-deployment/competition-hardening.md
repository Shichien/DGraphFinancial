# 评审补强说明

本文补齐官方规则中最容易失分的三块内容：安全合规、模型迭代闭环、性能与稳定性验收。当前实现仍以方向一欺诈交易智能识别为主线，不把方向二钓鱼链路识别和方向三反诈客服包装成已实现能力。

## 1. 安全合规方案

### 已落地能力

- 数据最小化：实时事件只保存风控判断需要的账户编号、设备编号、IP、商户编号、风险分、原因码和图邻域证据，不保存姓名、证件号、手机号等直接身份字段。
- 审计留痕：PostgreSQL 中已有 `risk_audit_logs` 和 `case_actions`，每次风险判定与人工处置都会写入审计记录。
- 字段契约：`packages/schema/` 维护交易、账户画像、设备登录、黑名单、延迟标签、实时特征和风险判定的 JSON Schema，Docker 链路会通过 Schema Registry 注册。
- 数据隔离：风险事件、原因、关联边、审计日志和处置记录拆表存储，Redis 只保存实时榜单和短期告警缓存，Neo4j 只保存追溯关系。
- 演示数据合规：仿真器生成的是模拟交易和公开图数据映射，不接入真实个人金融数据。

### 生产部署安全设计

- 接入层：实时大屏 API 前置网关鉴权，演示环境可使用本地白名单，生产环境接入统一身份认证。
- 传输层：Kafka、Schema Registry、PostgreSQL、Redis、Neo4j 和实时 API 在生产环境启用 TLS，内部服务只暴露在私有网络。
- Kafka 权限：按主题拆分生产者和消费者权限。仿真器只能写原始主题，Flink 只能读原始主题并写清洗与特征主题，评分服务只能读特征主题并写风险结果主题。
- 数据库权限：评分服务只拥有风险事件写入权限，大屏 API 只拥有查询权限，人工复核接口只允许写入 `case_actions` 和追加审计日志。
- 敏感字段处理：账户、设备、IP、商户编号在生产环境使用哈希化或内部主键映射，报告和截图只展示脱敏编号。
- 密钥管理：数据库密码、Neo4j 密码和 Kafka 凭据通过环境变量或密钥服务注入，不写入代码仓库。
- 审计不可抵赖：审计日志只追加不覆盖，处置记录更新时同步追加新的审计动作。

### 评审展示口径

项目演示使用仿真数据，因此不会触碰真实金融隐私。系统结构上已经保留完整审计链路和分层存储；生产化时通过网关鉴权、主题权限、数据库最小权限和传输加密补齐安全边界。

## 2. 模型迭代闭环

### 当前可运行基础

- 离线训练：`uv run dgcheater-train train --dataset dgraph_fin --data-path data/DGraphFin/DGraphFin1`
- 实时账户先验：实时评分器加载 DGraph-Fin 账户模型先验，并与实时行为、图团伙风险和规则命中融合。
- 延迟标签：仿真器会生成 `labels.delayed`，用于模拟交易发生后才确认欺诈与否的业务场景。
- 风险结果沉淀：评分消费者会写入 `risk_events`、`risk_event_reasons`、`risk_event_edges`、`risk_audit_logs` 和 `case_actions`。
- 旧版实时模型训练入口：`uv run dgcheater-realtime train-realtime-model --event-count 20000`

### 闭环流程

1. 交易进入 `transactions.raw`，账户画像、设备登录、黑名单和延迟标签同步进入各自主题。
2. Flink 计算实时窗口特征，输出 `transactions.cleaned` 和 `features.realtime`。
3. 评分服务融合离线模型先验、实时行为、图团伙风险和规则命中，输出风险分、风险等级、处置动作和解释证据。
4. 高危事件写入 PostgreSQL、Redis 和 Neo4j，人工复核结果写入 `case_actions`。
5. 延迟标签与人工复核结果汇总成训练样本，按时间切分重新训练模型，避免未来信息泄漏。
6. 新模型先在影子评估中只打分不拦截，对比旧模型的召回率、误报率、稳定性和延迟。
7. 达到阈值后切换模型版本；若告警率、延迟或误报率异常，则回滚到上一版本。

### 模型版本治理

- 每个模型包记录训练数据范围、特征版本、训练时间、验证指标和模型文件哈希。
- 评分服务启动时加载指定模型目录，默认使用当前稳定模型。
- 大屏和审计日志记录风险分解释，不只保存最终分数，便于复盘模型更新前后的差异。
- 延迟标签只用于模型迭代验证，不参与实时打分，避免把仿真真值泄漏到线上判定。

### 评审展示口径

当前系统已经具备离线模型、实时特征、延迟标签、人工复核、审计记录和模型训练入口。严格意义上的自动灰度发布不是本地演示必需项，但闭环的数据入口和工程接口已经准备好。

## 3. 性能与稳定性验收

### 已有验收命令

不依赖 Docker 的本地验收：

```powershell
uv run dgcheater-realtime smoke --event-count 1000
uv run dgcheater-realtime multisource-smoke --event-count 500
uv run dgcheater-realtime multisource-score-smoke --event-count 1000
uv run dgcheater-realtime graph-trace-smoke --event-count 1000
uv run dgcheater-realtime dashboard-contract-smoke --event-count 1000
uv run dgcheater-realtime flink-local-smoke --event-count 1000
uv run dgcheater-realtime multisource-join-smoke --event-count 1000
uv run dgcheater-realtime validate-schemas --sample-count 500
```

真实链路验收：

```powershell
uv run dev-system
uv run dgcheater-realtime e2e-check --event-count 200 --timeout-sec 180
```

### 已验证结果

- 本地 Schema 验证覆盖 5 类源事件，检查必填字段、类型、枚举和数值范围。
- Flink 本地状态逻辑验证覆盖账户画像、设备登录、黑名单、账户窗口、设备账户集合、IP 账户集合、商户入账窗口和图邻域特征。
- 真实端到端验收已验证 Kafka 生产、Flink 特征、评分消费者、PostgreSQL、Redis、Neo4j 和大屏快照。
- 风险事件入库后可追溯原因码、关联节点、关联边、审计日志和处置记录。

### 稳定性设计

- Kafka 多主题按 `event_id` 汇合，避免账户画像、设备登录、黑名单和交易事件乱序导致证据缺失。
- Flink 状态按账户、设备、IP、商户和黑名单实体拆键，避免并行处理时把跨账户复用关系切碎。
- PostgreSQL 使用主键和唯一约束保证重复消费不会生成重复风险事件。
- Redis 用于实时榜单和近期告警，数据库仍是最终审计依据。
- Neo4j 只承担关系追溯，不阻塞基础风险事件入库。
- 大屏 API 在数据库不可用时可使用内置演示运行时，保证答辩演示不断屏；正式验收以端到端检查为准。

### 压测指标口径

报告时不只报单机吞吐，还要说明三类指标：

- 事件吞吐：单位时间内仿真器写入 Kafka 的事件数。
- 特征延迟：交易进入后到 `features.realtime` 生成的耗时。
- 评分延迟：实时特征进入后到风险结果入库的耗时。

当前已有 `output/streaming/performance_report.md` 和 `output/realtime/runtime-metrics.json` 作为本机性能记录。演示大屏展示 Kafka 吞吐、Flink 延迟和评分耗时，用于证明链路不是静态页面。

## 4. 对官方评分项的补强映射

| 官方关注点 | 当前补强材料 |
| --- | --- |
| 自适应学习与模型迭代能力 | 延迟标签、人工复核、模型再训练入口、模型版本治理和回滚设计 |
| 高并发低延迟处理 | Kafka/Flink 链路、运行指标、性能报告、端到端验收 |
| 系统成熟度 | 一键启动、Schema Registry、PostgreSQL 审计库、Redis 榜单、Neo4j 追溯、大屏托管 |
| 安全性 | 数据最小化、脱敏编号、权限分层、传输加密设计、审计只追加 |
| 可解释与溯源 | 原因码、评分分解、团伙编号、相关节点、关联边和节点邻域接口 |

## 5. 答辩建议

答辩时不要说系统已经达到银行生产级安全，而要说本地演示已完成实时反诈闭环，生产化安全边界已经按金融系统要求设计好，当前通过仿真数据规避真实隐私风险。这样说更稳，也更符合项目真实状态。
