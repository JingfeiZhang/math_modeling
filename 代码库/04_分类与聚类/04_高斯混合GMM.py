# -*- coding: utf-8 -*-
"""
高斯混合模型 GMM (Gaussian Mixture Model) 软聚类 —— 国赛C题模板
================================================================
功能：
    1. 数据标准化
    2. 用 BIC / AIC 选择最优成分数（高斯分量个数）
    3. GMM 软聚类：不仅给硬标签，还给每个样本属于各簇的【概率】
    4. 聚类评价：轮廓系数、CH、DB
    5. 可视化：BIC/AIC 曲线、聚类散点 + 高斯等概率椭圆

GMM 相比 KMeans：
    - 软聚类：输出隶属概率（predict_proba），可表达“模糊归属”
    - 允许椭圆形（各向异性）簇，KMeans 只适合球形等径簇
    - 通过 covariance_type 控制协方差形状：
        'full'(每簇独立完整协方差,最灵活) / 'tied' / 'diag' / 'spherical'
    - 模型选择用 BIC（推荐，带复杂度惩罚）/ AIC，取最小值处成分数

输入格式：
    X : (n_samples, n_features) 数值矩阵，无监督。建议标准化。

适用 C题场景：
    需要“归属概率/不确定性”的分群、簇呈椭圆分布、
    概率密度建模（如成分数据的混合分布拟合）。

依赖：numpy pandas scikit-learn matplotlib
================================================================
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (silhouette_score, calinski_harabasz_score,
                             davies_bouldin_score)

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
SAVE_DIR = os.path.dirname(os.path.abspath(__file__))


def choose_components(X, n_range=range(1, 9), cov_type='full', save=True):
    """用 BIC / AIC 选最优成分数，返回 BIC 最小处的 n。"""
    bic_list, aic_list = [], []
    for n in n_range:
        g = GaussianMixture(n_components=n, covariance_type=cov_type,
                            random_state=42).fit(X)
        bic_list.append(g.bic(X))
        aic_list.append(g.aic(X))
    best_n = list(n_range)[int(np.argmin(bic_list))]

    plt.figure(figsize=(8, 5))
    plt.plot(list(n_range), bic_list, 'o-', lw=2, label='BIC(推荐)', color='#007172')
    plt.plot(list(n_range), aic_list, 's-', lw=2, label='AIC', color='#f29325')
    plt.axvline(best_n, ls='--', color='gray')
    plt.xlabel('高斯成分数'); plt.ylabel('信息准则值（越小越好）')
    plt.title(f'GMM 成分数选择：BIC 最小处 n={best_n}')
    plt.legend(); plt.grid(alpha=0.3)
    if save:
        plt.savefig(os.path.join(SAVE_DIR, 'GMM_选成分数.png'), dpi=150, bbox_inches='tight')
    plt.show()
    print(f'BIC 推荐成分数 n={best_n}')
    return best_n


def _draw_ellipse(pos, cov, ax, **kwargs):
    """给定均值与协方差画高斯等概率椭圆（仅二维）。"""
    if cov.shape == (2, 2):
        U, s, _ = np.linalg.svd(cov)
        angle = np.degrees(np.arctan2(U[1, 0], U[0, 0]))
        width, height = 2 * np.sqrt(s)
    else:
        angle = 0
        width = height = 2 * np.sqrt(cov)
    for nsig in (1, 2):   # 1σ、2σ 椭圆
        ax.add_patch(Ellipse(pos, nsig * width, nsig * height,
                             angle=angle, **kwargs))


def gmm_cluster(X, n_components, cov_type='full', feature_names=None, save=True):
    """执行 GMM 软聚类，返回模型、硬标签、隶属概率、评价指标。"""
    model = GaussianMixture(n_components=n_components, covariance_type=cov_type,
                            random_state=42).fit(X)
    labels = model.predict(X)          # 硬标签（取最大概率簇）
    proba = model.predict_proba(X)     # 软标签：属于各簇的概率

    metrics = {
        '轮廓系数(越大越好)': round(silhouette_score(X, labels), 4),
        'CH指数(越大越好)': round(calinski_harabasz_score(X, labels), 2),
        'DB指数(越小越好)': round(davies_bouldin_score(X, labels), 4),
        '平均对数似然': round(model.score(X), 4),
        '收敛': bool(model.converged_),
    }
    print('=' * 45)
    print(f'GMM 完成: 成分数={n_components}, covariance_type={cov_type}')
    for k, v in metrics.items():
        print(f'  {k}: {v}')
    uniq, cnt = np.unique(labels, return_counts=True)
    print('  各簇样本数:', dict(zip(uniq.tolist(), cnt.tolist())))
    print('  前3个样本的隶属概率:\n', np.round(proba[:3], 3))
    print('=' * 45)

    # 可视化：散点 + 高斯椭圆（二维）
    if X.shape[1] >= 2:
        fig, ax = plt.subplots(figsize=(8, 6))
        colors = plt.get_cmap('tab10', n_components)   # matplotlib 3.9 起 cm.get_cmap 已移除
        for c in range(n_components):
            pts = X[labels == c]
            ax.scatter(pts[:, 0], pts[:, 1], s=25, alpha=0.6, color=colors(c),
                       label=f'簇 {c}')
        w_factor = 0.25 / model.weights_.max()
        for c, (pos, cov, w) in enumerate(zip(model.means_,
                                              model.covariances_, model.weights_)):
            cov2 = cov if cov.shape == (2, 2) else np.diag(np.atleast_1d(cov)[:2])
            _draw_ellipse(pos[:2], cov2, ax, alpha=w * w_factor, color=colors(c))
        xl = feature_names[0] if feature_names else '特征1'
        yl = feature_names[1] if feature_names else '特征2'
        ax.set_xlabel(xl); ax.set_ylabel(yl)
        ax.set_title(f'GMM 软聚类结果（{n_components}成分 + 高斯椭圆）')
        ax.legend(); ax.grid(alpha=0.3)
        if save:
            plt.savefig(os.path.join(SAVE_DIR, 'GMM_聚类结果.png'), dpi=150, bbox_inches='tight')
        plt.show()

    return model, labels, proba, metrics


if __name__ == '__main__':
    # ============ 示例数据：3 个椭圆形高斯簇（GMM 强项）============
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
    cov_a = [[1.0, 0.8], [0.8, 1.0]]
    c1 = rng.multivariate_normal([2, 2], cov_a, 80)
    c2 = rng.multivariate_normal([8, 3], [[1.2, -0.6], [-0.6, 0.8]], 80)
    c3 = rng.multivariate_normal([5, 9], [[0.7, 0.0], [0.0, 1.5]], 80)
    X_raw = np.vstack([c1, c2, c3])
    feature_names = ['特征1', '特征2']

    # 1) 标准化
    X = StandardScaler().fit_transform(X_raw)

    # 2) BIC 选成分数
    best_n = choose_components(X, n_range=range(1, 9), cov_type='full')

    # 3) 软聚类
    model, labels, proba, metrics = gmm_cluster(
        X, n_components=best_n, cov_type='full', feature_names=feature_names)

    print('\n提示：GMM 输出隶属概率(predict_proba)，可用于表达“模糊/不确定归属”；'
          '成分数用 BIC 最小值确定，簇呈椭圆时优于 KMeans。')

