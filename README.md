# 智鉴流盾

基于 DGraphFin 数据集的金融反诈赛道一项目。当前主方案采用统一图结构特征工程、无泄漏邻域风险增强与 `XGBoost + LightGBM` 轻量融合，兼顾可复现性、工程落地与比赛展示。

## 目标

- 面向赛道一完成可复现的欺诈交易识别方案
- 使用 `uv` 管理 Python 环境与依赖
- 使用 Typst 编写比赛报告
- 产出训练结果、提交文件、报告与关键图表

## 项目结构

- `src/dgcheater/` 核心代码
- `docs/report/` Typst 报告
- `docs/presentation/` Typst 答辩稿
- `docs/` 多数据集接入说明
- `artifacts/` 最终报告、答辩稿和交付材料
- `tmp/` 本地运行指标、临时导出和中间结果

## 数据准备

默认读取：

`data/DGraphFin/DGraphFin1`

项目默认路径、训练参数、模型参数、流式服务端点与健康检查端点集中放在 `config.toml`。如需临时覆盖数据路径，也可以继续通过命令行参数传入。

实时大屏还会读取一组小型运行产物，用于加载 DGraph 账户风险先验。为了让新机器拉取代码后只挂载 `data/` 就能启动，运行产物统一放在：

`data/runtime-artifacts/output`

实时大屏启动时直接读取 `data/runtime-artifacts/output` 下的运行产物，不要求项目根目录存在 `output/`。

## 快速开始

```powershell
uv sync
uv run dgcheater-train list-datasets
uv run dgcheater-train train --dataset dgraph_fin --data-path data/DGraphFin/DGraphFin1
uv run dgcheater-train train --dataset dgraph_fin2 --data-path data/DGraphFin/DGraphFin2
uv run dgcheater-train train --dataset ieee_cis --data-path data/ieee-fraud-detection
uv run dgcheater-train train --dataset elliptic_pp --data-path data/elliptic-plus-plus
uv run dgcheater-train report-metrics
New-Item -ItemType Directory -Force artifacts/final/report | Out-Null
typst compile --root . docs/report/competition-report.typ artifacts/final/report/competition-report.pdf
```

实时大屏可以单独启动：

```powershell
uv run dgcheater-realtime-api --host 127.0.0.1 --port 8060
```

完整实时链路可以通过以下命令启动：

```powershell
uv run dev-system
```

## 当前结论

- 官方 `DGraph-Fin` 数据上，当前默认方案验证 AUC 约为 `0.8281`
- 官方 `DGraph-Fin2` 数据上，去除会泄漏目标的节点时间标签后，当前可信验证 AUC 约为 `0.8279`
- `IEEE-CIS` 数据上，改成基于 `TransactionDT` 的时间切分后，当前可信验证 AUC 约为 `0.9146`
- `EllipticPlusPlus` 在修正实现口径后，当前严格复核结果约为 `0.9266`
- 已形成多源仿真、实时评分、告警队列、团伙关系图、人工复核和审计留痕闭环
- 已新增 Vue 实时大屏，可查看交易监测、风险评分、告警队列、团伙追溯和复核结果

这些结果均来自当前已接入公开数据和本地实验产物。

## 多数据集扩展

当前工程已经扩展出统一数据集注册表，见 [public-datasets.md](docs/datasets/public-datasets.md)。

已注册的数据集包括：

- `dgraph_fin`
- `dgraph_fin2`
- `ieee_cis`
- `elliptic_pp`
- `ibm_aml`
- `amlsim_sample`

其中 `dgraph_fin` 和 `dgraph_fin2` 现在都已经接入当前框架，支持直接读取官方 `DGraphFin.zip` 与 `DGraphFin2.zip`。

`ieee_cis` 也已经接入当前框架，支持直接读取官方 `ieee-fraud-detection.zip`，自动完成交易表与身份表拼接、统一类别编码与提交文件生成。

`elliptic_pp` 也已经接入当前框架，支持直接读取当前下载的双 zip 包，自动构造地址级图数据并训练。

目前已经确认 `DGraphFin2.zip` 本身只包含 `dgraphfinv2_edge_timestamp.npy` 与 `dgraphfinv2_node_timestamp.npy` 两个时间文件，本质上是 `DGraph-Fin` 的时间增强包。当前工程会自动与 `DGraphFin.zip` 里的基础图组合加载。

需要注意的是，`DGraph-Fin2` 的节点时间标签在当前二分类任务设定下会直接暴露正类身份，因此本项目默认不会把节点时间标签本身作为训练特征，以避免得到虚高且不可用的离线分数。

`amlsim_sample` 已经完成接入并跑通训练链路，但由于样例过小，验证折可能只含单一类别，因此当前更适合作为 AML 仿真样例与工程接入验证，而不是正式 AUC 对比集。

需要注意的是，`IEEE-CIS` 在随机分层切分下会得到更乐观的离线结果，因此当前项目已改为基于 `TransactionDT` 的时间切分口径。

也需要注意的是，`EllipticPlusPlus` 这条线已经查出两层问题。第一层是我们历史实现里的口径问题，包括把 `Time step` 直接喂入特征、用地址最后出现时间伪造边时间戳，以及验证口径回退到训练段内随机切分；修正后分数从接近满分回落到约 `0.9266`。第二层是数据集本身的 actors csv 会把同一地址的全生命周期钱包特征重复贴在多个时间步行里，因此它更像公开 AML actor 分类补充集，而不是严格在线因果时序基准，不适合直接拿绝对分数与图节点反欺诈基准对比难度。
