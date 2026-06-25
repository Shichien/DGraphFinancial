import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.stats import skew, kurtosis, entropy
from lightgbm import LGBMClassifier
from sklearn.model_selection import train_test_split

# -----------------------------------------------------------------
# --- 步骤 1：特征工程 (与主脚本完全一致) ---
# -----------------------------------------------------------------

print("Loading npz: phase1_gdata.npz")
data = np.load("../phase1_gdata.npz", allow_pickle=True)

x = data["x"].astype(np.float32)
y = data["y"].squeeze()
edge_index = data["edge_index"].astype(np.int64)
edge_type = data["edge_type"].squeeze()
edge_timestamp = data["edge_timestamp"].squeeze()
train_mask = data["train_mask"].astype(np.int64)

N = x.shape[0]
E = edge_index.shape[0]

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

# -----------------------------------------------------------------
# --- 步骤 2：组合最终 X 和 y ---
# -----------------------------------------------------------------
X_all = np.concatenate(all_feature_arrays, axis=1).astype(np.float32)

print("\n--- 检查特征和名称 ---")
print(f"Final X shape: {X_all.shape}")
print(f"Total feature_names: {len(all_feature_names)}")

if X_all.shape[1] != len(all_feature_names):
    print("!!! 警告：特征数量 (X.shape[1]) 与 名称数量 (len(feature_names)) 不匹配 !!!")
    print(f"{X_all.shape[1]} != {len(all_feature_names)}")
else:
    print("特征和名称数量匹配。")

y_bin = np.zeros(N, dtype=np.int64)
mask_label = (y != -100)
y_bin[mask_label] = (y[mask_label] == 1).astype(np.int64)

# train/val split (我们只需要训练集来做分析)
train_idx = train_mask[y[train_mask] != -100]
train_idx_local, _ = train_test_split(
    train_idx, test_size=0.1, random_state=42, stratify=y_bin[train_idx]
)
X_train_all = X_all[train_idx_local]  # (!!!) 使用 X_all
y_train_all = y_bin[train_idx_local]

# --- 步骤 3：创建用于分析的 1:3 平衡子集 ---
pos_idx = np.where(y_train_all == 1)[0]
neg_idx = np.where(y_train_all == 0)[0]

N_NEG_RATIO = 3  # 使用你发现效果最好的 1:3 比例
n_pos_sample = len(pos_idx)
n_neg_sample = int(n_pos_sample * N_NEG_RATIO)

if n_neg_sample > len(neg_idx):
    n_neg_sample = len(neg_idx)
    print(f"警告: 负样本不足，使用所有 {n_neg_sample} 个负样本。")

neg_sample_idx = np.random.choice(neg_idx, size=n_neg_sample, replace=False)
train_idx_chunk = np.concatenate([pos_idx, neg_sample_idx])
np.random.shuffle(train_idx_chunk)

X_train = X_train_all[train_idx_chunk]
y_train = y_train_all[train_idx_chunk]

print(f"\n创建 1:{N_NEG_RATIO} 平衡子集 (共 {len(y_train)} 样本) 用于分析...")

# --- 步骤 4：训练 LGBM 并提取重要性 ---
params = {
    'objective': 'binary',
    'metric': 'auc',
    'n_estimators': 1000,
    'learning_rate': 0.01,
    'num_leaves': 50,
    'n_jobs': -1,
    'verbose': -1
}

print("Training single LGBM to get feature importances...")
clf = LGBMClassifier(**params)

# 确保 X_train 和 feature_names 匹配
if X_train.shape[1] == len(all_feature_names):
    clf.fit(X_train, y_train, feature_name=all_feature_names)  # 传入 feature_name
    print("Training complete.")

    # -----------------------------------------------------------------
    # --- (🚀 升级) 步骤 5：打印排行榜 (基于累积重要性) ---
    # -----------------------------------------------------------------
    importances = clf.feature_importances_

    df_importance = pd.DataFrame({
        'feature': all_feature_names,
        'importance': importances
    })

    # 按重要性降序排列
    df_importance = df_importance.sort_values(by='importance', ascending=False)

    # --- (新增) 累积重要性逻辑 ---

    # (!!!) 你可以调整这个阈值 (0.999 = 保留 99.9% 的重要性)
    CUMULATIVE_IMPORTANCE_THRESHOLD = 0.9

    df_importance['cumulative_importance'] = df_importance['importance'].cumsum()
    df_importance['cumulative_percentage'] = df_importance['cumulative_importance'] / df_importance['importance'].sum()

    # 找到 *保留* 的特征
    # 我们保留所有在 99.9% 阈值之内的特征
    vital_features_df = df_importance[df_importance['cumulative_percentage'] <= CUMULATIVE_IMPORTANCE_THRESHOLD]

    # (为了保险，我们也把第一个 *超过* 阈值的特征加回来)
    try:
        first_past_cutoff = df_importance[df_importance['cumulative_percentage'] > CUMULATIVE_IMPORTANCE_THRESHOLD].head(1)
        vital_features_df = pd.concat([vital_features_df, first_past_cutoff])
    except:
        print("所有特征都在 99.9% 阈值内。")

    # “琐碎特征”是 *不在* 保留列表中的所有特征
    trivial_features_df = df_importance[~df_importance['feature'].isin(vital_features_df['feature'])]

    # --- (结束新增) ---

    pd.set_option('display.max_rows', 200)

    print("\n\n" + "=" * 50)
    print("--- 🌟 特征重要性总览 (Top 50) 🌟 ---")
    print(df_importance.head(50))
    print("\n" + "=" * 50)
    print(f"--- 🗑️ “琐碎特征” (贡献低于 {CUMULATIVE_IMPORTANCE_THRESHOLD * 100}%) 🗑️ ---")
    print(trivial_features_df)
    print(f"\n总共 {len(all_feature_names)} 个特征中，有 {len(trivial_features_df)} 个特征被识别为“琐碎特征”。")
    print(f"我们将保留 {len(vital_features_df)} 个“关键特征”。")
    print("=" * 50)

    # (可选) 打印出重要性为 0 的，作为参考
    useless_features_zero = df_importance[df_importance['importance'] == 0]
    print(f"--- (参考：其中重要性 = 0 的特征有 {len(useless_features_zero)} 个) ---")
    print(useless_features_zero['feature'].tolist())
    print("=" * 50)

    print("\n--- 💡 如何使用 ---")
    print(f"1. 复制上面 '{len(trivial_features_df)} 个琐碎特征' 列表中的所有 'feature' 名称。")
    print("2. 回到你的 GBDT 主脚本。")
    print("3. 在脚本顶部定义一个 `USELESS_FEATURES = [...]` 列表，把它们粘贴进去。")
    print("4. 使用我给你的“特征换血”版完整脚本，它会自动使用这个列表。")

else:
    print("\n" + "!" * 50)
    print("!!! 严重错误：最终 X 维度与特征名称列表长度不匹配 !!!")
    print(f"!!! X.shape[1] = {X_train.shape[1]}, len(feature_names) = {len(all_feature_names)} !!!")
    print("!!! 脚本已停止。请仔细检查上面的特征工程和命名步骤。 !!!")
    print("!" * 50)