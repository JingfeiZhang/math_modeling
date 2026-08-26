# -*- coding: utf-8 -*-
"""
数据标准化与变换模板
==============================================================================
功能：
    评价类模型（TOPSIS/熵权法）、回归、聚类前的必备预处理。
    一、无量纲化
        1. min_max_scale     min-max 归一化到 [0,1]
        2. z_score_scale     z-score 标准化（均值0方差1）
        3. vector_normalize  向量归一化（TOPSIS 专用，结果为占比）
    二、指标正向化（评价类模型：把不同类型指标统一成"越大越好"）
        1. to_max            极小型指标 -> 极大型
        2. to_middle         中间型指标（越接近某值越好）-> 极大型
        3. to_interval       区间型指标（落在[a,b]最好）-> 极大型
    三、数据变换（改善偏态/异方差，让数据更接近正态）
        1. log_transform     对数变换
        2. boxcox_transform  Box-Cox 变换（自动寻优 lambda，要求数据>0）

输入格式：
    向量用一维 numpy 数组 / list；矩阵用二维 numpy 数组（行=样本，列=指标）。

输出：
    变换后的数组（Box-Cox 额外返回最优 lambda）。

依赖库：numpy, scipy, scikit-learn, matplotlib
==============================================================================
"""

import numpy as np
from scipy import stats
from sklearn.preprocessing import MinMaxScaler, StandardScaler
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


# ============================ 一、无量纲化 ============================

def min_max_scale(X):
    """
    min-max 归一化到 [0,1]。X 为二维数组（行样本列指标）。
    公式: (x - min) / (max - min)。对异常值敏感，适合分布均匀的数据。
    """
    return MinMaxScaler().fit_transform(np.asarray(X, dtype=float))


def z_score_scale(X):
    """
    z-score 标准化：减均值除标准差，结果均值0标准差1。
    适合近似正态、量纲差异大的数据，是回归/聚类/PCA 的常用选择。
    """
    return StandardScaler().fit_transform(np.asarray(X, dtype=float))


def vector_normalize(X):
    """
    向量归一化（TOPSIS 专用）：每列除以该列的平方和开根。
    结果为占比，不会出现 0，避免后续除零问题。X 为二维数组。
    """
    X = np.asarray(X, dtype=float)
    norm = np.sqrt((X ** 2).sum(axis=0))
    return X / norm


# ============================ 二、指标正向化 ============================

def to_max(x):
    """极小型指标 -> 极大型（越小越好变为越大越好）。公式: max - x。"""
    x = np.asarray(x, dtype=float)
    return np.max(x) - x


def to_middle(x, best=None):
    """
    中间型指标 -> 极大型：数据越接近 best 越好。
    best 为最优值，缺省取中位数。公式: 1 - |x-best| / max(|x-best|)。
    """
    x = np.asarray(x, dtype=float)
    best = np.median(x) if best is None else best
    d = np.abs(x - best)
    return 1 - d / d.max()


def to_interval(x, a, b):
    """
    区间型指标 -> 极大型：数据落在 [a,b] 内最好（值为1），偏离越远越差。
    a 下界、b 上界。
    """
    x = np.asarray(x, dtype=float)
    m = max(a - x.min(), x.max() - b)
    res = np.ones_like(x)
    res[x < a] = 1 - (a - x[x < a]) / m
    res[x > b] = 1 - (x[x > b] - b) / m
    return res


# ============================ 三、数据变换 ============================

def log_transform(x, shift=0.0):
    """
    对数变换 log(x + shift)：压缩右偏长尾数据、稳定方差。
    要求 x + shift > 0，若有非正值请传入合适的 shift。
    """
    x = np.asarray(x, dtype=float)
    return np.log(x + shift)


def boxcox_transform(x):
    """
    Box-Cox 变换：自动搜索最优 lambda 使数据最接近正态。
    要求 x 全为正数。返回 (变换后数据, 最优lambda)。
    lambda≈0 等价对数变换，lambda≈1 近似不变。
    """
    x = np.asarray(x, dtype=float)
    if np.any(x <= 0):
        raise ValueError("Box-Cox 要求所有数据 > 0，可先平移或改用 log_transform")
    y, lmbda = stats.boxcox(x)
    return y, lmbda


# ============================ 演示 ============================

if __name__ == '__main__':
    np.random.seed(1)

    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 无量纲化/正向化的输入矩阵 X（行=样本 列=指标）：
    #   X = df[['指标1', '指标2', '指标3']].values
    #   # 单个指标做正向化时取某一列（一维），如极小型的成本列：
    #   cost = df['成本'].values          # 极小型，to_max(cost)
    #   mid  = df['pH值'].values          # 中间型，to_middle(mid, best=7)
    #   itv  = df['体温'].values          # 区间型，to_interval(itv, 36, 37)
    #   # 数据变换的一维正数序列：
    #   data = df['某指标'].values        # log_transform / boxcox_transform
    #   详见 00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # -------- 无量纲化演示 --------
    X = np.array([[100, 0.2, 50],
                  [200, 0.5, 30],
                  [150, 0.8, 40],
                  [300, 0.1, 60]], dtype=float)
    print('=== 原始矩阵 ===\n', X)
    print('=== min-max 归一化 ===\n', np.round(min_max_scale(X), 3))
    print('=== z-score 标准化 ===\n', np.round(z_score_scale(X), 3))
    print('=== 向量归一化(TOPSIS) ===\n', np.round(vector_normalize(X), 3), '\n')

    # -------- 指标正向化演示 --------
    cost = np.array([10, 20, 30, 40])            # 极小型：成本
    mid = np.array([1, 3, 5, 7, 9])              # 中间型：最优=5
    itv = np.array([2, 5, 7, 10, 13])            # 区间型：最优[6,8]
    print('=== 极小型正向化 ===', np.round(to_max(cost), 3))
    print('=== 中间型正向化(best=5) ===', np.round(to_middle(mid, best=5), 3))
    print('=== 区间型正向化[6,8] ===', np.round(to_interval(itv, 6, 8), 3), '\n')

    # -------- 数据变换演示：右偏数据 --------
    data = np.random.exponential(scale=2.0, size=500) + 0.1   # 右偏正数
    log_data = log_transform(data)
    bc_data, lmbda = boxcox_transform(data)
    print('=== Box-Cox 最优 lambda ===', round(lmbda, 4))
    print('原始偏度 %.3f | log后 %.3f | Box-Cox后 %.3f' %
          (stats.skew(data), stats.skew(log_data), stats.skew(bc_data)))

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, d, t in zip(axes, [data, log_data, bc_data],
                        ['原始（右偏）', 'log 变换', 'Box-Cox 变换']):
        ax.hist(d, bins=30, color='#1b9e77', alpha=0.85)
        ax.set_title(f'{t}\n偏度={stats.skew(d):.2f}', fontsize=12)
        ax.set_xlabel('数值')
        ax.set_ylabel('频数')
    plt.suptitle('数据变换对偏态的改善', fontsize=14)
    plt.tight_layout()
    plt.show()
