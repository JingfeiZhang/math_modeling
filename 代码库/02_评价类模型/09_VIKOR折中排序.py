# -*- coding: utf-8 -*-
"""
VIKOR 折中排序法（多准则折中妥协解）
================================================================
功能：
    在多个互相冲突的准则下，对方案排序并给出“折中最优解”。
    与 TOPSIS 的区别：TOPSIS 找“综合最接近理想”的方案；
    VIKOR 同时权衡“群体效益 S（越小越好）”和“个体最大遗憾 R（越小越好）”，
    并用折中系数 v 调节，最后用 Q 值排序 + 一套接受条件判断解是否“可信折中”。
    非常适合评价类题目中“需要给出稳健的、不被单一指标绑架的推荐”场景。

输入：
    decision_matrix : (m方案 × n准则) 的 numpy 数组或 DataFrame
    weights         : 长度 n 的权重（可用熵权/AHP 得到，见同目录 02/03）
    benefit_cols    : 效益型准则的列索引集合（越大越好）；其余按成本型（越小越好）
    v               : 折中系数，0.5 为“多数决+个体遗憾”均衡；>0.5 偏群体效益

输出：
    每个方案的 S、R、Q 值与排名；并检验两条“可接受折中”条件

依赖：numpy, pandas（均为基础库，必跑）
运行：PYTHONIOENCODING=utf-8 python 09_VIKOR折中排序.py
================================================================
"""
import numpy as np
import pandas as pd


def vikor(decision_matrix, weights, benefit_cols=None, v=0.5):
    """返回含 S/R/Q 与排名的 DataFrame，以及折中解可接受性判断。"""
    X = np.asarray(decision_matrix, dtype=float)
    m, n = X.shape
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()
    benefit_cols = set(range(n)) if benefit_cols is None else set(benefit_cols)

    # 1) 确定每个准则的最优 f* 与最劣 f-
    f_best = np.zeros(n)
    f_worst = np.zeros(n)
    for j in range(n):
        col = X[:, j]
        if j in benefit_cols:      # 效益型：大者优
            f_best[j], f_worst[j] = col.max(), col.min()
        else:                      # 成本型：小者优
            f_best[j], f_worst[j] = col.min(), col.max()

    # 2) 归一化“距最优”的加权距离
    denom = f_best - f_worst
    denom[denom == 0] = 1e-12      # 防止某列全相等导致除零
    norm = (f_best - X) / denom    # 每个方案在每准则上的相对差距
    weighted = w * norm

    # 3) S = 加权距离之和（群体效益，越小越好）；R = 最大单项距离（个体遗憾）
    S = weighted.sum(axis=1)
    R = weighted.max(axis=1)

    # 4) Q 值：融合 S 与 R
    S_star, S_minus = S.min(), S.max()
    R_star, R_minus = R.min(), R.max()
    S_rng = (S_minus - S_star) or 1e-12
    R_rng = (R_minus - R_star) or 1e-12
    Q = v * (S - S_star) / S_rng + (1 - v) * (R - R_star) / R_rng

    df = pd.DataFrame({'S': S, 'R': R, 'Q': Q})
    df['S排名'] = df['S'].rank(method='min').astype(int)
    df['R排名'] = df['R'].rank(method='min').astype(int)
    df['Q排名'] = df['Q'].rank(method='min').astype(int)
    df = df.sort_values('Q排名')

    accept = _acceptability(df, m)
    return df, accept


def _acceptability(df_sorted, m):
    """VIKOR 两条折中解可接受条件：
       C1 可接受优势：Q(第2) - Q(第1) >= 1/(m-1)
       C2 决策稳定：排名第1的方案在 S 或 R 上也应排第1
       两条都满足 -> Q 第一即折中最优解；否则给出折中方案集合。"""
    order = df_sorted.sort_values('Q排名')
    q = order['Q'].values
    best_idx = order.index[0]
    msg = []
    DQ = 1.0 / (m - 1) if m > 1 else 0
    c1 = (len(q) >= 2) and (q[1] - q[0] >= DQ)
    c2 = (order.iloc[0]['S排名'] == 1) or (order.iloc[0]['R排名'] == 1)
    msg.append(f"C1 可接受优势 (ΔQ={q[1]-q[0]:.4f} ≥ {DQ:.4f}): {'满足' if c1 else '不满足'}")
    msg.append(f"C2 决策稳定性 (方案{best_idx} 在S或R上排第一): {'满足' if c2 else '不满足'}")
    if c1 and c2:
        msg.append(f"=> 折中最优解唯一：方案 {best_idx}")
    elif not c1:
        # 找出与第一名 Q 差距 < DQ 的方案，构成折中集
        close = order[order['Q'] - q[0] < DQ].index.tolist()
        msg.append(f"=> C1 不满足：折中方案集 = {close}（均可视为并列折中解）")
    else:
        msg.append(f"=> C2 不满足：方案 {best_idx} 与 {order.index[1]} 同为折中解")
    return "\n".join(msg)


if __name__ == '__main__':
    # 演示：4 个供货方案，准则=[利润(效益), 损耗率(成本), 缺货率(成本), 客户满意度(效益)]
    data = pd.DataFrame(
        [[520, 0.08, 0.05, 8.5],
         [610, 0.12, 0.03, 7.8],
         [480, 0.05, 0.08, 9.1],
         [560, 0.09, 0.04, 8.2]],
        index=['方案A', '方案B', '方案C', '方案D'],
        columns=['利润', '损耗率', '缺货率', '满意度'])
    weights = [0.4, 0.2, 0.2, 0.2]           # 可替换为熵权/AHP 结果
    benefit = [0, 3]                          # 利润、满意度为效益型

    print("=" * 56)
    print("VIKOR 折中排序演示")
    print("=" * 56)
    print("决策矩阵：")
    print(data.to_string(), "\n")
    res, accept = vikor(data.values, weights, benefit_cols=benefit, v=0.5)
    res.index = data.index[res.index]
    print(res.round(4).to_string(), "\n")
    print(accept)
