# -*- coding: utf-8 -*-
"""
================================================================================
线性规划 LP（Linear Programming）—— scipy.optimize.linprog 求解
================================================================================
功能：
    求解目标函数与约束条件均为线性的最优化问题（连续变量）。
    这是运筹优化最基础、最常用的模型：资源分配、生产计划、运输调配、
    配料/膳食问题等，凡是"线性目标 + 线性约束"都可以直接套用。

数学模型（linprog 的标准形式，一律为"最小化"）：
        min   c^T x
        s.t.  A_ub @ x <= b_ub      （不等式约束，统一写成 <= 形式）
              A_eq @ x  = b_eq      （等式约束）
              lb <= x <= ub         （变量上下界 bounds）
    - 求最大化 max c^T x：把目标系数取负 min (-c)^T x，结果再取负号即可。
    - 约束是 ">=" ：两边乘 -1 变成 "<="，例如 3x+2y>=12 -> -3x-2y<=-12。

输入格式：
    c    : 长度 n 的一维数组，目标函数系数（对应 min c^T x）
    A_ub : (p, n) 数组，不等式约束左端系数矩阵；b_ub 长度 p
    A_eq : (q, n) 数组，等式约束左端系数矩阵；b_eq 长度 q
    bounds: 长度 n 的列表，每个元素 (下界, 上界)，无界写 None，默认 (0, None)

输出：
    res.x     : 最优决策变量取值
    res.fun   : 最优目标值（若原问题是 max，需再取负）
    res.status: 0 表示成功找到最优解

依赖：numpy, scipy（pip install scipy）
================================================================================
"""

import numpy as np
from scipy.optimize import linprog


def solve_lp(c, A_ub=None, b_ub=None, A_eq=None, b_eq=None,
             bounds=None, maximize=False, method='highs'):
    """线性规划统一求解封装。

    参数:
        c        : 目标函数系数（按"最小化"给；若求最大化置 maximize=True）
        A_ub,b_ub: 不等式约束 A_ub @ x <= b_ub
        A_eq,b_eq: 等式约束   A_eq @ x  = b_eq
        bounds   : 变量边界列表 [(lb,ub), ...]，默认每个变量 >= 0
        maximize : True 表示原问题是最大化（内部自动对 c 取负）
        method   : 求解器，推荐 'highs'（scipy>=1.6 默认高性能单纯形/内点）
    返回:
        dict：{'x': 最优解, 'fun': 原问题最优目标值, 'success': 是否成功, 'status': 状态码}
    """
    c = np.array(c, dtype=float)
    # 最大化转最小化：min (-c)^T x
    c_solve = -c if maximize else c

    res = linprog(c_solve, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method=method)

    fun = None
    if res.success:
        # 若原问题为最大化，目标值取回正号
        fun = -res.fun if maximize else res.fun
    return {'x': res.x, 'fun': fun, 'success': res.success,
            'status': res.status, 'message': res.message}


if __name__ == '__main__':
    print('=' * 60)
    print('示例1：生产利润最大化（最大化问题）')
    print('=' * 60)
    # 某工厂生产两种产品 x1, x2，单位利润分别为 40、30（元）
    #   max  40 x1 + 30 x2
    #   s.t.  x1 +  x2 <= 40     （原材料约束）
    #        2 x1 +  x2 <= 60    （工时约束）
    #         x1, x2 >= 0
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   规划题的关键：从附件的参数表里"读出模型系数"，再填进 c / A_ub / b_ub。
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   c = df['单位利润'].values                 # 目标函数系数（每种产品的利润）
    #   # 约束矩阵：每行一个资源约束，每列一个产品；系数=单位产品的资源消耗
    #   A_ub = df[['耗原材料', '耗工时']].values.T # 转置成 (约束数, 变量数)
    #   b_ub = [原材料上限, 工时上限]              # 各资源上限（也可来自附件某列/单元格）
    #   bounds = [(0, None)] * len(c)             # 变量非负
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    c = [40, 30]                       # 目标系数（利润，最大化）
    A_ub = [[1, 1], [2, 1]]            # 不等式约束左端矩阵
    b_ub = [40, 60]                    # 不等式约束右端
    bounds = [(0, None), (0, None)]    # 变量非负

    r = solve_lp(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, maximize=True)
    print('求解成功:', r['success'])
    print('最优生产方案 x =', np.round(r['x'], 4))
    print('最大利润 =', round(r['fun'], 4))

    print('\n' + '=' * 60)
    print('示例2：运输/成本最小化（含等式约束与 >= 约束的转换）')
    print('=' * 60)
    # min  2 x1 + 3 x2 + x3
    # s.t.  x1 +  x2 + x3 = 100      （产量必须恰好 100，等式约束）
    #        x1 +      2x3 >= 40     （>= 约束 -> 两边乘 -1 变 <=）
    #        x1,x2,x3 >= 0
    c2 = [2, 3, 1]
    A_eq = [[1, 1, 1]]
    b_eq = [100]
    # 原约束 x1 + 2x3 >= 40  =>  -x1 - 2x3 <= -40
    A_ub2 = [[-1, 0, -2]]
    b_ub2 = [-40]
    bounds2 = [(0, None)] * 3

    r2 = solve_lp(c2, A_ub=A_ub2, b_ub=b_ub2, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds2, maximize=False)
    print('求解成功:', r2['success'])
    print('最优方案 x =', np.round(r2['x'], 4))
    print('最小成本 =', round(r2['fun'], 4))

    print('\n提示：变量若需为整数（如"件数/人数"），linprog 不支持，'
          '请改用 02_整数规划与0-1规划.py（pulp）。')
