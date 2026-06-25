import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# --- 设置 Matplotlib 支持中文 ---
# 请确保你的环境中安装了支持中文的字体，例如 'SimHei' (黑体)
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False  # 用来正常显示负号

# --- 1. 加载数据 ---
NPZ_PATH = "../phase1_gdata.npz"
print(f"Loading data from {NPZ_PATH}...\n")
try:
    data = np.load(NPZ_PATH, allow_pickle=True)
except FileNotFoundError:
    print(f"Error: 找不到文件 {NPZ_PATH}")
    print("请确保文件在正确的路径下。")
    exit()

x = data["x"]
y = data["y"].squeeze()
edge_index = data["edge_index"].astype(np.int64)
edge_type = data["edge_type"].squeeze()
edge_timestamp = data["edge_timestamp"].squeeze()
train_mask = data["train_mask"].astype(np.int64)
test_mask = data["test_mask"].astype(np.int64)

N_node = x.shape[0]
N_edge = edge_index.shape[0]

print("--- 📊 1. 图的概览 ---")
print(f"  节点总数 (N_node): {N_node}")
print(f"  有向边总数 (N_edge): {N_edge}")
print(f"  平均度数 (N_edge / N_node): {N_edge / N_node:.2f}")

# 检查自环边
self_loops = np.sum(edge_index[:, 0] == edge_index[:, 1])
print(f"  自环边数量: {self_loops}")

# 检查重复边 (具有相同源、目标、类型的边)
# 注意：这可能需要较多内存
# unique_edges = set(tuple(row) for row in np.hstack([edge_index, edge_type.reshape(-1, 1)]))
# N_unique_edge = len(unique_edges)
# print(f"  去重后边数: {N_unique_edge} (去重了 {N_edge - N_unique_edge} 条边)")
print(f"  节点特征维度: {x.shape[1]}")

print("\n--- 🏷️ 2. 节点与标签分析 ---")
# 使用 Pandas 进行快速统计
y_series = pd.Series(y)
label_counts = y_series.value_counts().sort_index()
print("  (A) 所有节点的标签分布:")
for label, count in label_counts.items():
    if label == -100:
        print(f"    Label -100 (测试集): {count} 个")
    else:
        print(f"    Label {int(label)}: {count} 个")

# 分析训练集中的标签
y_train = y[train_mask]
y_train_series = pd.Series(y_train)
train_label_counts = y_train_series.value_counts().sort_index()

print("\n  (B) 训练集 (train_mask) 的标签分布:")
if y_train_series.empty:
    print("    训练集为空或没有标签。")
else:
    for label, count in train_label_counts.items():
        print(f"    Label {int(label)}: {count} 个 (占训练集 {count / len(y_train):.2%})")

    # 绘制训练集标签分布图
    plt.figure(figsize=(10, 5))
    train_label_counts.plot(kind='bar', color='skyblue')
    plt.title(f'训练集标签分布 (共 {len(y_train)} 个样本)')
    plt.xlabel('节点标签')
    plt.ylabel('数量')
    plt.xticks(rotation=0)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.savefig("analysis_train_label_distribution.png")
    print("\n  [已保存] 训练集标签分布图 -> analysis_train_label_distribution.png")

print(f"\n  训练集大小 (train_mask): {len(train_mask)}")
print(f"  测试集大小 (test_mask): {len(test_mask)}")
print(f"  有标签的节点总数: {np.sum(y != -100)}")

print("\n--- 🔗 3. 边与时间分析 ---")
# 边类型
edge_type_series = pd.Series(edge_type)
edge_type_counts = edge_type_series.value_counts().sort_index()
print(f"  (A) 边类型 (共 {len(edge_type_counts)} 种):")
print(edge_type_counts.to_string())

# 绘制边类型分布图
plt.figure(figsize=(12, 6))
edge_type_counts.plot(kind='bar', color='coral')
plt.title(f'边类型分布 (共 {N_edge} 条边)')
plt.xlabel('边类型')
plt.ylabel('数量')
plt.xticks(rotation=45)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig("analysis_edge_type_distribution.png")
print("\n  [已保存] 边类型分布图 -> analysis_edge_type_distribution.png")

# 时间戳
min_day = edge_timestamp.min()
max_day = edge_timestamp.max()
print(f"\n  (B) 边时间戳 (单位: 天):")
print(f"    最早日期: 第 {min_day} 天")
print(f"    最晚日期: 第 {max_day} 天")
print(f"    时间跨度: {max_day - min_day + 1} 天")

# 绘制边的时间分布直方图
plt.figure(figsize=(14, 6))
# 使用 100 个 bin 来查看细节
bins_count = min(100, max_day - min_day + 1)
plt.hist(edge_timestamp, bins=bins_count, color='green', alpha=0.7)
plt.title('边的时间分布 (活跃度随时间变化)')
plt.xlabel('天 (Day)')
plt.ylabel('边的数量')
plt.gca().xaxis.set_major_locator(ticker.MaxNLocator(integer=True))  # 保证x轴为整数
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.savefig("analysis_edge_time_distribution.png")
print("\n  [已保存] 边的时间分布图 -> analysis_edge_time_distribution.png")

print("\n--- 📈 4. 节点度(Degree)分析 ---")
in_degree = np.bincount(edge_index[:, 1], minlength=N_node)
out_degree = np.bincount(edge_index[:, 0], minlength=N_node)
total_degree = in_degree + out_degree

print("  (A) 入度 (In-Degree) 统计:")
print(f"    平均值: {np.mean(in_degree):.2f}, 标准差: {np.std(in_degree):.2f}")
print(f"    最小: {np.min(in_degree)}, 中位数: {np.median(in_degree)}, 最大: {np.max(in_degree)}")

print("\n  (B) 出度 (Out-Degree) 统计:")
print(f"    平均值: {np.mean(out_degree):.2f}, 标准差: {np.std(out_degree):.2f}")
print(f"    最小: {np.min(out_degree)}, 中位数: {np.median(out_degree)}, 最大: {np.max(out_degree)}")

print("\n  (C) 总度数 (Total Degree) 统计:")
print(f"    平均值: {np.mean(total_degree):.2f}, 标准差: {np.std(total_degree):.2f}")
print(f"    最小: {np.min(total_degree)}, 中位数: {np.median(total_degree)}, 最大: {np.max(total_degree)}")

# 绘制度分布直方图 (使用对数刻度)
plt.figure(figsize=(18, 6))
plt.subplot(1, 3, 1)
plt.hist(in_degree, bins=50, color='blue', alpha=0.7)
plt.yscale('log')  # 度分布通常是长尾的，使用对数刻度
plt.title('入度分布 (Log Scale)')
plt.xlabel('入度')
plt.ylabel('节点数量 (Log)')

plt.subplot(1, 3, 2)
plt.hist(out_degree, bins=50, color='red', alpha=0.7)
plt.yscale('log')
plt.title('出度分布 (Log Scale)')
plt.xlabel('出度')
plt.ylabel('节点数量 (Log)')

plt.subplot(1, 3, 3)
plt.hist(total_degree, bins=50, color='purple', alpha=0.7)
plt.yscale('log')
plt.title('总度数分布 (Log Scale)')
plt.xlabel('总度数')
plt.ylabel('节点数量 (Log)')

plt.tight_layout()
plt.savefig("analysis_degree_distribution.png")
print("\n  [已保存] 度分布图 -> analysis_degree_distribution.png")

print("\n--- 🔬 5. 节点特征 (x) 分析 ---")
# 使用 Pandas DataFrame 来进行描述性统计
x_df = pd.DataFrame(x, columns=[f"feat_{i}" for i in range(x.shape[1])])
x_desc = x_df.describe()
print("  17维节点特征的描述性统计:")
print(x_desc.to_string())

# 检查特征中0的稀疏度
sparsity = (x == 0).sum() / x.size
print(f"\n  特征矩阵稀疏度 (0的比例): {sparsity:.2%}")

print("\n--- 分析完成 ---")