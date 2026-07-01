# 实时反诈平台应用目录

这里按服务边界组织实时反诈平台：

- `frontend`：Vue 风险大屏。
- `simulator`：多源异构事件仿真器。
- `scoring-service`：实时风险评分服务和 Kafka 评分 worker。
- `graph-state-service`：图状态查询与团伙追溯接口。

当前服务实现复用 `src/dgcheater/realtime` 中的公共包，避免复制两套逻辑。一键启动仍使用：

```powershell
uv run dev-system
```
