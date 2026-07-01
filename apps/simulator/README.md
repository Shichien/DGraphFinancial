# 多源仿真器

本目录是多源仿真服务边界。当前可执行实现位于 `dgcheater.realtime.simulator` 和 Kafka 生产入口：

```powershell
uv run dgcheater-realtime produce --event-count 400 --interval-ms 80
```

仿真器会产生交易、账户画像、设备登录、黑名单和延迟标签事件。
