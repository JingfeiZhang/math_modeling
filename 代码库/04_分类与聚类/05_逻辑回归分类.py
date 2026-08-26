# -*- coding: utf-8 -*-
"""
逻辑回归分类 (Logistic Regression) —— 国赛C题模板（二分类 / 多分类）
================================================================
功能：
    1. 训练集/测试集划分（分层抽样）+ 标准化
    2. 逻辑回归分类（二分类；多分类用 OvR/multinomial）
    3. 分类评价指标：准确率 Accuracy、精确率 Precision、召回率 Recall、
       F1、混淆矩阵、分类报告
    4. ROC 曲线 + AUC（二分类直接画；多分类画每类 + micro 平均）
    5. 输出回归系数（可解释：正系数增大该类概率）

逻辑回归特点：
    - 线性模型、可解释性强（系数=对数几率的影响），是分类的 baseline 首选
    - 输出概率（predict_proba），天然适合画 ROC / 设阈值
    - 核心参数：C(正则化强度倒数,越小正则越强) / penalty(l1,l2) / solver

输入格式：
    X : (n_samples, n_features) 数值特征；y : (n_samples,) 类别标签(整数/字符串)

适用 C题场景：
    有标签的二分类/多分类（如 2022 玻璃“风化/未风化”、企业违约与否、
    是否达标），需要概率与可解释系数时。

依赖：numpy pandas scikit-learn matplotlib
================================================================
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, label_binarize
from sklearn.model_selection import train_test_split
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix, classification_report,
                             roc_curve, auc)

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
SAVE_DIR = os.path.dirname(os.path.abspath(__file__))


def evaluate_classification(y_true, y_pred, class_names=None, title='混淆矩阵',
                            fname='混淆矩阵.png', save=True):
    """通用分类评价：打印四大指标 + 分类报告，绘制混淆矩阵热力图。
    可被所有分类模板复用。"""
    avg = 'binary' if len(np.unique(y_true)) == 2 else 'macro'
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, average=avg, zero_division=0)
    rec = recall_score(y_true, y_pred, average=avg, zero_division=0)
    f1 = f1_score(y_true, y_pred, average=avg, zero_division=0)
    print('-' * 45)
    print(f'准确率 Accuracy : {acc:.4f}')
    print(f'精确率 Precision: {prec:.4f}  ({avg})')
    print(f'召回率 Recall   : {rec:.4f}  ({avg})')
    print(f'F1 分数         : {f1:.4f}  ({avg})')
    print('分类报告:\n', classification_report(y_true, y_pred, zero_division=0))

    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 5))
    plt.imshow(cm, cmap='Blues')
    plt.colorbar()
    ticks = np.arange(len(np.unique(y_true)))
    names = class_names if class_names else ticks
    plt.xticks(ticks, names); plt.yticks(ticks, names)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(j, i, cm[i, j], ha='center',
                     color='white' if cm[i, j] > cm.max() / 2 else 'black')
    plt.xlabel('预测类别'); plt.ylabel('真实类别'); plt.title(title)
    plt.tight_layout()
    if save:
        plt.savefig(os.path.join(SAVE_DIR, fname), dpi=150, bbox_inches='tight')
    plt.show()
    return {'accuracy': acc, 'precision': prec, 'recall': rec, 'f1': f1}


def plot_roc(y_test, y_score, n_classes, save=True):
    """绘制 ROC 曲线并计算 AUC。
    二分类: y_score 为正类概率 (1D)；多分类: y_score 为各类概率 (2D) + y_test 独热。"""
    plt.figure(figsize=(8, 6))
    if n_classes == 2:
        fpr, tpr, _ = roc_curve(y_test, y_score)
        roc_auc = auc(fpr, tpr)
        plt.plot(fpr, tpr, lw=2.5, color='#d94f04', label=f'ROC (AUC={roc_auc:.3f})')
    else:
        colors = plt.get_cmap('tab10', n_classes)   # matplotlib 3.9 起 cm.get_cmap 已移除
        for i in range(n_classes):
            fpr, tpr, _ = roc_curve(y_test[:, i], y_score[:, i])
            plt.plot(fpr, tpr, lw=2, color=colors(i),
                     label=f'类 {i} (AUC={auc(fpr, tpr):.3f})')
        # micro 平均
        fpr, tpr, _ = roc_curve(y_test.ravel(), y_score.ravel())
        plt.plot(fpr, tpr, lw=3, ls=':', color='deeppink',
                 label=f'micro平均 (AUC={auc(fpr, tpr):.3f})')
    plt.plot([0, 1], [0, 1], 'k--', lw=1.5)
    plt.xlabel('假阳率 FPR'); plt.ylabel('真阳率 TPR')
    plt.title('ROC 曲线'); plt.legend(loc='lower right'); plt.grid(alpha=0.3)
    if save:
        plt.savefig(os.path.join(SAVE_DIR, '逻辑回归_ROC.png'), dpi=150, bbox_inches='tight')
    plt.show()


def run_logistic(X, y, C=1.0, test_size=0.3):
    """训练逻辑回归并完成评价 + ROC。自动判断二/多分类。"""
    classes = np.unique(y)
    n_classes = len(classes)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y)

    scaler = StandardScaler().fit(X_tr)
    X_tr, X_te = scaler.transform(X_tr), scaler.transform(X_te)

    # sklearn 1.7+ 移除了 multi_class 形参: 多分类默认即用 multinomial(softmax),
    # 二分类自动用 OvR, 无需再指定
    clf = LogisticRegression(C=C, max_iter=1000)
    clf.fit(X_tr, y_tr)
    y_pred = clf.predict(X_te)

    print('=' * 45)
    print(f'逻辑回归 (C={C}, {"多分类" if n_classes>2 else "二分类"})')
    print(f'训练集准确率: {clf.score(X_tr, y_tr):.4f}')
    evaluate_classification(y_te, y_pred, title='逻辑回归-混淆矩阵',
                            fname='逻辑回归_混淆矩阵.png')
    print('回归系数 shape:', clf.coef_.shape, '（每行对应一个类别的特征权重）')
    print('=' * 45)

    # ROC
    if n_classes == 2:
        y_score = clf.predict_proba(X_te)[:, 1]
        plot_roc(y_te, y_score, n_classes)
    else:
        y_te_bin = label_binarize(y_te, classes=classes)
        y_score = clf.predict_proba(X_te)
        plot_roc(y_te_bin, y_score, n_classes)
    return clf


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 分类是【有监督】：需要特征矩阵 X + 类别标签列 y
    #   X = df[['特征1', '特征2', '特征3']].values   # 特征矩阵 (n_samples, n_features)
    #   y = df['标签列'].values                      # 类别标签 (n_samples,) 二/多分类均可
    #   run_logistic(X, y, C=1.0)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    from sklearn.datasets import load_breast_cancer, load_iris

    print('\n########## 示例1：二分类（乳腺癌数据）##########')
    data = load_breast_cancer()
    run_logistic(data.data, data.target, C=1.0)

    print('\n########## 示例2：多分类（鸢尾花3类）##########')
    iris = load_iris()
    run_logistic(iris.data, iris.target, C=1.0)

    print('\n提示：C 越小正则化越强(防过拟合)；类别不平衡可加 class_weight="balanced"。')

