# -*- coding: utf-8 -*-
"""
================================================================================
熵权法（客观赋权法）
================================================================================
功能：
    根据各指标数据本身的"离散程度"客观地确定权重，无需人为主观判断。
    信息熵越小 -> 指标取值差异越大 -> 提供信息越多 -> 权重越大。

原理：
    对第 j 个指标，先算各对象所占比重 p_ij，再算信息熵 e_j，
    最后用差异系数 d_j = 1 - e_j 归一化得到权重 w_j。

适用竞赛场景：
    - 需要"用数据说话"、避免主观打分质疑时（评委喜欢客观赋权）
    - 常作为 TOPSIS / 综合评价的权重来源（见 07_熵权TOPSIS组合评价.py）
    - 与 AHP（主观）对比使用，或组合成"主客观组合赋权"更稳健

输入格式：
    X : (n, m) 数组或 DataFrame，n 个对象、m 个指标。
        要求：指标已正向化（越大越好），且数据非负。
        本文件内置正向化与平移，可直接传原始数据。

输出：
    各指标权重 w（长度 m，和为 1）。

依赖：numpy, pandas
================================================================================
"""

import numpy as np
import pandas as pd


def positivize(col, kind, best=None):
    """指标正向化，统一转为极大型。类型同 01_TOPSIS法.py。"""
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


def min_max_scale(X):
    """极差归一化到 [0, 1]，让不同量纲指标可比，同时保证非负。"""
    X = np.array(X, dtype=float)
    mn = X.min(axis=0)
    mx = X.max(axis=0)
    rng = mx - mn
    rng[rng == 0] = 1e-12  # 常数列防除零
    return (X - mn) / rng


def entropy_weight(X, indicator_types=None, best_values=None, do_positivize=True):
    """熵权法主函数。

    参数:
        X               : (n, m) 原始数据矩阵
        indicator_types : 长度 m 的指标类型列表；None 表示已全部正向化
        best_values     : dict，mid/range 型指标的目标值/区间
        do_positivize   : 是否执行正向化 + 归一化预处理
    返回:
        w : 各指标权重数组（和为 1）
        e : 各指标信息熵数组（供分析）
    """
    X = np.array(X, dtype=float)
    n, m = X.shape
    best_values = best_values or {}

    # 1) 正向化 + 归一化（保证非负、可比）
    if do_positivize:
        if indicator_types is not None:
            Xp = np.zeros_like(X)
            for j in range(m):
                Xp[:, j] = positivize(X[:, j], indicator_types[j], best_values.get(j))
        else:
            Xp = X
        X = min_max_scale(Xp)

    # 2) 计算比重 p_ij = x_ij / 列和
    col_sum = X.sum(axis=0)
    col_sum[col_sum == 0] = 1e-12
    P = X / col_sum

    # 3) 计算信息熵 e_j = -k * Σ p_ij ln(p_ij)，k = 1/ln(n)
    k = 1.0 / np.log(n)
    with np.errstate(divide='ignore', invalid='ignore'):
        lnP = np.log(P)
    lnP = np.nan_to_num(lnP)          # 0*ln0 视为 0
    e = -k * (P * lnP).sum(axis=0)

    # 4) 差异系数 d_j = 1 - e_j，归一化得权重
    d = 1 - e
    w = d / d.sum()
    return w, e


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   data       = df[['GDP', '失业率', '绿化率', 'PM2.5']].values  # 行=对象 列=指标
    #   indicators = ['GDP', '失业率', '绿化率', 'PM2.5']            # 指标名，用于展示权重
    #   # ↓ 按你的每个指标的类型逐个填（顺序与上面取列一致）：
    #   indicator_types = ['max', 'min', 'max', 'min']  # max极大/min极小/mid中间/range区间
    #   # 若有 mid/range 型指标，再传 best_values（键=列索引）给 entropy_weight，例如：
    #   #   w, e = entropy_weight(data, indicator_types, best_values={3: 50})
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 5 个城市，4 个指标：GDP(极大)、失业率(极小)、绿化率(极大)、PM2.5(极小)
    data = np.array([
        [3200,  4.5,  38,  55],
        [2800,  3.2,  42,  48],
        [4100,  5.8,  30,  72],
        [3600,  4.0,  45,  50],
        [2500,  6.2,  35,  65],
    ], dtype=float)
    indicators = ['GDP', '失业率', '绿化率', 'PM2.5']
    indicator_types = ['max', 'min', 'max', 'min']

    w, e = entropy_weight(data, indicator_types)

    print('===== 熵权法赋权结果 =====')
    df = pd.DataFrame({
        '指标': indicators,
        '信息熵e': np.round(e, 4),
        '权重w': np.round(w, 4),
    })
    print(df.to_string(index=False))
    print(f'\n权重之和：{w.sum():.4f}（应为 1）')
    print(f'权重最大的指标：{indicators[int(np.argmax(w))]}')
