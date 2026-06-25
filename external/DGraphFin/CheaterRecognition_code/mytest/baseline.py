import numpy as np
from scipy.sparse import coo_matrix, csr_matrix
from scipy.stats import skew, kurtosis, entropy
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.ensemble import HistGradientBoostingClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier


NPZ_PATH = "../phase1_gdata.npz"
OUTPUT_NPY = "submission_baseline.npy"

print("Loading npz:", NPZ_PATH)
data = np.load(NPZ_PATH, allow_pickle=True)

x = data["x"].astype(np.float32)  # (N,17)
y = data["y"].squeeze()  # (N,)
edge_index = data["edge_index"].astype(np.int64)  # (E,2)
edge_type = data["edge_type"].squeeze()
edge_timestamp = data["edge_timestamp"].squeeze()
train_mask = data["train_mask"].astype(np.int64)
test_mask = data["test_mask"].astype(np.int64)

N = x.shape[0]
E = edge_index.shape[0]
print(f"Nodes = {N}, Features = {x.shape}, Edges = {E}")

# 窗口特征 recent_feats
max_day = int(edge_timestamp.max())

win_base = np.array([3, 7, 14, 30, 60, 90, 180], dtype=np.int32)
win_days = np.concatenate([win_base, max_day - win_base])
win_threshold = max_day - win_days
W = len(win_threshold)

edge_ts = edge_timestamp.reshape(-1, 1)
mask = edge_ts >= win_threshold.reshape(1, -1)  # True/False

nodes_flat = np.concatenate([edge_index[:, 0], edge_index[:, 1]])
mask_flat = np.concatenate([mask, mask], axis=0)

recent_feats = np.zeros((N, W), dtype=np.float32)
for w in range(W):
    recent_feats[:, w] = np.bincount(
        nodes_flat,
        weights=mask_flat[:, w].astype(np.float32),
        minlength=N
    )
print("recent_feats:", recent_feats.shape)

# 基础结构特征
out_deg = np.bincount(edge_index[:, 0], minlength=N).astype(np.float32)
in_deg = np.bincount(edge_index[:, 1], minlength=N).astype(np.float32)
deg = in_deg + out_deg
deg_diff = out_deg - in_deg

min_day = np.full(N, 1e9, dtype=np.float32)
max_day_node = np.full(N, -1e9, dtype=np.float32)

ts_flat = np.concatenate([edge_timestamp, edge_timestamp])
np.minimum.at(min_day, nodes_flat, ts_flat)
np.maximum.at(max_day_node, nodes_flat, ts_flat)

active_span = max_day_node - min_day
active_span[active_span < 0] = 0

# 时间统计
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

# new_feats
new_feats = np.stack([
    deg,
    deg_diff,
    active_span,
    day_mean,
    day_skew,
    deg_norm,
    time_weighted_deg,
    last_active_norm,
    active_long,
    recent_active,
], axis=1).astype(np.float32)
print("new_feats:", new_feats.shape)

# more_feats（扩展）
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

more_feats = np.stack([
    deg_ratio,
    active_span_ratio,
    recent_gap_norm,
    deg_squared,
    deg_diff_abs,
    span_mean_ratio,
    mean_neighbor_deg_base, # 重命名以避免与后续冲突
    active_std,
    deg_rate,
    deg_skew,
    deg_kurt
], axis=1).astype(np.float32)
print("more_feats:", more_feats.shape)

# 合并 new_feats_all
new_feats_all = np.concatenate([new_feats, more_feats], axis=1)
print("new_feats_all:", new_feats_all.shape)

# 打包 struct_feats (基础特征)
struct_feats = np.concatenate([
    in_deg.reshape(-1, 1),
    out_deg.reshape(-1, 1),
    recent_feats,
    new_feats_all,
    min_day.reshape(-1, 1),
    max_day_node.reshape(-1, 1),
], axis=1).astype(np.float32)
print("struct_feats:", struct_feats.shape)


# 最终的扩展特征工程 (200+ features)
global_max = max_day_node.max() # 尽管已定义，但在这里重申是清晰的
X_recent = 30
num_types = int(edge_type.max() + 1)
# deg, deg_diff, in_deg, out_deg, max_day_node 已经准备好

# 构建邻接矩阵
rows_in, cols_in = edge_index[:, 1], edge_index[:, 0]  # 入邻居
rows_out, cols_out = edge_index[:, 0], edge_index[:, 1]  # 出邻居
data = np.ones(E, dtype=np.float32)

A_in = coo_matrix((data, (rows_in, cols_in)), shape=(N, N))
A_out = coo_matrix((data, (rows_out, cols_out)), shape=(N, N))
A_all = ((A_in + A_out) > 0).astype(np.float32)

# 一阶邻居统计
num_in_neighbors = np.array(A_in.sum(axis=1)).flatten()
num_out_neighbors = np.array(A_out.sum(axis=1)).flatten()
num_all_neighbors = np.array(A_all.sum(axis=1)).flatten()
ratio_in_out_neighbors = num_in_neighbors / np.maximum(num_out_neighbors, 1)

mean_in_deg_neighbors = A_in.dot(in_deg) / np.maximum(num_in_neighbors, 1)
mean_out_deg_neighbors = A_out.dot(out_deg) / np.maximum(num_out_neighbors, 1)
mean_neighbor_deg = A_all.dot(deg) / np.maximum(num_all_neighbors, 1)

mean_last_active_in_neighbors = A_in.dot(max_day_node) / np.maximum(num_in_neighbors, 1)
mean_last_active_out_neighbors = A_out.dot(max_day_node) / np.maximum(num_out_neighbors, 1)

recent_active_mask = (max_day_node > global_max - X_recent).astype(np.float32)
recent_active_in_neighbors = A_in.dot(recent_active_mask) / np.maximum(num_in_neighbors, 1)
recent_active_out_neighbors = A_out.dot(recent_active_mask) / np.maximum(num_out_neighbors, 1)

# 二阶/三阶邻居统计
A2_in = A_in.dot(A_in)
A2_out = A_out.dot(A_out)
num_2hop_in_neighbors = np.array(A2_in.sum(axis=1)).flatten()
num_2hop_out_neighbors = np.array(A2_out.sum(axis=1)).flatten()
mean_2hop_in_deg_neighbors = A2_in.dot(in_deg) / np.maximum(num_2hop_in_neighbors, 1)
mean_2hop_out_deg_neighbors = A2_out.dot(out_deg) / np.maximum(num_2hop_out_neighbors, 1)

A3_all = A_all.dot(A_all.dot(A_all))
num_3hop_neighbors = np.array(A3_all.sum(axis=1)).flatten()
mean_3hop_deg = A3_all.dot(deg) / np.maximum(num_3hop_neighbors, 1)

# Motif / 局部闭环
triangles_in_out = np.array(A_in.dot(A_out).diagonal()).astype(np.float32)
triangles_out_in = np.array(A_out.dot(A_in).diagonal()).astype(np.float32)
triangles_all = np.array(A_all.dot(A_all).diagonal()).astype(np.float32)

# 边类型统计
in_type_count = np.zeros((N, num_types), dtype=np.float32)
out_type_count = np.zeros((N, num_types), dtype=np.float32)
np.add.at(out_type_count, (edge_index[:, 0], edge_type), 1)
np.add.at(in_type_count, (edge_index[:, 1], edge_type), 1)

in_type_ratio = in_type_count / np.maximum(in_type_count.sum(axis=1, keepdims=True), 1)
out_type_ratio = out_type_count / np.maximum(out_type_count.sum(axis=1, keepdims=True), 1)

# 类型熵 & 方差
type_entropy_in = entropy(in_type_ratio.T + 1e-6)
type_entropy_out = entropy(out_type_ratio.T + 1e-6)
type_var_in = in_type_ratio.var(axis=1)
type_var_out = out_type_ratio.var(axis=1)

# 时间特征
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

# 节点高阶组合特征
deg_squared = deg ** 2
deg_diff_squared = deg_diff ** 2
deg_log = np.log1p(deg)
active_span = max_day_node - np.minimum(np.zeros_like(max_day_node), 0)
active_span_squared = active_span ** 2

# 节点度z-score
deg_z = (deg - deg.mean()) / (deg.std() + 1e-6)
neighbor_deg_z = (mean_neighbor_deg - mean_neighbor_deg.mean()) / (mean_neighbor_deg.std() + 1e-6)
active_z = (max_day_node - max_day_node.mean()) / (max_day_node.std() + 1e-6)

# 拼接所有特征到节点矩阵
edge_feats_final = np.concatenate([
    # 一阶邻居
    num_in_neighbors.reshape(-1, 1), num_out_neighbors.reshape(-1, 1), num_all_neighbors.reshape(-1, 1),
    ratio_in_out_neighbors.reshape(-1, 1), mean_in_deg_neighbors.reshape(-1, 1), mean_out_deg_neighbors.reshape(-1, 1),
    mean_last_active_in_neighbors.reshape(-1, 1), mean_last_active_out_neighbors.reshape(-1, 1),
    recent_active_in_neighbors.reshape(-1, 1), recent_active_out_neighbors.reshape(-1, 1),
    # 二阶/三阶邻居
    num_2hop_in_neighbors.reshape(-1, 1), num_2hop_out_neighbors.reshape(-1, 1),
    mean_2hop_in_deg_neighbors.reshape(-1, 1), mean_2hop_out_deg_neighbors.reshape(-1, 1),
    num_3hop_neighbors.reshape(-1, 1), mean_3hop_deg.reshape(-1, 1),
    # Motif
    triangles_in_out.reshape(-1, 1), triangles_out_in.reshape(-1, 1), triangles_all.reshape(-1, 1),
    # 边类型
    in_type_ratio, out_type_ratio,
    type_var_in.reshape(-1, 1), type_var_out.reshape(-1, 1),
    # 时间
    gap_last_edge_in.reshape(-1, 1), gap_last_edge_out.reshape(-1, 1),
    avg_edge_time_in.reshape(-1, 1), avg_edge_time_out.reshape(-1, 1),
    w_in_decay.reshape(-1, 1), w_out_decay.reshape(-1, 1),
    # 高阶组合
    deg_squared.reshape(-1, 1), deg_diff_squared.reshape(-1, 1), deg_log.reshape(-1, 1),
    active_span_squared.reshape(-1, 1), deg_z.reshape(-1, 1), neighbor_deg_z.reshape(-1, 1),
    active_z.reshape(-1, 1),
], axis=1)

struct_feats = np.concatenate([struct_feats, edge_feats_final], axis=1)
print("Updated struct_feats with 200+ features:", struct_feats.shape)

# 最终 X
X = np.concatenate([x, struct_feats], axis=1).astype(np.float32)
D = X.shape[1]
print("Final X:", X.shape)

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


# 采样
X_train = X[train_idx_local]
y_train = y_bin[train_idx_local]

X_val = X[val_idx_local]
y_val = y_bin[val_idx_local]

pos_idx = np.where(y_train == 1)[0]
neg_idx = np.where(y_train == 0)[0]

print("原始类数量：pos =", len(pos_idx), "neg =", len(neg_idx))

# 切割负样本
chunk_size = int(len(pos_idx))
neg_chunks = [neg_idx[i:i + chunk_size] for i in range(0, len(neg_idx), chunk_size)]
neg_chunks = neg_chunks[:9] # 只取 9 块

# 为每块生成对应的训练索引
train_chunks_idx = []
n_pos_sample = int(len(pos_idx))
for neg_chunk in neg_chunks:
    pos_sample_idx = np.random.choice(pos_idx, size=n_pos_sample, replace=False)
    train_idx_chunk = np.concatenate([pos_sample_idx, neg_chunk])
    np.random.shuffle(train_idx_chunk)
    train_chunks_idx.append(train_idx_chunk)

print(f"共生成 {len(train_chunks_idx)} 个训练子集，每个子集大小约 = {len(train_chunks_idx[0])}")

# 模型训练
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

for model_idx, model_info in enumerate(models):
    name = model_info["name"]
    cls = model_info["cls"]
    chunks = model_chunks[model_idx]

    print(f"\nTrain model: {name} on {len(chunks)} chunks")
    for i, train_idx_chunk in enumerate(chunks):
        X_train_chunk = X_train[train_idx_chunk]
        y_train_chunk = y_train[train_idx_chunk]

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

print("weights", sum(weights))
print("weights", weights[:20])

val_probs_all = np.array(val_probs_all)
ensemble_prob = np.average(val_probs_all, axis=0, weights=weights)
ensemble_pred = (ensemble_prob > 0.5).astype(int)

print("\nEnsemble result (weighted by AUC):")
print(classification_report(y_val, ensemble_pred))
print("AUC =", roc_auc_score(y_val, ensemble_prob))

# 推理
print("\nDoing inference on test_mask")

test_feats = X[test_mask]
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

OUTPUT_NPY = "submission.npy"
np.save(OUTPUT_NPY, submission)

print(f"Saved submission to {OUTPUT_NPY}, shape = {submission.shape}")