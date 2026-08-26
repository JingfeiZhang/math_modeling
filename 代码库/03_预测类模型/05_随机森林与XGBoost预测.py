# -*- coding: utf-8 -*-
"""
05 随机森林 与 XGBoost 回归预测 (Random Forest / XGBoost Regression)
================================================================
功能：
    面向国赛 C 题的“多特征驱动的数值预测 + 特征重要性分析”
    （呼应 2025 年 C 题数据挖掘/随机森林类题型、2023 蔬菜定价补货等）：
      1. 随机森林回归 RandomForestRegressor（稳健、少调参、抗过拟合）；
      2. XGBoost 回归（精度更高；未安装时自动退回梯度提升树 GBDT）；
      3. 特征重要性排序（论文里解释“哪些因素影响最大”的关键图表）；
      4. 训练/测试划分 + 交叉验证 + 预测误差 RMSE / MAE / MAPE / R²。

    也可用于“时间序列 → 监督学习”：用滞后特征做多步预测（见 make_lag_features）。

输入格式：
    - 特征矩阵 X：(n_samples, n_features)，数值型（类别需先编码）。
    - 目标 y：(n_samples,) 连续值。
    - feature_names：特征名列表（可选，用于重要性可读性）。

输出：
    - 各模型测试集误差、交叉验证得分、特征重要性排序。

依赖：numpy, pandas, scikit-learn, (可选) xgboost, (可选) matplotlib
    可选安装：pip install xgboost
运行：python 05_随机森林与XGBoost预测.py
"""

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score, KFold

# XGBoost 为可选依赖；未安装时用 sklearn 的 GradientBoostingRegressor 替代
try:
    from xgboost import XGBRegressor
    _HAS_XGB = True
except Exception:
    _HAS_XGB = False

try:
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False


def regression_metrics(y_true, y_pred):
    """回归预测误差：RMSE / MAE / MAPE(%) / R²。"""
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    err = y_true - y_pred
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mae = float(np.mean(np.abs(err)))
    mask = y_true != 0
    mape = float(np.mean(np.abs(err[mask] / y_true[mask])) * 100) if mask.any() else np.nan
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return {'RMSE': rmse, 'MAE': mae, 'MAPE(%)': mape, 'R2': r2}


def _report(name, model, X_tr, X_te, y_tr, y_te, X_all, y_all):
    """训练 + 测试评估 + 5 折交叉验证，返回 (模型, 指标)。"""
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)
    m = regression_metrics(y_te, pred)
    cv = cross_val_score(model, X_all, y_all, cv=KFold(5, shuffle=True, random_state=0),
                         scoring='r2')
    print("=" * 60)
    print(name)
    print("  测试集: RMSE=%.4f  MAE=%.4f  MAPE=%.2f%%  R2=%.4f"
          % (m['RMSE'], m['MAE'], m['MAPE(%)'], m['R2']))
    print("  5折交叉验证 R2: 均值=%.4f  标准差=%.4f" % (cv.mean(), cv.std()))
    return model, m


# ----------------------------------------------------------------------
# 1. 随机森林回归
# ----------------------------------------------------------------------
def random_forest_regression(X, y, feature_names=None, test_size=0.25,
                             n_estimators=200, max_depth=None):
    """随机森林回归。

    关键参数：
        n_estimators: 树的数量，越多越稳但越慢（常用 100~500）。
        max_depth: 单棵树最大深度，None 不限；数据少时设 5~15 防过拟合。
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=test_size, random_state=0)
    model = RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth,
                                  random_state=0, n_jobs=-1)
    model, m = _report('随机森林回归 RandomForest', model,
                       X_tr, X_te, y_tr, y_te, X, y)
    _print_importance(model.feature_importances_, feature_names, X.shape[1])
    return model, m


# ----------------------------------------------------------------------
# 2. XGBoost 回归（未装则退回 GBDT）
# ----------------------------------------------------------------------
def xgboost_regression(X, y, feature_names=None, test_size=0.25,
                       n_estimators=300, max_depth=5, learning_rate=0.1):
    """XGBoost 回归；未安装 xgboost 时自动使用 sklearn GradientBoosting。

    关键参数：
        n_estimators: 提升轮数；learning_rate: 学习率(越小需越多轮)；
        max_depth: 单树深度(3~8 常用)。三者需配合调（lr小+轮数多更稳）。
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=test_size, random_state=0)
    if _HAS_XGB:
        name = 'XGBoost 回归'
        model = XGBRegressor(n_estimators=n_estimators, max_depth=max_depth,
                             learning_rate=learning_rate, subsample=0.9,
                             colsample_bytree=0.9, random_state=0, n_jobs=-1)
    else:
        name = 'XGBoost 未安装 → 退回 GradientBoosting(GBDT)'
        model = GradientBoostingRegressor(n_estimators=n_estimators,
                                          max_depth=max_depth,
                                          learning_rate=learning_rate,
                                          random_state=0)
    model, m = _report(name, model, X_tr, X_te, y_tr, y_te, X, y)
    _print_importance(model.feature_importances_, feature_names, X.shape[1])
    return model, m


def _print_importance(importances, feature_names, n_features):
    """打印特征重要性排序（论文常用：解释关键影响因素）。"""
    if feature_names is None:
        feature_names = ['特征%d' % (i + 1) for i in range(n_features)]
    order = np.argsort(importances)[::-1]
    print("  特征重要性排序：")
    for rank, idx in enumerate(order, 1):
        print("    %d. %-10s %.4f" % (rank, feature_names[idx], importances[idx]))


# ----------------------------------------------------------------------
# 工具：把单变量时间序列转成“滞后特征”监督学习问题
# ----------------------------------------------------------------------
def make_lag_features(series, n_lags=3):
    """用前 n_lags 个时刻预测当前值，返回 (X, y)。

    可将机器学习模型用于时间序列预测（滚动预测未来点）。
    """
    s = np.asarray(series, dtype=float)
    X, y = [], []
    for i in range(n_lags, len(s)):
        X.append(s[i - n_lags:i])
        y.append(s[i])
    return np.array(X), np.array(y)


# ----------------------------------------------------------------------
# 演示
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 多特征驱动的数值预测：多个特征列 → 一个目标列
    #   names = ['特征1', '特征2', '特征3', '特征4']
    #   X = df[names].values          # 特征矩阵 (n_samples, n_features)
    #   y = df['目标列'].values       # 目标 (n_samples,) 连续值
    #   rf_model, rf_m = random_forest_regression(X, y, feature_names=names)
    #   # (类别型特征需先编码；时序数据可用 make_lag_features 转滞后特征)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    rng = np.random.RandomState(42)
    n = 400
    # 构造带非线性关系与噪声特征的回归数据（模拟“定价/销量”多因素预测）
    x1 = rng.uniform(0, 10, n)      # 强相关
    x2 = rng.uniform(0, 5, n)       # 中等相关
    x3 = rng.uniform(0, 1, n)       # 非线性
    x4 = rng.normal(0, 1, n)        # 噪声（应重要性最低）
    y = (3 * x1 + 2 * np.sin(x2) + 8 * x3 ** 2 + rng.normal(0, 1.0, n))
    X = np.column_stack([x1, x2, x3, x4])
    names = ['价格', '促销力度', '季节指数', '无关噪声']

    print("########## 随机森林 / XGBoost 回归预测演示 ##########")
    rf_model, rf_m = random_forest_regression(X, y, feature_names=names,
                                              n_estimators=200, max_depth=None)
    xgb_model, xgb_m = xgboost_regression(X, y, feature_names=names,
                                          n_estimators=300, max_depth=4,
                                          learning_rate=0.1)

    print("\n模型对比(测试集 R2)：随机森林=%.4f  XGBoost=%.4f"
          % (rf_m['R2'], xgb_m['R2']))
    if not _HAS_XGB:
        print("提示：未检测到 xgboost，已用 GBDT 替代。安装：pip install xgboost")

    # 时间序列 → 机器学习预测的用法演示
    print("\n########## 附：用随机森林做时间序列滚动预测 ##########")
    t = np.arange(150)
    ts = 20 + 0.3 * t + 5 * np.sin(2 * np.pi * t / 12) + rng.normal(0, 1, 150)
    Xl, yl = make_lag_features(ts, n_lags=6)
    split = len(Xl) - 12
    rf_ts = RandomForestRegressor(n_estimators=200, random_state=0)
    rf_ts.fit(Xl[:split], yl[:split])
    pred_ts = rf_ts.predict(Xl[split:])
    m_ts = regression_metrics(yl[split:], pred_ts)
    print("  滞后特征(n_lags=6)预测末12点: RMSE=%.4f  MAPE=%.2f%%  R2=%.4f"
          % (m_ts['RMSE'], m_ts['MAPE(%)'], m_ts['R2']))

    if _HAS_PLT:
        try:
            order = np.argsort(rf_model.feature_importances_)[::-1]
            plt.figure(figsize=(9, 5))
            plt.bar([names[i] for i in order],
                    rf_model.feature_importances_[order], color='steelblue')
            plt.title('随机森林 特征重要性'); plt.ylabel('重要性')
            plt.grid(alpha=0.3, axis='y'); plt.tight_layout()
            plt.savefig('05_特征重要性示例.png', dpi=120)
            print("[图已保存] 05_特征重要性示例.png")
        except Exception as e:
            print("绘图跳过：", e)

    print("\n演示完成。多特征预测优先随机森林/XGBoost，并输出特征重要性支撑论文。")
