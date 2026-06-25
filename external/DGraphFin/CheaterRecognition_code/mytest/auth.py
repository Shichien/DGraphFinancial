import numpy as np
import pandas as pd

# --- 1. 加载数据 ---
NPZ_PATH = "../phase1_gdata.npz"
print(f"Loading data from {NPZ_PATH}...")
try:
    data = np.load(NPZ_PATH, allow_pickle=True)
except FileNotFoundError:
    print(f"Error: 找不到文件 {NPZ_PATH}")
    exit()

y = data["y"].squeeze()
edge_index = data["edge_index"].astype(np.int64)
edge_type = data["edge_type"].squeeze()
train_mask = data["train_mask"].astype(np.int64)
N = data["x"].shape[0]

# --- 2. 计算每种类型的边 ---
# (这部分逻辑和你 GBDT 脚本中的一致)
num_types = int(edge_type.max() + 1)
print(f"Nodes = {N}, Found {num_types} edge types.")

# in_type_count[i, t] = 节点 i 作为“目标”时，类型 t 边的数量
# out_type_count[i, t] = 节点 i 作为“源头”时，类型 t 边的数量
in_type_count = np.zeros((N, num_types), dtype=np.float32)
out_type_count = np.zeros((N, num_types), dtype=np.float32)

np.add.at(out_type_count, (edge_index[:, 0], edge_type), 1)
np.add.at(in_type_count, (edge_index[:, 1], edge_type), 1)

# --- 3. 找到有标签的 欺诈/正常 节点 ---
# 我们只分析在 train_mask 中，且标签为 0 或 1 的节点
train_idx_labeled = train_mask[y[train_mask] != -100]
y_labeled = y[train_idx_labeled]

fraud_indices = train_idx_labeled[y_labeled == 1]
normal_indices = train_idx_labeled[y_labeled == 0]

print(f"Analyzing {len(fraud_indices)} fraud nodes vs. {len(normal_indices)} normal nodes.")

if len(fraud_indices) == 0:
    print("错误：在训练集中未找到 y=1 的欺诈节点。")
    exit()

# --- 4. 聚合两组的“边类型”总和 ---
# 欺诈节点总共收到了多少条每种类型的边
fraud_in_type_sum = in_type_count[fraud_indices].sum(axis=0)
# 正常节点总共收到了多少条每种类型的边
normal_in_type_sum = in_type_count[normal_indices].sum(axis=0)

# 欺诈节点总共发出了多少条每种类型的边
fraud_out_type_sum = out_type_count[fraud_indices].sum(axis=0)
# 正常节点总共发出了多少条每种类型的边
normal_out_type_sum = out_type_count[normal_indices].sum(axis=0)

# --- 5. 计算分布并打印 ---
# (我们用总和 + 1e-9 来避免除以 0)
df = pd.DataFrame({
    # "入边" (作为目标)
    'Fraud_In_Dist': fraud_in_type_sum / (fraud_in_type_sum.sum() + 1e-9),
    'Normal_In_Dist': normal_in_type_sum / (normal_in_type_sum.sum() + 1e-9),

    # "出边" (作为源头)
    'Fraud_Out_Dist': fraud_out_type_sum / (fraud_out_type_sum.sum() + 1e-9),
    'Normal_Out_Dist': normal_out_type_sum / (normal_out_type_sum.sum() + 1e-9),

    # 原始计数 (供参考)
    'Fraud_In_Count': fraud_in_type_sum,
    'Normal_In_Count': normal_in_type_sum,
    'Fraud_Out_Count': fraud_out_type_sum,
    'Normal_Out_Count': normal_out_type_sum,
})

# 格式化输出
df.index.name = "Edge Type"
pd.set_option('display.float_format', '{:,.4f}'.format)  # 格式化为 4 位小数

print("\n" + "=" * 80)
print("--- 边类型与欺诈标签的交叉分析 ---")
print("  (比较 Fraud_In_Dist 和 Normal_In_Dist，看分布是否有巨大差异)")
print("=" * 80)
print(df.to_string())
print("=" * 80)

# --- 6. 最终结论 ---
print("\n--- 结论 ---")
print("请看上面的表格，特别是 'Dist' (分布) 列：")
print("1. [黄金特征？] 如果你发现某个 Edge Type (例如 9)，")
print("   'Fraud_In_Dist' = 0.30 (30%) 而 'Normal_In_Dist' = 0.00 (0%)，")
print("   那么恭喜你，`in_type_ratio_9` 就是一个黄金特征！")
print("\n2. [不是黄金特征] 如果 'Fraud_...' 和 'Normal_...' 的分布**大致相似**，")
print("   (例如，类型 3 在两边都是 20%，类型 5 在两边都是 10%)...")
print("   ...那么这就证明了：**不存在**简单的“黄金边类型”。")
print("   那个 0.9958 的分数，几乎 100% 是通过**数据泄露**（Data Leakage）得到的。")