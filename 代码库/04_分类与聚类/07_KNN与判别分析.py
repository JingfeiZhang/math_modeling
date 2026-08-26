# -*- coding: utf-8 -*-
"""
KNN 分类 + 判别分析 (LDA / Fisher 线性判别 / QDA) —— 国赛C题模板
================================================================
呼应 2022 国赛 C题（古代玻璃成分分类判别）：用已知类别样本训练判别模型，
再对未知样本进行类别判定。

功能：
    1. 训练/测试划分 + 标准化
    2. KNN 分类：k 值选择曲线（过小过拟合、过大欠拟合）
    3. LDA 线性判别分析（Fisher 判别）：有监督降维 + 分类
    4. QDA 二次判别（各类协方差不等时更优）
    5. 三种方法评价对比：准确率/精确率/召回率/F1/混淆矩阵
    6. LDA 降维投影可视化（把高维数据投到判别方向上看类别分离）

方法要点：
    KNN —— 基于距离投票，无训练过程，必须标准化；k 通常取奇数、交叉验证选。
    LDA —— 假设各类协方差相同，寻找“类间散度/类内散度最大”的投影方向(Fisher准则)；
           既能分类又能降维(降到 类别数-1 维)，可解释性强。
    QDA —— 放宽“协方差相同”假设，边界为二次曲面。

输入格式：
    X : (n_samples, n_features) 数值特征；y : (n_samples,) 类别标签。

适用 C题场景：
    有标签样本的类别判定（2022 玻璃“高钾/铅钡”判别）、
    需要有监督降维可视化时用 LDA。

依赖：numpy pandas scikit-learn matplotlib
================================================================
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.neighbors import KNeighborsClassifier
from sklearn.discriminant_analysis import (LinearDiscriminantAnalysis,
                                           QuadraticDiscriminantAnalysis)
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix, classification_report)

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
SAVE_DIR = os.path.dirname(os.path.abspath(__file__))


def evaluate(y_true, y_pred, name='模型'):
    """打印四大分类指标，返回指标字典（不画图，便于多模型对比）。"""
    avg = 'binary' if len(np.unique(y_true)) == 2 else 'macro'
    m = {
        '准确率': accuracy_score(y_true, y_pred),
        '精确率': precision_score(y_true, y_pred, average=avg, zero_division=0),
        '召回率': recall_score(y_true, y_pred, average=avg, zero_division=0),
        'F1': f1_score(y_true, y_pred, average=avg, zero_division=0),
    }
    print(f'[{name}] ' + '  '.join(f'{k}={v:.4f}' for k, v in m.items()))
    return m


def plot_confusion(y_true, y_pred, title, fname):
    """绘制混淆矩阵热力图。"""
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
    plt.savefig(os.path.join(SAVE_DIR, fname), dpi=150, bbox_inches='tight')
    plt.show()


def choose_k(X_tr, y_tr, k_max=20, save=True):
    """交叉验证选 KNN 的 k 值。"""
    ks = range(1, k_max + 1)
    scores = [cross_val_score(KNeighborsClassifier(n_neighbors=k),
                              X_tr, y_tr, cv=5).mean() for k in ks]
    best_k = list(ks)[int(np.argmax(scores))]
    plt.figure(figsize=(8, 5))
    plt.plot(list(ks), scores, 'o-', lw=2, color='#2779ac')
    plt.axvline(best_k, ls='--', color='gray')
    plt.xlabel('k 值'); plt.ylabel('5折交叉验证准确率')
    plt.title(f'KNN 选 k：最优 k={best_k}')
    plt.grid(alpha=0.3)
    if save:
        plt.savefig(os.path.join(SAVE_DIR, 'KNN_选k.png'), dpi=150, bbox_inches='tight')
    plt.show()
    print(f'KNN 交叉验证最优 k={best_k}')
    return best_k


def lda_projection_plot(X, y, save=True):
    """用 LDA 把数据投到判别方向（2维）可视化类别分离效果。"""
    n_comp = min(2, len(np.unique(y)) - 1)
    if n_comp < 1:
        return
    Z = LinearDiscriminantAnalysis(n_components=n_comp).fit_transform(X, y)
    plt.figure(figsize=(8, 6))
    if n_comp == 1:
        for c in np.unique(y):
            plt.scatter(Z[y == c, 0], np.random.rand((y == c).sum()) * 0.1,
                        s=25, alpha=0.7, label=f'类 {c}')
        plt.ylabel('抖动(仅显示)')
    else:
        for c in np.unique(y):
            plt.scatter(Z[y == c, 0], Z[y == c, 1], s=25, alpha=0.7, label=f'类 {c}')
        plt.ylabel('判别方向 2')
    plt.xlabel('判别方向 1')
    plt.title('LDA 有监督降维投影（类别分离可视化）')
    plt.legend(); plt.grid(alpha=0.3)
    if save:
        plt.savefig(os.path.join(SAVE_DIR, 'LDA_投影.png'), dpi=150, bbox_inches='tight')
    plt.show()


def run_all(X, y, test_size=0.3):
    """KNN / LDA / QDA 三种方法训练 + 评价对比。"""
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y)
    scaler = StandardScaler().fit(X_tr)
    X_tr_s, X_te_s = scaler.transform(X_tr), scaler.transform(X_te)

    print('=' * 45)
    # ---- KNN ----
    best_k = choose_k(X_tr_s, y_tr)
    knn = KNeighborsClassifier(n_neighbors=best_k).fit(X_tr_s, y_tr)
    yk = knn.predict(X_te_s)
    evaluate(y_te, yk, name=f'KNN(k={best_k})')
    plot_confusion(y_te, yk, f'KNN(k={best_k}) 混淆矩阵', 'KNN_混淆矩阵.png')

    # ---- LDA (Fisher 判别) ----
    lda = LinearDiscriminantAnalysis().fit(X_tr_s, y_tr)
    yl = lda.predict(X_te_s)
    evaluate(y_te, yl, name='LDA/Fisher判别')
    plot_confusion(y_te, yl, 'LDA 混淆矩阵', 'LDA_混淆矩阵.png')

    # ---- QDA ----
    qda = QuadraticDiscriminantAnalysis().fit(X_tr_s, y_tr)
    yq = qda.predict(X_te_s)
    evaluate(y_te, yq, name='QDA二次判别')
    print('=' * 45)

    # LDA 降维投影可视化（用全部数据）
    lda_projection_plot(scaler.transform(X), y)
    return knn, lda, qda


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 判别分析是【有监督】：需要"已知类别"的特征矩阵 X + 类别标签列 y
    #   # 呼应 2022 C题(古代玻璃成分判别)：标签为玻璃类型(高钾/铅钡)
    #   X = df[['SiO2', 'Na2O', 'K2O', 'CaO']].values   # 成分/特征矩阵 (n_samples, k)
    #   y = df['类型'].values                            # 类别标签 (n_samples,)
    #   run_all(X, y)     # (KNN/LDA 必须标准化，run_all 内部已内置)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    from sklearn.datasets import load_wine

    print('\n########## 示例：红酒数据（3类，13特征）判别分类 ##########')
    wine = load_wine()
    run_all(wine.data, wine.target)

    print('\n提示：KNN 必标准化、k 用交叉验证；LDA 假设各类协方差相同、'
          '兼具降维；协方差差异大时用 QDA。判别分析需要“已知类别的训练样本”。')

