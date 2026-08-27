# -*- coding: utf-8 -*-
"""
06 NSGA-II 多目标搜索：约束、随机性与 Pareto approximation
==========================================================

study-only 模板。NSGA-II 是有限预算下构造非支配候选集的搜索器，不因算法名称或
第一非支配层的存在就自动得到“完整/全局 Pareto 前沿”。正式使用必须报告：

- 实际变量范围与约束；
- 种群/代数/函数评估预算；
- 随机种子与多种子稳定性；
- 可行解比例；
- 当前非支配集覆盖范围；
- 与 ε-constraint、精确小实例或其他 reference 的差异（能获得时）。
"""

from __future__ import annotations

import numpy as np


def _dominates(a, b):
    """无约束最小化支配关系。"""
    return bool(np.all(a <= b) and np.any(a < b))


def _constrained_dominates(a, b, va, vb, tol=1e-10):
    """Deb-style feasibility priority: feasible > infeasible; both infeasible -> lower violation."""
    fa, fb = va <= tol, vb <= tol
    if fa and not fb:
        return True
    if fb and not fa:
        return False
    if not fa and not fb:
        return va < vb - tol
    return _dominates(a, b)


def fast_non_dominated_sort(F, violation=None):
    F = np.asarray(F, dtype=float)
    if F.ndim != 2 or len(F) == 0 or not np.isfinite(F).all():
        raise ValueError("F 必须是非空有限二维目标矩阵")
    v = np.zeros(len(F), dtype=float) if violation is None else np.asarray(violation, dtype=float).ravel()
    if len(v) != len(F) or np.any(v < 0) or not np.isfinite(v).all():
        raise ValueError("violation 必须与种群等长、非负且有限")

    pop = len(F)
    dominated = [[] for _ in range(pop)]
    n_dom = np.zeros(pop, dtype=int)
    fronts = [[]]
    for p in range(pop):
        for q in range(pop):
            if p == q:
                continue
            if _constrained_dominates(F[p], F[q], v[p], v[q]):
                dominated[p].append(q)
            elif _constrained_dominates(F[q], F[p], v[q], v[p]):
                n_dom[p] += 1
        if n_dom[p] == 0:
            fronts[0].append(p)

    i = 0
    while fronts[i]:
        nxt = []
        for p in fronts[i]:
            for q in dominated[p]:
                n_dom[q] -= 1
                if n_dom[q] == 0:
                    nxt.append(q)
        i += 1
        fronts.append(nxt)
    fronts.pop()
    return fronts


def crowding_distance(F, front):
    F = np.asarray(F, dtype=float)
    front = list(front)
    n = len(front)
    if n <= 2:
        return np.full(n, np.inf)
    dist = np.zeros(n)
    local = F[front]
    for m in range(F.shape[1]):
        order = np.argsort(local[:, m])
        dist[order[0]] = dist[order[-1]] = np.inf
        lo, hi = local[order[0], m], local[order[-1], m]
        if hi <= lo:
            continue
        for k in range(1, n - 1):
            dist[order[k]] += (local[order[k + 1], m] - local[order[k - 1], m]) / (hi - lo)
    return dist


class NSGA2:
    """简化 NSGA-II；用于学习/原型，不替代成熟库或 Formal 求解器审计。"""

    def __init__(self, evaluate, n_var, xl, xu, pop_size=100, max_gen=200,
                 seed=42, constraint_violation=None):
        self.evaluate = evaluate
        self.constraint_violation = constraint_violation
        self.n_var = int(n_var)
        self.xl = np.asarray(xl, dtype=float) * np.ones(self.n_var)
        self.xu = np.asarray(xu, dtype=float) * np.ones(self.n_var)
        if np.any(~np.isfinite(self.xl)) or np.any(~np.isfinite(self.xu)) or np.any(self.xu <= self.xl):
            raise ValueError("NSGA-II 示例要求有限且严格递增的变量边界")
        if pop_size < 4 or max_gen < 1:
            raise ValueError("pop_size>=4 且 max_gen>=1")
        self.pop_size = int(pop_size)
        self.max_gen = int(max_gen)
        self.seed = int(seed)
        self.rng = np.random.default_rng(self.seed)
        self.evaluations = 0

    def _eval(self, X):
        X = np.asarray(X, dtype=float)
        F = np.asarray(self.evaluate(X), dtype=float)
        if F.ndim != 2 or F.shape[0] != X.shape[0] or F.shape[1] < 2:
            raise ValueError("evaluate(X) 必须返回 (n_samples, n_objectives>=2)")
        if not np.isfinite(F).all():
            raise ValueError("目标函数返回 NaN/Inf")
        if self.constraint_violation is None:
            V = np.zeros(len(X), dtype=float)
        else:
            V = np.asarray(self.constraint_violation(X), dtype=float).ravel()
            if len(V) != len(X) or np.any(V < 0) or not np.isfinite(V).all():
                raise ValueError("constraint_violation(X) 必须返回等长非负有限违反量")
        self.evaluations += len(X)
        return F, V

    def _make_offspring(self, X):
        off = X[self.rng.permutation(len(X))].copy()
        for i in range(0, self.pop_size - 1, 2):
            if self.rng.random() < 0.9:
                alpha = self.rng.random(self.n_var)
                p1, p2 = off[i].copy(), off[i + 1].copy()
                off[i] = alpha * p1 + (1 - alpha) * p2
                off[i + 1] = alpha * p2 + (1 - alpha) * p1
        mask = self.rng.random((self.pop_size, self.n_var)) < (1.0 / self.n_var)
        noise = self.rng.normal(size=(self.pop_size, self.n_var)) * (self.xu - self.xl) * 0.1
        off = np.where(mask, off + noise, off)
        return np.clip(off, self.xl, self.xu)

    def _select(self, X, F, V):
        fronts = fast_non_dominated_sort(F, V)
        keep = []
        for front in fronts:
            if len(keep) + len(front) <= self.pop_size:
                keep.extend(front)
            else:
                cd = crowding_distance(F, front)
                order = np.argsort(-cd)
                need = self.pop_size - len(keep)
                keep.extend([front[k] for k in order[:need]])
                break
        idx = np.asarray(keep, dtype=int)
        return X[idx], F[idx], V[idx]

    def run(self):
        self.evaluations = 0
        X = self.rng.uniform(self.xl, self.xu, (self.pop_size, self.n_var))
        F, V = self._eval(X)
        for _ in range(self.max_gen):
            off = self._make_offspring(X)
            F_off, V_off = self._eval(off)
            X, F, V = self._select(
                np.vstack([X, off]), np.vstack([F, F_off]), np.concatenate([V, V_off])
            )

        fronts = fast_non_dominated_sort(F, V)
        first = np.asarray(fronts[0], dtype=int)
        X1, F1, V1 = X[first], F[first], V[first]
        feasible = V1 <= 1e-10
        # 若第一层含不可行点，只把可行子集作为 Pareto approximation 输出。
        Xp, Fp, Vp = X1[feasible], F1[feasible], V1[feasible]
        return {
            "X": Xp, "F": Fp, "violation": Vp, "seed": self.seed,
            "evaluations": self.evaluations,
            "population_size": self.pop_size, "generations": self.max_gen,
            "feasible_fraction_final_population": float(np.mean(V <= 1e-10)),
            "claim_boundary": "当前随机种子、搜索域和有限评估预算下得到的可行非支配近似集；不等于完整或全局 Pareto 前沿",
        }


def run_many(evaluate, n_var, xl, xu, seeds, pop_size=100, max_gen=200,
             constraint_violation=None):
    """多种子运行；正式比较时不同算法应使用可比的函数评估预算。"""
    runs = []
    for seed in seeds:
        alg = NSGA2(evaluate, n_var, xl, xu, pop_size=pop_size, max_gen=max_gen,
                    seed=seed, constraint_violation=constraint_violation)
        runs.append(alg.run())
    return {
        "runs": runs,
        "front_sizes": [len(r["F"]) for r in runs],
        "feasible_fractions": [r["feasible_fraction_final_population"] for r in runs],
        "evaluation_budgets": [r["evaluations"] for r in runs],
    }


def demo_pymoo():
    try:
        from pymoo.algorithms.moo.nsga2 import NSGA2 as PymooNSGA2
        from pymoo.core.problem import Problem
        from pymoo.optimize import minimize as pymoo_minimize
    except ImportError:
        print("[跳过] 未安装 pymoo")
        return None

    class MyProblem(Problem):
        def __init__(self):
            super().__init__(n_var=1, n_obj=2, n_constr=0, xl=-2.0, xu=2.0)

        def _evaluate(self, X, out, *args, **kwargs):
            out["F"] = np.column_stack([X[:, 0] ** 2, (X[:, 0] - 2) ** 2])

    res = pymoo_minimize(MyProblem(), PymooNSGA2(pop_size=100), ("n_gen", 200), seed=1, verbose=False)
    print(f"[pymoo] 当前预算下返回 {len(res.F)} 个非支配候选点")
    return res


if __name__ == "__main__":
    def evaluate(X):
        return np.column_stack([X[:, 0] ** 2, (X[:, 0] - 2) ** 2])

    summary = run_many(evaluate, n_var=1, xl=[-2], xu=[2], seeds=[1, 2, 3],
                       pop_size=100, max_gen=200)
    print("多种子 front sizes:", summary["front_sizes"])
    print("多种子 feasible fractions:", np.round(summary["feasible_fractions"], 4))
    print("evaluation budgets:", summary["evaluation_budgets"])
    print("结论边界：有限预算下的 Pareto approximation；若要比较覆盖质量，还需 reference/hypervolume 等证据。")
    demo_pymoo()
