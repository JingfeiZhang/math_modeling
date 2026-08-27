# -*- coding: utf-8 -*-
"""
02 整数规划 / 0-1 规划：状态、可行性与结构化结果
=================================================

study-only 模板。整数规划最重要的不是“变量能取整数”，而是：

- 变量类型与题面语义一致；
- 求解器状态明确；
- 只有得到可接受状态后才读取解；
- 关键硬约束重新回查；
- 连续松弛解不能靠四舍五入冒充整数最优解。

正式项目若使用 CBC/Gurobi/CPLEX/SCIP 等，还应保存 solver status、时间限制、gap/bound
（可取得时）以及当前项目自己的约束审计。
"""

from __future__ import annotations

import numpy as np
import pulp


def _solve(prob, solver=None):
    solver = solver or pulp.PULP_CBC_CMD(msg=0)
    prob.solve(solver)
    status = pulp.LpStatus.get(prob.status, str(prob.status))
    accepted = status == "Optimal"
    return status, accepted


def knapsack_01(values, weights, capacity):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if values.ndim != 1 or weights.ndim != 1 or len(values) != len(weights):
        raise ValueError("values/weights 必须是一维等长向量")
    if np.any(weights < 0) or capacity < 0:
        raise ValueError("重量和容量必须非负")

    n = len(values)
    prob = pulp.LpProblem("knapsack_01", pulp.LpMaximize)
    x = [pulp.LpVariable(f"x{i}", cat="Binary") for i in range(n)]
    prob += pulp.lpDot(values, x)
    prob += pulp.lpDot(weights, x) <= float(capacity)

    status, accepted = _solve(prob)
    result = {"status": status, "accepted": accepted, "chosen": None, "objective": None,
              "total_weight": None, "capacity": float(capacity)}
    if not accepted:
        return result

    chosen = [i for i in range(n) if float(x[i].value()) > 0.5]
    total_weight = float(weights[chosen].sum()) if chosen else 0.0
    feasible = total_weight <= capacity + 1e-8
    result.update({
        "accepted": bool(feasible), "chosen": chosen,
        "objective": float(pulp.value(prob.objective)), "total_weight": total_weight,
        "feasible": bool(feasible),
    })
    return result


def assignment_problem(cost):
    cost = np.asarray(cost, dtype=float)
    if cost.ndim != 2 or cost.shape[0] != cost.shape[1]:
        raise ValueError("示例函数要求方阵成本矩阵；非方阵指派需显式定义虚拟任务/人员或改模型")
    if not np.isfinite(cost).all():
        raise ValueError("成本矩阵含非有限值")

    n = cost.shape[0]
    prob = pulp.LpProblem("assignment", pulp.LpMinimize)
    x = pulp.LpVariable.dicts("x", (range(n), range(n)), cat="Binary")
    prob += pulp.lpSum(cost[i, j] * x[i][j] for i in range(n) for j in range(n))
    for i in range(n):
        prob += pulp.lpSum(x[i][j] for j in range(n)) == 1
    for j in range(n):
        prob += pulp.lpSum(x[i][j] for i in range(n)) == 1

    status, accepted = _solve(prob)
    result = {"status": status, "accepted": accepted, "assignment": None, "objective": None}
    if not accepted:
        return result

    assignment = [None] * n
    for i in range(n):
        selected = [j for j in range(n) if float(x[i][j].value()) > 0.5]
        if len(selected) != 1:
            result["accepted"] = False
            result["feasible"] = False
            return result
        assignment[i] = selected[0]
    feasible = len(set(assignment)) == n
    result.update({
        "accepted": bool(feasible), "feasible": bool(feasible),
        "assignment": assignment, "objective": float(pulp.value(prob.objective)),
    })
    return result


def integer_program_demo():
    prob = pulp.LpProblem("IP_demo", pulp.LpMaximize)
    x1 = pulp.LpVariable("x1", lowBound=0, cat="Integer")
    x2 = pulp.LpVariable("x2", lowBound=0, cat="Integer")
    prob += 5 * x1 + 4 * x2
    prob += 6 * x1 + 4 * x2 <= 24
    prob += x1 + 2 * x2 <= 6

    status, accepted = _solve(prob)
    result = {"status": status, "accepted": accepted, "x1": None, "x2": None, "objective": None}
    if not accepted:
        return result
    v1, v2 = float(x1.value()), float(x2.value())
    feasible = (v1 >= -1e-8 and v2 >= -1e-8 and
                6 * v1 + 4 * v2 <= 24 + 1e-8 and v1 + 2 * v2 <= 6 + 1e-8 and
                abs(v1 - round(v1)) <= 1e-8 and abs(v2 - round(v2)) <= 1e-8)
    result.update({"accepted": bool(feasible), "feasible": bool(feasible),
                   "x1": v1, "x2": v2, "objective": float(pulp.value(prob.objective))})
    return result


if __name__ == "__main__":
    print("########## 0-1 背包 ##########")
    r = knapsack_01([60, 100, 120, 80], [10, 20, 30, 15], 50)
    print(r)

    print("\n########## 指派 ##########")
    cost = [[9, 2, 7], [6, 4, 3], [5, 8, 1]]
    r = assignment_problem(cost)
    print(r)

    print("\n########## 一般整数规划 ##########")
    r = integer_program_demo()
    print(r)

    print("\n正式使用时：先看 status/feasible，再解释目标值；若有时间限制或 gap，必须一并报告。")
