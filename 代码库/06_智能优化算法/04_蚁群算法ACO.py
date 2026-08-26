# -*- coding: utf-8 -*-
"""
蚁群算法（Ant Colony Optimization, ACO）模板
==========================================================================
功能
    求解 TSP（旅行商问题）。给出两种实现：
        (A) 手写实现   —— 含信息素重要度 alpha、启发式重要度 beta、挥发系数 rho
        (B) scikit-opt 调用 —— sko.ACA_TSP

原理
    模拟蚂蚁觅食。蚂蚁在城市间移动时，按概率选择下一城市：
        P(i->j) ∝ (信息素 τ_ij)^alpha * (启发式 η_ij)^beta
    其中启发式 η_ij = 1 / 距离_ij（越近越倾向选择）。
    每轮所有蚂蚁走完后更新信息素：
        τ = (1 - rho) * τ + Δτ
    - (1-rho)*τ 表示信息素挥发（避免过早收敛到某条路径）。
    - Δτ 为本轮蚂蚁在走过的边上留下的信息素，越短的路径留下越多。

参数直觉
    - alpha：信息素重要度，大则更依赖历史经验（易早熟）。
    - beta ：启发式重要度，大则更贪心（偏向近邻）。常用 alpha=1, beta=2~5。
    - rho  ：挥发系数，大则遗忘快、探索强；常取 0.1~0.5。

输入格式
    城市坐标 points，形状 (N, 2)；内部自动算距离矩阵。

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
# 手写蚁群算法（解 TSP）
# =========================================================================
class ACOTSP:
    """蚁群算法求解 TSP。

    参数
    ----
    dist_mat : 距离矩阵 (N, N)
    n_ant    : 蚂蚁数量（通常取城市数附近）
    max_iter : 迭代轮数
    alpha    : 信息素重要度
    beta     : 启发式（距离倒数）重要度
    rho      : 信息素挥发系数
    Q        : 信息素强度常数
    """

    def __init__(self, dist_mat, n_ant=None, max_iter=200,
                 alpha=1.0, beta=2.0, rho=0.1, Q=1.0):
        self.dist = dist_mat + 1e-10 * np.eye(dist_mat.shape[0])  # 防止除零
        self.n = dist_mat.shape[0]
        self.n_ant = n_ant or self.n
        self.max_iter = max_iter
        self.alpha, self.beta, self.rho, self.Q = alpha, beta, rho, Q
        self.eta = 1.0 / self.dist          # 启发式信息（距离越短越大）
        self.tau = np.ones((self.n, self.n))  # 信息素矩阵，初始均匀
        self.best_route, self.best_len = None, np.inf
        self.history = []

    def _route_len(self, route):
        return self.dist[route, np.roll(route, -1)].sum()

    def _build_route(self):
        """单只蚂蚁构造一条完整路径。"""
        start = np.random.randint(self.n)
        route = [start]
        allowed = set(range(self.n)) - {start}
        while allowed:
            cur = route[-1]
            allow_list = list(allowed)
            # 转移概率 ∝ τ^alpha * η^beta
            prob = (self.tau[cur, allow_list] ** self.alpha
                    * self.eta[cur, allow_list] ** self.beta)
            prob = prob / prob.sum()
            nxt = np.random.choice(allow_list, p=prob)
            route.append(nxt)
            allowed.remove(nxt)
        return np.array(route)

    def run(self):
        for _ in range(self.max_iter):
            routes = [self._build_route() for _ in range(self.n_ant)]
            lengths = np.array([self._route_len(r) for r in routes])
            # 记录本轮最优
            idx = lengths.argmin()
            if lengths[idx] < self.best_len:
                self.best_len = lengths[idx]
                self.best_route = routes[idx].copy()
            self.history.append(self.best_len)
            # 信息素更新：先挥发，再由每只蚂蚁按 Q/路径长 涂抹
            delta = np.zeros((self.n, self.n))
            for r, L in zip(routes, lengths):
                nxt = np.roll(r, -1)
                delta[r, nxt] += self.Q / L
            self.tau = (1 - self.rho) * self.tau + delta
        return self.best_route, self.best_len


# =========================================================================
# scikit-opt 调用版（pip install scikit-opt）
# =========================================================================
def demo_sko_aca(points):
    # 兼容补丁：scikit-opt 0.6.6 源码用了 numpy 2.0 已删除的 np.int，
    # 在导入 sko 之前补回别名，避免 AttributeError（不修改第三方库文件）。
    if not hasattr(np, 'int'):
        np.int = int
    try:
        from sko.ACA import ACA_TSP
        from scipy import spatial
    except ImportError:
        print('[跳过] 未安装 scikit-opt / scipy')
        return None
    dist = spatial.distance.cdist(points, points, metric='euclidean')
    n = len(points)

    def total_dist(routine):
        return sum(dist[routine[i % n], routine[(i + 1) % n]] for i in range(n))

    aca = ACA_TSP(func=total_dist, n_dim=n, size_pop=n, max_iter=200,
                  distance_matrix=dist, alpha=1, beta=2, rho=0.1)
    best_route, best_len = aca.run()
    print('[sko.ACA_TSP] 最短路径长度 =', round(float(np.ravel(best_len)[0]), 4))
    return best_route


# =========================================================================
# 主程序演示
# =========================================================================
if __name__ == '__main__':
    print('=' * 60)
    print('蚁群算法求解 TSP：20 个随机城市的最短巡回')
    print('=' * 60)
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   ACO 解 TSP/路径问题，城市坐标或距离矩阵从附件读：
    #   import pandas as pd
    #   df = pd.read_csv('附件_城市坐标.csv', encoding='gbk')  # 乱码换 utf-8/gb18030
    #   points = df[['x', 'y']].values             # 城市坐标 (N,2)，下面据此算距离矩阵
    #   # 若附件直接给的是距离/成本矩阵（N×N 方阵），跳过坐标一步直接读：
    #   #   dist_mat = pd.read_csv('距离矩阵.csv', encoding='gbk', index_col=0).values
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    n_city = 20
    points = np.random.rand(n_city, 2) * 100
    dist_mat = np.sqrt(((points[:, None, :] - points[None, :, :]) ** 2).sum(-1))

    aco = ACOTSP(dist_mat, n_ant=n_city, max_iter=200,
                 alpha=1.0, beta=2.0, rho=0.1)
    route, length = aco.run()
    print('[手写ACO] 最短路径长度 =', round(length, 4))
    demo_sko_aca(points)

    # 收敛曲线 + 路线图
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].plot(aco.history)
    axes[0].set_title('ACO 收敛曲线')
    axes[0].set_xlabel('迭代轮数')
    axes[0].set_ylabel('最短路径长度')
    axes[0].grid(True)

    closed = np.append(route, route[0])
    axes[1].plot(points[closed, 0], points[closed, 1], 'o-')
    axes[1].scatter(points[route[0], 0], points[route[0], 1],
                    c='red', s=120, zorder=5, label='起点')
    axes[1].set_title('ACO 求得的 TSP 最优路线')
    axes[1].legend()
    axes[1].grid(True)

    plt.tight_layout()
    plt.savefig('aco_result.png', dpi=150)
    print('\n结果图已保存为 aco_result.png')
    plt.show()
