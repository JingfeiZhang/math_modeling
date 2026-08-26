# -*- coding: utf-8 -*-
"""
================================================================================
TOPSIS 法（优劣解距离法 / 逼近理想解排序法）
================================================================================
功能：
    对多个待评价对象（方案/样本），在多个指标下进行综合排序打分。
    核心思想：构造正理想解（最优）和负理想解（最差），计算每个对象到两者
    的加权欧氏距离，用相对贴近度 C = D-/(D+ + D-) 衡量优劣，C 越大越好。

适用竞赛场景：
    - C 题中"给指标数据、要给对象排序打分"的问题（如企业信贷评级、方案优选）
    - 常与熵权法/AHP 搭配确定权重（见 07_熵权TOPSIS组合评价.py）

输入格式：
    X : 二维 numpy 数组或 DataFrame，形状 (n, m)
        n = 待评价对象个数（行），m = 指标个数（列）
    indicator_types : 长度为 m 的列表，标注每个指标类型：
        'max'    极大型（越大越好，如收益率）
        'min'    极小型（越小越好，如成本、污染）
        'mid'    中间型（越接近某个值越好，如 pH 值），需在 best_values 给目标值
        'range'  区间型（落在某区间最好），需在 best_values 给 [下界, 上界]
    weights : 长度为 m 的权重列表，默认等权。

输出：
    每个对象的相对贴近度 C（0~1）及排名（C 越大排名越靠前）。

依赖：numpy, pandas
================================================================================
"""

import numpy as np
import pandas as pd


def positivize(col, kind, best=None):
    """指标正向化：把各类指标统一转成"越大越好"的极大型指标。

    参数:
        col  : 一维数组，某个指标下所有对象的取值
        kind : 指标类型 'max' / 'min' / 'mid' / 'range'
        best : mid 型给目标值(标量)，range 型给 [下界, 上界]
    返回:
        正向化后的一维数组
    """
    col = np.array(col, dtype=float)
    if kind == 'max':
        # 极大型：本身越大越好，无需转换
        return col
    elif kind == 'min':
        # 极小型 -> 极大型：用 (max - x)，也可用 1/x（需非零）
        return np.max(col) - col
    elif kind == 'mid':
        # 中间型 -> 极大型：越接近目标值 best 越好
        M = np.max(np.abs(col - best))
        M = M if M != 0 else 1e-12
        return 1 - np.abs(col - best) / M
    elif kind == 'range':
        # 区间型 -> 极大型：落在 [a, b] 内为最好
        a, b = best[0], best[1]
        M = max(a - np.min(col), np.max(col) - b)
        M = M if M != 0 else 1e-12
        res = np.ones_like(col)
        res = np.where(col < a, 1 - (a - col) / M, res)
        res = np.where(col > b, 1 - (col - b) / M, res)
        return res
    else:
        raise ValueError(f"未知指标类型: {kind}")


def standardize(X):
    """向量归一化（TOPSIS 标准）：每列除以该列的平方和开根，消除量纲。"""
    X = np.array(X, dtype=float)
    norm = np.sqrt((X ** 2).sum(axis=0))
    norm[norm == 0] = 1e-12  # 防止除零
    return X / norm


def topsis(X, indicator_types, best_values=None, weights=None):
    """TOPSIS 主函数。

    参数:
        X               : (n, m) 原始数据矩阵
        indicator_types : 长度 m 的指标类型列表
        best_values     : dict，键为指标列索引，值为该指标的目标值/区间
                          （仅 'mid'/'range' 型需要）
        weights         : 长度 m 的权重列表，默认等权
    返回:
        C     : 各对象相对贴近度数组
        rank  : 各对象排名（1 为最优）
    """
    X = np.array(X, dtype=float)
    n, m = X.shape
    best_values = best_values or {}

    # 1) 指标正向化
    Xp = np.zeros_like(X)
    for j in range(m):
        Xp[:, j] = positivize(X[:, j], indicator_types[j], best_values.get(j))

    # 2) 标准化（向量归一化，消除量纲）
    Z = standardize(Xp)

    # 3) 加权
    if weights is None:
        weights = np.ones(m) / m
    weights = np.array(weights, dtype=float)
    weights = weights / weights.sum()  # 权重归一化
    Zw = Z * weights

    # 4) 确定正/负理想解（加权后逐列最大/最小）
    z_pos = Zw.max(axis=0)  # 正理想解
    z_neg = Zw.min(axis=0)  # 负理想解

    # 5) 计算各对象到正/负理想解的欧氏距离
    D_pos = np.sqrt(((Zw - z_pos) ** 2).sum(axis=1))
    D_neg = np.sqrt(((Zw - z_neg) ** 2).sum(axis=1))

    # 6) 相对贴近度 C（越大越好）
    C = D_neg / (D_pos + D_neg)

    # 7) 排名：C 越大排名越靠前
    rank = pd.Series(C).rank(ascending=False, method='min').astype(int).values
    return C, rank


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   data    = df[['净利润', '负债率', '研发投入', '员工满意度']].values  # 行=对象 列=指标
    #   objects = df['企业名称'].tolist()               # 对象名，用于展示排名
    #   # ↓ 按你的每个指标的类型逐个填（顺序与上面取列的顺序一致）：
    #   indicator_types = ['max', 'min', 'max', 'mid']  # max极大/min极小/mid中间/range区间
    #   # mid(中间型)、range(区间型)才需要 best_values，键=该指标的列索引(从0起)：
    #   best_values = {3: 85}          # 第3列是中间型，目标值85；区间型写 {3: [下界, 上界]}
    #   weights = [0.35, 0.20, 0.30, 0.15]  # 各指标权重(和不必为1，内部会归一化)；不确定就删掉这行用等权
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 4 个企业，4 个指标：净利润(极大)、负债率(极小)、研发投入(极大)、员工满意度目标85(中间)
    data = np.array([
        [1200,  0.55,  300,  80],
        [ 900,  0.30,  450,  90],
        [1500,  0.70,  200,  75],
        [1100,  0.40,  380,  88],
    ], dtype=float)
    objects = ['企业A', '企业B', '企业C', '企业D']
    indicator_types = ['max', 'min', 'max', 'mid']
    best_values = {3: 85}          # 第 3 列(员工满意度)目标值为 85
    weights = [0.35, 0.20, 0.30, 0.15]

    C, rank = topsis(data, indicator_types, best_values, weights)

    result = pd.DataFrame({
        '对象': objects,
        '相对贴近度C': np.round(C, 4),
        '排名': rank,
    }).sort_values('排名')
    print('===== TOPSIS 评价结果 =====')
    print(result.to_string(index=False))
    print(f'\n最优对象：{objects[int(np.argmax(C))]}')
