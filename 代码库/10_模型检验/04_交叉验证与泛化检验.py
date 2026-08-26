# -*- coding: utf-8 -*-
"""
================================================================================
04 交叉验证与泛化检验 (Cross-Validation & Generalization)
================================================================================
功能：
    检验模型的“泛化能力”——在没见过的数据上表现如何，是否过拟合/欠拟合。提供：
      1. 训练/测试集划分：单次 hold-out 评估。
      2. K 折交叉验证：数据分 K 份轮流当验证集，得到每折指标分布。
      3. 留一法 LOO：每次留 1 个样本当验证集（小样本适用）。
      4. 学习曲线：训练集/验证集得分随样本量变化，判断过拟合(高方差)/欠拟合(高偏差)。
    分类任务给准确率/F1 的每折箱线图；回归任务给 RMSE/R² 的每折分布。

适用竞赛场景：
    - 分类/回归/预测模型选完后，用交叉验证给出“可信的泛化误差”而非训练误差。
    - 呼应 2026 自查表对“结果合理性/避免过拟合”的要求，是论文检验环的重要一环。

输入格式：
    - X：特征矩阵 (n_samples, n_features)；y：标签/目标 (n_samples,)。
    - task：'reg'（回归）或 'clf'（分类）。
    - model：sklearn 兼容模型（不传则回归用线性回归、分类用逻辑回归）。

输出：
    - 控制台打印各折指标、均值±标准差；
    - 保存 04_交叉验证箱线图.png、04_学习曲线.png。

依赖：numpy, scikit-learn, (可选) matplotlib
================================================================================
"""

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np
from sklearn.model_selection import (train_test_split, KFold, StratifiedKFold,
                                     LeaveOneOut, cross_val_score, learning_curve)
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (mean_squared_error, r2_score,
                             accuracy_score, f1_score)

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
    plt.rcParams['axes.unicode_minus'] = False
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False


def _default_model(task):
    """默认模型：回归=线性回归，分类=逻辑回归。"""
    if task == 'clf':
        return LogisticRegression(max_iter=1000)
    return LinearRegression()


# ----------------------------------------------------------------------
# 1. 训练/测试集单次划分评估
# ----------------------------------------------------------------------
def holdout_eval(X, y, task='reg', model=None, test_size=0.3, seed=0):
    """单次 hold-out：划分训练/测试集，评估测试集泛化表现。"""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y).ravel()
    if model is None:
        model = _default_model(task)
    strat = y if task == 'clf' else None
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=strat)
    model.fit(X_tr, y_tr)
    y_pred_tr = model.predict(X_tr)
    y_pred_te = model.predict(X_te)
    print("=" * 64)
    print("训练/测试集划分评估 (test_size=%.0f%%)" % (test_size * 100))
    print("=" * 64)
    if task == 'clf':
        print("  训练集 准确率=%.4f  F1=%.4f"
              % (accuracy_score(y_tr, y_pred_tr),
                 f1_score(y_tr, y_pred_tr, average='macro')))
        print("  测试集 准确率=%.4f  F1=%.4f"
              % (accuracy_score(y_te, y_pred_te),
                 f1_score(y_te, y_pred_te, average='macro')))
    else:
        print("  训练集 RMSE=%.4f  R²=%.4f"
              % (np.sqrt(mean_squared_error(y_tr, y_pred_tr)), r2_score(y_tr, y_pred_tr)))
        print("  测试集 RMSE=%.4f  R²=%.4f"
              % (np.sqrt(mean_squared_error(y_te, y_pred_te)), r2_score(y_te, y_pred_te)))
    print("  （训练远好于测试 → 过拟合；两者都差 → 欠拟合）")


# ----------------------------------------------------------------------
# 2. K 折交叉验证（含每折分布箱线图）
# ----------------------------------------------------------------------
def kfold_cv(X, y, task='reg', model=None, k=5, seed=0, save_path='04_交叉验证箱线图.png'):
    """K 折交叉验证：返回每折得分，打印均值±标准差，画箱线图。

    分类默认评 准确率 与 F1(macro)；回归默认评 RMSE 与 R²。
    标准差小 = 模型在不同数据划分上稳定 = 泛化可靠。
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y).ravel()
    if model is None:
        model = _default_model(task)

    print("=" * 64)
    print("%d 折交叉验证" % k)
    print("=" * 64)
    box_data, box_labels = [], []
    if task == 'clf':
        splitter = StratifiedKFold(n_splits=k, shuffle=True, random_state=seed)
        acc = cross_val_score(model, X, y, cv=splitter, scoring='accuracy')
        f1 = cross_val_score(model, X, y, cv=splitter, scoring='f1_macro')
        print("  准确率 每折=%s" % np.round(acc, 4))
        print("         均值=%.4f  标准差=%.4f" % (acc.mean(), acc.std()))
        print("  F1     每折=%s" % np.round(f1, 4))
        print("         均值=%.4f  标准差=%.4f" % (f1.mean(), f1.std()))
        box_data = [acc, f1]; box_labels = ['准确率', 'F1(macro)']
    else:
        splitter = KFold(n_splits=k, shuffle=True, random_state=seed)
        # neg_root_mean_squared_error 返回负值，取反得 RMSE
        rmse = -cross_val_score(model, X, y, cv=splitter,
                                scoring='neg_root_mean_squared_error')
        r2 = cross_val_score(model, X, y, cv=splitter, scoring='r2')
        print("  RMSE 每折=%s" % np.round(rmse, 4))
        print("       均值=%.4f  标准差=%.4f" % (rmse.mean(), rmse.std()))
        print("  R²   每折=%s" % np.round(r2, 4))
        print("       均值=%.4f  标准差=%.4f" % (r2.mean(), r2.std()))
        box_data = [rmse, r2]; box_labels = ['RMSE', 'R2']

    if _HAS_PLT:
        try:
            fig, axes = plt.subplots(1, 2, figsize=(12, 5))
            for ax, data, lab in zip(axes, box_data, box_labels):
                ax.boxplot([data], tick_labels=[lab])
                ax.scatter(np.ones(len(data)), data, alpha=0.6, color='#c0504d', zorder=3)
                ax.set_title('%d 折 %s 分布' % (k, lab)); ax.grid(alpha=0.3, axis='y')
            plt.tight_layout(); plt.savefig(save_path, dpi=120); plt.close(fig)
            print("[图已保存] %s" % save_path)
        except Exception as e:
            print("绘图跳过：", e)
    return box_data


# ----------------------------------------------------------------------
# 3. 留一法 LOO（小样本）
# ----------------------------------------------------------------------
def loo_cv(X, y, task='reg', model=None):
    """留一法：每次留 1 个样本验证。样本很少(<50)时替代 K 折。计算量大，样本多勿用。"""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y).ravel()
    if model is None:
        model = _default_model(task)
    n = X.shape[0]
    if n > 200:
        print("[提示] 样本数 %d 较大，LOO 计算量高，建议用 K 折。此处仍演示。" % n)
    loo = LeaveOneOut()
    y_true_all, y_pred_all = [], []
    for tr_idx, te_idx in loo.split(X):
        model.fit(X[tr_idx], y[tr_idx])
        y_pred_all.append(model.predict(X[te_idx])[0])
        y_true_all.append(y[te_idx][0])
    y_true_all = np.array(y_true_all); y_pred_all = np.array(y_pred_all)
    print("=" * 64)
    print("留一法 LOO 交叉验证 (n=%d)" % n)
    print("=" * 64)
    if task == 'clf':
        print("  LOO 准确率=%.4f" % accuracy_score(y_true_all, y_pred_all))
    else:
        print("  LOO RMSE=%.4f  R²=%.4f"
              % (np.sqrt(mean_squared_error(y_true_all, y_pred_all)),
                 r2_score(y_true_all, y_pred_all)))


# ----------------------------------------------------------------------
# 4. 学习曲线（判断过拟合/欠拟合）
# ----------------------------------------------------------------------
def plot_learning_curve(X, y, task='reg', model=None, k=5, seed=0,
                        save_path='04_学习曲线.png'):
    """学习曲线：训练/验证得分随训练样本量变化。

    诊断口诀:
      - 两条曲线都低且贴近 → 欠拟合(高偏差)：换更强模型/加特征。
      - 训练高、验证低、间隙大 → 过拟合(高方差)：加数据/正则/降复杂度。
      - 两条都高且收敛 → 拟合良好。
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y).ravel()
    if model is None:
        model = _default_model(task)
    scoring = 'accuracy' if task == 'clf' else 'r2'
    cv = (StratifiedKFold(n_splits=k, shuffle=True, random_state=seed)
          if task == 'clf' else KFold(n_splits=k, shuffle=True, random_state=seed))
    train_sizes, train_scores, val_scores = learning_curve(
        model, X, y, cv=cv, scoring=scoring,
        train_sizes=np.linspace(0.1, 1.0, 8))
    tr_mean, tr_std = train_scores.mean(1), train_scores.std(1)
    va_mean, va_std = val_scores.mean(1), val_scores.std(1)
    print("=" * 64)
    print("学习曲线（评分=%s）" % scoring)
    print("=" * 64)
    print("  末端：训练得分=%.4f  验证得分=%.4f  间隙=%.4f"
          % (tr_mean[-1], va_mean[-1], tr_mean[-1] - va_mean[-1]))
    gap = tr_mean[-1] - va_mean[-1]
    if va_mean[-1] < 0.6 and tr_mean[-1] < 0.7:
        diag = '疑似欠拟合(两者都偏低)：建议换更强模型或增加特征'
    elif gap > 0.15:
        diag = '疑似过拟合(训练远高于验证)：建议加数据/正则/降复杂度'
    else:
        diag = '拟合较好(训练验证接近且不低)'
    print("  诊断：%s" % diag)

    if _HAS_PLT:
        try:
            fig, ax = plt.subplots(figsize=(9, 6))
            ax.plot(train_sizes, tr_mean, 'o-', color='#c0504d', label='训练得分')
            ax.fill_between(train_sizes, tr_mean - tr_std, tr_mean + tr_std,
                            alpha=0.15, color='#c0504d')
            ax.plot(train_sizes, va_mean, 's-', color='#4f81bd', label='验证得分(交叉验证)')
            ax.fill_between(train_sizes, va_mean - va_std, va_mean + va_std,
                            alpha=0.15, color='#4f81bd')
            ax.set_xlabel('训练样本量'); ax.set_ylabel('得分 (%s)' % scoring)
            ax.set_title('学习曲线（判断过拟合/欠拟合）')
            ax.legend(); ax.grid(alpha=0.3)
            plt.tight_layout(); plt.savefig(save_path, dpi=120); plt.close(fig)
            print("[图已保存] %s" % save_path)
        except Exception as e:
            print("绘图跳过：", e)


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   X = df[['特征1','特征2','特征3']].values     # 特征矩阵 (n_samples, k)
    #   y = df['标签列'].values                       # 分类标签 或 回归目标
    #   task = 'clf'   # 分类填 'clf'，回归/预测填 'reg'
    #   # 想检验自己的模型：model = 你的sklearn模型(...)，各函数传 model=model
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    rng = np.random.RandomState(42)

    print("\n########## A. 回归任务演示 ##########")
    n, k = 200, 3
    Xr = rng.uniform(0, 10, (n, k))
    yr = Xr @ np.array([2.0, -1.5, 0.8]) + 5 + rng.normal(0, 1.5, n)
    holdout_eval(Xr, yr, task='reg')
    kfold_cv(Xr, yr, task='reg', k=5, save_path='04_交叉验证箱线图_回归.png')
    plot_learning_curve(Xr, yr, task='reg', save_path='04_学习曲线_回归.png')

    print("\n########## B. 分类任务演示 ##########")
    n2 = 200
    Xc = np.vstack([rng.normal(0, 1, (n2 // 2, 2)),
                    rng.normal(2.5, 1, (n2 // 2, 2))])
    yc = np.array([0] * (n2 // 2) + [1] * (n2 // 2))
    holdout_eval(Xc, yc, task='clf')
    kfold_cv(Xc, yc, task='clf', k=5, save_path='04_交叉验证箱线图_分类.png')
    # LOO 用小子集演示（计算量）：两类各取 30 个，保证类别齐全
    loo_idx = np.r_[np.arange(30), np.arange(n2 // 2, n2 // 2 + 30)]
    loo_cv(Xc[loo_idx], yc[loo_idx], task='clf')
    plot_learning_curve(Xc, yc, task='clf', save_path='04_学习曲线_分类.png')

    print("\n演示完成。把 X、y、task 换成你的数据即可；传 model 检验自己的模型。")
