# -*- coding: utf-8 -*-
"""
================================================================================
熵权 TOPSIS 组合评价（竞赛最常用组合，完整流程）
================================================================================
功能：
    先用【熵权法】客观确定各指标权重，再用【TOPSIS】做加权综合排序。
    这是国赛评价类问题最稳妥、被质疑最少的组合：权重来自数据（客观），
    排序逻辑清晰（逼近理想解），可直接写进论文并做灵敏度分析。

完整流程：
    原始数据 -> 指标正向化 -> 标准化 -> 熵权法定权 -> TOPSIS 加权距离
    -> 相对贴近度 C -> 排名 -> （可选）灵敏度分析

适用竞赛场景：
    - C 题"给一批指标数据、要对对象（企业/地区/方案）综合排序打分"
    - 需要"客观权重 + 明确排序 + 结果可解释"的一站式方案
    - 想对比主观（AHP）与客观（熵权）时，本文件给客观基准

输入格式：
    X : (n, m) 数组或 DataFrame，行=对象、列=指标。
    indicator_types : 长度 m 的指标类型列表 'max'/'min'/'mid'/'range'。
    best_values     : dict，mid/range 型指标的目标值/区间。

输出：
    各指标熵权、各对象相对贴近度 C 与排名。

依赖：numpy, pandas
================================================================================
"""

import numpy as np
import pandas as pd

def positivize(col, kind, best=None):
    """指标正向化，统一转极大型。"""
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


def entropy_weight(Xp):
    """对已正向化矩阵用熵权法求权重。返回权重与信息熵。"""
    Xp = np.array(Xp, dtype=float)
    n, m = Xp.shape
    # 极差归一化到 [0,1]，保证非负可比
    mn, mx = Xp.min(axis=0), Xp.max(axis=0)
    rng = mx - mn
    rng[rng == 0] = 1e-12
    Z = (Xp - mn) / rng
    # 比重
    col_sum = Z.sum(axis=0)
    col_sum[col_sum == 0] = 1e-12
    P = Z / col_sum
    # 信息熵
    k = 1.0 / np.log(n)
    with np.errstate(divide='ignore', invalid='ignore'):
        lnP = np.nan_to_num(np.log(P))
    e = -k * (P * lnP).sum(axis=0)
    # 权重
    d = 1 - e
    w = d / d.sum()
    return w, e


def topsis_score(Xp, weights):
    """对已正向化矩阵，用给定权重做 TOPSIS，返回相对贴近度 C。"""
    Xp = np.array(Xp, dtype=float)
    # 向量归一化（TOPSIS 标准）
    norm = np.sqrt((Xp ** 2).sum(axis=0))
    norm[norm == 0] = 1e-12
    Z = Xp / norm
    # 加权
    weights = np.array(weights, dtype=float)
    weights = weights / weights.sum()
    Zw = Z * weights
    # 正/负理想解
    z_pos, z_neg = Zw.max(axis=0), Zw.min(axis=0)
    D_pos = np.sqrt(((Zw - z_pos) ** 2).sum(axis=1))
    D_neg = np.sqrt(((Zw - z_neg) ** 2).sum(axis=1))
    C = D_neg / (D_pos + D_neg)
    return C


def entropy_topsis(X, indicator_types, best_values=None):
    """熵权 TOPSIS 组合评价主流程。

    参数:
        X               : (n, m) 原始数据
        indicator_types : 长度 m 的指标类型列表
        best_values     : dict，mid/range 型目标值
    返回:
        C     : 相对贴近度数组
        rank  : 排名（1 为最优）
        w     : 熵权
    """
    X = np.array(X, dtype=float)
    n, m = X.shape
    best_values = best_values or {}

    # 1) 正向化
    Xp = np.zeros_like(X)
    for j in range(m):
        Xp[:, j] = positivize(X[:, j], indicator_types[j], best_values.get(j))

    # 2) 熵权法定权
    w, e = entropy_weight(Xp)

    # 3) TOPSIS 加权排序
    C = topsis_score(Xp, w)
    rank = pd.Series(C).rank(ascending=False, method='min').astype(int).values
    return C, rank, w


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   data       = df[['人均GDP','单位能耗','教育投入','空气质量','失业率']].values  # 行=对象 列=指标
    #   regions    = df['地区名称'].tolist()            # 对象名，用于展示排名
    #   indicators = ['人均GDP','单位能耗','教育投入','空气质量','失业率']  # 指标名，用于展示权重/灵敏度
    #   # ↓ 按你的每个指标的类型逐个填（顺序与上面取列一致）：
    #   types = ['max', 'min', 'max', 'mid', 'min']  # max极大/min极小/mid中间/range区间
    #   # mid(中间型)、range(区间型)才需要 best_values，键=该指标列索引(从0起)：
    #   best_values = {3: 50}          # 第3列是中间型，目标值50；区间型写 {3: [下界, 上界]}
    #   # 本模板权重由熵权法自动算出，无需手填 weights
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 指标：人均GDP(极大)、单位能耗(极小)、教育投入(极大)、
    #       空气质量指数目标50(中间)、失业率(极小)
    data = np.array([
        [6.8, 1.2, 8.5, 45, 3.9],
        [5.2, 0.9, 7.2, 52, 4.5],
        [7.9, 1.6, 9.1, 60, 3.2],
        [4.5, 0.8, 6.0, 48, 5.1],
        [6.1, 1.1, 8.0, 55, 4.0],
        [5.8, 1.4, 7.8, 42, 4.8],
    ], dtype=float)
    regions = ['地区A', '地区B', '地区C', '地区D', '地区E', '地区F']
    indicators = ['人均GDP', '单位能耗', '教育投入', '空气质量', '失业率']
    types = ['max', 'min', 'max', 'mid', 'min']
    best_values = {3: 50}   # 空气质量指数目标 50

    C, rank, w = entropy_topsis(data, types, best_values)

    print('===== 熵权法确定的指标权重 =====')
    print(pd.DataFrame({'指标': indicators, '权重': np.round(w, 4)})
          .to_string(index=False))

    print('\n===== 熵权 TOPSIS 综合评价结果 =====')
    result = pd.DataFrame({
        '对象': regions,
        '相对贴近度C': np.round(C, 4),
        '排名': rank,
    }).sort_values('排名')
    print(result.to_string(index=False))
    print(f'\n综合最优：{regions[int(np.argmax(C))]}')

    # ------------------- 灵敏度分析（可选，论文常加分项） -------------------
    print('\n===== 灵敏度分析：权重 ±20% 扰动对排名的影响 =====')
    Xp = np.column_stack([positivize(data[:, j], types[j], best_values.get(j))
                          for j in range(data.shape[1])])
    for j in range(len(indicators)):
        w2 = w.copy()
        w2[j] *= 1.2                      # 第 j 个权重放大 20%
        C2 = topsis_score(Xp, w2)
        r2 = pd.Series(C2).rank(ascending=False, method='min').astype(int).values
        changed = '排名变化' if not np.array_equal(r2, rank) else '排名不变'
        print(f'放大【{indicators[j]}】权重 20% -> {changed}')

