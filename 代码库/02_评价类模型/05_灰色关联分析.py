# -*- coding: utf-8 -*-
"""
================================================================================
灰色关联分析（Grey Relational Analysis, GRA）
================================================================================
功能：
    在样本量小、信息不完全（"灰"）的情况下，衡量各子序列与参考（母）序列的
    几何相似程度。既可用于"指标关联度分析"，也可用于"多对象综合评价排序"。

原理：
    1) 无量纲化（均值化 / 极差归一化 / 标准化）；
    2) 计算各子序列与参考序列的绝对差矩阵，取全局最小 a、最大 b；
    3) 关联系数 ξ_ik = (a + ρ·b) / (|Δ_ik| + ρ·b)，ρ 为分辨系数（默认 0.5）；
    4) 关联度 = 关联系数按序列平均（或加权），越大越相关/越优。

两种用法：
    - 关联度分析：参考序列为某个目标指标，看哪些因素与它关系最紧密。
    - 综合评价：参考序列取各指标最优值构成"理想对象"，各对象与它的
      关联度即综合得分，越大越好（灰色关联综合评价）。

分辨系数 ρ：
    取值 (0,1]，默认 0.5。ρ 越小分辨力越强、关联系数差异被放大；
    一般 0.5 最常用，可在 0.1~0.5 间做灵敏度分析。

输入格式：
    X : (n, m) 数据矩阵。综合评价时行=对象、列=指标（需先正向化）。

依赖：numpy, pandas
================================================================================
"""

import numpy as np
import pandas as pd


def positivize(col, kind, best=None):
    """指标正向化，统一转极大型。类型同 01_TOPSIS法.py。"""
    col = np.array(col, dtype=float)
    if kind == 'max':
        return col
    elif kind == 'min':
        return np.max(col) - col
    elif kind == 'mid':
        M = np.max(np.abs(col - best))
        M = M if M != 0 else 1e-12
        return 1 - np.abs(col - best) / M
    elif kind == 'range':
        a, b = best[0], best[1]
        M = max(a - np.min(col), np.max(col) - b)
        M = M if M != 0 else 1e-12
        res = np.ones_like(col)
        res = np.where(col < a, 1 - (a - col) / M, res)
        res = np.where(col > b, 1 - (col - b) / M, res)
        return res
    else:
        raise ValueError(f"未知指标类型: {kind}")


def mean_normalize(X):
    """均值化无量纲处理：每列除以该列均值（灰色关联常用）。"""
    X = np.array(X, dtype=float)
    mean = X.mean(axis=0)
    mean[mean == 0] = 1e-12
    return X / mean


def grey_relation_degree(ref, sub, rho=0.5):
    """计算参考序列与若干子序列的灰色关联度（用于关联度分析）。

    参数:
        ref : 长度 n 的参考（母）序列（已无量纲化）
        sub : (n, m) 子序列矩阵（已无量纲化）
        rho : 分辨系数，默认 0.5
    返回:
        长度 m 的各子序列关联度
    """
    ref = np.array(ref, dtype=float).reshape(-1, 1)
    sub = np.array(sub, dtype=float)
    delta = np.abs(sub - ref)      # 绝对差矩阵 (n, m)
    a = delta.min()                # 两级最小差
    b = delta.max()                # 两级最大差
    xi = (a + rho * b) / (delta + rho * b)  # 关联系数
    return xi.mean(axis=0)         # 按序列求平均得关联度


def grey_evaluate(X, indicator_types=None, best_values=None, weights=None, rho=0.5):
    """灰色关联综合评价：以各指标最优值为参考对象，算各对象关联度作为得分。

    参数:
        X               : (n, m) 原始数据（行=对象，列=指标）
        indicator_types : 指标类型列表；None 表示已正向化
        best_values     : dict，mid/range 型目标值
        weights         : 长度 m 的指标权重，默认等权
        rho             : 分辨系数
    返回:
        scores : 各对象关联度（综合得分，越大越好）
        rank   : 排名（1 为最优）
    """
    X = np.array(X, dtype=float)
    n, m = X.shape
    best_values = best_values or {}

    # 1) 正向化
    if indicator_types is not None:
        Xp = np.zeros_like(X)
        for j in range(m):
            Xp[:, j] = positivize(X[:, j], indicator_types[j], best_values.get(j))
    else:
        Xp = X.copy()

    # 2) 均值化无量纲
    Z = mean_normalize(Xp)

    # 3) 参考序列 = 每列最大值（理想对象）
    ref = Z.max(axis=0)

    # 4) 关联系数矩阵
    delta = np.abs(Z - ref)
    a, b = delta.min(), delta.max()
    xi = (a + rho * b) / (delta + rho * b)   # (n, m)

    # 5) 加权求关联度作为综合得分
    if weights is None:
        weights = np.ones(m) / m
    weights = np.array(weights, dtype=float)
    weights = weights / weights.sum()
    scores = xi @ weights

    rank = pd.Series(scores).rank(ascending=False, method='min').astype(int).values
    return scores, rank


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   用法一｜关联度分析(找主要影响因素)：参考序列=目标指标，子序列=各因素
    #     ref_seq = df['经济总量'].values                 # 参考(母)序列
    #     sub_seq = df[['因素1', '因素2', '因素3']].values # 各子序列(列=因素)
    #     # 再 mean_normalize 后调用 grey_relation_degree
    #   用法二｜综合评价排序：行=对象、列=指标
    #     data    = df[['质量', '成本', '交货期']].values  # 行=对象 列=指标
    #     objects = df['供应商名称'].tolist()              # 对象名
    #     types   = ['max', 'min', 'min']  # 各指标类型 max极大/min极小/mid中间/range区间
    #     weights = [0.5, 0.3, 0.2]        # 指标权重；mid/range 型再传 best_values 给 grey_evaluate
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # ------------------- 用法一：关联度分析 -------------------
    # 参考序列（如经济总量），5 个子序列（各影响因素），10 个时间点
    print('===== 灰色关联度分析 =====')
    np.random.seed(0)
    ref_seq = np.array([10, 12, 14, 15, 17, 19, 21, 24, 26, 29], dtype=float)
    sub_seq = np.array([
        ref_seq * 0.8 + np.random.rand(10),   # 因素1（强相关）
        ref_seq * 0.3 + np.random.rand(10)*5,  # 因素2
        np.random.rand(10) * 20,               # 因素3（弱相关）
    ]).T
    ref_n = mean_normalize(ref_seq.reshape(-1, 1)).ravel()
    sub_n = mean_normalize(sub_seq)
    degrees = grey_relation_degree(ref_n, sub_n, rho=0.5)
    for i, d in enumerate(degrees):
        print(f'因素{i+1} 关联度 = {d:.4f}')

    # ------------------- 用法二：灰色关联综合评价 -------------------
    print('\n===== 灰色关联综合评价（对象排序） =====')
    # 4 个供应商，3 个指标：质量(极大)、成本(极小)、交货期(极小)
    data = np.array([
        [90,  120,  7],
        [85,  100,  5],
        [95,  150,  9],
        [88,  110,  6],
    ], dtype=float)
    objects = ['供应商A', '供应商B', '供应商C', '供应商D']
    types = ['max', 'min', 'min']
    weights = [0.5, 0.3, 0.2]

    scores, rank = grey_evaluate(data, types, weights=weights, rho=0.5)
    res = pd.DataFrame({
        '对象': objects,
        '灰色关联度': np.round(scores, 4),
        '排名': rank,
    }).sort_values('排名')
    print(res.to_string(index=False))
    print(f'\n最优对象：{objects[int(np.argmax(scores))]}')
