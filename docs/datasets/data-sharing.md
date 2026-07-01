# 数据集获取与演示包说明

这份文档用于给评委、同学或部署机器说明：哪些数据需要下载，下载后放到哪里，以及只看实时大屏时最小需要哪些文件。

## 当前项目会用到的数据

| 用途 | 数据 | 获取入口 | 是否需要登录 | 放置目录 |
| --- | --- | --- | --- | --- |
| 主图模型训练和账户风险先验 | DGraph-Fin | <https://dgraph.xinye.com/dataset> | 需要 | `data/DGraphFin/DGraphFin1` |
| 时间增强图数据复核 | DGraph-Fin2 | <https://dgraph.xinye.com/dataset> | 需要 | `data/DGraphFin/DGraphFin2` |
| 表格交易欺诈验证 | IEEE-CIS Fraud Detection | <https://www.kaggle.com/c/ieee-fraud-detection> | 需要 Kaggle 账号 | `data/ieee-fraud-detection` |
| 区块链反洗钱图验证 | Elliptic++ | <https://github.com/git-disl/EllipticPlusPlus> | 仓库不需要，数据云盘视访问情况而定 | `data/elliptic-plus-plus` |
| Elliptic++ 原始数据云盘 | Elliptic++ Google Drive | <https://drive.google.com/drive/folders/1MRPXz79Lu_JGLlJ21MDfML44dKN9R08l?usp=sharing> | 视 Google 云盘访问情况而定 | `data/elliptic-plus-plus` |
| 合成反洗钱交易数据 | IBM AML Kaggle 数据集 | <https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml> | 需要 Kaggle 账号 | `data/ibm-aml` |
| 小型反洗钱演示样例 | AMLSim | <https://github.com/IBM/AMLSim> | 不需要 | `data/amlsim/sample/outputs` |
| IBM 合成数据说明论文 | IBM Research 说明页 | <https://research.ibm.com/publications/realistic-synthetic-financial-transactions-for-anti-money-laundering-models> | 不需要 | 说明资料，不是代码必需文件 |

## 最小演示包

只展示实时大屏和数据源切换时，不需要把所有公开大数据集都带上。最小演示包只需要：

- `data/amlsim/sample/outputs/accounts.csv`
- `data/amlsim/sample/outputs/tx.csv`
- `data/amlsim/sample/outputs/alerts.csv`
- `data/amlsim/sample/outputs/cash_tx.csv`
- `data/runtime-artifacts/output/realtime/dgraph_account_prior_12000.joblib`
- `data/runtime-artifacts/output/realtime/models/xgboost.joblib`
- `data/runtime-artifacts/output/realtime/models/lightgbm_aux.joblib`
- `data/runtime-artifacts/output/realtime/models/metadata.json`
- `data/runtime-artifacts/output/dgraph_fin/models/xgboost.joblib`
- `data/runtime-artifacts/output/dgraph_fin/models/lightgbm_aux.joblib`
- `data/runtime-artifacts/output/dgraph_fin/metrics/xgboost_metrics.json`

实时大屏直接读取 `data/runtime-artifacts/output` 下的运行产物。因此新机器只要把完整 `data/` 目录挂载到项目根目录，就能让实时大屏加载账户风险先验，不要求项目根目录存在 `output/`。

当前已生成的演示包位置：

```text
artifacts/share/zhijian-liudun-demo-data-runtime.zip
```

解压时保持目录结构不变，直接覆盖到项目根目录即可。解压后，实时大屏可以使用内置仿真数据、DGraph 风险先验回放和 AMLSim 样例数据。IEEE-CIS 选项需要另行下载 Kaggle 数据后才可复现。

## 为什么不把大数据直接打进仓库

`data` 目录默认是本地数据目录，大型生成结果放入 `artifacts` 或 `tmp`，仓库通过 `.gitignore` 忽略它们。这样做有三个原因：

- DGraph-Fin 和 IEEE-CIS 单文件体积很大，不适合放进代码仓库。
- 部分数据集需要登录或遵守平台协议，不能直接二次分发。
- 评委复现时更清楚：代码从仓库拿，公开数据从官方入口拿，演示缓存从演示包拿。

## Google 云盘上传方式

Google 云盘上传需要账号授权。本机当前没有可用的命令行上传工具。推荐使用 `rclone`：

```powershell
rclone config
rclone copy artifacts/share/zhijian-liudun-demo-data-runtime.zip gdrive:zhijian-liudun/
```

其中 `gdrive:` 是你本机配置的 Google 云盘名称。配置完成后，再执行上传命令即可。
