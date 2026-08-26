# -*- coding: utf-8 -*-
"""
================================================================================
非线性规划 NLP（Nonlinear Programming）—— scipy.optimize.minimize 求解
================================================================================
功能：
    求解目标函数或约束中含有非线性项（平方、乘积、除法、指数、三角等）的
    最优化问题。国赛中大量"投资收益率、非线性成本、几何/物理约束"的建模
    最终都归结为 NLP。

数学模型：
        min   f(x)                     （目标函数，可非线性）
        s.t.  g_i(x) <= 0              （不等式约束）
              h_j(x)  = 0              （等式约束）
              lb <= x <= ub            （变量边界）

scipy.optimize.minimize 关键用法：
    - method 选择（有约束时二选一）：
        'SLSQP'       序列二次规划，支持等式/不等式约束+边界，最常用、快
        'trust-constr' 信赖域内点法，支持约束，鲁棒性更好、适合较难问题
      无约束光滑问题可用 'BFGS' / 'Nelder-Mead'（后者不需梯度）
    - constraints：约束以字典列表给出，每项 {'type': 'ineq'/'eq', 'fun': 函数}
        注意约定：'ineq' 表示 fun(x) >= 0；'eq' 表示 fun(x) == 0
        （与 linprog 的 <= 方向相反！写约束时务必转成 >= 0 的形式）
    - bounds：变量边界 [(lb, ub), ...]
    - 多初值策略：非凸问题 minimize 只保证局部最优，需用多个随机初值 x0
      分别求解，取目标最小的那个，逼近全局最优。

输入格式：
    fun         : 目标函数 f(x)，x 为一维数组
    x0 / bounds : 初值与边界
    constraints : 约束字典列表
输出：
    res.x（最优解）, res.fun（最优目标值）, res.success（是否收敛）

依赖：numpy, scipy（pip install scipy）
================================================================================
"""

import numpy as np
from scipy.optimize import minimize


def solve_nlp_multistart(fun, bounds, constraints=None, n_starts=30,
                         method='SLSQP', seed=42):
    """多初值非线性规划求解，缓解"陷入局部最优"问题。

    参数:
        fun         : 目标函数（最小化）；求最大化则传入 -f 或在外层取负
        bounds      : 变量边界列表 [(lb, ub), ...]，用于生成随机初值
        constraints : 约束字典列表，每项 {'type':'ineq'/'eq','fun':...}
                      约定 'ineq' 为 fun(x) >= 0
        n_starts    : 随机初值个数，越多越可能命中全局最优（但更慢）
        method      : 'SLSQP' 或 'trust-constr'
        seed        : 随机种子，保证结果可复现
    返回:
        dict：{'x': 最优解, 'fun': 最优目标值, 'success': 是否成功}
    """
    rng = np.random.default_rng(seed)
    bounds = list(bounds)
    # 为随机采样处理无穷边界（用有限范围替代 None）
    lows = [b[0] if b[0] is not None else -10.0 for b in bounds]
    highs = [b[1] if b[1] is not None else 10.0 for b in bounds]

    best = None
    for _ in range(n_starts):
        x0 = np.array([rng.uniform(lo, hi) for lo, hi in zip(lows, highs)])
        res = minimize(fun, x0, method=method,
                       bounds=bounds, constraints=constraints or ())
        if res.success and (best is None or res.fun < best.fun):
            best = res
    if best is None:
        return {'x': None, 'fun': None, 'success': False}
    return {'x': best.x, 'fun': best.fun, 'success': True}


if __name__ == '__main__':
    print('=' * 60)
    print('示例1：带约束的非线性规划（SLSQP）')
    print('=' * 60)
    # min  f(x) = (x1-1)^2 + (x2-2.5)^2
    # s.t.   x1 - 2 x2 + 2 >= 0
    #       -x1 - 2 x2 + 6 >= 0
    #       -x1 + 2 x2 + 2 >= 0
    #        x1, x2 >= 0
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   非线性规划里，目标/约束函数中的"系数"往往来自附件（成本、价格、系数表）。
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   price = df['单价'].values                  # 例如把附件某列读成参数向量
    #   cost  = df['成本'].values
    #   def f(x):                                  # 目标函数里直接引用上面的参数
    #       return np.sum(cost * x ** 2) - np.sum(price * x)
    #   bnds = [(0, None)] * len(price)            # 变量边界
    #   cons = [{'type': 'ineq', 'fun': lambda x: 资源上限 - np.sum(x)}]  # 约束写成 >=0
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    def f(x):
        return (x[0] - 1) ** 2 + (x[1] - 2.5) ** 2

    # 约束统一写成 fun(x) >= 0 的形式
    cons = [
        {'type': 'ineq', 'fun': lambda x: x[0] - 2 * x[1] + 2},
        {'type': 'ineq', 'fun': lambda x: -x[0] - 2 * x[1] + 6},
        {'type': 'ineq', 'fun': lambda x: -x[0] + 2 * x[1] + 2},
    ]
    bnds = [(0, None), (0, None)]
    r = solve_nlp_multistart(f, bnds, cons, n_starts=20, method='SLSQP')
    print('最优解 x =', np.round(r['x'], 4))
    print('最优目标值 f =', round(r['fun'], 6), '（理论最优约 0.8）')

    print('\n' + '=' * 60)
    print('示例2：多峰函数 —— 单初值 vs 多初值（体现局部最优陷阱）')
    print('=' * 60)
    # 目标：f(x) = x*sin(x) + 0.5*x，在 [0, 20] 上有多个局部极小
    def g(x):
        return x[0] * np.sin(x[0]) + 0.5 * x[0]

    # 单初值（从 x0=2 出发，容易停在局部最优）
    single = minimize(g, x0=[2.0], method='SLSQP', bounds=[(0, 20)])
    # 多初值（更接近全局最优）
    multi = solve_nlp_multistart(g, [(0, 20)], n_starts=50, method='SLSQP')
    print(f"单初值(x0=2): x={single.x[0]:.4f}, f={single.fun:.4f}")
    print(f"多初值(50次): x={multi['x'][0]:.4f}, f={multi['fun']:.4f}")
    print('结论：非凸问题务必多初值，否则结果依赖初值、可能非全局最优。')

    print('\n' + '=' * 60)
    print('示例3：等式约束（trust-constr）')
    print('=' * 60)
    # min  x1^2 + x2^2   s.t.  x1 + x2 = 1
    r3 = minimize(lambda x: x[0] ** 2 + x[1] ** 2, x0=[0.0, 0.0],
                  method='trust-constr',
                  constraints=[{'type': 'eq', 'fun': lambda x: x[0] + x[1] - 1}])
    print('最优解 x =', np.round(r3.x, 4), '（理论 [0.5, 0.5]）')
    print('最优目标值 =', round(r3.fun, 6))
