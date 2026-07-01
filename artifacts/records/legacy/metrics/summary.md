# 训练结果摘要

- 模型: xgboost_lightgbm_graph_blend
- 验证 AUC: 0.832586
- 训练样本数: 744612
- 验证样本数: 82735
- 训练集正样本比例: 0.011806
- 特征数: 126
- 模型文件: `output\models\xgboost.joblib`
- 辅助模型文件: `output\models\lightgbm_aux.joblib`
- 提交文件: `output\submissions\submission.npy`
- 融合规则: `0.9 * xgboost + 0.1 * lightgbm`