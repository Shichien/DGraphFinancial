# 图状态服务

本目录是图状态服务边界。当前实现复用实时 API 中的图接口：

- `GET /graph/node/{id}/features`
- `GET /graph/node/{id}/neighbors`
- `GET /graph/community/{id}`

动态图状态核心位于 `dgcheater.realtime.graph_state`，Neo4j 写入位于 `dgcheater.realtime.realtime_sinks`。
