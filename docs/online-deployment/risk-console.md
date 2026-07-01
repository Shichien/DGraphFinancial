# Risk Console 使用说明

`risk-console` 是本地交易分析控制台. 它不依赖 Kafka, Flink, PostgreSQL, Redis 或 Neo4j. 它直接复用 realtime 主链路:

```text
manual transaction
-> account profile
-> device login
-> optional blacklist
-> RealtimeFeatureEngine
-> FusionRiskScorer
-> risk decision
```

## 前端控制台

浏览器控制台集成在实时大屏中. 启动方式:

```bash
just frontend-console
```

启动后打开:

```text
http://127.0.0.1:8060/#console
```

如果前端已经构建过, 也可以只启动 API 和静态文件托管:

```bash
just frontend-console-api
```

开发模式可以分开启动后端 API 和 Vite 前端:

```bash
just frontend-console-api
just frontend-console-ui
```

前端控制台支持两种输入方式:

- 使用字段构造器生成 `send`, `batch`, `set` 命令.
- 直接编辑 JSON, 提交单条命令, 命令数组, 或 `{ "commands": [...] }`.

它会返回本次批量结果, 会话历史, 风险等级分布, 原因码统计, Top 风险事件, 单条评分拆解和实时特征.

## 交互模式

```bash
uv run dgcheater-realtime risk-console
```

常用命令:

```text
send src=560 dst=568 amount=80000 blacklist=device login=challenge
batch 20 src=500..520 dst=650 amount=5000..120000 shared_device=true historical_risk=0.72 blacklist=device
set channel=wallet_pay historical_risk=0.61 blacklist=none
show defaults
show history
detail -1
export tmp/realtime/manual-risk-results.json
reset
quit
```

字段可以用短名, 也可以用完整路径:

```text
src=560
transaction.src_account=560
historical_risk=0.72
account.historical_risk_score=0.72
blacklist=device
blacklist.entity_type=device
```

批量字段支持标量, 列表, 范围:

```text
channel=wallet_pay,qr_pay,mobile_banking
src=500..520
amount=5000..120000
```

范围在小整数区间会逐个取值. 在大数值区间会按批次数插值.

## 脚本模式

```bash
uv run dgcheater-realtime risk-console --script docs/online-deployment/examples/risk-console-script.json --output tmp/realtime/manual-risk-results.json
```

脚本可以是 JSON:

```json
{
  "commands": [
    {
      "type": "send",
      "src": 120,
      "dst": 220,
      "amount": 800,
      "historical_risk": 0.08,
      "scenario": "manual-normal"
    },
    {
      "type": "batch",
      "count": 5,
      "src": "500..504",
      "dst": 650,
      "amount": "65000..110000",
      "channel": ["wallet_pay", "qr_pay", "mobile_banking"],
      "shared_device": true,
      "historical_risk": 0.72,
      "login": "challenge",
      "blacklist": "device",
      "scenario": "manual-shared-device",
      "scripted": true,
      "fraud_type": "device_reuse"
    }
  ]
}
```

输出 JSON 包含:

```text
summary
results[].input
results[].features
results[].decision
results[].score_breakdown
```

其中 `score_breakdown` 会展示四个评分分量:

```text
offline_model_score
realtime_behavior_score
graph_community_score
rule_score
```

## 适合调试的场景

- 正常小额交易: 低历史风险, 小金额, 不命中黑名单.
- 大额突发交易: 提高 `amount`, 缩短 `timestamp_step`.
- 共用设备: `shared_device=true`, 批量发送多个 `src`.
- IP 聚集: `shared_ip=true`, 批量发送多个 `src`.
- 黑名单命中: `blacklist=account`, `blacklist=device`, `blacklist=ip`, `blacklist=merchant`.
- 团伙关系: 多个账户指向同一个 `dst`, 或者多个事件复用同一设备, IP, 商户.

这个控制台用于模型效果调试和演示解释. 它不会写入 Kafka 或数据库.
