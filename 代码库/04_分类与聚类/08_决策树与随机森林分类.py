# -*- coding: utf-8 -*-
"""
决策树 + 随机森林 分类 —— 国赛C题模板
================================================================
功能：
    1. 训练/测试划分（分层）；树模型对量纲不敏感，无需标准化
    2. 决策树分类 + 树结构可视化 + 过拟合控制(max_depth)
    3. 随机森林分类 + 袋外(OOB)评分
    4. 特征重要性排序与可视化（数据挖掘/解释题的高频得分点）
    5. 分类评价：准确率/精确率/召回率/F1/混淆矩阵/分类报告
    6. 随机森林关键参数网格搜索

方法要点：
    决策树   —— 规则可视、可解释；易过拟合，靠 max_depth/min_samples_leaf 剪枝。
    随机森林 —— 多棵树 Bagging 集成，抗过拟合、精度高、给特征重要性，
                 是 C题分类/数据挖掘的“万金油”（2025 类随机森林题）。

核心参数（随机森林）：
    n_estimators      : 树的棵数，越多越稳(100~500)，边际递减
    max_depth         : 单树最大深度，控过拟合
    max_features      : 每次分裂考虑的特征数('sqrt'常用)
    min_samples_leaf  : 叶节点最小样本数，增大可平滑、防过拟合
    class_weight      : 'balanced' 处理类别不平衡

输入格式：
    X : (n_samples, n_features) 数值/编码后特征；y : (n_samples,) 类别标签。

适用 C题场景：
    有标签分类、需要特征重要性解释（哪些指标最关键）、
    非线性且含交互作用的数据挖掘题。

依赖：numpy pandas scikit-learn matplotlib
================================================================
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix, classification_report)

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
SAVE_DIR = os.path.dirname(os.path.abspath(__file__))


def evaluate(y_true, y_pred, name, fname, class_names=None, save=True):
    """四大指标 + 分类报告 + 混淆矩阵图。"""
    avg = 'binary' if len(np.unique(y_true)) == 2 else 'macro'
    print(f'--- [{name}] ---')
    print(f'  准确率={accuracy_score(y_true, y_pred):.4f}  '
          f'精确率={precision_score(y_true, y_pred, average=avg, zero_division=0):.4f}  '
          f'召回率={recall_score(y_true, y_pred, average=avg, zero_division=0):.4f}  '
          f'F1={f1_score(y_true, y_pred, average=avg, zero_division=0):.4f}')
    print(classification_report(y_true, y_pred, zero_division=0))

    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 5))
    plt.imshow(cm, cmap='Blues'); plt.colorbar()
    ticks = np.arange(len(np.unique(y_true)))
    names = class_names if class_names else ticks
    plt.xticks(ticks, names); plt.yticks(ticks, names)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(j, i, cm[i, j], ha='center',
                     color='white' if cm[i, j] > cm.max() / 2 else 'black')
    plt.xlabel('预测类别'); plt.ylabel('真实类别'); plt.title(f'{name} 混淆矩阵')
    plt.tight_layout()
    if save:
        plt.savefig(os.path.join(SAVE_DIR, fname), dpi=150, bbox_inches='tight')
    plt.show()


def plot_feature_importance(importances, feature_names, save=True):
    """特征重要性条形图（降序）。"""
    idx = np.argsort(importances)[::-1]
    plt.figure(figsize=(9, 5))
    plt.bar(range(len(importances)), importances[idx], color='#007172')
    plt.xticks(range(len(importances)),
               [feature_names[i] for i in idx], rotation=45, ha='right')
    plt.ylabel('重要性'); plt.title('随机森林特征重要性排序')
    plt.tight_layout()
    if save:
        plt.savefig(os.path.join(SAVE_DIR, '随机森林_特征重要性.png'), dpi=150, bbox_inches='tight')
    plt.show()
    print('特征重要性（降序）:')
    for i in idx:
        print(f'  {feature_names[i]}: {importances[i]:.4f}')


def run_decision_tree(X_tr, X_te, y_tr, y_te, feature_names, class_names=None,
                      max_depth=4, save=True):
    """决策树分类 + 树结构可视化。"""
    dt = DecisionTreeClassifier(max_depth=max_depth, random_state=42).fit(X_tr, y_tr)
    y_pred = dt.predict(X_te)
    print('=' * 45)
    evaluate(y_te, y_pred, name=f'决策树(max_depth={max_depth})',
             fname='决策树_混淆矩阵.png', class_names=class_names)

    plt.figure(figsize=(16, 8))
    plot_tree(dt, feature_names=feature_names,
              class_names=[str(c) for c in (class_names or np.unique(y_tr))],
              filled=True, rounded=True, fontsize=8)
    plt.title('决策树结构')
    if save:
        plt.savefig(os.path.join(SAVE_DIR, '决策树_结构.png'), dpi=150, bbox_inches='tight')
    plt.show()
    return dt


def run_random_forest(X_tr, X_te, y_tr, y_te, feature_names, class_names=None,
                      do_grid=True):
    """随机森林分类 + OOB + 特征重要性 + 可选网格搜索。"""
    if do_grid:
        param_grid = {'n_estimators': [100, 200],
                      'max_depth': [None, 5, 10],
                      'max_features': ['sqrt', 'log2']}
        # n_jobs=1 保证各平台稳定；本机多核可改 -1
        grid = GridSearchCV(RandomForestClassifier(random_state=42),
                            param_grid, cv=5, n_jobs=1)
        grid.fit(X_tr, y_tr)
        print(f'随机森林最优参数: {grid.best_params_}  '
              f'交叉验证准确率: {grid.best_score_:.4f}')
        rf = grid.best_estimator_
    else:
        rf = RandomForestClassifier(n_estimators=200, random_state=42).fit(X_tr, y_tr)

    # OOB 评分（需 bootstrap=True，默认）
    rf_oob = RandomForestClassifier(n_estimators=rf.n_estimators, oob_score=True,
                                    random_state=42).fit(X_tr, y_tr)
    print(f'袋外(OOB)得分: {rf_oob.oob_score_:.4f}')

    y_pred = rf.predict(X_te)
    evaluate(y_te, y_pred, name='随机森林',
             fname='随机森林_混淆矩阵.png', class_names=class_names)
    plot_feature_importance(rf.feature_importances_, feature_names)
    print('=' * 45)
    return rf


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 分类是【有监督】：需要特征矩阵 X + 类别标签列 y
    #   feature_names = ['特征1', '特征2', '特征3']
    #   X = df[feature_names].values                 # 特征矩阵 (n_samples, n_features)
    #   y = df['标签列'].values                       # 类别标签 (n_samples,)
    #   class_names = [str(c) for c in np.unique(y)]  # 类别名(用于图例)
    #   X_tr, X_te, y_tr, y_te = train_test_split(
    #       X, y, test_size=0.3, random_state=42, stratify=y)
    #   run_decision_tree(X_tr, X_te, y_tr, y_te, feature_names, class_names, max_depth=4)
    #   run_random_forest(X_tr, X_te, y_tr, y_te, feature_names, class_names, do_grid=True)
    #   # (树模型无需标准化)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    from sklearn.datasets import load_wine

    print('\n########## 示例：红酒数据（3类，13特征）##########')
    wine = load_wine()
    X, y = wine.data, wine.target
    feature_names = list(wine.feature_names)
    class_names = [str(c) for c in wine.target_names]

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y)

    # 决策树（树模型无需标准化）
    run_decision_tree(X_tr, X_te, y_tr, y_te, feature_names, class_names, max_depth=4)

    # 随机森林 + 特征重要性
    run_random_forest(X_tr, X_te, y_tr, y_te, feature_names, class_names, do_grid=True)

    print('\n提示：树模型不用标准化；决策树靠 max_depth 剪枝防过拟合；'
          '随机森林精度高且直接给“特征重要性”，是C题分类/数据挖掘首选。')

