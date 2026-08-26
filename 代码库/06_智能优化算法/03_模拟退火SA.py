# -*- coding: utf-8 -*-
"""
模拟退火算法（Simulated Annealing, SA）模板
==========================================================================
功能
    - 例1：连续函数优化
    - 例2：TSP 组合优化
    每个例子给出两种实现：
        (A) 手写实现   —— 含初温 T0、降温系数 alpha、每温度链长 L
        (B) scikit-opt 调用 —— sko.SA / sko.SA_TSP

原理
    模拟金属退火：高温时分子活跃（大范围搜索），缓慢降温逐渐稳定（收敛）。
    每步产生一个新解，用 Metropolis 准则决定是否接受：
        - 新解更优 -> 一定接受
        - 新解更差 -> 以概率 exp(-Δf / T) 接受（T 越高越容易接受劣解，
          从而能跳出局部最优）
    温度按 T = alpha * T 逐步下降，直到低于终止温度 T_min。

参数直觉
    - 初温 T0：应让初始接受概率接近 1（可由目标值波动幅度估计）。
    - 降温系数 alpha：常取 0.90~0.99，越接近 1 降温越慢、解越好但越慢。
    - 链长 L：每个温度下的迭代次数，越大越充分。

输入格式
    - 连续：func(x)->float，上下界 lb/ub。
    - TSP：距离矩阵 dist_mat，形状 (N, N)。

依赖
    numpy, matplotlib（必需）；scikit-opt（可选）：pip install scikit-opt

作者：数学建模国赛模板库
"""

import numpy as np
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
np.random.seed(42)


# =========================================================================
# 第一部分：手写模拟退火 —— 连续函数优化
# =========================================================================
class SAContinuous:
    """连续变量模拟退火。

    参数
    ----
    func   : 目标函数 func(x)->float
    x0     : 初始解（numpy 向量）
    lb, ub : 上下界
    T0     : 初始温度
    T_min  : 终止温度
    alpha  : 降温系数（0<alpha<1）
    L      : 每个温度下的迭代链长
    """

    def __init__(self, func, x0, lb, ub, T0=100, T_min=1e-3, alpha=0.95, L=100):
        self.func = func
        self.lb = np.array(lb) * np.ones(len(x0))
        self.ub = np.array(ub) * np.ones(len(x0))
        self.T0, self.T_min, self.alpha, self.L = T0, T_min, alpha, L
        self.x = np.array(x0, dtype=float)
        self.y = func(self.x)
        self.best_x, self.best_y = self.x.copy(), self.y
        self.history = []

    def run(self):
        T = self.T0
        while T > self.T_min:
            for _ in range(self.L):
                # 产生新解：在当前解附近扰动，扰动幅度随温度缩放
                step = np.random.randn(len(self.x)) * (self.ub - self.lb) * 0.1
                x_new = np.clip(self.x + step, self.lb, self.ub)
                y_new = self.func(x_new)
                df = y_new - self.y
                # Metropolis 准则
                if df < 0 or np.random.rand() < np.exp(-df / T):
                    self.x, self.y = x_new, y_new
                    if y_new < self.best_y:
                        self.best_x, self.best_y = x_new.copy(), y_new
            self.history.append(self.best_y)
            T *= self.alpha  # 降温
        return self.best_x, self.best_y


# =========================================================================
# 第二部分：手写模拟退火 —— TSP
# =========================================================================
class SATSP:
    """TSP 模拟退火。新解由随机翻转一段子路径产生（2-opt 邻域）。"""

    def __init__(self, dist_mat, T0=1000, T_min=1e-2, alpha=0.98, L=200):
        self.dist_mat = dist_mat
        self.n = dist_mat.shape[0]
        self.T0, self.T_min, self.alpha, self.L = T0, T_min, alpha, L
        self.route = np.random.permutation(self.n)
        self.length = self._route_len(self.route)
        self.best_route, self.best_len = self.route.copy(), self.length
        self.history = []

    def _route_len(self, route):
        return self.dist_mat[route, np.roll(route, -1)].sum()

    def _new_route(self, route):
        a, b = sorted(np.random.choice(self.n, 2, replace=False))
        new = route.copy()
        new[a:b] = new[a:b][::-1]
        return new

    def run(self):
        T = self.T0
        while T > self.T_min:
            for _ in range(self.L):
                new = self._new_route(self.route)
                new_len = self._route_len(new)
                df = new_len - self.length
                if df < 0 or np.random.rand() < np.exp(-df / T):
                    self.route, self.length = new, new_len
                    if new_len < self.best_len:
                        self.best_route, self.best_len = new.copy(), new_len
            self.history.append(self.best_len)
            T *= self.alpha
        return self.best_route, self.best_len


# =========================================================================
# 第三部分：scikit-opt 调用版（pip install scikit-opt）
# =========================================================================
def demo_sko_sa_continuous(func, x0, lb, ub):
    try:
        from sko.SA import SA
    except ImportError:
        print('[跳过] 未安装 scikit-opt')
        return
    sa = SA(func=func, x0=x0, T_max=100, T_min=1e-7, L=100,
            max_stay_counter=150, lb=lb, ub=ub)
    best_x, best_y = sa.run()
    print('[sko.SA 连续] 最优解 =', np.round(best_x, 4),
          ' 最优值 =', round(float(best_y), 6))


def demo_sko_sa_tsp(points):
    try:
        from sko.SA import SA_TSP
        from scipy import spatial
    except ImportError:
        print('[跳过] 未安装 scikit-opt / scipy')
        return None
    dist = spatial.distance.cdist(points, points, metric='euclidean')
    n = len(points)

    def total_dist(routine):
        return sum(dist[routine[i % n], routine[(i + 1) % n]] for i in range(n))

    sa_tsp = SA_TSP(func=total_dist, x0=range(n), T_max=100, T_min=1, L=10 * n)
    best_route, best_len = sa_tsp.run()
    print('[sko.SA_TSP] 最短路径长度 =', round(float(np.ravel(best_len)[0]), 4))
    return best_route


# =========================================================================
# 主程序演示
# =========================================================================
if __name__ == '__main__':
    print('=' * 60)
    print('例1  连续函数优化：最小化 f(x,y)=x^2+y^2')
    print('=' * 60)
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   连续优化：目标函数里的参数（成本、系数等）从附件读入并在 func 内引用：
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   coef = df['系数'].values
    #   func = lambda x: np.sum(coef * x ** 2)     # 目标函数引用附件参数
    #
    #   TSP（例2）：城市坐标/距离矩阵从附件读——
    #   points = df[['x', 'y']].values             # 城市坐标 (N,2)，下面据此算距离矩阵
    #   # 或直接读现成距离矩阵：
    #   #   dist_mat = pd.read_csv('距离矩阵.csv', encoding='gbk', index_col=0).values
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    func = lambda x: x[0] ** 2 + x[1] ** 2
    sa = SAContinuous(func, x0=[4.0, 4.0], lb=[-5, -5], ub=[5, 5],
                      T0=100, T_min=1e-3, alpha=0.95, L=100)
    bx, by = sa.run()
    print('[手写SA] 最优解 =', np.round(bx, 4), ' 最优值 =', round(by, 6))
    demo_sko_sa_continuous(func, [4.0, 4.0], [-5, -5], [5, 5])

    print('\n' + '=' * 60)
    print('例2  TSP 组合优化：20 个随机城市')
    print('=' * 60)
    n_city = 20
    points = np.random.rand(n_city, 2) * 100
    dist_mat = np.sqrt(((points[:, None, :] - points[None, :, :]) ** 2).sum(-1))
    sa_tsp = SATSP(dist_mat, T0=1000, T_min=1e-2, alpha=0.98, L=200)
    route, length = sa_tsp.run()
    print('[手写SA_TSP] 最短路径长度 =', round(length, 4))
    demo_sko_sa_tsp(points)

    # 收敛曲线 + TSP 路线
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    axes[0].plot(sa.history)
    axes[0].set_title('连续优化收敛曲线')
    axes[0].set_xlabel('降温步数')
    axes[0].set_ylabel('目标函数值')
    axes[0].grid(True)

    axes[1].plot(sa_tsp.history, color='orange')
    axes[1].set_title('TSP 收敛曲线')
    axes[1].set_xlabel('降温步数')
    axes[1].set_ylabel('最短路径长度')
    axes[1].grid(True)

    closed = np.append(route, route[0])
    axes[2].plot(points[closed, 0], points[closed, 1], 'o-')
    axes[2].scatter(points[route[0], 0], points[route[0], 1],
                    c='red', s=120, zorder=5, label='起点')
    axes[2].set_title('SA 求得的 TSP 最优路线')
    axes[2].legend()
    axes[2].grid(True)

    plt.tight_layout()
    plt.savefig('sa_result.png', dpi=150)
    print('\n结果图已保存为 sa_result.png')
    plt.show()
