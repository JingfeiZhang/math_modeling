# -*- coding: utf-8 -*-
"""
凝聚层次聚类 (Agglomerative Hierarchical Clustering) —— 国赛C题模板
================================================================
功能：
    1. 数据标准化
    2. 绘制树状图 dendrogram（层次聚类核心产物，据此“横切”定簇数）
    3. 依据不同 linkage（ward/average/complete）+ 轮廓系数选参数
    4. 输出聚类标签与聚类评价（轮廓系数、CH、DB）
    5. 可视化：树状图 + 聚类散点图

方法要点：
    - 自底向上：每个样本先各成一类，反复合并最近的两类，直到成一类。
    - 无需预设 K；通过树状图选择“切割高度”决定簇数。
    - linkage（簇间距离度量）：
        ward     —— 最小化合并后方差，簇较均衡（最常用，仅欧氏距离）
        average  —— 类平均距离，较稳健
        complete —— 最远点距离，倾向紧凑等径簇
        single   —— 最近点距离，易“链式效应”

输入格式：
    X : (n_samples, n_features) 数值矩阵，无监督。样本数不宜过大(树状图 <~ 数百)。

适用 C题场景：
    样本量中小、需要“分组层级关系可视化”的分群（如 2022 玻璃按成分分层、
    地区/指标聚类树），或需要展示聚合过程时。

依赖：numpy pandas scipy scikit-learn matplotlib
================================================================
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster
from sklearn.cluster import AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (silhouette_score, calinski_harabasz_score,
                             davies_bouldin_score)

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
SAVE_DIR = os.path.dirname(os.path.abspath(__file__))


def plot_dendrogram(X, method='ward', labels=None, save=True):
    """绘制树状图。method 对应 scipy linkage 方法。
    看图技巧：找“最长的、未被横线穿过的竖直线段”，在其中部水平切割，
    切到几条竖线就分几类。"""
    Z = linkage(X, method=method)
    plt.figure(figsize=(11, 6))
    dendrogram(Z, labels=labels, leaf_rotation=90, leaf_font_size=8)
    plt.xlabel('样本'); plt.ylabel('合并距离(高度)')
    plt.title(f'层次聚类树状图 (linkage={method})')
    plt.tight_layout()
    if save:
        plt.savefig(os.path.join(SAVE_DIR, '层次聚类_树状图.png'), dpi=150, bbox_inches='tight')
    plt.show()
    return Z


def choose_by_silhouette(X, k_range=range(2, 8), linkage_method='ward'):
    """在不同 K 下计算轮廓系数，辅助确定簇数。"""
    sils = []
    for k in k_range:
        model = AgglomerativeClustering(n_clusters=k, linkage=linkage_method)
        labels = model.fit_predict(X)
        sils.append(silhouette_score(X, labels))
    best_k = list(k_range)[int(np.argmax(sils))]

    plt.figure(figsize=(8, 5))
    plt.plot(list(k_range), sils, 'o-', lw=2, color='#d94f04')
    plt.axvline(best_k, ls='--', color='gray')
    plt.xlabel('簇数 K'); plt.ylabel('轮廓系数')
    plt.title(f'层次聚类选 K：轮廓系数最大 K={best_k}')
    plt.grid(alpha=0.3)
    plt.savefig(os.path.join(SAVE_DIR, '层次聚类_选K.png'), dpi=150, bbox_inches='tight')
    plt.show()
    print(f'轮廓系数推荐簇数 K={best_k}')
    return best_k


def hierarchical_cluster(X, n_clusters, linkage_method='ward',
                         feature_names=None, save=True):
    """执行凝聚层次聚类，返回标签与评价指标。"""
    model = AgglomerativeClustering(n_clusters=n_clusters, linkage=linkage_method)
    labels = model.fit_predict(X)

    metrics = {
        '轮廓系数(越大越好)': round(silhouette_score(X, labels), 4),
        'CH指数(越大越好)': round(calinski_harabasz_score(X, labels), 2),
        'DB指数(越小越好)': round(davies_bouldin_score(X, labels), 4),
    }
    print('=' * 45)
    print(f'层次聚类完成: K={n_clusters}, linkage={linkage_method}')
    for k, v in metrics.items():
        print(f'  {k}: {v}')
    uniq, cnt = np.unique(labels, return_counts=True)
    print('  各簇样本数:', dict(zip(uniq.tolist(), cnt.tolist())))
    print('=' * 45)

    plt.figure(figsize=(8, 6))
    for c in range(n_clusters):
        pts = X[labels == c]
        plt.scatter(pts[:, 0], pts[:, 1], s=30, alpha=0.7, label=f'簇 {c}')
    xl = feature_names[0] if feature_names else '特征1'
    yl = feature_names[1] if feature_names else '特征2'
    plt.xlabel(xl); plt.ylabel(yl)
    plt.title(f'层次聚类结果 (K={n_clusters}, {linkage_method})')
    plt.legend(); plt.grid(alpha=0.3)
    if save:
        plt.savefig(os.path.join(SAVE_DIR, '层次聚类_结果.png'), dpi=150, bbox_inches='tight')
    plt.show()
    return labels, metrics


if __name__ == '__main__':
    # ================ 示例数据：4 个高斯簇 ================
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 聚类是【无监督】，只需特征矩阵 X_raw，不需要标签 y：
    #   feature_names = ['指标1', '指标2', '指标3']
    #   X_raw = df[feature_names].values     # (n_samples, n_features) 纯数值
    #   # (样本数不宜过大，树状图适合几百个样本以内；下面已内置标准化)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    rng = np.random.RandomState(42)
    centers = [[2, 2], [8, 3], [5, 9], [10, 9]]
    X_raw = np.vstack([rng.randn(35, 2) * 0.6 + c for c in centers])
    feature_names = ['特征1', '特征2']

    # 1) 标准化
    X = StandardScaler().fit_transform(X_raw)

    # 2) 树状图（据此判断切几类）
    plot_dendrogram(X, method='ward')

    # 3) 轮廓系数辅助选 K
    best_k = choose_by_silhouette(X, k_range=range(2, 8), linkage_method='ward')

    # 4) 聚类
    labels, metrics = hierarchical_cluster(X, n_clusters=best_k,
                                           linkage_method='ward',
                                           feature_names=feature_names)

    # 也可直接用 scipy 的 fcluster 从 linkage 矩阵按簇数/高度切割：
    Z = linkage(X, method='ward')
    labels_scipy = fcluster(Z, t=best_k, criterion='maxclust')
    print('scipy fcluster 切割标签（前20）:', labels_scipy[:20])

    print('\n提示：树状图切割高度越高、簇数越少；ward 最常用，'
          '若簇形状差异大可试 average/complete。')

