import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import KFold
from utils.evaluator import Evaluator


def get_xgb_pred(data_baseline, k=5, seed=42):
    x = data_baseline.x.cpu().numpy()
    y = data_baseline.y.cpu().numpy()  # 这是 baseline 的 y_bin (二分类)
    train_index = data_baseline.train_mask.cpu().numpy()
    test_index = data_baseline.test_mask.cpu().numpy()

    feat_names = [f'feat_{i}' for i in range(x.shape[1])]

    # device = torch.device('cuda:0') # 未使用，可删除
    evaluator = Evaluator('auc')

    # k-fold cross training
    x_train, y_train = x[train_index], y[train_index]
    x_test, y_test = x[test_index], y[test_index]

    kf = KFold(n_splits=k, shuffle=True, random_state=seed)
    models = []
    y_preds = []

    for kfold_train, kfold_test in kf.split(x_train):
        x_kfold_train, x_kfold_test = x_train[kfold_train], x_train[kfold_test]
        y_kfold_train, y_kfold_test = y_train[kfold_train], y_train[kfold_test]

        model = XGBClassifier()  # y 是二分类 (0,1)，XGB 会自动进行二分类
        model.fit(x_kfold_train, y_kfold_train)

        y_kfold_pred = model.predict_proba(x_kfold_test)  # (N_kfold_test, 2)
        # evaluator 会自动处理 (N, 2) 的二分类 AUC
        kfold_test_auc = evaluator.eval(y_kfold_test, y_kfold_pred)["auc"]

        y_pred = model.predict_proba(x_test)  # (N_test, 2)
        test_auc = evaluator.eval(y_test, y_pred)["auc"]

        print(f'Fold finished, kfold test auc={kfold_test_auc}, test_auc={test_auc}.')
        models.append(model)
        y_preds.append(y_pred)

    final_pred = np.mean(np.array(y_preds), axis=0)  # (N_test, 2)
    final_auc = evaluator.eval(y_test, final_pred)["auc"]
    print(f'Final AUC: {final_auc}')

    return final_pred  # 返回 (N_test, 2) 的概率