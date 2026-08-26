# -*- coding: utf-8 -*-
"""
差分进化算法（Differential Evolution, DE）模板
==========================================================================
功能
    连续函数优化（尤其擅长高维、非凸问题）。给出三种实现：
        (A) 手写实现              —— DE/rand/1/bin 经典策略，含缩放因子 F、交叉率 CR
        (B) scipy 调用            —— scipy.optimize.differential_evolution（稳定、无需额外装库）
        (C) scikit-opt 调用       —— sko.DE

原理
    差分进化是一种基于种群的进化算法，核心是"差分变异"：
        变异： V = X_r1 + F * (X_r2 - X_r3)     # 用两个随机个体的差向量扰动第三个
        交叉： 按概率 CR 把 V 的分量混入目标个体，得到试验向量 U
        选择： U 若优于原个体则替换（贪婪选择）
    差分变异让步长自适应种群分布，早期分散步长大、后期聚拢步长小。

参数直觉
    - F  （缩放因子）：控制差分扰动幅度，常取 0.4~0.9。大则探索强、收敛慢。
    - CR （交叉率）  ：控制试验向量继承变异体的比例，常取 0.7~0.9。
                       可分离问题用小 CR，非可分离问题用大 CR。

输入格式
    目标函数 func(x)->float，x 为 numpy 向量；上下界 bounds=[(lb,ub),...]。

依赖
    numpy, scipy, matplotlib（必需）；scikit-opt（可选）：pip install scikit-opt

作者：数学建模国赛模板库
"""

import numpy as np
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
np.random.seed(42)


# =========================================================================
# 第一部分：手写差分进化 DE/rand/1/bin
# =========================================================================
class DE:
    """经典差分进化算法。

    参数
    ----
    func     : 目标函数 func(x)->float
    n_dim    : 变量维度
    lb, ub   : 上下界
    size_pop : 种群规模（建议 >= 4，通常取 5~10 倍维度）
    max_iter : 迭代次数
    F        : 缩放因子
    CR       : 交叉率
    """

    def __init__(self, func, n_dim, lb, ub, size_pop=50, max_iter=200,
                 F=0.5, CR=0.9):
        self.func = func
        self.n_dim = n_dim
        self.lb = np.array(lb) * np.ones(n_dim)
        self.ub = np.array(ub) * np.ones(n_dim)
        self.size_pop = max(size_pop, 4)
        self.max_iter = max_iter
        self.F, self.CR = F, CR
        self.X = np.random.uniform(self.lb, self.ub, (self.size_pop, n_dim))
        self.y = np.array([func(x) for x in self.X])
        self.history = []

    def run(self):
        for _ in range(self.max_iter):
            for i in range(self.size_pop):
                # 从种群中随机取 3 个互不相同且不等于 i 的个体
                idxs = [j for j in range(self.size_pop) if j != i]
                r1, r2, r3 = np.random.choice(idxs, 3, replace=False)
                # 变异：V = X_r1 + F*(X_r2 - X_r3)
                V = self.X[r1] + self.F * (self.X[r2] - self.X[r3])
                V = np.clip(V, self.lb, self.ub)
                # 二项交叉：至少保证一维来自变异体 V
                U = self.X[i].copy()
                j_rand = np.random.randint(self.n_dim)
                for j in range(self.n_dim):
                    if np.random.rand() < self.CR or j == j_rand:
                        U[j] = V[j]
                # 贪婪选择
                fu = self.func(U)
                if fu < self.y[i]:
                    self.X[i], self.y[i] = U, fu
            self.history.append(self.y.min())
        best_idx = self.y.argmin()
        return self.X[best_idx], self.y[best_idx]


# =========================================================================
# 第二部分：scipy 调用版（无需额外装库，稳定推荐）
# =========================================================================
def demo_scipy_de(func, bounds):
    from scipy.optimize import differential_evolution
    result = differential_evolution(func, bounds, maxiter=200, popsize=15,
                                    mutation=0.5, recombination=0.9, seed=42)
    print('[scipy DE] 最优解 =', np.round(result.x, 4),
          ' 最优值 =', round(float(result.fun), 6))
    return result


# =========================================================================
# 第三部分：scikit-opt 调用版（pip install scikit-opt）
# =========================================================================
def demo_sko_de(func, n_dim, lb, ub):
    try:
        from sko.DE import DE as SkoDE
    except ImportError:
        print('[跳过] 未安装 scikit-opt')
        return
    de = SkoDE(func=func, n_dim=n_dim, size_pop=50, max_iter=200,
               lb=lb, ub=ub, F=0.5, prob_mut=0.3)
    best_x, best_y = de.run()
    print('[sko.DE] 最优解 =', np.round(best_x, 4),
          ' 最优值 =', round(float(best_y[0]), 6))


# =========================================================================
# 主程序演示
# =========================================================================
if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   DE 擅长高维连续优化，目标函数里的参数（成本/系数/需求）从附件读入并引用：
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   coef = df['系数'].values
    #   def obj(x): return np.sum(coef * x ** 2)   # 目标函数引用附件参数
    #   n_dim = len(coef)                          # 变量维度 = 参数个数
    #   lb, ub = [下界] * n_dim, [上界] * n_dim    # 各维范围（也可来自附件列）
    #   bounds = list(zip(lb, ub))
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 测试函数：Ackley，多峰、非凸，全局最优在原点，值为 0
    def ackley(x):
        x = np.asarray(x)
        n = len(x)
        s1 = np.sum(x ** 2)
        s2 = np.sum(np.cos(2 * np.pi * x))
        return (-20 * np.exp(-0.2 * np.sqrt(s1 / n))
                - np.exp(s2 / n) + 20 + np.e)

    n_dim = 5
    lb, ub = [-32.768] * n_dim, [32.768] * n_dim
    bounds = list(zip(lb, ub))

    print('=' * 60)
    print('连续函数优化：Ackley 函数（5 维，全局最优值 = 0）')
    print('=' * 60)
    de = DE(ackley, n_dim, lb, ub, size_pop=50, max_iter=200, F=0.5, CR=0.9)
    bx, by = de.run()
    print('[手写DE] 最优解 =', np.round(bx, 4), ' 最优值 =', round(by, 6))
    demo_scipy_de(ackley, bounds)
    demo_sko_de(ackley, n_dim, lb, ub)

    # 收敛曲线
    plt.figure(figsize=(8, 5))
    plt.plot(de.history)
    plt.title('手写 DE 收敛曲线（Ackley 5维）')
    plt.xlabel('迭代次数')
    plt.ylabel('种群最优目标值')
    plt.yscale('log')  # 对数坐标更能体现收敛过程
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('de_result.png', dpi=150)
    print('\n结果图已保存为 de_result.png')
    plt.show()
