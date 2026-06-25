from utils import DGraphFin

import torch
import torch.nn.functional as F
from torch import Tensor
import torch_geometric
from torch_scatter import scatter, scatter_add

from torch_geometric.utils import to_undirected
import numpy as np

'''
Node Features
''' 

def add_degree_features(x: Tensor, edge_index: Tensor, feat_names: list):
    row, col = edge_index
    in_degree = torch_geometric.utils.degree(col, x.size(0), x.dtype)
    out_degree = torch_geometric.utils.degree(row, x.size(0), x.dtype)
    feat_names += ['in_degree', 'out_degree']
    return feat_names, torch.cat([x, in_degree.view(-1, 1), out_degree.view(-1, 1)], dim=1)


def add_missing_value_flag_sum_feature(x: Tensor, feat_names: list):
    count_minus_one = (x[:, :17] == -1).sum(dim=1, keepdim=True)
    feat_names += ['miss_value_sum']
    return feat_names, torch.cat((x, count_minus_one), dim=1)


'''
Edge Features
''' 

def add_feature_num_unique_edge_attrs(x: Tensor, edge_index: Tensor, edge_attr: Tensor, feat_names: list):
    src_nodes = edge_index[0]
    dst_nodes = edge_index[1]
    unique_src_attrs = scatter(edge_attr, src_nodes, dim=0, dim_size=x.size(0), reduce='mean')
    unique_dst_attrs = scatter(edge_attr, dst_nodes, dim=0, dim_size=x.size(0), reduce='mean')
    num_unique_attrs = unique_src_attrs + unique_dst_attrs
    x = torch.cat([x, 
                    unique_src_attrs.view(-1, 1).float(), 
                    unique_dst_attrs.view(-1, 1).float(), 
                    num_unique_attrs.view(-1, 1).float()], 
                    dim=1)
    feat_names += ['mean_unique_src_edge_attrs', 'mean_unique_dst_edge_attrs','mean_unique_edge_attrs']
    
    return feat_names, x

def add_edge_attr_sum_feature(x: Tensor, edge_index: Tensor, edge_attr: Tensor, feat_names: list):
    src, dst = edge_index[0], edge_index[1]
    num_nodes = x.shape[0]
    num_attrs = 11
    edge_attr = edge_attr.long() - 1
    
    new_features = torch.zeros((num_nodes, num_attrs), dtype=torch.float)
    src_one_hot = F.one_hot(edge_attr, num_attrs)
    src_counts = scatter_add(src_one_hot, src, dim=0, dim_size=num_nodes)
    dst_counts = scatter_add(src_one_hot, dst, dim=0, dim_size=num_nodes)
    new_features = src_counts + dst_counts
    
    x = torch.cat([x, src_counts, dst_counts, new_features], dim=1)
    
    feat_names += [f'src_edge_attr_{i}_sum' for i in range(11)]
    feat_names += [f'dst_edge_attr_{i}_sum' for i in range(11)]
    feat_names += [f'edge_attr_{i}_sum' for i in range(11)]
    
    return feat_names, x

def add_edge_timestamp_features(x, edge_index, edge_attr, edge_timestamp, feat_names):
    num_nodes = x.size(0)
    row, col = edge_index[0], edge_index[1]
    edge_timestamp = torch.Tensor(edge_timestamp)
    
    max_time_row = scatter(edge_timestamp, row, dim=0, dim_size=num_nodes, reduce='max')
    max_time_col = scatter(edge_timestamp, col, dim=0, dim_size=num_nodes, reduce='max')
    max_time = torch.max(torch.stack([max_time_row, max_time_col]), dim=0).values

    min_time_row = scatter(edge_timestamp, row, dim=0, dim_size=num_nodes, reduce='min')
    min_time_col = scatter(edge_timestamp, col, dim=0, dim_size=num_nodes, reduce='min')
    min_time = torch.min(torch.stack([min_time_row, min_time_col]), dim=0).values

    time_diff = max_time - min_time

    mean_time_row = scatter(edge_timestamp, row, dim=0, dim_size=num_nodes, reduce='mean')
    mean_time_col = scatter(edge_timestamp, col, dim=0, dim_size=num_nodes, reduce='mean')
    mean_time = (mean_time_row + mean_time_col) / 2

    min_time_indices_row = scatter(torch.arange(edge_timestamp.size(0), device=edge_timestamp.device), row, dim=0, dim_size=num_nodes, reduce='min')
    min_time_indices_col = scatter(torch.arange(edge_timestamp.size(0), device=edge_timestamp.device), col, dim=0, dim_size=num_nodes, reduce='min')
    min_time_indices = torch.min(torch.stack([min_time_indices_row, min_time_indices_col]), dim=0).values.long()
    min_time_edge_types = edge_attr[min_time_indices]
    
    max_time_indices_row = scatter(torch.arange(edge_timestamp.size(0), device=edge_timestamp.device), row, dim=0, dim_size=num_nodes, reduce='max')
    max_time_indices_col = scatter(torch.arange(edge_timestamp.size(0), device=edge_timestamp.device), col, dim=0, dim_size=num_nodes, reduce='max')
    max_time_indices = torch.max(torch.stack([max_time_indices_row, max_time_indices_col]), dim=0).values.long()
    max_time_edge_types = edge_attr[max_time_indices]

    x = torch.cat([x, 
                    max_time_row.unsqueeze(1),
                    max_time_col.unsqueeze(1),
                    max_time.unsqueeze(1), 
                    min_time_row.unsqueeze(1),
                    min_time_col.unsqueeze(1),
                    min_time.unsqueeze(1), 
                    time_diff.unsqueeze(1),
                    mean_time_row.unsqueeze(1),
                    mean_time_col.unsqueeze(1),
                    mean_time.unsqueeze(1), 
                    min_time_edge_types.unsqueeze(1), 
                    max_time_edge_types.unsqueeze(1),
                    ], 
                    dim=1)
    
    feat_names += ['src_max_timestamp',
                  'dst_max_timestamp',
                  'max_timestamp',
                  'src_min_timestamp',
                  'dst_min_timestamp',
                  'min_timestamp',
                  'timestamp_diff',
                  'src_mean_timestamp',
                  'dst_mean_timestamp',
                  'mean_timestamp',
                  'min_time_edge_attr',
                  'max_time_edge_attr',
                  ]
    
    return feat_names, x

'''
1-hop neighbor features
''' 

def add_one_hop_neighbor_feature_statistics(x, edge_index, feat_names):
    num_nodes = x.size(0)
    row, col = edge_index[0], edge_index[1]
    x_first_17 = x[:, :17]
    new_features = []
    
    for i in range(17):
        feature = x_first_17[:, i]
        
        max_neighbor_row = scatter(feature[col], row, dim=0, dim_size=num_nodes, reduce='max')
        max_neighbor_col = scatter(feature[row], col, dim=0, dim_size=num_nodes, reduce='max')
        max_neighbor = torch.max(torch.stack([max_neighbor_row, max_neighbor_col]), dim=0).values
        
        min_neighbor_row = scatter(feature[col], row, dim=0, dim_size=num_nodes, reduce='min')
        min_neighbor_col = scatter(feature[row], col, dim=0, dim_size=num_nodes, reduce='min')
        min_neighbor = torch.min(torch.stack([min_neighbor_row, min_neighbor_col]), dim=0).values
        
        mean_neighbor_row = scatter(feature[col], row, dim=0, dim_size=num_nodes, reduce='mean')
        mean_neighbor_col = scatter(feature[row], col, dim=0, dim_size=num_nodes, reduce='mean')
        mean_neighbor = (mean_neighbor_row + mean_neighbor_col) / 2
        
        new_features.append(max_neighbor)
        new_features.append(min_neighbor)
        new_features.append(mean_neighbor)
    
    new_features = torch.stack(new_features, dim=1)
    x = torch.cat([x, new_features], dim=1)
    
    feat_names += [f'one_hop_neaighbor_feat{i}_max' for i in range(17)]
    feat_names += [f'one_hop_neaighbor_feat{i}_min' for i in range(17)]
    feat_names += [f'one_hop_neaighbor_feat{i}_mean' for i in range(17)]
    
    return feat_names, x

def add_one_hop_neighbor_background_features(x, y, edge_index, feat_names):
    num_nodes = x.size(0)
    row, col = edge_index[0], edge_index[1]

    count_y2_row = scatter((y[col] == 2).float(), row, dim=0, dim_size=num_nodes, reduce='sum').squeeze(1)
    count_y2_col = scatter((y[row] == 2).float(), col, dim=0, dim_size=num_nodes, reduce='sum').squeeze(1)
    count_y2 = count_y2_row + count_y2_col

    count_y3_row = scatter((y[col] == 3).float(), row, dim=0, dim_size=num_nodes, reduce='sum').squeeze(1)
    count_y3_col = scatter((y[row] == 3).float(), col, dim=0, dim_size=num_nodes, reduce='sum').squeeze(1)
    count_y3 = count_y3_row + count_y3_col
    
    neighbor_count_row = scatter(torch.ones_like(row).float(), row, dim=0, dim_size=num_nodes, reduce='sum')
    neighbor_count_col = scatter(torch.ones_like(col).float(), col, dim=0, dim_size=num_nodes, reduce='sum')
    neighbor_count = neighbor_count_row + neighbor_count_col

    neighbor_count_row[neighbor_count_row == 0] = 1
    neighbor_count_col[neighbor_count_col == 0] = 1
    neighbor_count[neighbor_count == 0] = 1

    ratio_y2_row = count_y2_row / neighbor_count_row
    ratio_y2_col = count_y2_col / neighbor_count_col
    ratio_y2 = count_y2 / neighbor_count

    ratio_y3_row = count_y3_row / neighbor_count_row
    ratio_y3_col = count_y3_col / neighbor_count_col
    ratio_y3 = count_y3 / neighbor_count

    x = torch.cat([x,
                    count_y2.unsqueeze(1),
                    count_y3.unsqueeze(1),
                    ratio_y2_row.unsqueeze(1),
                    ratio_y2_col.unsqueeze(1),
                    ratio_y2.unsqueeze(1),
                    ratio_y3_row.unsqueeze(1),
                    ratio_y3_col.unsqueeze(1),
                    ratio_y3.unsqueeze(1),
                    ], dim=1)
    
    feat_names += ['label2_counts', 'label3_counts', 'src_label2_ratio', 'dst_label2_ratio',
                   'label2_ratio', 'src_label3_ratio', 'dst_label3_ratio', 'label3_ratio']
    
    return feat_names, x

def to_undirected(edge_index, edge_attr, edge_timestamp):

    row, col = edge_index
    row, col = torch.cat([row, col], dim=0), torch.cat([col, row], dim=0)
    edge_index = torch.stack([row, col], dim=0)

    edge_attr = torch.cat([edge_attr, edge_attr], dim=0)
    edge_timestamp = torch.cat([edge_timestamp, edge_timestamp], dim=0)
    return edge_index, edge_attr, edge_timestamp

def data_process():
    dataset = DGraphFin(root='./dataset/', name='DGraphFin',) # transform=T.ToSparseTensor()
    data = dataset[0]
    
    split_idx = {'train':data.train_mask, 'valid':data.valid_mask, 'test':data.test_mask}
    train_idx = split_idx['train']
    valid_idx = split_idx['valid']
    test_idx = split_idx['test']
    
    feat_names = [f'feat{i}' for i in range(17)]
    edge_index, edge_attr = (
        data.edge_index,
        data.edge_attr,
        # data.edge_timestamp,
    )
    edge_timestamp = np.load('dataset/DGraphFin/raw/DGraphFin/dgraphfinv2_edge_timestamp.npy')
    # node_timestamp = np.load('dataset/DGraphFin/raw/DGraphFin/dgraphfinv2_node_timestamp.npy')
    
    edge_timestamp = torch.Tensor(edge_timestamp)
    x = data.x
    y = data.y
    
    # data process
    feat_names, x = add_degree_features(x, edge_index, feat_names)
    feat_names, x = add_missing_value_flag_sum_feature(x, feat_names)
    feat_names, x = add_feature_num_unique_edge_attrs(x, edge_index, edge_attr, feat_names)
    feat_names, x = add_edge_attr_sum_feature(x, edge_index, edge_attr, feat_names)
    feat_names, x = add_edge_timestamp_features(x, edge_index, edge_attr, edge_timestamp, feat_names)
    feat_names, x = add_one_hop_neighbor_feature_statistics(x, edge_index, feat_names)
    feat_names, x = add_one_hop_neighbor_background_features(x, y, edge_index, feat_names)
    # data.x = x
    # data.edge_timestamp = torch.Tensor(edge_timestamp)
    
    edge_index, edge_attr, edge_timestamp = to_undirected(
        edge_index, edge_attr, edge_timestamp
    )
    mask = edge_index[0] < edge_index[1]
    edge_index = edge_index[:, mask]
    edge_attr = edge_attr[mask]
    edge_timestamp = edge_timestamp[mask]
    data.edge_index, data.edge_attr, data.edge_timestamp = to_undirected(
        edge_index, edge_attr, edge_timestamp
    )

    data.edge_direct = torch.ones(data.edge_attr.size(0), dtype=torch.long)
    data.edge_direct[: data.edge_attr.size(0) // 2] = 0
    
    data.x = x
    if data.y.dim() == 2:
        data.y = data.y.squeeze(1)
    
    print('data process over.')
    
    return data




# def xgb_auc(x_train, y_train, x_test, y_test):
#     evaluator = Evaluator('auc')
#     model = XGBClassifier()
#     model.fit(x_train, y_train)
#     y_pred = model.predict_proba(x_test)
#     test_auc = evaluator.eval(y_test.to_numpy(), y_pred)
#     return test_auc
    
    
# def main():
#     feat_names, x, y, train_idx, valid_idx, test_idx = data_process()
#     x_train, y_train = x[train_idx], y[train_idx]
#     x_valid, y_valid = x[valid_idx], y[valid_idx]
#     x_test, y_test = x[test_idx], y[test_idx]
#     x_train, y_train = pd.DataFrame(x_train.numpy(), columns=feat_names), pd.DataFrame(y_train.numpy(), columns=['y'])
#     x_valid, y_valid = pd.DataFrame(x_valid.numpy(), columns=feat_names), pd.DataFrame(y_valid.numpy(), columns=['y'])
#     x_test, y_test = pd.DataFrame(x_test.numpy(), columns=feat_names), pd.DataFrame(y_test.numpy(), columns=['y'])
#     print('Test auc:', xgb_auc(x_train, y_train, x_test, y_test))

    
# if __name__ == "__main__":
#     main()
    
    
    
    