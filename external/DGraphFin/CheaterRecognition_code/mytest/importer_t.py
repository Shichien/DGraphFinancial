import torch_geometric

# Please download DGraphFin dataset file 'DGraphFin.zip' on our website 'https://dgraph.xinye.com' and place it under directory './dataset/raw'
# Otherwise an error would pop out "Dataset not found. Please download 'DGraphFin.zip' from 'https://dgraph.xinye.com' and move it to './raw' "
from torch_geometric.datasets import DGraphFin

dataset = DGraphFin(root='./dataset')
data = dataset[0]
print(data)
