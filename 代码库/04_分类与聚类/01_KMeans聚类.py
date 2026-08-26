# -*- coding: utf-8 -*-
"""
KMeans 聚类（K均值）——数学建模国赛 C题 标准化模板
================================================================
功能：
    1. 数据标准化（聚类必做，消除量纲影响）
    2. 肘部法则（Elbow）+ 轮廓系数 自动辅助选择最优簇数 K
    3. KMeans 聚类，输出每个样本的类别标签与聚类中心
    4. 聚类评价：轮廓系数 Silhouette、CH 指数 Calinski-Harabasz、DB 指数、SSE
    5. 可视化：肘部图、轮廓系数图、聚类散点图、各类特征均值雷达/柱状对比

输入格式：
    X : 2D 数组或 DataFrame，形状 (n_samples, n_features)，纯数值型特征。
        KMeans 是【无监督】方法，不需要标签 y。
        若特征量纲差异大，务必先标准化（本模板已内置）。

输出：
    - labels     : 每个样本所属簇编号 (0 ~ K-1)
    - centers    : 各簇中心坐标（标准化空间；可反标准化解释）
    - 评价指标字典 + 若干 PNG 图（保存在脚本同目录）

适用 C题场景：
    对企业/商品/样本按特征分群（如 2022 玻璃成分先聚类再判别、
    客户分层、地区分类），簇数事先未知时的探索性分组。

依赖：numpy pandas scikit-learn matplotlib
================================================================
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (silhouette_score, calinski_harabasz_score,
                             davies_bouldin_score)

# 中文显示设置（Windows 黑体；Mac 可改 'Arial Unicode MS'）
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 图片保存目录 = 脚本所在目录
SAVE_DIR = os.path.dirname(os.path.abspath(__file__))


def choose_k(X, k_range=range(2, 11), save=True):
    """肘部法则 + 轮廓系数 联合选 K。

    参数:
        X       : 已标准化的特征矩阵
        k_range : 待尝试的簇数范围
    返回:
        sse_list, sil_list : SSE 序列与轮廓系数序列
    """
    sse_list, sil_list = [], []
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = km.fit_predict(X)
        sse_list.append(km.inertia_)                 # SSE=簇内平方和，越小越紧
        sil_list.append(silhouette_score(X, labels))  # 轮廓系数，越大越好(-1~1)

    # 双子图：左肘部、右轮廓
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    axes[0].plot(list(k_range), sse_list, 'o-', lw=2, color='#2779ac')
    axes[0].set_xlabel('簇数 K'); axes[0].set_ylabel('SSE（簇内平方和）')
    axes[0].set_title('肘部法则：拐点处即为较优 K'); axes[0].grid(alpha=0.3)

    axes[1].plot(list(k_range), sil_list, 's-', lw=2, color='#d94f04')
    best_k = list(k_range)[int(np.argmax(sil_list))]
    axes[1].axvline(best_k, ls='--', color='gray')
    axes[1].set_xlabel('簇数 K'); axes[1].set_ylabel('轮廓系数')
    axes[1].set_title(f'轮廓系数：最大处 K={best_k}'); axes[1].grid(alpha=0.3)
    plt.tight_layout()
    if save:
        plt.savefig(os.path.join(SAVE_DIR, 'KMeans_选K.png'), dpi=150, bbox_inches='tight')
    plt.show()
    return sse_list, sil_list


def kmeans_cluster(X, n_clusters, feature_names=None, save=True):
    """执行 KMeans 聚类并返回模型、标签、评价指标。

    参数:
        X          : 已标准化特征矩阵 (n_samples, n_features)
        n_clusters : 簇数 K
    返回:
        model, labels, metrics(dict)
    """
    model = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    labels = model.fit_predict(X)

    # ---- 聚类评价指标 ----
    metrics = {
        '轮廓系数(越大越好,-1~1)': round(silhouette_score(X, labels), 4),
        'CH指数(越大越好)': round(calinski_harabasz_score(X, labels), 2),
        'DB指数(越小越好)': round(davies_bouldin_score(X, labels), 4),
        'SSE簇内平方和(越小越紧)': round(model.inertia_, 2),
    }
    print('=' * 45)
    print(f'KMeans 聚类完成，K={n_clusters}')
    for k, v in metrics.items():
        print(f'  {k}: {v}')
    # 各簇样本数
    uniq, cnt = np.unique(labels, return_counts=True)
    print('  各簇样本数:', dict(zip(uniq.tolist(), cnt.tolist())))
    print('=' * 45)

    # ---- 可视化：取前两个特征画散点（>2维时仅用于示意）----
    plt.figure(figsize=(8, 6))
    for c in range(n_clusters):
        pts = X[labels == c]
        plt.scatter(pts[:, 0], pts[:, 1], s=30, alpha=0.7, label=f'簇 {c}')
    plt.scatter(model.cluster_centers_[:, 0], model.cluster_centers_[:, 1],
                marker='X', s=250, c='black', edgecolors='white',
                linewidths=1.5, label='聚类中心')
    xl = feature_names[0] if feature_names else '特征1'
    yl = feature_names[1] if feature_names else '特征2'
    plt.xlabel(xl); plt.ylabel(yl)
    plt.title(f'KMeans 聚类结果 (K={n_clusters})')
    plt.legend(); plt.grid(alpha=0.3)
    if save:
        plt.savefig(os.path.join(SAVE_DIR, 'KMeans_聚类结果.png'), dpi=150, bbox_inches='tight')
    plt.show()

    return model, labels, metrics


def profile_clusters(X_raw, labels, feature_names):
    """输出各簇在【原始尺度】下的特征均值画像，便于赛题解释每一类的含义。"""
    df = pd.DataFrame(X_raw, columns=feature_names)
    df['簇'] = labels
    profile = df.groupby('簇').mean()
    print('\n各簇特征均值画像（原始尺度，用于解释每类特点）:')
    print(profile.round(3))

    # 柱状对比图
    profile.T.plot(kind='bar', figsize=(10, 6))
    plt.title('各簇特征均值对比'); plt.ylabel('均值'); plt.xlabel('特征')
    plt.xticks(rotation=30); plt.legend(title='簇'); plt.grid(alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(os.path.join(SAVE_DIR, 'KMeans_簇画像.png'), dpi=150, bbox_inches='tight')
    plt.show()
    return profile


if __name__ == '__main__':
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
    # ================= 示例数据：3 个明显分离的簇 =================
    rng = np.random.RandomState(42)
    c1 = rng.randn(60, 2) * 0.6 + [2, 2]
    c2 = rng.randn(60, 2) * 0.6 + [8, 3]
    c3 = rng.randn(60, 2) * 0.6 + [5, 8]
    X_raw = np.vstack([c1, c2, c3])
    feature_names = ['特征1', '特征2']

    # 1) 标准化（KMeans 基于欧氏距离，必须消除量纲）
    scaler = StandardScaler()
    X = scaler.fit_transform(X_raw)

    # 2) 选 K
    choose_k(X, k_range=range(2, 9))

    # 3) 聚类（示例已知 3 类）
    model, labels, metrics = kmeans_cluster(X, n_clusters=3, feature_names=feature_names)

    # 4) 簇画像（原始尺度解释）
    profile_clusters(X_raw, labels, feature_names)

    print('\n提示：真实赛题请先看肘部图/轮廓系数图确定 K，再解释各簇业务含义。')

