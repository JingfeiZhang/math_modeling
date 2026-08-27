# -*- coding: utf-8 -*-
"""
01 KMeans 聚类：尺度、K 候选与稳定性
====================================

study-only 模板。KMeans 强制把数据分成 K 个簇；得到 K 个标签不等于数据天然存在 K 类。

高质量使用原则：
- 欧氏距离对尺度敏感，但“标准化必做”并不总成立：若原始单位本身具有可比业务意义，
  或某变量的绝对尺度就是距离定义的一部分，应保留原尺度或采用业务定义的加权距离。
- silhouette/CH/DB/SSE 都只是内部结构指标，不能单独证明聚类“正确”。
- K 的选择应同时看结构指标、不同初始化/样本扰动的稳定性和簇画像是否可解释。
- 高维数据取前两个原始特征画散点只是一种切片，不应当作完整聚类证据。
"""

from __future__ import annotations

import itertools
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (silhouette_score, calinski_harabasz_score,
                             davies_bouldin_score, adjusted_rand_score)


def prepare_features(X, scale=True):
    X = np.asarray(X, dtype=float)
    if X.ndim != 2 or len(X) < 3 or not np.isfinite(X).all():
        raise ValueError("X 必须为有限二维数值矩阵")
    if scale:
        scaler = StandardScaler().fit(X)
        return scaler.transform(X), scaler
    return X.copy(), None


def _seed_stability(X, k, seeds):
    labels = []
    inertias = []
    silhouettes = []
    for seed in seeds:
        km = KMeans(n_clusters=k, n_init=10, random_state=int(seed))
        lab = km.fit_predict(X)
        labels.append(lab)
        inertias.append(float(km.inertia_))
        silhouettes.append(float(silhouette_score(X, lab)))
    if len(labels) >= 2:
        ari = [adjusted_rand_score(a, b) for a, b in itertools.combinations(labels, 2)]
        stability = float(np.mean(ari))
        stability_min = float(np.min(ari))
    else:
        stability = stability_min = float("nan")
    return {
        "silhouette_mean": float(np.mean(silhouettes)),
        "silhouette_std": float(np.std(silhouettes)),
        "inertia_mean": float(np.mean(inertias)),
        "seed_ari_mean": stability,
        "seed_ari_min": stability_min,
    }


def compare_k(X, k_values=range(2, 9), seeds=(1, 2, 3, 4, 5)):
    """比较多个 K；不自动宣布“最优 K”，返回供人工/题意联合判断的证据表。"""
    X = np.asarray(X, dtype=float)
    rows = []
    for k in k_values:
        if k < 2 or k >= len(X):
            continue
        summary = _seed_stability(X, int(k), seeds)
        km = KMeans(n_clusters=int(k), n_init=20, random_state=int(seeds[0]))
        labels = km.fit_predict(X)
        rows.append({
            "k": int(k),
            **summary,
            "calinski_harabasz": float(calinski_harabasz_score(X, labels)),
            "davies_bouldin": float(davies_bouldin_score(X, labels)),
            "cluster_sizes": np.bincount(labels, minlength=int(k)).tolist(),
        })
    table = pd.DataFrame(rows)
    print("【K 候选证据表】")
    if not table.empty:
        print(table[["k", "silhouette_mean", "silhouette_std", "seed_ari_mean",
                     "seed_ari_min", "calinski_harabasz", "davies_bouldin"]].round(4).to_string(index=False))
    print("选择 K 时还要检查簇画像、极小簇、题面用途和样本扰动；不要仅取 silhouette 最大值。")
    return table


def kmeans_cluster(X, n_clusters, seed=42, n_init=20):
    X = np.asarray(X, dtype=float)
    model = KMeans(n_clusters=int(n_clusters), n_init=int(n_init), random_state=int(seed))
    labels = model.fit_predict(X)
    metrics = {
        "silhouette": float(silhouette_score(X, labels)),
        "calinski_harabasz": float(calinski_harabasz_score(X, labels)),
        "davies_bouldin": float(davies_bouldin_score(X, labels)),
        "inertia": float(model.inertia_),
        "cluster_sizes": np.bincount(labels, minlength=int(n_clusters)).tolist(),
        "seed": int(seed),
    }
    return {"model": model, "labels": labels, "metrics": metrics}


def profile_clusters(X_raw, labels, feature_names=None):
    X_raw = np.asarray(X_raw, dtype=float)
    labels = np.asarray(labels)
    names = feature_names or [f"特征{i+1}" for i in range(X_raw.shape[1])]
    df = pd.DataFrame(X_raw, columns=names)
    df["簇"] = labels
    mean_profile = df.groupby("簇").mean()
    median_profile = df.groupby("簇").median()
    size = df.groupby("簇").size().rename("n")
    print("【原始尺度簇画像】")
    print(pd.concat([size, mean_profile.add_prefix("mean_"), median_profile.add_prefix("median_")], axis=1).round(3))
    return {"mean": mean_profile, "median": median_profile, "size": size}


def perturbation_stability(X, n_clusters, repeats=20, sample_fraction=0.8, seed=0):
    """简单样本扰动稳定性：对子样本重聚类，并与全样本基准在交集上比较 ARI。"""
    X = np.asarray(X, dtype=float)
    if not 0.5 <= sample_fraction <= 1.0:
        raise ValueError("sample_fraction 建议在 [0.5,1] 内")
    rng = np.random.default_rng(seed)
    base = KMeans(n_clusters=n_clusters, n_init=20, random_state=seed).fit_predict(X)
    scores = []
    m = max(n_clusters + 1, int(round(len(X) * sample_fraction)))
    for r in range(repeats):
        idx = np.sort(rng.choice(len(X), size=m, replace=False))
        lab = KMeans(n_clusters=n_clusters, n_init=20, random_state=seed + r + 1).fit_predict(X[idx])
        scores.append(adjusted_rand_score(base[idx], lab))
    return {"ari_mean": float(np.mean(scores)), "ari_min": float(np.min(scores)),
            "ari_std": float(np.std(scores)), "repeats": repeats, "sample_fraction": sample_fraction}


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    X_raw = np.vstack([
        rng.normal([2, 2], [0.6, 0.6], size=(60, 2)),
        rng.normal([8, 3], [0.6, 0.6], size=(60, 2)),
        rng.normal([5, 8], [0.6, 0.6], size=(60, 2)),
    ])
    X, scaler = prepare_features(X_raw, scale=True)
    compare_k(X, range(2, 7))
    result = kmeans_cluster(X, 3)
    profile_clusters(X_raw, result["labels"], ["特征1", "特征2"])
    print("扰动稳定性:", perturbation_stability(X, 3))
    print("结论边界：内部指标与稳定性只能说明结构证据；最终簇数仍需由题面用途和现实解释共同决定。")
