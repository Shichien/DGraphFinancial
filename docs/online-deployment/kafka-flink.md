# Kafka/Flink Streaming Deployment

本文档说明当前仓库新增的 Kafka + Flink + PostgreSQL 流式风险识别部署原型。它不是只写在报告里的架构图，而是包含可启动服务、Flink 作业、风险评分服务、Kafka producer、结果 consumer、事件库和实时大屏的完整本地部署包。

## 当前边界

- 已完成：Kafka 输入主题、Flink 流处理作业、HTTP 风险评分服务、Kafka 输出主题、事件生产者、结果消费者、PostgreSQL 事件库、实时大屏服务、Docker Compose 部署文件。
- 已完成：评分服务复用本项目已训练的 `XGBoost + LightGBM` 模型和统一图特征缓存。
- 未完成：多节点云上部署、TLS/SASL 安全认证、Flink checkpoint 外部持久化、Kubernetes 编排、生产级监控告警。

## 目录结构

- `deploy/streaming/docker-compose.yml`
- `deploy/streaming/Dockerfile`
- `deploy/streaming/flink/Dockerfile`
- `deploy/streaming/flink/risk_job.py`
- `scripts/wait.py`
- `scripts/consume.py`
- `scripts/health.py`
- `scripts/smoke.py`
- `src/dgcheater/streaming_runtime.py`
- `src/dgcheater/streaming/runtime.py`

## 服务拓扑

```text
DGraph-Fin replay producer
  -> Kafka topic transactions.raw
  -> Flink risk_job.py
  -> HTTP risk-scorer /score-batch
  -> Kafka topic transactions.risk
  -> result consumer
  -> PostgreSQL risk_events
  -> live dashboard /api/risk-events
```

## 前置条件

当前机器需要安装 Docker Desktop 或兼容的 Docker Engine，并确保 `docker compose` 可用。

本机当前检查结果：Java 和 Python 已存在，但命令行未检测到 Docker，因此本轮已完成静态验证，未实际启动 Compose 集群。

## 启动命令

```powershell
just stream-up
just stream-wait
just stream-smoke
just live-open
```

这里的分层是：业务逻辑放在 Python 脚本中，运行环境由 Docker Compose 管理，任务编排由 `justfile` 承担。

## 访问入口

- Kafka UI: `http://localhost:8088`
- Flink Web UI: `http://localhost:8081`
- Risk scorer health: `http://localhost:8000/health`
- Live dashboard: `http://localhost:8050`
- Live dashboard health: `http://localhost:8050/health`

## 本地无 Kafka 的服务自检

如果只想检查评分服务接口，可以先启动 `risk-scorer`，然后运行：

```powershell
uv run dgcheater-stream score-http-once --event-count 10
```

## 主题约定

- 输入主题：`transactions.raw`
- 输出主题：`transactions.risk`

输入事件 JSON 字段：

- `event_id`
- `timestamp`
- `src_node`
- `dst_node`
- `edge_type`
- `channel`
- `amount`
- `device_fingerprint`
- `is_fraud_edge`

输出风险 JSON 字段：

- `risk_score`
- `risk_level`
- `action`
- `focus_node`
- `src_node_score`
- `dst_node_score`
- `explanation`

事件库表：

- 表名：`risk_events`
- 主键：`event_id`
- 风险字段：`risk_score`、`risk_level`、`action`
- 案件字段：`focus_node`、`status`、`review`
- 审计字段：`trace_json`、`audit_json`、`created_at`

## 为什么模型服务独立于 Flink

当前方案没有把 XGBoost 和 LightGBM 模型直接嵌入 Flink JVM，而是由 Flink 调用独立的 HTTP 风险评分服务。这样做有三个理由：

- 模型服务可以独立扩缩容，避免 Flink 作业和模型依赖强耦合。
- Python 模型依赖保留在本项目环境内，减少 JVM 和 native library 冲突。
- 后续替换模型或灰度发布时，只需要替换评分服务，不需要重启整条流处理链路。

## 后续生产化增强

- Kafka 增加 SASL/SSL 和 ACL。
- Flink 开启 checkpoint，并把状态后端持久化到对象存储或分布式文件系统。
- Risk scorer 增加多副本、负载均衡、熔断和请求超时重试。
- 输出结果接入风控台和人工复核系统。
- 增加 Prometheus/Grafana 监控吞吐、延迟、错误率和风险等级分布。
