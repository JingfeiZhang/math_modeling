# -*- coding: utf-8 -*-
"""
================================================================================
多目标规划（Multi-Objective Programming, MOP）
================================================================================
功能：
    同时优化多个相互冲突的目标（如"利润最大"且"风险最小"、"成本最低"且
    "覆盖率最高"）。多目标问题一般不存在使所有目标同时最优的解，只能求
    "帕累托最优解"，再由决策者按偏好选择。2024 国赛 C 题（农作物种植）
    即典型的多目标 + 不确定性问题。

帕累托（Pareto）前沿概念：
    一个解称为帕累托最优（非支配解），当且仅当：不存在另一个解在所有目标上
    都不差、且至少一个目标更好。所有帕累托最优解在目标空间中构成"帕累托前沿"。
    多目标求解的本质就是逼近这条前沿，供决策者权衡取舍（trade-off）。

三种经典标量化方法（把多目标转成单目标求解）：
    1) 线性加权法 (weighted sum)：min  sum(w_i * f_i(x))，w_i 为偏好权重。
       简单直观，但对非凸前沿会漏解，权重难定。目标需先归一化消除量纲。
    2) ε-约束法 (epsilon-constraint)：只优化一个主目标，其余目标转成约束
       f_j(x) <= ε_j。通过改变 ε 逐点扫出帕累托前沿，能处理非凸前沿。
    3) 理想点法 (ideal point / 目标规划)：先求各目标单独最优得"理想点" f*，
       再最小化解到理想点的加权距离 min ||f(x) - f*||，使各目标尽量逼近理想。

输入格式：
    objs   : 目标函数列表 [f1, f2, ...]，每个 f 接受一维数组 x 返回标量（均按最小化）
    bounds : 变量边界；constraints：scipy 约束字典列表（'ineq' 为 >=0）

依赖：numpy, scipy（pip install scipy）
================================================================================
"""

import numpy as np
from scipy.optimize import minimize


def weighted_sum(objs, weights, bounds, x0, constraints=None, normalize_scale=None):
    """线性加权法：min sum(w_i * f_i(x))。

    参数:
        objs            : 目标函数列表（均为最小化）
        weights         : 权重列表，反映各目标重要程度（内部归一化）
        normalize_scale : 各目标的量纲尺度（如各目标单独最优值），用于归一化；
                          None 表示不归一化（要求各目标量纲相近）
    返回:
        res（scipy 结果对象），res.x 为折中解
    """
    w = np.array(weights, dtype=float)
    w = w / w.sum()
    scale = np.array(normalize_scale, dtype=float) if normalize_scale is not None \
        else np.ones(len(objs))

    def combined(x):
        return sum(w[i] * objs[i](x) / (abs(scale[i]) + 1e-12)
                   for i in range(len(objs)))

    return minimize(combined, x0, method='SLSQP', bounds=bounds,
                    constraints=constraints or ())


def epsilon_constraint(objs, main_idx, eps, bounds, x0, constraints=None):
    """ε-约束法：优化主目标 objs[main_idx]，其余目标 f_j(x) <= eps[j]。

    参数:
        main_idx : 作为唯一优化目标的目标索引
        eps      : 字典 {目标索引: 上界}，把非主目标转成约束
    返回:
        res（scipy 结果对象）
    """
    cons = list(constraints or [])
    # 每个受约束目标：eps_j - f_j(x) >= 0  即  f_j(x) <= eps_j
    for j, e in eps.items():
        cons.append({'type': 'ineq', 'fun': (lambda x, jj=j, ee=e: ee - objs[jj](x))})
    return minimize(objs[main_idx], x0, method='SLSQP', bounds=bounds,
                    constraints=cons)


def ideal_point(objs, bounds, x0, constraints=None, weights=None, p=2):
    """理想点法：先求各目标单独最优 f*，再最小化到理想点的 Lp 距离。

    参数:
        weights : 各目标距离权重，默认等权
        p       : 距离范数（2 为欧氏距离，1 为曼哈顿距离，np.inf 为切比雪夫）
    返回:
        dict：{'ideal': 理想点, 'x': 折中解, 'f': 折中解各目标值}
    """
    k = len(objs)
    weights = np.array(weights, dtype=float) if weights is not None else np.ones(k)
    weights = weights / weights.sum()

    # 1) 分别求每个目标的单独最优，构成理想点 f*
    ideal = []
    for f in objs:
        r = minimize(f, x0, method='SLSQP', bounds=bounds,
                     constraints=constraints or ())
        ideal.append(r.fun)
    ideal = np.array(ideal)

    # 2) 最小化解到理想点的加权 Lp 距离（各目标用理想点归一化）
    def dist(x):
        f = np.array([objs[i](x) for i in range(k)])
        diff = weights * (f - ideal) / (np.abs(ideal) + 1e-12)
        if np.isinf(p):
            return np.max(np.abs(diff))
        return np.sum(np.abs(diff) ** p) ** (1.0 / p)

    r = minimize(dist, x0, method='SLSQP', bounds=bounds,
                 constraints=constraints or ())
    f_final = np.array([objs[i](r.x) for i in range(k)])
    return {'ideal': ideal, 'x': r.x, 'f': f_final}


if __name__ == '__main__':
    # ---------------- 双目标示例 ----------------
    # 决策变量 x=[x1,x2]，x1,x2 ∈ [0,5]，约束 x1+x2<=5
    #   目标1（最小化成本）:  f1 = x1^2 + x2^2
    #   目标2（最大化收益 -> 取负最小化）: f2 = -(2*x1 + x2)
    # 两个目标冲突：降成本希望 x 小，增收益希望 x 大。
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   多目标规划里，两个目标函数的系数分别来自附件不同的列（如成本列、收益列）。
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   cost   = df['成本'].values                 # 目标1（最小化成本）的系数
    #   profit = df['收益'].values                 # 目标2（最大化收益）的系数
    #   def f1(x): return np.sum(cost * x)         # 目标1：成本最小
    #   def f2(x): return -np.sum(profit * x)      # 目标2：收益最大→取负转最小化
    #   objs = [f1, f2]
    #   bounds = [(0, 上限)] * len(cost)           # 变量边界
    #   cons = [{'type': 'ineq', 'fun': lambda x: 总量约束 - np.sum(x)}]  # 约束写成 >=0
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    def f1(x):
        return x[0] ** 2 + x[1] ** 2

    def f2(x):
        return -(2 * x[0] + x[1])   # 收益最大化 -> 负号转最小化

    objs = [f1, f2]
    bounds = [(0, 5), (0, 5)]
    x0 = [1.0, 1.0]
    cons = [{'type': 'ineq', 'fun': lambda x: 5 - x[0] - x[1]}]  # x1+x2<=5

    print('=' * 60)
    print('方法1：线性加权法（权重 [0.5, 0.5]，已按各目标尺度归一化）')
    print('=' * 60)
    # 用各目标粗略尺度归一化，避免量纲差异导致某目标主导
    r1 = weighted_sum(objs, [0.5, 0.5], bounds, x0, cons,
                      normalize_scale=[25, 15])
    print('折中解 x =', np.round(r1.x, 4))
    print(f'  f1(成本)={f1(r1.x):.4f}, 收益={-f2(r1.x):.4f}')

    print('\n' + '=' * 60)
    print('方法2：ε-约束法（主目标=最小化成本 f1，要求收益 >= 8 即 f2<=-8）')
    print('=' * 60)
    r2 = epsilon_constraint(objs, main_idx=0, eps={1: -8.0},
                            bounds=bounds, x0=x0, constraints=cons)
    print('解 x =', np.round(r2.x, 4))
    print(f'  f1(成本)={f1(r2.x):.4f}, 收益={-f2(r2.x):.4f}')

    print('\n' + '=' * 60)
    print('方法3：理想点法（各目标尽量逼近单独最优）')
    print('=' * 60)
    r3 = ideal_point(objs, bounds, x0, cons, weights=[1, 1], p=2)
    print('理想点 f* =', np.round(r3['ideal'], 4), '（[成本理想, 负收益理想]）')
    print('折中解 x =', np.round(r3['x'], 4))
    print(f"  f1(成本)={r3['f'][0]:.4f}, 收益={-r3['f'][1]:.4f}")

    print('\n' + '=' * 60)
    print('用 ε-约束法扫描帕累托前沿（改变收益下界 ε）')
    print('=' * 60)
    print(f"{'收益下界':>8} | {'成本 f1':>10} | {'实际收益':>10}")
    for target in [2, 4, 6, 8, 10]:
        r = epsilon_constraint(objs, 0, {1: -target}, bounds, x0, cons)
        if r.success:
            print(f"{target:>8} | {f1(r.x):>10.4f} | {-f2(r.x):>10.4f}")
    print('\n上表每一行是一个帕累托最优解，连起来即帕累托前沿；')
    print('决策者据此权衡"多花成本换多少收益"。大规模多目标建议用 06 的 NSGA-II。')
