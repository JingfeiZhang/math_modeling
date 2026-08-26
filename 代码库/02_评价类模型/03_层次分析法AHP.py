# -*- coding: utf-8 -*-
"""
================================================================================
层次分析法 AHP（Analytic Hierarchy Process）
================================================================================
功能：
    通过两两比较构造判断矩阵，主观确定各指标（准则）权重，并做一致性检验。
    可只求准则层权重，也可结合方案层判断矩阵得到方案综合得分。

原理：
    1) 按 1~9 标度构造正互反判断矩阵 A（a_ij 表示 i 相对 j 的重要程度）；
    2) 求权重（算术平均法 / 几何平均法 / 特征值法，本文件三者取平均更稳健）；
    3) 一致性检验：CI = (λmax - n)/(n - 1)，CR = CI/RI，CR < 0.1 视为通过。

1~9 标度含义（构造判断矩阵的核心）：
    1   两指标同等重要
    3   前者比后者稍微重要
    5   前者比后者明显重要
    7   前者比后者强烈重要
    9   前者比后者极端重要
    2,4,6,8 为上述相邻程度的中间值；倒数表示反向比较（a_ji = 1/a_ij）。

适用竞赛场景：
    - 指标权重需要"专家经验/主观判断"时（无客观数据或数据不足）
    - 方案个数少、可两两比较（准则/方案个数建议 <= 9，否则一致性难通过）
    - 常与熵权法（客观）组合，主客观结合

输入格式：
    criteria : (n, n) 准则层判断矩阵（正互反）
    b        : 方案层判断矩阵列表，每个元素形状 (p, p)（p=方案数），可选

输出：
    准则层权重、一致性比例 CR；若给方案层，输出方案综合得分与最优方案。

依赖：numpy, pandas
================================================================================
"""

import numpy as np
import pandas as pd
import warnings

# 随机一致性指标 RI 表（矩阵阶数 1~15 对应索引 0~14）
RI_TABLE = (0, 0, 0.52, 0.89, 1.12, 1.26, 1.36, 1.41,
            1.46, 1.49, 1.52, 1.54, 1.56, 1.58, 1.59)


def check_reciprocal(A, tol=1e-7):
    """校验是否为正互反矩阵：a_ij * a_ji == 1。"""
    A = np.array(A, dtype=float)
    n, m = A.shape
    assert n == m, '判断矩阵必须是方阵'
    for i in range(n):
        for j in range(n):
            if abs(A[i, j] * A[j, i] - 1) > tol:
                raise ValueError(f'非正互反矩阵：a[{i},{j}]*a[{j},{i}] != 1')


def cal_weights(A, algorithm='comprehensive'):
    """由判断矩阵计算权重并做一致性检验。

    参数:
        A         : (n, n) 判断矩阵
        algorithm : 'arithmetic'(算术平均) / 'geometric'(几何平均)
                    / 'eigen'(特征值法) / 'comprehensive'(三者平均, 默认)
    返回:
        lambda_max : 最大特征值
        CR         : 一致性比例（n>15 时为 None）
        weights    : 权重数组（和为 1）
    """
    A = np.array(A, dtype=float)
    check_reciprocal(A)
    n = A.shape[0]

    # 最大特征值（特征值法要用）
    eigvals, eigvecs = np.linalg.eig(A)
    idx = np.argmax(eigvals.real)
    lambda_max = eigvals[idx].real

    # 1) 算术平均法：先列归一化，再按行求平均
    w_arith = (A / A.sum(axis=0)).sum(axis=1) / n

    # 2) 几何平均法：每行元素连乘开 n 次方，再归一化
    w_geo = np.prod(A, axis=1) ** (1.0 / n)
    w_geo = w_geo / w_geo.sum()

    # 3) 特征值法：最大特征值对应的特征向量归一化
    w_eig = eigvecs[:, idx].real
    w_eig = w_eig / w_eig.sum()

    # 4) 综合法：三者取平均
    w_comp = (w_arith + w_geo + w_eig) / 3

    weights = {
        'arithmetic': w_arith,
        'geometric': w_geo,
        'eigen': w_eig,
        'comprehensive': w_comp,
    }[algorithm]

    # 一致性检验
    if n > 15:
        CR = None
        warnings.warn('矩阵阶数 > 15，无 RI 值，无法做一致性检验')
    elif n <= 2:
        CR = 0.0  # 1、2 阶矩阵永远一致
    else:
        CI = (lambda_max - n) / (n - 1)
        CR = CI / RI_TABLE[n - 1]
    return lambda_max, CR, weights


def ahp(criteria, b=None, algorithm='comprehensive', verbose=True):
    """AHP 主流程。

    参数:
        criteria : (n, n) 准则层判断矩阵
        b        : 方案层判断矩阵列表（长度 n，每个 (p, p)），可选
        algorithm: 权重计算方法
        verbose  : 是否打印过程
    返回:
        若 b 为 None：返回准则层权重；否则返回方案综合得分数组
    """
    lam, CR, crit_w = cal_weights(criteria, algorithm)
    if verbose:
        flag = '通过' if (CR is not None and CR < 0.1) else '不通过'
        print(f'准则层：λmax={lam:.4f}, CR={CR:.4f}, 一致性检验{flag}')
        print(f'准则层权重={np.round(crit_w, 4)}\n')

    if b is None:
        return crit_w

    # 方案层：对每个准则求方案权重
    weights_list, lam_list, cr_list = [], [], []
    for k, Bk in enumerate(b):
        lk, crk, wk = cal_weights(Bk, algorithm)
        weights_list.append(wk)
        lam_list.append(lk)
        cr_list.append(crk)

    W = np.array(weights_list)  # (n准则, p方案)
    if verbose:
        df = pd.DataFrame(
            W.T,
            index=[f'方案{i+1}' for i in range(W.shape[1])],
            columns=[f'准则{i+1}' for i in range(W.shape[0])],
        )
        print('方案层权重（每列一个准则下各方案的相对优劣）:')
        print(df.round(4).to_string())
        cr_info = pd.DataFrame({
            '准则': [f'准则{i+1}' for i in range(len(cr_list))],
            'CR': np.round(cr_list, 4),
            '一致性': ['通过' if c < 0.1 else '不通过' for c in cr_list],
        })
        print('\n方案层一致性检验:')
        print(cr_info.to_string(index=False))

    # 目标层综合得分 = 准则权重 · 方案层权重矩阵
    scores = crit_w @ W
    if verbose:
        print(f'\n方案综合得分：{np.round(scores, 4)}')
        print(f'最优方案：方案{int(np.argmax(scores)) + 1}')
    return scores


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   AHP 的输入不是原始指标数据，而是你按 1~9 标度【自己填写的判断矩阵】
    #   （正互反方阵，阶数=准则数，建议≤9 否则一致性难通过）。两种来源：
    #   方式A｜直接在代码里手写（最常用）：
    #     criteria = np.array([[1, 3, 5],
    #                          [1/3, 1, 2],
    #                          [1/5, 1/2, 1]], dtype=float)  # 3个准则的两两比较
    #   方式B｜若把判断矩阵存成了 CSV（n×n，无表头），读进来：
    #     import pandas as pd
    #     criteria = pd.read_csv('准则判断矩阵.csv', header=None, encoding='gbk').values.astype(float)
    #   # 若还要算方案层综合得分，b 为各准则下方案两两比较矩阵的列表(每个 p×p)：
    #   #   b = [b1, b2, b3];  ahp(criteria, b)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 5 个准则：景色、费用、居住、饮食、旅途
    criteria = np.array([
        [1,   2,   7,   5,   5],
        [1/2, 1,   4,   3,   3],
        [1/7, 1/4, 1,   1/2, 1/3],
        [1/5, 1/3, 2,   1,   1],
        [1/5, 1/3, 3,   1,   1],
    ], dtype=float)

    # 3 个方案（地点）在每个准则下的两两比较
    b1 = np.array([[1, 1/3, 1/8], [3, 1, 1/3], [8, 3, 1]], dtype=float)
    b2 = np.array([[1, 2, 5], [1/2, 1, 2], [1/5, 1/2, 1]], dtype=float)
    b3 = np.array([[1, 1, 3], [1, 1, 3], [1/3, 1/3, 1]], dtype=float)
    b4 = np.array([[1, 3, 4], [1/3, 1, 1], [1/4, 1, 1]], dtype=float)
    b5 = np.array([[1, 4, 1/2], [1/4, 1, 1/4], [2, 4, 1]], dtype=float)
    b = [b1, b2, b3, b4, b5]

    print('===== AHP：仅求准则层权重 =====')
    ahp(criteria, verbose=True)

    print('\n===== AHP：结合方案层求综合得分 =====')
    ahp(criteria, b, verbose=True)
