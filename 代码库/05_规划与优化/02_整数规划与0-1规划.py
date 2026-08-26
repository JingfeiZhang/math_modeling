# -*- coding: utf-8 -*-
"""
================================================================================
整数规划 / 0-1 规划（Integer & Binary Programming）—— pulp 建模求解
================================================================================
功能：
    求解决策变量必须取整数（整数规划 IP）或只能取 0/1（0-1 规划）的线性优化。
    典型问题：指派问题、背包问题、选址、排班、投资项目选择、切割下料等。
    凡是"选或不选 / 做几个（必须整数）"的决策，都属于本类。

为什么不用 scipy.optimize.linprog？
    linprog 只解【连续】线性规划，不支持整数约束（把结果四舍五入往往不可行
    或非最优）。整数规划需要分支定界等专门算法。这里用 pulp（自带 CBC 求解器，
    开箱即用），也可换 cvxpy / gurobipy / ortools。
        安装：pip install pulp

数学模型（0-1 背包为例）：
        max   sum(value_i * x_i)
        s.t.  sum(weight_i * x_i) <= 容量
              x_i ∈ {0, 1}

pulp 建模三步走：
    1) prob = LpProblem('名字', LpMaximize/LpMinimize)   # 定义问题与优化方向
    2) x = LpVariable(...) / LpVariable.dicts(...)        # 定义变量，指定 cat 类型
       cat='Continuous'(连续) / 'Integer'(整数) / 'Binary'(0-1)
    3) prob += 目标表达式 ; prob += 约束表达式 ; prob.solve()

依赖：pulp（pip install pulp），numpy
================================================================================
"""

import numpy as np
import pulp


def knapsack_01(values, weights, capacity):
    """0-1 背包：在容量限制下选择物品，使总价值最大（每件物品选或不选）。

    参数:
        values   : 各物品价值列表
        weights  : 各物品重量列表
        capacity : 背包容量上限
    返回:
        chosen   : 被选中物品的索引列表
        total_v  : 最大总价值
    """
    n = len(values)
    prob = pulp.LpProblem('knapsack_01', pulp.LpMaximize)
    # 定义 0-1 变量 x0..x_{n-1}
    x = [pulp.LpVariable(f'x{i}', cat='Binary') for i in range(n)]
    # 目标函数：最大化总价值（lpDot = 向量点积）
    prob += pulp.lpDot(values, x)
    # 约束：总重量不超过容量
    prob += pulp.lpDot(weights, x) <= capacity
    prob.solve(pulp.PULP_CBC_CMD(msg=0))  # msg=0 关闭求解器日志

    chosen = [i for i in range(n) if x[i].value() > 0.5]
    return chosen, pulp.value(prob.objective)


def assignment_problem(cost):
    """指派问题：n 个人分配 n 项任务，每人一任务、每任务一人，使总成本最小。

    参数:
        cost : (n, n) 成本矩阵，cost[i][j] = 第 i 人做第 j 任务的成本
    返回:
        assign  : 列表，assign[i] = 第 i 人被分配到的任务编号
        total_c : 最小总成本
    """
    cost = np.array(cost, dtype=float)
    n = cost.shape[0]
    prob = pulp.LpProblem('assignment', pulp.LpMinimize)
    # 0-1 变量 x[i][j]：第 i 人是否做第 j 任务
    x = pulp.LpVariable.dicts('x', (range(n), range(n)), cat='Binary')
    # 目标：总成本最小
    prob += pulp.lpSum(cost[i][j] * x[i][j] for i in range(n) for j in range(n))
    # 约束1：每人恰好做一项任务
    for i in range(n):
        prob += pulp.lpSum(x[i][j] for j in range(n)) == 1
    # 约束2：每项任务恰好由一人完成
    for j in range(n):
        prob += pulp.lpSum(x[i][j] for i in range(n)) == 1
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    assign = [None] * n
    for i in range(n):
        for j in range(n):
            if x[i][j].value() > 0.5:
                assign[i] = j
    return assign, pulp.value(prob.objective)


def integer_program_demo():
    """一般整数规划示例：变量取非负整数。
        max  5 x1 + 4 x2
        s.t. 6 x1 + 4 x2 <= 24
             x1 + 2 x2 <= 6
             x1, x2 >= 0 且为整数
    """
    prob = pulp.LpProblem('IP_demo', pulp.LpMaximize)
    # cat='Integer' 且 lowBound=0 表示非负整数变量
    x1 = pulp.LpVariable('x1', lowBound=0, cat='Integer')
    x2 = pulp.LpVariable('x2', lowBound=0, cat='Integer')
    prob += 5 * x1 + 4 * x2               # 目标函数
    prob += 6 * x1 + 4 * x2 <= 24         # 约束1
    prob += x1 + 2 * x2 <= 6              # 约束2
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    return {'x1': x1.value(), 'x2': x2.value(),
            'obj': pulp.value(prob.objective),
            'status': pulp.LpStatus[prob.status]}


if __name__ == '__main__':
    print('=' * 60)
    print('示例1：0-1 背包问题')
    print('=' * 60)
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   整数/0-1 规划同样是"从附件读参数表 → 填进模型系数"。
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   values = df['价值'].values                # 每件物品的价值（目标系数）
    #   weights = df['重量'].values               # 每件物品的重量（约束系数）
    #   capacity = 50                             # 容量上限（来自题目或附件单元格）
    #   # 指派问题：成本矩阵可由附件透视得到，如
    #   #   cost = df.pivot(index='人', columns='任务', values='成本').values
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    values = [60, 100, 120, 80]     # 物品价值
    weights = [10, 20, 30, 15]      # 物品重量
    capacity = 50                    # 背包容量
    chosen, total_v = knapsack_01(values, weights, capacity)
    print(f'容量 {capacity} 下，选中物品索引: {chosen}')
    print(f'选中物品总重: {sum(weights[i] for i in chosen)}，总价值: {total_v}')

    print('\n' + '=' * 60)
    print('示例2：指派问题（3 人 3 任务，成本最小）')
    print('=' * 60)
    cost = [[9, 2, 7],
            [6, 4, 3],
            [5, 8, 1]]
    assign, total_c = assignment_problem(cost)
    for i, j in enumerate(assign):
        print(f'  第{i}人 -> 任务{j}（成本 {cost[i][j]}）')
    print(f'最小总成本: {total_c}')

    print('\n' + '=' * 60)
    print('示例3：一般整数规划（变量取非负整数）')
    print('=' * 60)
    r = integer_program_demo()
    print(f"求解状态: {r['status']}")
    print(f"最优解 x1={r['x1']}, x2={r['x2']}，最大目标值={r['obj']}")

    print('\n提示：混合整数（部分变量连续、部分整数）只需对不同变量指定不同 '
          "cat（'Continuous'/'Integer'/'Binary'）即可，其余建模方式相同。")
