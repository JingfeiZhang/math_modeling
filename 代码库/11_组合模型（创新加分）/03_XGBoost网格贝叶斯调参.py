# -*- coding: utf-8 -*-
"""
================================================================================
XGBoost + 自动超参数搜索（基模型 + 网格/随机搜索调参组合套路）
================================================================================
功能：
    展示"强基模型 + 自动调参"的组合建模套路（很多创新组合的通用范式，如
    XGBoost+贝叶斯优化、RF+GA 本质都是"模型+参数搜索器"）：
      1. 基模型：优先用 XGBoost（梯度提升树，Kaggle/建模竞赛主力）；
         若环境没装 xgboost，自动优雅退化为 sklearn 的 GradientBoosting；
      2. 调参器：用 sklearn 自带的 GridSearchCV（网格穷举）与
         RandomizedSearchCV（随机采样，等价"轻量贝叶斯式"高效搜索），
         交叉验证自动选出最优超参，避免手动试参的盲目性；
      3. 对比"默认参数 vs 调参后"的测试集表现，量化调参增益。
    只用 sklearn(+可选 xgboost)，不依赖冷门贝叶斯库，稳妥可跑、可复现。

适用竞赛场景：
    - C 题里的回归/分类预测：销量、价格、次品率、违约概率等，
      高维特征 + 强非线性时，梯度提升树 + 自动调参是稳健高分选择。

输入格式：
    - 特征矩阵 X（n_samples × n_features）、目标向量 y（回归连续值）。

输出：
    - 最优超参数、交叉验证得分、默认 vs 调参后测试集 RMSE/R² 对比。

依赖：numpy, scikit-learn；(可选) xgboost —— 未装会自动退化，不影响运行。
运行：python 03_XGBoost网格贝叶斯调参.py
================================================================================
"""

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV, RandomizedSearchCV
from sklearn.metrics import mean_squared_error, r2_score

# ---- 基模型：优先 XGBoost，未装则退化到 sklearn GradientBoosting ----
try:
    from xgboost import XGBRegressor
    _HAS_XGB = True
except Exception:
    _HAS_XGB = False
    from sklearn.ensemble import GradientBoostingRegressor


def make_base_model():
    """构造基模型 + 返回配套的超参数搜索空间。"""
    if _HAS_XGB:
        model = XGBRegressor(objective='reg:squarederror',
                             random_state=42, n_jobs=1, verbosity=0)
        # XGBoost 关键超参：学习率、树深、树数量、子采样
        grid = {
            'n_estimators': [100, 200, 300],
            'max_depth': [3, 4, 5],
            'learning_rate': [0.05, 0.1, 0.2],
            'subsample': [0.8, 1.0],
        }
        name = 'XGBoost'
    else:
        model = GradientBoostingRegressor(random_state=42)
        grid = {
            'n_estimators': [100, 200, 300],
            'max_depth': [2, 3, 4],
            'learning_rate': [0.05, 0.1, 0.2],
            'subsample': [0.8, 1.0],
        }
        name = 'sklearn GradientBoosting (xgboost 未安装, 已自动退化)'
    return model, grid, name


def evaluate(model, X_test, y_test):
    """返回测试集 RMSE 与 R²。"""
    pred = model.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
    r2 = float(r2_score(y_test, pred))
    return rmse, r2


# ----------------------------------------------------------------------
# 演示
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   feature_cols = ['特征1', '特征2', '特征3']       # 选做特征的列
    #   X = df[feature_cols].values.astype(float)        # 特征矩阵
    #   y = df['目标列'].values.astype(float)            # 回归目标(连续值)
    #   # 分类任务改用 XGBClassifier / GradientBoostingClassifier + 分类评分
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 造一个非线性回归数据集（含交互项与噪声），模拟高维特征预测场景
    rng = np.random.default_rng(42)
    n, p = 400, 6
    X = rng.uniform(-2, 2, size=(n, p))
    y = (np.sin(X[:, 0]) * 3 + X[:, 1] ** 2 - 2 * X[:, 2] * X[:, 3]
         + 0.5 * X[:, 4] + rng.normal(0, 0.3, size=n))

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=42)

    model, grid, name = make_base_model()
    print("########## XGBoost + 自动调参 组合套路演示 ##########")
    print("基模型：%s" % name)
    print("训练/测试样本：%d / %d，特征数：%d" % (len(X_tr), len(X_te), p))

    # ---- 基线：默认参数 ----
    model.fit(X_tr, y_tr)
    base_rmse, base_r2 = evaluate(model, X_te, y_te)
    print("\n【基线】默认参数：RMSE=%.4f  R2=%.4f" % (base_rmse, base_r2))

    # ---- 调参器一：网格搜索（穷举，适合搜索空间小时）----
    base_est, _, _ = make_base_model()
    gs = GridSearchCV(base_est, grid, cv=3,
                      scoring='neg_root_mean_squared_error', n_jobs=1)
    gs.fit(X_tr, y_tr)
    gs_rmse, gs_r2 = evaluate(gs.best_estimator_, X_te, y_te)
    print("\n【网格搜索 GridSearchCV】")
    print("  最优超参：", gs.best_params_)
    print("  交叉验证 RMSE=%.4f" % (-gs.best_score_))
    print("  测试集：RMSE=%.4f  R2=%.4f" % (gs_rmse, gs_r2))

    # ---- 调参器二：随机搜索（在同空间随机采样，等价轻量贝叶斯式高效搜索）----
    base_est2, _, _ = make_base_model()
    rs = RandomizedSearchCV(base_est2, grid, n_iter=12, cv=3,
                            scoring='neg_root_mean_squared_error',
                            random_state=42, n_jobs=1)
    rs.fit(X_tr, y_tr)
    rs_rmse, rs_r2 = evaluate(rs.best_estimator_, X_te, y_te)
    print("\n【随机搜索 RandomizedSearchCV】(只试 12 组, 更省时)")
    print("  最优超参：", rs.best_params_)
    print("  测试集：RMSE=%.4f  R2=%.4f" % (rs_rmse, rs_r2))

    # ---- 小结 ----
    print("\n【调参增益对比】")
    print("  默认参数     ：RMSE=%.4f  R2=%.4f" % (base_rmse, base_r2))
    print("  网格搜索调参 ：RMSE=%.4f  R2=%.4f" % (gs_rmse, gs_r2))
    print("  随机搜索调参 ：RMSE=%.4f  R2=%.4f" % (rs_rmse, rs_r2))
    best = min([('默认', base_rmse), ('网格', gs_rmse), ('随机', rs_rmse)],
               key=lambda t: t[1])
    print("  -> 最优方案：%s搜索（RMSE 最低）。" % best[0]
          if best[0] != '默认' else "  -> 本例默认已足够好，调参空间可再放宽。")

    print("\n调参说明：")
    print("  - n_estimators↑、max_depth↑ 拟合更强但易过拟合；learning_rate 小则需更多树。")
    print("  - 搜索空间大用 RandomizedSearchCV(省时)，空间小用 GridSearchCV(穷举更全)。")
    print("  - 这套'基模型+自动调参'即 RF+GA、XGBoost+贝叶斯优化等组合的通用范式。")
    print("\n演示完成。")
