# -*- coding: utf-8 -*-
"""
NSGA-II 多目标优化算法模板
==========================================================================
功能
    多目标优化，求解帕累托前沿（Pareto Front）。给出两种实现：
        (A) 手写简版 NSGA-II —— 含非支配排序 + 拥挤度距离，可直接跑，便于理解与改造
        (B) pymoo 调用       —— 工业级库，参数丰富（pip install pymoo）

原理
    多目标问题往往不存在使所有目标同时最优的单一解，而是一组"互不占优"的
    折中解，称为帕累托前沿。NSGA-II 的两大核心机制：
        1) 快速非支配排序：把种群按"支配层级"分层（第 1 层最优前沿）。
        2) 拥挤度距离：同层内偏好分布稀疏处的解，保证前沿分布均匀。
    选择时优先取层级低的，同层取拥挤度大的，兼顾收敛性与多样性。

支配关系定义（最小化）
    解 a 支配解 b：a 的每个目标都 <= b，且至少一个目标 < b。

输入格式
    - 目标函数 evaluate(X)->F，X 形状 (pop, n_var)，F 形状 (pop, n_obj)。
    - 变量上下界 xl, xu。

依赖
    numpy, matplotlib（必需）；pymoo（可选）：pip install pymoo

作者：数学建模国赛模板库
"""

import numpy as np
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
np.random.seed(42)


# =========================================================================
# 第一部分：手写简版 NSGA-II
# =========================================================================
def fast_non_dominated_sort(F):
    """快速非支配排序，返回每个个体所在的前沿层级列表 fronts。

    F : 目标矩阵，形状 (pop, n_obj)，均为最小化目标。
    返回 fronts：列表的列表，fronts[0] 是第一非支配层（最优前沿）的个体下标。
    """
    pop = F.shape[0]
    S = [[] for _ in range(pop)]   # S[p]：被 p 支配的个体集合
    n = np.zeros(pop, dtype=int)   # n[p]：支配 p 的个体数
    fronts = [[]]
    for p in range(pop):
        for q in range(pop):
            if _dominates(F[p], F[q]):
                S[p].append(q)
            elif _dominates(F[q], F[p]):
                n[p] += 1
        if n[p] == 0:
            fronts[0].append(p)
    i = 0
    while fronts[i]:
        nxt = []
        for p in fronts[i]:
            for q in S[p]:
                n[q] -= 1
                if n[q] == 0:
                    nxt.append(q)
        i += 1
        fronts.append(nxt)
    fronts.pop()  # 去掉最后的空层
    return fronts


def _dominates(a, b):
    """判断 a 是否支配 b（最小化）。"""
    return np.all(a <= b) and np.any(a < b)
def crowding_distance(F, front):
    """计算某一前沿层内各解的拥挤度距离（越大表示越稀疏、越应保留）。"""
    l = len(front)
    dist = np.zeros(l)
    if l <= 2:
        return np.full(l, np.inf)  # 边界解优先保留
    F_front = F[front]
    for m in range(F.shape[1]):  # 对每个目标维度
        order = np.argsort(F_front[:, m])
        dist[order[0]] = dist[order[-1]] = np.inf  # 边界置无穷
        f_min, f_max = F_front[order[0], m], F_front[order[-1], m]
        if f_max - f_min == 0:
            continue
        for k in range(1, l - 1):
            dist[order[k]] += (F_front[order[k + 1], m]
                               - F_front[order[k - 1], m]) / (f_max - f_min)
    return dist


class NSGA2:
    """手写简版 NSGA-II（实数编码，SBX 交叉 + 多项式变异的简化版）。

    参数
    ----
    evaluate : 函数 evaluate(X)->F，X 形状 (pop,n_var)，F 形状 (pop,n_obj)
    n_var    : 决策变量维度
    xl, xu   : 上下界（数组）
    pop_size : 种群规模
    max_gen  : 迭代代数
    """

    def __init__(self, evaluate, n_var, xl, xu, pop_size=100, max_gen=200):
        self.evaluate = evaluate
        self.n_var = n_var
        self.xl = np.array(xl) * np.ones(n_var)
        self.xu = np.array(xu) * np.ones(n_var)
        self.pop_size = pop_size
        self.max_gen = max_gen

    def _make_offspring(self, X):
        """产生子代：模拟二进制交叉 + 均匀变异（简化实现）。"""
        off = X.copy()
        np.random.shuffle(off)
        for i in range(0, self.pop_size - 1, 2):
            if np.random.rand() < 0.9:  # 交叉概率
                alpha = np.random.rand(self.n_var)
                p1, p2 = off[i].copy(), off[i + 1].copy()
                off[i] = alpha * p1 + (1 - alpha) * p2
                off[i + 1] = alpha * p2 + (1 - alpha) * p1
        # 变异
        mask = np.random.rand(self.pop_size, self.n_var) < (1.0 / self.n_var)
        noise = np.random.randn(self.pop_size, self.n_var) * (self.xu - self.xl) * 0.1
        off = np.where(mask, off + noise, off)
        return np.clip(off, self.xl, self.xu)

    def _select(self, X, F):
        """基于非支配层级 + 拥挤度距离，从合并种群中选出 pop_size 个。"""
        fronts = fast_non_dominated_sort(F)
        new_idx = []
        for front in fronts:
            if len(new_idx) + len(front) <= self.pop_size:
                new_idx.extend(front)
            else:
                # 该层放不下，按拥挤度距离降序挑选
                cd = crowding_distance(F, front)
                order = np.argsort(-cd)
                need = self.pop_size - len(new_idx)
                new_idx.extend([front[k] for k in order[:need]])
                break
        return X[new_idx], F[new_idx]

    def run(self):
        # 初始化种群并评估
        X = np.random.uniform(self.xl, self.xu, (self.pop_size, self.n_var))
        F = self.evaluate(X)
        for _ in range(self.max_gen):
            off = self._make_offspring(X)
            F_off = self.evaluate(off)
            # 父代与子代合并，再环境选择（精英保留）
            X_all = np.vstack([X, off])
            F_all = np.vstack([F, F_off])
            X, F = self._select(X_all, F_all)
        # 返回第一非支配前沿作为最终帕累托解集
        fronts = fast_non_dominated_sort(F)
        return X[fronts[0]], F[fronts[0]]


# =========================================================================
# 第二部分：pymoo 调用版（pip install pymoo）
# =========================================================================
def demo_pymoo():
    """pymoo 官方接口示例（未安装时打印提示并跳过）。"""
    try:
        from pymoo.algorithms.moo.nsga2 import NSGA2 as PymooNSGA2
        from pymoo.core.problem import Problem
        from pymoo.optimize import minimize
    except ImportError:
        print('[跳过] 未安装 pymoo，运行 pip install pymoo 后可用')
        print('       pymoo 参考写法见本函数源码注释。')
        return None

    class MyProblem(Problem):
        def __init__(self):
            super().__init__(n_var=1, n_obj=2, n_constr=0, xl=-2.0, xu=2.0)

        def _evaluate(self, X, out, *args, **kwargs):
            f1 = X[:, 0] ** 2
            f2 = (X[:, 0] - 2) ** 2
            out['F'] = np.column_stack([f1, f2])

    res = minimize(MyProblem(), PymooNSGA2(pop_size=100),
                   ('n_gen', 200), seed=1, verbose=False)
    print('[pymoo NSGA-II] 帕累托前沿点数 =', len(res.F))
    return res.F


# =========================================================================
# 主程序演示
# =========================================================================
if __name__ == '__main__':
    # 经典双目标测试问题 Schaffer：min f1=x^2, f2=(x-2)^2
    # 理论帕累托前沿对应 x∈[0,2]，是一条凸曲线
    print('=' * 60)
    print('多目标优化：Schaffer 问题  min f1=x^2, f2=(x-2)^2')
    print('=' * 60)
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   NSGA-II 求帕累托前沿，两个目标函数的参数分别来自附件不同的列：
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   profit = df['收益'].values                 # 目标1（最大化收益→取负）的系数
    #   risk   = df['风险'].values                 # 目标2（最小化风险）的系数
    #   def evaluate(X):                           # X 形状 (pop, n_var)
    #       f1 = -(X * profit).sum(axis=1)         # 收益最大→取负转最小化
    #       f2 =  (X * risk).sum(axis=1)           # 风险最小
    #       return np.column_stack([f1, f2])
    #   n_var = len(profit)                        # 决策变量维度
    #   xl, xu = [下界] * n_var, [上界] * n_var    # 变量上下界（也可来自附件列）
    #   nsga = NSGA2(evaluate, n_var, xl, xu, ...)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    def evaluate(X):
        f1 = (X[:, 0] ** 2)
        f2 = ((X[:, 0] - 2) ** 2)
        return np.column_stack([f1, f2])

    nsga = NSGA2(evaluate, n_var=1, xl=[-2], xu=[2],
                 pop_size=100, max_gen=200)
    ps_X, ps_F = nsga.run()
    print('[手写NSGA-II] 帕累托前沿点数 =', len(ps_F))

    pymoo_F = demo_pymoo()

    # 帕累托前沿图
    plt.figure(figsize=(8, 6))
    plt.scatter(ps_F[:, 0], ps_F[:, 1], facecolors='none',
                edgecolors='b', s=40, label='手写 NSGA-II')
    if pymoo_F is not None:
        plt.scatter(pymoo_F[:, 0], pymoo_F[:, 1], marker='x',
                    c='r', s=30, label='pymoo NSGA-II')
    plt.title('帕累托前沿（Schaffer 问题）')
    plt.xlabel('目标 f1')
    plt.ylabel('目标 f2')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('nsga2_result.png', dpi=150)
    print('\n结果图已保存为 nsga2_result.png')
    plt.show()
