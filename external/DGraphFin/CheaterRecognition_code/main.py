import argparse
import random

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.utils import k_hop_subgraph
from scipy.sparse import coo_matrix
from scipy.stats import skew, kurtosis, entropy
from sklearn.model_selection import train_test_split
from torch_geometric.data import Data
from models import Sage
from utils.evaluator import Evaluator
from utils.utils import prepare_folder
from boost import get_xgb_pred

NPZ_PATH = "phase1_gdata.npz"

def to_undirected_baseline(edge_index, edge_attr, edge_timestamp):
    # baseline.py 的 edge_index 是 (E, 2)，先转成 (2, E)
    edge_index = torch.tensor(edge_index.transpose(), dtype=torch.int64)
    edge_attr = torch.tensor(edge_attr, dtype=torch.long)
    edge_timestamp = torch.tensor(edge_timestamp, dtype=torch.float)

    row, col = edge_index
    row, col = torch.cat([row, col], dim=0), torch.cat([col, row], dim=0)
    edge_index = torch.stack([row, col], dim=0)

    edge_attr = torch.cat([edge_attr, edge_attr], dim=0)
    edge_timestamp = torch.cat([edge_timestamp, edge_timestamp], dim=0)

    # 创建 edge_direct
    edge_direct = torch.ones(edge_attr.size(0), dtype=torch.long)
    edge_direct[: edge_attr.size(0) // 2] = 0

    return edge_index, edge_attr, edge_timestamp, edge_direct


def load_and_process_baseline_data(npz_path):
    print("Loading npz:", npz_path)
    data = np.load(npz_path, allow_pickle=True)

    x = data["x"].astype(np.float32)  # (N,17)
    y = data["y"].squeeze()  # (N,)
    edge_index_np = data["edge_index"].astype(np.int64)  # (E,2)
    edge_type_np = data["edge_type"].squeeze()
    edge_timestamp_np = data["edge_timestamp"].squeeze()
    train_mask_np = data["train_mask"].astype(np.int64)  # 这是索引
    test_mask_np = data["test_mask"].astype(np.int64)  # 这是索引

    N = x.shape[0]
    E = edge_index_np.shape[0]
    print(f"Nodes = {N}, Features = {x.shape}, Edges = {E}")

    # --- 开始 baseline.py 的特征工程 ---
    max_day = int(edge_timestamp_np.max())

    win_base = np.array([3, 7, 14, 30, 60, 90, 180], dtype=np.int32)
    win_days = np.concatenate([win_base, max_day - win_base])
    win_threshold = max_day - win_days
    W = len(win_threshold)

    edge_ts = edge_timestamp_np.reshape(-1, 1)
    mask_np = edge_ts >= win_threshold.reshape(1, -1)

    nodes_flat = np.concatenate([edge_index_np[:, 0], edge_index_np[:, 1]])
    mask_flat = np.concatenate([mask_np, mask_np], axis=0)

    recent_feats = np.zeros((N, W), dtype=np.float32)
    for w in range(W):
        recent_feats[:, w] = np.bincount(
            nodes_flat,
            weights=mask_flat[:, w].astype(np.float32),
            minlength=N
        )
    print("recent_feats:", recent_feats.shape)

    # 基础结构特征
    out_deg = np.bincount(edge_index_np[:, 0], minlength=N).astype(np.float32)
    in_deg = np.bincount(edge_index_np[:, 1], minlength=N).astype(np.float32)
    deg = in_deg + out_deg
    deg_diff = out_deg - in_deg

    min_day = np.full(N, 1e9, dtype=np.float32)
    max_day_node = np.full(N, -1e9, dtype=np.float32)

    ts_flat = np.concatenate([edge_timestamp_np, edge_timestamp_np])
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

    np.add.at(w_out, edge_index_np[:, 0], time_weight[:E])
    np.add.at(w_in, edge_index_np[:, 1], time_weight[E:])
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

    rows = np.concatenate([edge_index_np[:, 0], edge_index_np[:, 1]])
    cols = np.concatenate([edge_index_np[:, 1], edge_index_np[:, 0]])
    adj = coo_matrix((np.ones_like(rows), (rows, cols)), shape=(N, N))
    mean_neighbor_deg_base = adj.dot(deg.reshape(-1, 1)).flatten() / np.maximum(adj.sum(axis=1).A1, 1)

    sum_ts = np.bincount(nodes_flat, weights=ts_flat, minlength=N)
    sum_ts2 = np.bincount(nodes_flat, weights=ts_flat ** 2, minlength=N)
    cnt_ts = np.bincount(nodes_flat, minlength=N)
    active_std = np.sqrt(np.maximum(0, sum_ts2 / cnt_ts - (sum_ts / cnt_ts) ** 2))
    active_std[cnt_ts == 0] = 0

    deg_rate = deg / np.maximum(active_span, 1e-6)

    # 修复 baseline.py 中的 bug：skew/kurtosis 应为标量
    deg_skew_val = skew(deg.astype(np.float64))
    deg_kurt_val = kurtosis(deg.astype(np.float64))
    deg_skew = np.full(N, deg_skew_val)
    deg_kurt = np.full(N, deg_kurt_val)

    more_feats = np.stack([
        deg_ratio,
        active_span_ratio,
        recent_gap_norm,
        deg_squared,
        deg_diff_abs,
        span_mean_ratio,
        mean_neighbor_deg_base,
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
    num_types = int(edge_type_np.max() + 1)

    # 构建邻接矩阵
    rows_in, cols_in = edge_index_np[:, 1], edge_index_np[:, 0]
    rows_out, cols_out = edge_index_np[:, 0], edge_index_np[:, 1]
    data_np = np.ones(E, dtype=np.float32)

    A_in = coo_matrix((data_np, (rows_in, cols_in)), shape=(N, N))
    A_out = coo_matrix((data_np, (rows_out, cols_out)), shape=(N, N))
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
    np.add.at(out_type_count, (edge_index_np[:, 0], edge_type_np), 1)
    np.add.at(in_type_count, (edge_index_np[:, 1], edge_type_np), 1)

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
    np.maximum.at(last_edge_out, edge_index_np[:, 0], edge_timestamp_np)
    np.maximum.at(last_edge_in, edge_index_np[:, 1], edge_timestamp_np)

    gap_last_edge_out = global_max - last_edge_out
    gap_last_edge_in = global_max - last_edge_in

    sum_ts_out = np.zeros(N, dtype=np.float32)
    cnt_out = np.zeros(N, dtype=np.float32)
    np.add.at(sum_ts_out, edge_index_np[:, 0], edge_timestamp_np)
    np.add.at(cnt_out, edge_index_np[:, 0], 1)
    avg_edge_time_out = sum_ts_out / np.maximum(cnt_out, 1)

    sum_ts_in = np.zeros(N, dtype=np.float32)
    cnt_in = np.zeros(N, dtype=np.float32)
    np.add.at(sum_ts_in, edge_index_np[:, 1], edge_timestamp_np)
    np.add.at(cnt_in, edge_index_np[:, 1], 1)
    avg_edge_time_in = sum_ts_in / np.maximum(cnt_in, 1)

    time_decay = np.exp(-(global_max - edge_timestamp_np) / global_max)
    w_out_decay = np.zeros(N, dtype=np.float32)
    w_in_decay = np.zeros(N, dtype=np.float32)
    np.add.at(w_out_decay, edge_index_np[:, 0], time_decay)
    np.add.at(w_in_decay, edge_index_np[:, 1], time_decay)

    # 节点高阶组合特征
    deg_diff_squared = deg_diff ** 2
    deg_log = np.log1p(deg)
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
    print("Final X:", X.shape)

    # --- 结束 baseline.py 的特征工程 ---

    # --- 开始 baseline.py 的 y 和 mask 处理 ---
    # 二分类 (只关心 y==1)
    y_bin = np.zeros(N, dtype=np.int64)
    mask_label = (y != -100)
    y_bin[mask_label] = (y[mask_label] == 1).astype(np.int64)

    # train/val split (使用索引)
    train_idx_all = train_mask_np[y[train_mask_np] != -100]
    train_idx_local, val_idx_local = train_test_split(
        train_idx_all,
        test_size=0.1,
        random_state=42,
        stratify=y_bin[train_idx_all]
    )

    test_idx = test_mask_np

    print("Train:", len(train_idx_local),
          "Val:", len(val_idx_local),
          "Test:", len(test_idx))
    # --- 结束 y 和 mask 处理 ---

    # --- 开始处理边和创建 Data 对象 ---

    # 应用 to_undirected 并创建 edge_direct
    edge_index, edge_attr, edge_timestamp, edge_direct = to_undirected_baseline(
        edge_index_np, edge_type_np, edge_timestamp_np
    )

    # 创建 Data 对象
    data_obj = Data(
        x=torch.tensor(X, dtype=torch.float),
        edge_index=edge_index,
        edge_attr=edge_attr,
        y=torch.tensor(y_bin, dtype=torch.long),
        train_mask=torch.tensor(train_idx_local, dtype=torch.long),  # 使用索引
        valid_mask=torch.tensor(val_idx_local, dtype=torch.long),  # 使用索引
        test_mask=torch.tensor(test_idx, dtype=torch.long),  # 使用索引
        edge_timestamp=edge_timestamp,
        edge_direct=edge_direct
    )

    print('Data object created from baseline processing.')

    return data_obj


# --- 结束新增函数 ---


def set_seed(seed):
    np.random.seed(seed)
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def train(model, data, optimizer):
    model.train()

    optimizer.zero_grad()
    # data.train_pos 和 data.train_neg 在 main() 中创建
    neg_sample_size = data.train_pos.size(0) * 3
    neg_idx = data.train_neg[
        torch.randperm(data.train_neg.size(0))[: neg_sample_size]
    ]
    train_idx = torch.cat([data.train_pos, neg_idx], dim=0)

    nodeandneighbor, edge_index, node_map, mask = k_hop_subgraph(
        train_idx, 3, data.edge_index, relabel_nodes=True, num_nodes=data.x.size(0)
    )

    out = model(
        data.x[nodeandneighbor],
        edge_index,
        data.edge_attr[mask],
        data.edge_timestamp[mask],
        data.edge_direct[mask],
    )
    # data.y 是二分类 (y_bin)
    loss = F.nll_loss(out[node_map], data.y[train_idx])
    loss.backward()

    nn.utils.clip_grad_norm_(model.parameters(), 2.0)

    optimizer.step()
    torch.cuda.empty_cache()
    return loss.item()


@torch.no_grad()
def test(model, data):
    model.eval()
    out = model(
        data.x, data.edge_index, data.edge_attr, data.edge_timestamp, data.edge_direct,
    )

    y_pred = out.exp()
    return y_pred


def main():
    parser = argparse.ArgumentParser(description="Sage for DGraphFin Dataset")
    parser.add_argument("--dataset", type=str, default="DGraphFin")
    parser.add_argument("--model", type=str, default="Sage")
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=1000)
    parser.add_argument("--hiddens", type=int, default=256)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.2)

    args = parser.parse_args()
    print(args)

    device = f"cuda:{args.device}" if torch.cuda.is_available() else "cpu"
    device = torch.device(device)
    model_dir = prepare_folder(args.dataset, args.model)
    print("model_dir:", model_dir)
    set_seed(42)

    nlabels = 2  # 明确为二分类 (来自 baseline.py)

    # --- 数据加载修改 ---
    # 使用 baseline.py 的方式加载数据
    data = load_and_process_baseline_data(NPZ_PATH).to(device)

    # data.train_mask 等已是索引
    train_idx = data.train_mask

    # data.edge_attr = data.edge_attr.long() # 已在加载函数中处理

    # 基于 train_idx (索引) 和 y (二分类) 创建 train_pos 和 train_neg
    data.train_pos = train_idx[data.y[train_idx] == 1]
    data.train_neg = train_idx[data.y[train_idx] == 0]

    model = Sage(
        in_channels=data.x.size(-1),  # 使用 baseline 的 X 特征维度
        hidden_channels=args.hiddens,
        out_channels=nlabels,
        num_layers=args.layers,
        dropout=args.dropout,
        activation="elu",
        bn=True,
    ).to(device)

    print(f"Model {args.model} initialized")
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.003, weight_decay=1e-5)
    best_auc = 0.0
    evaluator = Evaluator("auc")

    # y_... 使用索引 mask
    y_train, y_valid, y_test = data.y[data.train_mask], data.y[data.valid_mask], data.y[data.test_mask]

    for epoch in range(1, args.epochs + 1):
        loss = train(model, data, optimizer)
        out = test(model, data)

        # preds_... 使用索引 mask
        preds_train, preds_valid, preds_test = out[data.train_mask], out[data.valid_mask], out[data.test_mask]

        # evaluator 使用二分类 y 和 (N, 2) 的 preds
        train_auc = evaluator.eval(y_train, preds_train)["auc"]
        valid_auc = evaluator.eval(y_valid, preds_valid)["auc"]
        test_auc = evaluator.eval(y_test, preds_test)["auc"]

        if valid_auc >= best_auc:
            best_auc = valid_auc
            torch.save(model.state_dict(), model_dir + "model.pt")
            preds = out[data.test_mask].cpu().numpy()
        print(
            f"Epoch: {epoch:02d}, "
            f"Loss: {loss:.4f}, "
            f"Train: {train_auc:.2%}, "
            f"Valid: {valid_auc:.2%},"
            f"Test: {test_auc:.4%},"
            f"Best: {best_auc:.4%},"
        )

    model.load_state_dict(torch.load(model_dir + "model.pt"))
    out = test(model, data)
    preds = out[data.test_mask].cpu().numpy()  # (N_test, 2)

    test_auc = evaluator.eval(data.y[data.test_mask], preds)["auc"]
    print(f"Sage test_auc: {test_auc}")

    print('Now fitting XGBoost.')
    # 将 baseline data 传递给 get_xgb_pred
    xgb_preds = get_xgb_pred(data, k=5, seed=42)  # (N_test, 2)

    # 融合 (preds 和 xgb_preds 都是 (N_test, 2))
    final_auc = evaluator.eval(data.y[data.test_mask], (preds + xgb_preds) / 2)["auc"]
    print(f"final auc: {final_auc}")


if __name__ == "__main__":
    main()