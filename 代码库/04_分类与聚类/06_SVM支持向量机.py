# -*- coding: utf-8 -*-
"""
支持向量机 SVM (Support Vector Machine) 分类 —— 国赛C题模板
================================================================
功能：
    1. 训练/测试划分（分层）+ 标准化（SVM 对量纲极敏感，必做）
    2. 核函数选择说明 + GridSearchCV 网格搜索调参 (C, gamma, kernel)
    3. 分类评价：准确率/精确率/召回率/F1/混淆矩阵/分类报告
    4. 决策边界可视化（二维特征时）
    5. （对应 2022 C题）SVM 判别分类思路

核函数（kernel）选择：
    linear  —— 线性可分或特征维数很高时（文本/高维），速度快、可解释
    rbf     —— 高斯核，默认首选，能拟合非线性边界（绝大多数情况用它）
    poly    —— 多项式核，有明显多项式关系时
    sigmoid —— 类神经网络，较少用

核心参数：
    C     : 惩罚系数。大→对误分类惩罚重，间隔小，易过拟合；小→间隔大，易欠拟合。
    gamma : rbf/poly 核系数。大→单样本影响范围小，决策边界复杂易过拟合；
            小→边界平滑。常用 'scale'(默认) 或网格搜索。

输入格式：
    X : (n_samples, n_features) 数值；y : (n_samples,) 类别标签。

适用 C题场景：
    中小样本、特征间非线性关系的分类判别（2022 玻璃类型判别的经典方法）。

依赖：numpy pandas scikit-learn matplotlib
================================================================
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix, classification_report)

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
SAVE_DIR = os.path.dirname(os.path.abspath(__file__))


def evaluate_classification(y_true, y_pred, title='混淆矩阵', fname='混淆矩阵.png', save=True):
    """通用分类评价：四大指标 + 分类报告 + 混淆矩阵图。"""
    avg = 'binary' if len(np.unique(y_true)) == 2 else 'macro'
    metrics = {
        '准确率Accuracy': accuracy_score(y_true, y_pred),
        '精确率Precision': precision_score(y_true, y_pred, average=avg, zero_division=0),
        '召回率Recall': recall_score(y_true, y_pred, average=avg, zero_division=0),
        'F1': f1_score(y_true, y_pred, average=avg, zero_division=0),
    }
    print('-' * 45)
    for k, v in metrics.items():
        print(f'  {k}: {v:.4f}')
    print('分类报告:\n', classification_report(y_true, y_pred, zero_division=0))

    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 5))
    plt.imshow(cm, cmap='Blues'); plt.colorbar()
    ticks = np.arange(len(np.unique(y_true)))
    plt.xticks(ticks); plt.yticks(ticks)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(j, i, cm[i, j], ha='center',
                     color='white' if cm[i, j] > cm.max() / 2 else 'black')
    plt.xlabel('预测类别'); plt.ylabel('真实类别'); plt.title(title)
    plt.tight_layout()
    if save:
        plt.savefig(os.path.join(SAVE_DIR, fname), dpi=150, bbox_inches='tight')
    plt.show()
    return metrics


def grid_search_svm(X_tr, y_tr):
    """网格搜索最优 (kernel, C, gamma)，5 折交叉验证。"""
    param_grid = [
        {'kernel': ['linear'], 'C': [0.1, 1, 10, 100]},
        {'kernel': ['rbf'], 'C': [0.1, 1, 10, 100],
         'gamma': ['scale', 0.01, 0.1, 1]},
    ]
    # n_jobs=1 保证各平台稳定；本机 CPU 多核时可改 -1 加速
    grid = GridSearchCV(SVC(), param_grid, cv=5, scoring='accuracy', n_jobs=1)
    grid.fit(X_tr, y_tr)
    print(f'最优参数: {grid.best_params_}')
    print(f'交叉验证最优准确率: {grid.best_score_:.4f}')
    return grid.best_estimator_, grid.best_params_


def plot_decision_boundary(model, X, y, save=True):
    """二维特征时绘制 SVM 决策边界。"""
    if X.shape[1] != 2:
        print('特征非二维，跳过决策边界绘制。')
        return
    h = 0.02
    x_min, x_max = X[:, 0].min() - 1, X[:, 0].max() + 1
    y_min, y_max = X[:, 1].min() - 1, X[:, 1].max() + 1
    xx, yy = np.meshgrid(np.arange(x_min, x_max, h), np.arange(y_min, y_max, h))
    Z = model.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
    plt.figure(figsize=(8, 6))
    plt.contourf(xx, yy, Z, alpha=0.3, cmap='coolwarm')
    plt.scatter(X[:, 0], X[:, 1], c=y, cmap='coolwarm', edgecolors='k', s=30)
    plt.xlabel('特征1'); plt.ylabel('特征2')
    plt.title('SVM 决策边界')
    if save:
        plt.savefig(os.path.join(SAVE_DIR, 'SVM_决策边界.png'), dpi=150, bbox_inches='tight')
    plt.show()


def run_svm(X, y, test_size=0.3, do_grid=True, draw_boundary=False):
    """SVM 分类完整流程：标准化 → 调参 → 评价。"""
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y)
    scaler = StandardScaler().fit(X_tr)
    X_tr, X_te = scaler.transform(X_tr), scaler.transform(X_te)

    print('=' * 45)
    if do_grid:
        model, best = grid_search_svm(X_tr, y_tr)
    else:
        model = SVC(kernel='rbf', C=1.0, gamma='scale').fit(X_tr, y_tr)
    y_pred = model.predict(X_te)
    print(f'测试集准确率: {accuracy_score(y_te, y_pred):.4f}')
    evaluate_classification(y_te, y_pred, title='SVM-混淆矩阵', fname='SVM_混淆矩阵.png')
    print('支持向量个数(每类):', model.n_support_)
    print('=' * 45)

    if draw_boundary and X.shape[1] == 2:
        plot_decision_boundary(model, np.vstack([X_tr, X_te]),
                               np.concatenate([y_tr, y_te]))
    return model


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 分类是【有监督】：需要特征矩阵 X + 类别标签列 y
    #   X = df[['特征1', '特征2', '特征3']].values   # 特征矩阵 (n_samples, n_features)
    #   y = df['标签列'].values                      # 类别标签 (n_samples,)
    #   run_svm(X, y)     # (SVM 必须标准化，run_svm 内部已内置)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    from sklearn.datasets import load_iris, load_wine

    print('\n########## 示例1：鸢尾花取前2特征（可画决策边界）##########')
    iris = load_iris()
    run_svm(iris.data[:, :2], iris.target, do_grid=True, draw_boundary=True)

    print('\n########## 示例2：红酒数据（多分类，全特征）##########')
    wine = load_wine()
    run_svm(wine.data, wine.target, do_grid=True, draw_boundary=False)

    print('\n提示：SVM 必须标准化；rbf 核最通用，C 控过拟合、gamma 控边界复杂度；'
          '样本量大(>1万)时 SVM 慢，可换随机森林。')

