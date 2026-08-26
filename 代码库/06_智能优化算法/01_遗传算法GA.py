# -*- coding: utf-8 -*-
"""
遗传算法（Genetic Algorithm, GA）模板
==========================================================================
功能
    - 例1：连续函数优化（最小化多峰函数，含约束示例）
    - 例2：TSP 组合优化（旅行商问题，寻找最短巡回路径）
    每个例子给出两种实现：
        (A) 手写实现   —— 结构透明，便于按题目需求魔改算子
        (B) scikit-opt 调用 —— 接口成熟，几行代码即可跑，适合比赛抢时间

原理
    遗传算法模拟自然选择：把候选解编码成"染色体"，通过
        选择(selection) -> 交叉(crossover) -> 变异(mutation)
    不断迭代，让适应度高的个体更可能把基因传给下一代，从而逼近最优解。
    - 连续问题：染色体是实数向量（本模板用实数编码）。
    - TSP 问题：染色体是城市访问顺序（排列编码），交叉用顺序交叉 OX，
      变异用片段翻转，保证解始终是合法排列。

输入格式
    - 连续优化：目标函数 func(x) -> float，x 为 numpy 向量；给定上下界 lb/ub。
    - TSP：城市坐标数组 points，形状 (N, 2)。

依赖
    numpy, matplotlib（必需）
    scikit-opt（可选，B 版本需要）：  pip install scikit-opt

作者：数学建模国赛模板库
"""

import numpy as np
import matplotlib.pyplot as plt

# 中文显示配置（Windows 常见字体，找不到会自动回退）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

# 固定随机种子，保证结果可复现（比赛写论文时便于复算）
np.random.seed(42)


# =========================================================================
# 第一部分：手写遗传算法 —— 连续函数优化
# =========================================================================
class GAContinuous:
    """实数编码遗传算法，用于连续函数最小化。

    参数
    ----
    func      : 目标函数，输入一维 numpy 向量，返回标量（越小越好）
    n_dim     : 决策变量维度
    lb, ub    : 长度为 n_dim 的下界、上界（可传标量自动广播）
    size_pop  : 种群规模（个体数量），必须为偶数，便于两两交叉
    max_iter  : 最大迭代代数
    prob_cross: 交叉概率
    prob_mut  : 变异概率
    """

    def __init__(self, func, n_dim, lb, ub, size_pop=50, max_iter=200,
                 prob_cross=0.8, prob_mut=0.1):
        self.func = func
        self.n_dim = n_dim
        self.lb = np.array(lb) * np.ones(n_dim)
        self.ub = np.array(ub) * np.ones(n_dim)
        self.size_pop = size_pop if size_pop % 2 == 0 else size_pop + 1
        self.max_iter = max_iter
        self.prob_cross = prob_cross
        self.prob_mut = prob_mut
        # 在上下界内随机初始化种群
        self.pop = np.random.uniform(self.lb, self.ub,
                                     size=(self.size_pop, n_dim))
        self.best_x = None
        self.best_y = np.inf
        self.history = []  # 记录每代最优值，用于画收敛曲线

    def _fitness(self, pop):
        """计算种群目标值。适应度越小越优（最小化问题）。"""
        return np.array([self.func(ind) for ind in pop])

    def _select(self, pop, y):
        """锦标赛选择：每次随机挑 2 个个体，保留较优者。"""
        new_pop = np.zeros_like(pop)
        for i in range(self.size_pop):
            a, b = np.random.randint(0, self.size_pop, 2)
            new_pop[i] = pop[a] if y[a] < y[b] else pop[b]
        return new_pop

    def _crossover(self, pop):
        """算术交叉：对相邻个体按随机权重线性组合。"""
        for i in range(0, self.size_pop, 2):
            if np.random.rand() < self.prob_cross:
                alpha = np.random.rand(self.n_dim)
                p1, p2 = pop[i].copy(), pop[i + 1].copy()
                pop[i] = alpha * p1 + (1 - alpha) * p2
                pop[i + 1] = alpha * p2 + (1 - alpha) * p1
        return pop

    def _mutate(self, pop):
        """高斯变异：对每个基因以 prob_mut 概率加一个正态扰动。"""
        for i in range(self.size_pop):
            for j in range(self.n_dim):
                if np.random.rand() < self.prob_mut:
                    scale = (self.ub[j] - self.lb[j]) * 0.1
                    pop[i, j] += np.random.randn() * scale
        # 越界修剪，保证解始终在可行域内
        return np.clip(pop, self.lb, self.ub)

    def run(self):
        for _ in range(self.max_iter):
            y = self._fitness(self.pop)
            # 记录并保留历史最优（精英保留，避免最优解在迭代中丢失）
            idx = y.argmin()
            if y[idx] < self.best_y:
                self.best_y = y[idx]
                self.best_x = self.pop[idx].copy()
            self.history.append(self.best_y)
            # 遗传三算子
            self.pop = self._select(self.pop, y)
            self.pop = self._crossover(self.pop)
            self.pop = self._mutate(self.pop)
            # 精英回插：把历史最优放回种群，防止退化
            self.pop[0] = self.best_x
        return self.best_x, self.best_y


# =========================================================================
# 第二部分：手写遗传算法 —— TSP 组合优化
# =========================================================================
class GATSP:
    """排列编码遗传算法，求解 TSP（最短巡回路径）。

    参数
    ----
    dist_mat  : 距离矩阵，形状 (N, N)，dist_mat[i, j] 为城市 i 到 j 的距离
    size_pop  : 种群规模
    max_iter  : 迭代代数
    prob_mut  : 变异概率
    """

    def __init__(self, dist_mat, size_pop=100, max_iter=500, prob_mut=0.2):
        self.dist_mat = dist_mat
        self.n = dist_mat.shape[0]
        self.size_pop = size_pop
        self.max_iter = max_iter
        self.prob_mut = prob_mut
        # 每个个体是一条 0..N-1 的随机排列（城市访问顺序）
        self.pop = np.array([np.random.permutation(self.n)
                             for _ in range(size_pop)])
        self.best_route = None
        self.best_len = np.inf
        self.history = []

    def _route_len(self, route):
        """计算一条闭合回路的总长度（末尾回到起点）。"""
        idx_next = np.roll(route, -1)
        return self.dist_mat[route, idx_next].sum()

    def _ox_crossover(self, p1, p2):
        """顺序交叉 OX：保留 p1 一段，其余按 p2 顺序填充，保证合法排列。"""
        a, b = sorted(np.random.choice(self.n, 2, replace=False))
        child = -np.ones(self.n, dtype=int)
        child[a:b] = p1[a:b]
        fill = [c for c in p2 if c not in p1[a:b]]
        k = 0
        for i in range(self.n):
            if child[i] == -1:
                child[i] = fill[k]
                k += 1
        return child

    def _reverse_mutate(self, route):
        """片段翻转变异（2-opt 思想）：随机翻转一段子路径。"""
        a, b = sorted(np.random.choice(self.n, 2, replace=False))
        route[a:b] = route[a:b][::-1]
        return route

    def run(self):
        for _ in range(self.max_iter):
            lengths = np.array([self._route_len(r) for r in self.pop])
            idx = lengths.argmin()
            if lengths[idx] < self.best_len:
                self.best_len = lengths[idx]
                self.best_route = self.pop[idx].copy()
            self.history.append(self.best_len)
            # 锦标赛选择
            new_pop = []
            for _ in range(self.size_pop):
                i, j = np.random.randint(0, self.size_pop, 2)
                winner = self.pop[i] if lengths[i] < lengths[j] else self.pop[j]
                new_pop.append(winner.copy())
            # 交叉 + 变异
            for i in range(0, self.size_pop - 1, 2):
                new_pop[i] = self._ox_crossover(new_pop[i], new_pop[i + 1])
                new_pop[i + 1] = self._ox_crossover(new_pop[i + 1], new_pop[i])
            for i in range(self.size_pop):
                if np.random.rand() < self.prob_mut:
                    new_pop[i] = self._reverse_mutate(new_pop[i])
            self.pop = np.array(new_pop)
            self.pop[0] = self.best_route  # 精英保留
        return self.best_route, self.best_len


# =========================================================================
# 第三部分：scikit-opt 调用版（比赛抢时间用，pip install scikit-opt）
# =========================================================================
def demo_sko_continuous():
    """用 sko.GA 做连续函数优化。"""
    try:
        from sko.GA import GA
    except ImportError:
        print('[跳过] 未安装 scikit-opt，运行 pip install scikit-opt 后可用')
        return
    # 目标：最小化 f(x,y) = x^2 + y^2 （最优在原点，值为 0）
    func = lambda p: p[0] ** 2 + p[1] ** 2
    ga = GA(func=func, n_dim=2, size_pop=50, max_iter=200,
            lb=[-5, -5], ub=[5, 5], precision=1e-7)
    best_x, best_y = ga.run()
    # numpy 2.x 不允许对非 0 维数组直接 float(); 用 np.ravel()[0] 取标量
    print('[sko.GA 连续] 最优解 =', np.round(best_x, 4),
          ' 最优值 =', round(float(np.ravel(best_y)[0]), 6))


def demo_sko_tsp(points):
    """用 sko.GA_TSP 求解 TSP。"""
    try:
        from sko.GA import GA_TSP
        from scipy import spatial
    except ImportError:
        print('[跳过] 未安装 scikit-opt / scipy')
        return None
    dist = spatial.distance.cdist(points, points, metric='euclidean')

    def total_dist(routine):
        n = len(routine)
        return sum(dist[routine[i % n], routine[(i + 1) % n]] for i in range(n))

    ga_tsp = GA_TSP(func=total_dist, n_dim=len(points),
                    size_pop=100, max_iter=500, prob_mut=0.2)
    best_route, best_len = ga_tsp.run()
    print('[sko.GA_TSP] 最短路径长度 =', round(float(np.ravel(best_len)[0]), 4))
    return best_route


# =========================================================================
# 主程序演示
# =========================================================================
if __name__ == '__main__':
    # ---------- 例1：连续函数优化 ----------
    print('=' * 60)
    print('例1  连续函数优化：最小化 f(x,y)=x^2+y^2')
    print('=' * 60)
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   连续优化：目标函数常含来自附件的参数（成本系数、距离等），在 func 内引用：
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   cost = df['成本'].values
    #   func = lambda x: np.sum(cost * x ** 2)     # 目标函数引用附件参数
    #   ga = GAContinuous(func, n_dim=len(cost), lb=0, ub=100, ...)
    #
    #   TSP（例2）：城市坐标或距离矩阵从附件读——
    #   points = df[['x', 'y']].values             # 读城市坐标 (N,2)，再算距离矩阵
    #   # 或直接读现成距离矩阵：
    #   #   dist_mat = pd.read_csv('距离矩阵.csv', encoding='gbk', index_col=0).values
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    ga = GAContinuous(func=lambda x: x[0] ** 2 + x[1] ** 2,
                      n_dim=2, lb=[-5, -5], ub=[5, 5],
                      size_pop=50, max_iter=200)
    bx, by = ga.run()
    print('[手写GA] 最优解 =', np.round(bx, 4), ' 最优值 =', round(by, 6))
    demo_sko_continuous()

    # ---------- 例2：TSP ----------
    print('\n' + '=' * 60)
    print('例2  TSP 组合优化：20 个随机城市的最短巡回')
    print('=' * 60)
    n_city = 20
    points = np.random.rand(n_city, 2) * 100
    dist_mat = np.sqrt(((points[:, None, :] - points[None, :, :]) ** 2).sum(-1))
    ga_tsp = GATSP(dist_mat, size_pop=100, max_iter=500, prob_mut=0.2)
    route, length = ga_tsp.run()
    print('[手写GA_TSP] 最短路径长度 =', round(length, 4))
    demo_sko_tsp(points)

    # ---------- 收敛曲线 + TSP 路线图 ----------
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    axes[0].plot(ga.history)
    axes[0].set_title('连续优化收敛曲线')
    axes[0].set_xlabel('迭代代数')
    axes[0].set_ylabel('目标函数值')
    axes[0].grid(True)

    axes[1].plot(ga_tsp.history, color='orange')
    axes[1].set_title('TSP 收敛曲线')
    axes[1].set_xlabel('迭代代数')
    axes[1].set_ylabel('最短路径长度')
    axes[1].grid(True)

    closed = np.append(route, route[0])
    axes[2].plot(points[closed, 0], points[closed, 1], 'o-')
    axes[2].scatter(points[route[0], 0], points[route[0], 1],
                    c='red', s=120, zorder=5, label='起点')
    axes[2].set_title('GA 求得的 TSP 最优路线')
    axes[2].legend()
    axes[2].grid(True)

    plt.tight_layout()
    plt.savefig('ga_result.png', dpi=150)
    print('\n结果图已保存为 ga_result.png')
    plt.show()
