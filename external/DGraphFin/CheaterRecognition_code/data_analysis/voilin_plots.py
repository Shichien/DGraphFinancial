import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import math

# --- 设置 Matplotlib 支持中文 ---
# 确保你的环境中有这个字体，或者换成 'SimHei' 等其他中文字体
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False  # 正常显示负号


def analyze_anonymous_features(npz_path):
    print("Loading data...")
    try:
        data = np.load(npz_path, allow_pickle=True)
    except FileNotFoundError:
        print(f"Error: 找不到文件 {npz_path}")
        return

    x = data["x"].astype(np.float32)
    y = data["y"].squeeze()
    train_mask = data["train_mask"].astype(np.int64)

    # --- 关键步骤：筛选出我们要分析的节点 ---
    # 我们只关心训练集中，标签为 0 (正常) 或 1 (欺诈) 的节点

    # 1. 获取在训练集中的 y
    y_train_all = y[train_mask]

    # 2. 找到 y_train_all 中等于 0 或 1 的 *相对索引*
    train_fg_mask_relative = (y_train_all == 0) | (y_train_all == 1)

    # 3. 获取这些节点在 *原数据* 中的 *绝对索引*
    nodes_to_analyze_idx = train_mask[train_fg_mask_relative]

    # 4. 获取这些节点的特征和标签
    x_to_analyze = x[nodes_to_analyze_idx]
    y_to_analyze = y[nodes_to_analyze_idx]

    print(f"Total nodes in train_mask: {len(train_mask)}")
    print(f"Found {len(y_to_analyze)} foreground nodes (Label 0 or 1) to analyze.")

    # --- 2. 检查特征的类型 (连续 vs 离散) ---
    print("\n--- Feature Type Analysis (nunique) ---")
    x_df_temp = pd.DataFrame(x_to_analyze)
    nunique = x_df_temp.nunique()
    print("Number of unique values per feature (in analyzed set):")
    print(nunique)
    print("------------------------------------------")

    # --- 3. 可视化特征分布 (小提琴图) ---

    # 将数据转换为 Pandas DataFrame，方便 Seaborn 处理
    df = pd.DataFrame(x_to_analyze, columns=[f"feat_{i}" for i in range(x.shape[1])])
    df['label'] = y_to_analyze.astype(int)

    n_features = x.shape[1]  # 17
    n_cols = 3
    n_rows = math.ceil(n_features / n_cols)  # 17/3 = 6

    print("Generating feature distribution plots (violin plots)...")
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 6, n_rows * 4))

    # 将 axes 展平，方便循环
    axes = axes.flatten()

    for i in range(n_features):
        ax = axes[i]
        feature_name = f"feat_{i}"

        # 检查这个特征是否是“离散的”（例如，唯一值 < 30）
        if nunique[i] < 30:
            # 如果是离散的，用条形图 (countplot) 更合适
            sns.countplot(data=df, x=feature_name, hue='label', ax=ax, palette="muted")
            ax.set_title(f"特征 {i} (离散) 按标签分布", weight='bold')
            ax.legend(title='Label')
        else:
            # 如果是连续的，用小提琴图
            sns.violinplot(data=df, x='label', y=feature_name, ax=ax, palette="muted", inner="quartile")
            ax.set_title(f"特征 {i} (连续) 按标签分布", weight='bold')
            ax.set_xlabel("Label (0=正常, 1=欺诈)")
            ax.set_ylabel(f"feat_{i} 的值")

    # 隐藏多余的子图
    for j in range(n_features, len(axes)):
        axes[j].set_visible(False)

    plt.tight_layout()
    plt.savefig("feature_analysis_violins.png")
    print("\n[已保存] 特征分析图 -> feature_analysis_violins.png")
    plt.show()


if __name__ == "__main__":
    analyze_anonymous_features("../phase1_gdata.npz")