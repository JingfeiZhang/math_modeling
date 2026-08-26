# -*- coding: utf-8 -*-
"""
================================================================================
DEA 数据包络分析（Data Envelopment Analysis, CCR 模型·投入导向）
================================================================================
功能：
    评价多个"决策单元(DMU)"在【多投入-多产出】下的相对效率。
    不需要预设指标权重（区别于 TOPSIS/熵权法），由线性规划自动为每个单元
    找最有利的权重，算出效率值 θ∈(0,1]。θ=1 且松弛变量全为 0 → DEA 有效
    （落在效率前沿）；θ<1 → 相对无效，存在改进空间。

适用竞赛场景：
    - C 题"效率/绩效评估"类：医院运营效率、企业生产率、区域投入产出效率、
      学校/银行网点效能等——只要能分清"投入指标"和"产出指标"就能用。
    - 常与 TOPSIS 组合（DEA 先筛效率，TOPSIS 再综合排序），见组合模型目录。

输入格式：
    X : 投入矩阵，形状 (n, m)，n=决策单元数(行)，m=投入指标数(列)。投入越小越好。
    Y : 产出矩阵，形状 (n, s)，s=产出指标数(列)。产出越大越好。

输出：
    每个决策单元的效率值 θ 及是否 DEA 有效、排名。

依赖：numpy, scipy（linprog 需 scipy>=1.6，用 'highs' 求解器）
================================================================================
"""

import numpy as np
from scipy.optimize import linprog


def dea_ccr(X, Y, eps=1e-6):
    """DEA-CCR 投入导向模型。
    对每个决策单元 j 求解：
        min  θ - eps*(Σs⁻ + Σs⁺)
        s.t. Xᵀλ + s⁻ = θ·X_j     (投入约束)
             Yᵀλ - s⁺ = Y_j        (产出约束)
             λ, s⁻, s⁺ ≥ 0
    参数:
        X, Y : 投入/产出矩阵
        eps  : 非阿基米德无穷小，用于把松弛变量纳入目标（判定强有效）
    返回:
        theta   : 长度 n 的效率值数组
        effective : 布尔数组，True=DEA 有效(θ≈1)
    """
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    n, m = X.shape
    s = Y.shape[1]
    theta = np.zeros(n)

    for j in range(n):
        # 决策变量顺序: [λ(n个), s⁻(m个), s⁺(s个), θ(1个)]
        # 目标: min θ - eps*(Σs⁻+Σs⁺)  → θ系数=1, 松弛系数=-eps, λ系数=0
        c = np.concatenate([np.zeros(n), -eps * np.ones(m), -eps * np.ones(s), [1.0]])

        # 投入约束: Xᵀλ + s⁻ - θ·X_j = 0
        A_in = np.hstack([X.T, np.eye(m), np.zeros((m, s)), -X[j].reshape(-1, 1)])
        b_in = np.zeros(m)
        # 产出约束: Yᵀλ - s⁺ = Y_j
        A_out = np.hstack([Y.T, np.zeros((s, m)), -np.eye(s), np.zeros((s, 1))])
        b_out = Y[j]

        A_eq = np.vstack([A_in, A_out])
        b_eq = np.concatenate([b_in, b_out])

        bounds = [(0, None)] * (n + m + s) + [(None, None)]  # θ 无下界约束（实际>0）
        res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
        theta[j] = res.x[-1] if res.success else np.nan

    effective = np.abs(theta - 1.0) < 1e-4
    return theta, effective


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   X = df[['固定资产', '员工人数']].values     # 投入指标列（越小越优）
    #   Y = df[['总产值', '净利润']].values          # 产出指标列（越大越优）
    #   names = df['企业名称'].tolist()              # 决策单元名，用于展示
    #   关键：分清哪些列是"投入"、哪些是"产出"，这是 DEA 的前提。
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(6 家企业, 2 投入 2 产出; 替换为真实数据后可删除)
    names = [f'企业{i}' for i in range(1, 7)]
    X = np.array([[500, 80], [600, 90], [400, 70], [700, 100], [300, 60], [550, 85]])
    Y = np.array([[1200, 300], [1350, 320], [1000, 280], [1500, 350], [800, 220], [1250, 310]])

    theta, effective = dea_ccr(X, Y)

    print('DEA-CCR 效率评价结果')
    print('=' * 46)
    order = np.argsort(-theta)
    rank = 1
    for idx in order:
        flag = 'DEA有效✔' if effective[idx] else '相对无效'
        print(f'第{rank}名  {names[idx]:6s}  效率值={theta[idx]:.4f}  {flag}')
        rank += 1
    print('=' * 46)
    print(f'DEA 有效单元数：{effective.sum()} / {len(theta)}')
    print('提示：θ<1 的单元可按投入导向缩减投入至 θ·投入 达到效率前沿。')
