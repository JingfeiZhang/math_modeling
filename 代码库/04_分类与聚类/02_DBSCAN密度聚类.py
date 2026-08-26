# -*- coding: utf-8 -*-
"""
DBSCAN 密度聚类 —— 数学建模国赛 C题 标准化模板
================================================================
功能：
    1. 数据标准化
    2. k-距离图（k-distance）辅助确定 eps（核心调参手段）
    3. 网格搜索 (eps, min_samples) 组合，用轮廓系数挑最优参数
    4. DBSCAN 聚类：自动发现簇数 + 识别异常点（标签 = -1）
    5. 聚类评价（剔除噪声后计算轮廓系数、CH、DB）
    6. 可视化：k-距离图、参数热力图、聚类结果（噪声单独标黑）

DBSCAN 相比 KMeans 的优势：
    - 不需要预先指定簇数 K
    - 能发现任意形状的簇（非球形）
    - 天然识别离群点 / 异常点（label == -1）

核心参数：
    eps         : 邻域半径。太小→大量点变噪声；太大→簇合并。用 k-距离图定。
    min_samples : 成为核心点所需邻域内最少样本数。经验值 ≈ 2 * 特征维数。

输入格式：
    X : (n_samples, n_features) 数值特征矩阵，无监督，无需标签。务必标准化。

适用 C题场景：
    异常点/离群样本识别、任意形状分群、密度不均的空间数据聚类。

依赖：numpy pandas scikit-learn matplotlib
================================================================
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import (silhouette_score, calinski_harabasz_score,
                             davies_bouldin_score)

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
SAVE_DIR = os.path.dirname(os.path.abspath(__file__))


def k_distance_plot(X, k=4, save=True):
    """绘制 k-距离图：每个点到第 k 近邻的距离排序后作图，
    曲线的“拐点/陡增处”对应的纵坐标即为推荐 eps。
    经验：k 取 min_samples（约 2*维数）。
    """
    nn = NearestNeighbors(n_neighbors=k).fit(X)
    dist, _ = nn.kneighbors(X)
    kth = np.sort(dist[:, -1])   # 每个点到第 k 近邻的距离，升序
    plt.figure(figsize=(8, 5))
    plt.plot(kth, lw=2, color='#2779ac')
    plt.xlabel('样本点（按距离升序）')
    plt.ylabel(f'到第 {k} 近邻的距离')
    plt.title('k-距离图：曲线陡增拐点的纵坐标 ≈ 推荐 eps')
    plt.grid(alpha=0.3)
    if save:
        plt.savefig(os.path.join(SAVE_DIR, 'DBSCAN_k距离图.png'), dpi=150, bbox_inches='tight')
    plt.show()
    return kth


def grid_search_dbscan(X, eps_range, min_samples_range, save=True):
    """网格搜索 (eps, min_samples)，以轮廓系数为准则选最优参数。
    只在“有效聚类（簇数>=2 且噪声不占绝大多数）”时计算轮廓系数。
    """
    records = []
    for eps in eps_range:
        for ms in min_samples_range:
            labels = DBSCAN(eps=eps, min_samples=ms).fit_predict(X)
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            n_noise = int(np.sum(labels == -1))
            # 至少2簇、且非噪声样本>1 才能算轮廓系数
            mask = labels != -1
            noise_ratio = n_noise / len(labels)
            # 噪声占比过高(>40%)视为无效聚类，避免选出“大部分变噪声”的畸形解
            if n_clusters >= 2 and mask.sum() > n_clusters and noise_ratio <= 0.4:
                sil = silhouette_score(X[mask], labels[mask])
            else:
                sil = -1
            records.append((eps, ms, n_clusters, n_noise, round(sil, 4)))

    df = pd.DataFrame(records, columns=['eps', 'min_samples', '簇数', '噪声数', '轮廓系数'])
    best = df.sort_values('轮廓系数', ascending=False).iloc[0]
    print('参数网格搜索结果（按轮廓系数排序 Top5）:')
    print(df.sort_values('轮廓系数', ascending=False).head().to_string(index=False))
    print(f'\n推荐参数: eps={best.eps}, min_samples={int(best.min_samples)}, '
          f'簇数={int(best.簇数)}, 轮廓系数={best.轮廓系数}')

    # 轮廓系数热力图
    pivot = df.pivot(index='min_samples', columns='eps', values='轮廓系数')
    plt.figure(figsize=(9, 5))
    im = plt.imshow(pivot.values, aspect='auto', cmap='viridis', origin='lower')
    plt.colorbar(im, label='轮廓系数')
    plt.xticks(range(len(pivot.columns)), [f'{c:.2f}' for c in pivot.columns], rotation=45)
    plt.yticks(range(len(pivot.index)), pivot.index)
    plt.xlabel('eps'); plt.ylabel('min_samples')
    plt.title('DBSCAN 参数网格 - 轮廓系数热力图')
    plt.tight_layout()
    if save:
        plt.savefig(os.path.join(SAVE_DIR, 'DBSCAN_参数热力图.png'), dpi=150, bbox_inches='tight')
    plt.show()
    return df, float(best.eps), int(best.min_samples)


def dbscan_cluster(X, eps, min_samples, feature_names=None, save=True):
    """执行 DBSCAN，返回标签与评价指标；label==-1 为异常点。"""
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(X)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = int(np.sum(labels == -1))

    print('=' * 45)
    print(f'DBSCAN 完成: eps={eps}, min_samples={min_samples}')
    print(f'  发现簇数: {n_clusters}    异常点数: {n_noise} / {len(labels)}')
    mask = labels != -1
    metrics = {}
    if n_clusters >= 2 and mask.sum() > n_clusters:
        metrics = {
            '轮廓系数(剔噪声)': round(silhouette_score(X[mask], labels[mask]), 4),
            'CH指数(剔噪声)': round(calinski_harabasz_score(X[mask], labels[mask]), 2),
            'DB指数(剔噪声)': round(davies_bouldin_score(X[mask], labels[mask]), 4),
        }
        for k, v in metrics.items():
            print(f'  {k}: {v}')
    print('=' * 45)

    # 可视化：噪声点用黑色 x
    plt.figure(figsize=(8, 6))
    uniq = sorted(set(labels))
    cmap = plt.get_cmap('tab10', max(n_clusters, 1))   # matplotlib 3.9 起 cm.get_cmap 已移除
    for lab in uniq:
        pts = X[labels == lab]
        if lab == -1:
            plt.scatter(pts[:, 0], pts[:, 1], c='black', marker='x', s=40, label='异常点(-1)')
        else:
            plt.scatter(pts[:, 0], pts[:, 1], color=cmap(lab), s=30, alpha=0.7, label=f'簇 {lab}')
    xl = feature_names[0] if feature_names else '特征1'
    yl = feature_names[1] if feature_names else '特征2'
    plt.xlabel(xl); plt.ylabel(yl)
    plt.title(f'DBSCAN 聚类结果（{n_clusters}簇，{n_noise}个异常点）')
    plt.legend(); plt.grid(alpha=0.3)
    if save:
        plt.savefig(os.path.join(SAVE_DIR, 'DBSCAN_聚类结果.png'), dpi=150, bbox_inches='tight')
    plt.show()
    return labels, metrics


if __name__ == '__main__':
    # ============ 示例数据：3 个密度簇 + 一批离群点（突出 DBSCAN 识别异常）============
    # 说明：DBSCAN 也能处理半月形/环形等任意形状（make_moons），但轮廓系数对
    #       非凸簇会偏低，此处用高斯簇 + 离群点更能演示“异常点识别”这一核心卖点。
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 聚类是【无监督】，只需特征矩阵 X_raw，不需要标签 y：
    #   feature_names = ['指标1', '指标2', '指标3']
    #   X_raw = df[feature_names].values     # (n_samples, n_features) 纯数值
    #   # (下面已内置 StandardScaler 标准化，直接往下跑即可)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    rng = np.random.RandomState(42)
    c1 = rng.randn(80, 2) * 0.5 + [2, 2]
    c2 = rng.randn(80, 2) * 0.5 + [8, 8]
    c3 = rng.randn(80, 2) * 0.5 + [2, 8]
    outliers = rng.uniform(-2, 12, size=(15, 2))   # 15 个离群点
    X_raw = np.vstack([c1, c2, c3, outliers])
    feature_names = ['特征1', '特征2']

    # 1) 标准化
    X = StandardScaler().fit_transform(X_raw)

    # 2) k-距离图辅助定 eps（k = min_samples）
    k_distance_plot(X, k=4)

    # 3) 网格搜索最优 (eps, min_samples)
    _, best_eps, best_ms = grid_search_dbscan(
        X, eps_range=np.round(np.arange(0.15, 0.7, 0.05), 2),
        min_samples_range=range(4, 9))

    # 4) 用最优参数聚类并识别异常点
    labels, metrics = dbscan_cluster(X, eps=best_eps, min_samples=best_ms,
                                     feature_names=feature_names)

    print('\n提示：eps 先看 k-距离图拐点，再在其附近网格微调；'
          'min_samples 经验取 2*特征维数起步。')

