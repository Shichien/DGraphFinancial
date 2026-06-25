import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix, csr_matrix
from scipy.stats import skew, kurtosis, entropy
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.ensemble import HistGradientBoostingClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
import lightgbm as lgb
import optuna


USELESS_FEATURES = ['deg_norm', 'last_active_norm', 'recent_7', 'recent_active', 'active_span_ratio', 'deg_squared', 'active_long', 'triangles_out_in', 'deg_skew', 'deg_kurt', 'num_in_neighbors', 'num_out_neighbors', 'in_type_ratio_0', 'triangles_all', 'triangles_in_out', 'out_type_ratio_0', 'deg_log', 'deg_diff_squared', 'deg_squared_2', 'active_span_squared']
# -----------------------------------------------------------------
# --- 步骤 1：特征工程 (带命名) ---
# -----------------------------------------------------------------

NPZ_PATH = "../phase1_gdata.npz"
print("Loading npz:", NPZ_PATH)
data = np.load(NPZ_PATH, allow_pickle=True)

x = data["x"].astype(np.float32)
y = data["y"].squeeze()
edge_index = data["edge_index"].astype(np.int64)
edge_type = data["edge_type"].squeeze()
edge_timestamp = data["edge_timestamp"].squeeze()
train_mask = data["train_mask"].astype(np.int64)
test_mask = data["test_mask"].astype(np.int64)

N = x.shape[0]
E = edge_index.shape[0]
print(f"Nodes = {N}, Features = {x.shape}, Edges = {E}")

# (!!!) 我们创建两个列表：一个装特征数组，一个装特征名称
all_feature_arrays = []
all_feature_names = []

# --- 1. 原始 x 特征 ---
all_feature_arrays.append(x)
all_feature_names.extend([f'x_{i}' for i in range(x.shape[1])])  # 17 个
print(f"Added {x.shape[1]} original x features.")

# --- 2. 窗口特征 recent_feats ---
max_day = int(edge_timestamp.max())
win_base = np.array([3, 7, 14, 30, 60, 90, 180], dtype=np.int32)
win_days = np.concatenate([win_base, max_day - win_base])
win_threshold = max_day - win_days
W = len(win_threshold)
edge_ts = edge_timestamp.reshape(-1, 1)
mask = edge_ts >= win_threshold.reshape(1, -1)
nodes_flat = np.concatenate([edge_index[:, 0], edge_index[:, 1]])
mask_flat = np.concatenate([mask, mask], axis=0)
recent_feats_list = []
win_names = [f'recent_{d}' for d in win_base] + [f'recent_hist_{d}' for d in win_base]
for w in range(W):
    feat = np.bincount(nodes_flat, weights=mask_flat[:, w].astype(np.float32), minlength=N)
    recent_feats_list.append(feat.reshape(-1, 1))
all_feature_names.extend(win_names)  # 14 个
recent_feats = np.concatenate(recent_feats_list, axis=1)
all_feature_arrays.append(recent_feats)
print(f"Added {len(win_names)} recent_feats features.")

# --- 3. 基础结构特征 (in_deg, out_deg, min/max_day) ---
out_deg = np.bincount(edge_index[:, 0], minlength=N).astype(np.float32)
in_deg = np.bincount(edge_index[:, 1], minlength=N).astype(np.float32)
all_feature_arrays.extend([in_deg.reshape(-1, 1), out_deg.reshape(-1, 1)])
all_feature_names.extend(['in_deg', 'out_deg'])  # 2 个

min_day = np.full(N, 1e9, dtype=np.float32)
max_day_node = np.full(N, -1e9, dtype=np.float32)
ts_flat = np.concatenate([edge_timestamp, edge_timestamp])
np.minimum.at(min_day, nodes_flat, ts_flat)
np.maximum.at(max_day_node, nodes_flat, ts_flat)
all_feature_arrays.extend([min_day.reshape(-1, 1), max_day_node.reshape(-1, 1)])
all_feature_names.extend(['min_day', 'max_day_node'])  # 2 个
print("Added in_deg, out_deg, min_day, max_day_node.")

# --- 4. new_feats_all ---
deg = in_deg + out_deg
deg_diff = out_deg - in_deg
active_span = max_day_node - min_day
active_span[active_span < 0] = 0
day_sum = np.bincount(nodes_flat, weights=ts_flat, minlength=N)
day_cnt = np.bincount(nodes_flat, minlength=N)
day_mean = day_sum / np.maximum(day_cnt, 1)
day_skew = (max_day_node - day_mean) / (active_span + 1e-6)
deg_norm = deg / np.maximum(day_cnt, 1)
Tmax = max_day_node.max() + 1e-6
time_weight = ts_flat / Tmax
w_out = np.zeros(N, dtype=np.float32)
w_in = np.zeros(N, dtype=np.float32)
np.add.at(w_out, edge_index[:, 0], time_weight[:E])
np.add.at(w_in, edge_index[:, 1], time_weight[E:])
time_weighted_deg = w_out + w_in
mmin = min_day.min()
mmax = min_day.max() + 1e-6
last_active_norm = (max_day_node - mmin) / (mmax - mmin)
X_recent = 30
global_max = max_day_node.max()
recent_active = (max_day_node > global_max - X_recent).astype(np.float32)
median_span = np.median(active_span)
active_long = (active_span > median_span).astype(np.float32)

new_feats_1 = [
    deg, deg_diff, active_span, day_mean, day_skew, deg_norm,
    time_weighted_deg, last_active_norm, active_long, recent_active
]
new_feats_names_1 = [
    'deg', 'deg_diff', 'active_span', 'day_mean', 'day_skew', 'deg_norm',
    'time_weighted_deg', 'last_active_norm', 'active_long', 'recent_active'
]

deg_ratio = out_deg / (in_deg + 1e-6)
active_span_ratio = active_span / (active_span.max() + 1e-6)
last_edge = np.zeros(N, dtype=np.float32)
np.maximum.at(last_edge, nodes_flat, ts_flat)
recent_gap = global_max - last_edge
recent_gap_norm = recent_gap / (global_max + 1e-6)
deg_squared = deg ** 2
deg_diff_abs = np.abs(deg_diff)
span_mean_ratio = active_span / (day_mean + 1e-6)
rows = np.concatenate([edge_index[:, 0], edge_index[:, 1]])
cols = np.concatenate([edge_index[:, 1], edge_index[:, 0]])
adj = coo_matrix((np.ones_like(rows), (rows, cols)), shape=(N, N))
mean_neighbor_deg_base = adj.dot(deg.reshape(-1, 1)).flatten() / np.maximum(adj.sum(axis=1).A1, 1)
sum_ts = np.bincount(nodes_flat, weights=ts_flat, minlength=N)
sum_ts2 = np.bincount(nodes_flat, weights=ts_flat ** 2, minlength=N)
cnt_ts = np.bincount(nodes_flat, minlength=N)
active_std = np.sqrt(np.maximum(0, sum_ts2 / cnt_ts - (sum_ts / cnt_ts) ** 2))
active_std[cnt_ts == 0] = 0
deg_rate = deg / np.maximum(active_span, 1e-6)
deg_skew = np.full(N, skew(deg.astype(np.float64)))
deg_kurt = np.full(N, kurtosis(deg.astype(np.float64)))

new_feats_2 = [
    deg_ratio, active_span_ratio, recent_gap_norm, deg_squared, deg_diff_abs,
    span_mean_ratio, mean_neighbor_deg_base, active_std, deg_rate, deg_skew, deg_kurt
]
new_feats_names_2 = [
    'deg_ratio', 'active_span_ratio', 'recent_gap_norm', 'deg_squared', 'deg_diff_abs',
    'span_mean_ratio', 'mean_neighbor_deg_base', 'active_std', 'deg_rate', 'deg_skew', 'deg_kurt'
]

new_feats_all = np.stack(new_feats_1 + new_feats_2, axis=1)
all_feature_arrays.append(new_feats_all)
all_feature_names.extend(new_feats_names_1 + new_feats_names_2)  # 21 个
print(f"Added {len(new_feats_names_1) + len(new_feats_names_2)} new_feats_all features.")

# --- 5. edge_feats_final (包含 🚀 新增的 STD 特征) ---
rows_in, cols_in = edge_index[:, 1], edge_index[:, 0]
rows_out, cols_out = edge_index[:, 0], edge_index[:, 1]
data_ones = np.ones(E, dtype=np.float32)

A_in = coo_matrix((data_ones, (rows_in, cols_in)), shape=(N, N))
A_out = coo_matrix((data_ones, (rows_out, cols_out)), shape=(N, N))
A_all = ((A_in + A_out) > 0).astype(np.float32)

num_in_neighbors = np.array(A_in.sum(axis=1)).flatten()
num_out_neighbors = np.array(A_out.sum(axis=1)).flatten()
num_all_neighbors = np.array(A_all.sum(axis=1)).flatten()
ratio_in_out_neighbors = num_in_neighbors / np.maximum(num_out_neighbors, 1)

N_in = np.maximum(num_in_neighbors, 1)
N_out = np.maximum(num_out_neighbors, 1)
N_all = np.maximum(num_all_neighbors, 1)

mean_in_deg_neighbors = A_in.dot(in_deg) / N_in
mean_out_deg_neighbors = A_out.dot(out_deg) / N_out
mean_neighbor_deg = A_all.dot(deg) / N_all
mean_last_active_in_neighbors = A_in.dot(max_day_node) / N_in
mean_last_active_out_neighbors = A_out.dot(max_day_node) / N_out

# (🚀 新增) 邻居标准差 (Std)
mean_in_deg_neighbors_sq = A_in.dot(in_deg ** 2) / N_in
mean_out_deg_neighbors_sq = A_out.dot(out_deg ** 2) / N_out
mean_neighbor_deg_sq = A_all.dot(deg ** 2) / N_all
mean_last_active_in_sq = A_in.dot(max_day_node ** 2) / N_in
std_in_deg_neighbors = np.sqrt(np.maximum(0, mean_in_deg_neighbors_sq - mean_in_deg_neighbors ** 2))
std_out_deg_neighbors = np.sqrt(np.maximum(0, mean_out_deg_neighbors_sq - mean_out_deg_neighbors ** 2))
std_neighbor_deg = np.sqrt(np.maximum(0, mean_neighbor_deg_sq - mean_neighbor_deg ** 2))
std_last_active_in = np.sqrt(np.maximum(0, mean_last_active_in_sq - mean_last_active_in_neighbors ** 2))
print("Added 4 new STD (standard deviation) features.")

recent_active_mask = (max_day_node > global_max - X_recent).astype(np.float32)
recent_active_in_neighbors = A_in.dot(recent_active_mask) / N_in
recent_active_out_neighbors = A_out.dot(recent_active_mask) / N_out
A2_in = A_in.dot(A_in)
A2_out = A_out.dot(A_out)
num_2hop_in_neighbors = np.array(A2_in.sum(axis=1)).flatten()
num_2hop_out_neighbors = np.array(A2_out.sum(axis=1)).flatten()
mean_2hop_in_deg_neighbors = A2_in.dot(in_deg) / np.maximum(num_2hop_in_neighbors, 1)
mean_2hop_out_deg_neighbors = A2_out.dot(out_deg) / np.maximum(num_2hop_out_neighbors, 1)
A3_all = A_all.dot(A_all.dot(A_all))
num_3hop_neighbors = np.array(A3_all.sum(axis=1)).flatten()
mean_3hop_deg = A3_all.dot(deg) / np.maximum(num_3hop_neighbors, 1)
triangles_in_out = np.array(A_in.dot(A_out).diagonal()).astype(np.float32)
triangles_out_in = np.array(A_out.dot(A_in).diagonal()).astype(np.float32)
triangles_all = np.array(A_all.dot(A_all).diagonal()).astype(np.float32)
num_types = int(edge_type.max() + 1)
in_type_count = np.zeros((N, num_types), dtype=np.float32)
out_type_count = np.zeros((N, num_types), dtype=np.float32)
np.add.at(out_type_count, (edge_index[:, 0], edge_type), 1)
np.add.at(in_type_count, (edge_index[:, 1], edge_type), 1)
in_type_ratio = in_type_count / np.maximum(in_type_count.sum(axis=1, keepdims=True), 1)
out_type_ratio = out_type_count / np.maximum(out_type_count.sum(axis=1, keepdims=True), 1)
type_entropy_in = entropy(in_type_ratio.T + 1e-6)
type_entropy_out = entropy(out_type_ratio.T + 1e-6)
type_var_in = in_type_ratio.var(axis=1)
type_var_out = out_type_ratio.var(axis=1)
last_edge_out = np.zeros(N, dtype=np.float32)
last_edge_in = np.zeros(N, dtype=np.float32)
np.maximum.at(last_edge_out, edge_index[:, 0], edge_timestamp)
np.maximum.at(last_edge_in, edge_index[:, 1], edge_timestamp)
gap_last_edge_out = global_max - last_edge_out
gap_last_edge_in = global_max - last_edge_in
sum_ts_out = np.zeros(N, dtype=np.float32)
cnt_out = np.zeros(N, dtype=np.float32)
np.add.at(sum_ts_out, edge_index[:, 0], edge_timestamp)
np.add.at(cnt_out, edge_index[:, 0], 1)
avg_edge_time_out = sum_ts_out / np.maximum(cnt_out, 1)
sum_ts_in = np.zeros(N, dtype=np.float32)
cnt_in = np.zeros(N, dtype=np.float32)
np.add.at(sum_ts_in, edge_index[:, 1], edge_timestamp)
np.add.at(cnt_in, edge_index[:, 1], 1)
avg_edge_time_in = sum_ts_in / np.maximum(cnt_in, 1)
time_decay = np.exp(-(global_max - edge_timestamp) / global_max)
w_out_decay = np.zeros(N, dtype=np.float32)
w_in_decay = np.zeros(N, dtype=np.float32)
np.add.at(w_out_decay, edge_index[:, 0], time_decay)
np.add.at(w_in_decay, edge_index[:, 1], time_decay)
deg_squared_2 = deg ** 2
deg_diff_squared = deg_diff ** 2
deg_log = np.log1p(deg)
active_span_2 = max_day_node - np.minimum(np.zeros_like(max_day_node), 0)
active_span_squared = active_span_2 ** 2
deg_z = (deg - deg.mean()) / (deg.std() + 1e-6)
neighbor_deg_z = (mean_neighbor_deg - mean_neighbor_deg.mean()) / (mean_neighbor_deg.std() + 1e-6)
active_z = (max_day_node - max_day_node.mean()) / (max_day_node.std() + 1e-6)

edge_feats_final_list = [
    num_in_neighbors.reshape(-1, 1), num_out_neighbors.reshape(-1, 1), num_all_neighbors.reshape(-1, 1),
    ratio_in_out_neighbors.reshape(-1, 1), mean_in_deg_neighbors.reshape(-1, 1), mean_out_deg_neighbors.reshape(-1, 1),
    mean_last_active_in_neighbors.reshape(-1, 1), mean_last_active_out_neighbors.reshape(-1, 1),

    # (🚀 新增) 拼接 Std 特征
    std_in_deg_neighbors.reshape(-1, 1),
    std_out_deg_neighbors.reshape(-1, 1),
    std_neighbor_deg.reshape(-1, 1),
    std_last_active_in.reshape(-1, 1),

    recent_active_in_neighbors.reshape(-1, 1), recent_active_out_neighbors.reshape(-1, 1),
    num_2hop_in_neighbors.reshape(-1, 1), num_2hop_out_neighbors.reshape(-1, 1),
    mean_2hop_in_deg_neighbors.reshape(-1, 1), mean_2hop_out_deg_neighbors.reshape(-1, 1),
    num_3hop_neighbors.reshape(-1, 1), mean_3hop_deg.reshape(-1, 1),
    triangles_in_out.reshape(-1, 1), triangles_out_in.reshape(-1, 1), triangles_all.reshape(-1, 1),
    in_type_ratio, out_type_ratio,
    type_var_in.reshape(-1, 1), type_var_out.reshape(-1, 1),
    gap_last_edge_in.reshape(-1, 1), gap_last_edge_out.reshape(-1, 1),
    avg_edge_time_in.reshape(-1, 1), avg_edge_time_out.reshape(-1, 1),
    w_in_decay.reshape(-1, 1), w_out_decay.reshape(-1, 1),
    deg_squared_2.reshape(-1, 1), deg_diff_squared.reshape(-1, 1), deg_log.reshape(-1, 1),
    active_span_squared.reshape(-1, 1), deg_z.reshape(-1, 1), neighbor_deg_z.reshape(-1, 1),
    active_z.reshape(-1, 1),
]

edge_feats_final_names = [
    'num_in_neighbors', 'num_out_neighbors', 'num_all_neighbors',
    'ratio_in_out_neighbors', 'mean_in_deg_neighbors', 'mean_out_deg_neighbors',
    'mean_last_active_in_neighbors', 'mean_last_active_out_neighbors',

    # (🚀 新增) Std 特征命名
    'std_in_deg_neighbors', 'std_out_deg_neighbors',
    'std_neighbor_deg', 'std_last_active_in',

    'recent_active_in_neighbors', 'recent_active_out_neighbors',
    'num_2hop_in_neighbors', 'num_2hop_out_neighbors',
    'mean_2hop_in_deg_neighbors', 'mean_2hop_out_deg_neighbors',
    'num_3hop_neighbors', 'mean_3hop_deg',
    'triangles_in_out', 'triangles_out_in', 'triangles_all'
]
edge_feats_final_names.extend([f'in_type_ratio_{i}' for i in range(num_types)])
edge_feats_final_names.extend([f'out_type_ratio_{i}' for i in range(num_types)])
edge_feats_final_names.extend([
    'type_var_in', 'type_var_out',
    'gap_last_edge_in', 'gap_last_edge_out',
    'avg_edge_time_in', 'avg_edge_time_out',
    'w_in_decay', 'w_out_decay',
    'deg_squared_2', 'deg_diff_squared', 'deg_log',
    'active_span_squared', 'deg_z', 'neighbor_deg_z', 'active_z'
])
edge_feats_final = np.concatenate(edge_feats_final_list, axis=1)
all_feature_arrays.append(edge_feats_final)
all_feature_names.extend(edge_feats_final_names)
print(f"Added {len(edge_feats_final_names)} edge_feats_final features (incl. 4 new STD).")
# 总特征数 = 17 (x) + 14 (recent) + 4 (base) + 21 (new) + 62 (final_no_std) + 4 (std) = 122
# 修正：你的脚本显示 118 个，我的 find_feature 脚本也是 118 个。
# 17 (x) + 14 (recent) + 4 (base) + 21 (new) + 62 (final_with_std) = 118
# edge_feats_final_names 列表是 62 个。
# 17 + 14 + 4 + 21 = 56
# 56 + 62 = 118. OK.

# -----------------------------------------------------------------
# --- 步骤 2：组合与精炼 (RFE) ---
# -----------------------------------------------------------------
print("\n--- Assembling & Refining Features ---")

# (!!! 关键) 这是你刚刚运行 find_features.py 找出的 25 个“琐碎特征”
# 我已为你复制粘贴
TRIVIAL_FEATURES = [
    'out_type_ratio_2', 'in_type_ratio_7', 'deg_z', 'recent_14', 'recent_7',
    'deg_norm', 'last_active_norm', 'recent_3', 'recent_active',
    'active_span_ratio', 'deg_squared', 'active_long', 'triangles_out_in',
    'deg_skew', 'deg_kurt', 'num_in_neighbors', 'num_out_neighbors',
    'in_type_ratio_0', 'triangles_all', 'triangles_in_out',
    'out_type_ratio_0', 'deg_log', 'deg_diff_squared', 'deg_squared_2',
    'active_span_squared'
]
print(f"Defined {len(TRIVIAL_FEATURES)} trivial features to remove (based on 99.9% threshold).")

# 1. 组合所有特征
X_all = np.concatenate(all_feature_arrays, axis=1).astype(np.float32)

# 2. 检查名称和数组是否对齐 (总共 118 个特征)
if X_all.shape[1] != len(all_feature_names):
    print(f"!!! 严重错误：特征数量 {X_all.shape[1]} 与名称数量 {len(all_feature_names)} 不匹配 !!!")
    exit()
else:
    print(f"Total features before removal: {X_all.shape[1]}")

# 3. 找到要删除的特征的索引
useless_indices = []
for f_name in TRIVIAL_FEATURES:
    if f_name in all_feature_names:
        useless_indices.append(all_feature_names.index(f_name))
    else:
        print(f"Warning: Trivial feature '{f_name}' not found in feature list.")

useless_indices = sorted(list(set(useless_indices)), reverse=True)  # 排序后反转，方便删除
print(f"Found {len(useless_indices)} features to remove by index.")

# 4. (!!!) 从 X_all 和 all_feature_names 中删除它们
X_final = np.delete(X_all, useless_indices, axis=1)

# 也从名称列表中删除，以便调试
for index in useless_indices:
    all_feature_names.pop(index)

# 118 - 25 = 93
print(f"Final features after removal: {X_final.shape[1]} (Names: {len(all_feature_names)})")

# -----------------------------------------------------------------
# --- 步骤 3：准备训练 (逻辑不变，但使用 X_final) ---
# -----------------------------------------------------------------

X = X_final  # (!!!) 使用我们精炼后的 93 维 X
D = X.shape[1]
print("Final X shape:", X.shape)

# 二分类 (只关心 y==1)
y_bin = np.zeros(N, dtype=np.int64)
mask_label = (y != -100)
y_bin[mask_label] = (y[mask_label] == 1).astype(np.int64)

# train/val split
train_idx = train_mask[y[train_mask] != -100]
train_idx_local, val_idx_local = train_test_split(
    train_idx,
    test_size=0.1,
    random_state=42,
    stratify=y_bin[train_idx]
)

print("Train:", len(train_idx_local),
      "Val:", len(val_idx_local),
      "Test:", len(test_mask))

# 准备数据
X_train_all = X[train_idx_local]
y_train_all = y_bin[train_idx_local]

X_val = X[val_idx_local]
y_val = y_bin[val_idx_local]

# -----------------------------------------------------------------
# --- 步骤 4：采样 (使用你最好的 1:3 策略) ---
# -----------------------------------------------------------------
pos_idx = np.where(y_train_all == 1)[0]
neg_idx = np.where(y_train_all == 0)[0]
print("\n原始类数量：pos =", len(pos_idx), "neg =", len(neg_idx))

N_NEG_RATIO = 3  # (!!!) 使用你验证过的 1:3 最佳比例
N_CHUNKS = 9  # 保持 9 个模型

chunk_size = int(len(pos_idx)) * N_NEG_RATIO
neg_chunks = [neg_idx[i:i + chunk_size] for i in range(0, len(neg_idx), chunk_size)]

if len(neg_chunks) == 0 or chunk_size == 0:
    print("错误：负样本或正样本为0，无法创建块。")
    exit()

if len(neg_chunks) < N_CHUNKS:
    neg_chunks = (neg_chunks * (N_CHUNKS // len(neg_chunks) + 1))[:N_CHUNKS]
else:
    neg_chunks = neg_chunks[:N_CHUNKS]
print(f"使用 1:{N_NEG_RATIO} 采样比例，共 {len(neg_chunks)} 个训练子集")

train_chunks_idx = []
n_pos_sample = int(len(pos_idx))
for neg_chunk in neg_chunks:
    pos_sample_idx = np.random.choice(pos_idx, size=n_pos_sample, replace=False)
    train_idx_chunk = np.concatenate([pos_sample_idx, neg_chunk])
    np.random.shuffle(train_idx_chunk)
    train_chunks_idx.append(train_idx_chunk)

# 准备 Optuna 调参数据 (在 1:3 平衡块上)
optuna_train_idx = train_chunks_idx[0]
X_train_optuna = X_train_all[optuna_train_idx]
y_train_optuna = y_train_all[optuna_train_idx]
print(f"Optuna 将在 1:3 平衡的、{X_train_optuna.shape[1]} 维的子集上调参...")

# -----------------------------------------------------------------
# --- 步骤 5：Optuna 自动调参 (在精炼后的数据上) ---
# -----------------------------------------------------------------
print("\n--- 🚀 开始 Optuna 超参数调优 (for LightGBM) ---")
print("这会运行 50 次试验以找到最佳参数，请耐心等待...")


def objective(trial):
    params = {
        'objective': 'binary',
        'metric': 'auc',
        'verbosity': -1,
        'boosting_type': 'gbdt',
        'n_jobs': -1,
        'n_estimators': trial.suggest_int('n_estimators', 200, 2500),  # 增加搜索空间
        'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.05, log=True),  # 缩小学习率
        'num_leaves': trial.suggest_int('num_leaves', 20, 300),
        'max_depth': trial.suggest_int('max_depth', 5, 20),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 1.0),
        'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 1.0),
    }
    clf = LGBMClassifier(**params)
    clf.fit(X_train_optuna, y_train_optuna,
            eval_set=[(X_val, y_val)],
            eval_metric='auc',
            callbacks=[lgb.early_stopping(50, verbose=False)])
    val_prob = clf.predict_proba(X_val)[:, 1]
    val_auc = roc_auc_score(y_val, val_prob)
    return val_auc


study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=50)  # 你可以根据需要增减 n_trials

print("\n--- 🎉 调优完成 ---")
print(f"最佳试验次数: {study.best_trial.number}")
print(f"最佳 Val AUC: {study.best_value:.6f}")
print("\n[关键] 找到的 LGBM 最佳参数 (Best Parameters):")
print(study.best_params)
best_params_lgbm = study.best_params

# -----------------------------------------------------------------
# --- 步骤 6：模型训练与融合 (逻辑不变) ---
# -----------------------------------------------------------------
print("\n--- 开始 Bagging 训练 ---")
models = [
    {"name": "HistGB", "cls": HistGradientBoostingClassifier},
    {"name": "XGBoost", "cls": XGBClassifier},
    {"name": "LightGBM", "cls": LGBMClassifier},
]

trained_models = []
val_probs_all = []

n_chunks = len(train_chunks_idx)
part_size = n_chunks // len(models)
model_chunks = [train_chunks_idx[i * part_size: (i + 1) * part_size if i < len(models) - 1 else n_chunks] for i in range(len(models))]
fit_callbacks = [lgb.early_stopping(50, verbose=False)]

for model_idx, model_info in enumerate(models):
    name = model_info["name"]
    cls = model_info["cls"]
    chunks = model_chunks[model_idx]
    print(f"\nTrain model: {name} on {len(chunks)} chunks")

    for i, train_idx_chunk in enumerate(chunks):
        X_train_chunk = X_train_all[train_idx_chunk]
        y_train_chunk = y_train_all[train_idx_chunk]

        if name == "LightGBM":
            print("   >> (应用 Optuna 最佳参数进行训练...)")
            lgbm_params = best_params_lgbm.copy()
            if 'n_estimators' in lgbm_params:
                lgbm_params['n_estimators'] = 3000  # 设一个大值，让 early_stopping 决定
            clf = LGBMClassifier(**lgbm_params)
            clf.fit(X_train_chunk, y_train_chunk,
                    eval_set=[(X_val, y_val)],
                    eval_metric='auc',
                    callbacks=fit_callbacks)
        else:
            clf = cls() if callable(cls) else cls
            clf.fit(X_train_chunk, y_train_chunk)

        trained_models.append(clf)

        # validation
        if hasattr(clf, "predict_proba"):
            val_prob = clf.predict_proba(X_val)[:, 1]
        else:
            val_prob = clf.decision_function(X_val)
            val_prob = (val_prob - val_prob.min()) / (val_prob.max() - val_prob.min())
        val_probs_all.append(val_prob)
        val_pred = (val_prob > 0.5).astype(int)
        print(f"   >> {name} chunk {i + 1}/{len(chunks)}")
        print(classification_report(y_val, val_pred))
        print("AUC =", roc_auc_score(y_val, val_prob))

# 模型融合
auc_list = []
for val_prob in val_probs_all:
    auc = roc_auc_score(y_val, val_prob)
    auc_list.append(auc)
auc_array = np.array(auc_list)
weights = auc_array / auc_array.sum()
print("\nweights", sum(weights))
print("weights", weights[:20])

val_probs_all = np.array(val_probs_all)
ensemble_prob = np.average(val_probs_all, axis=0, weights=weights)
ensemble_pred = (ensemble_prob > 0.5).astype(int)
print("\nEnsemble result (weighted by AUC):")
print(classification_report(y_val, ensemble_pred))
print("AUC =", roc_auc_score(y_val, ensemble_prob))

# -----------------------------------------------------------------
# --- 步骤 7：推理 (逻辑不变) ---
# -----------------------------------------------------------------
print("\nDoing inference on test_mask")
test_feats = X[test_mask]  # (!!!) X 是精炼后的
test_probs_all = []

for clf in trained_models:
    if hasattr(clf, "predict_proba"):
        prob = clf.predict_proba(test_feats)[:, 1]
    else:
        prob = clf.decision_function(test_feats)
        prob = (prob - prob.min()) / (prob.max() - prob.min() + 1e-9)
    test_probs_all.append(prob)

test_probs_all = np.array(test_probs_all)
test_ensemble_prob = np.average(test_probs_all, axis=0, weights=weights)

submission = np.vstack([
    1.0 - test_ensemble_prob,
    test_ensemble_prob
]).T.astype(np.float32)

OUTPUT_NPY = "submission_refined.npy"  # 改个名，避免覆盖
np.save(OUTPUT_NPY, submission)

print(f"Saved submission to {OUTPUT_NPY}, shape = {submission.shape}")