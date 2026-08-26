# -*- coding: utf-8 -*-
"""
粒子群算法（Particle Swarm Optimization, PSO）模板
==========================================================================
功能
    连续函数寻优。给出两种实现：
        (A) 手写实现   —— 含惯性权重 w、学习因子 c1/c2，支持 w 线性递减
        (B) scikit-opt 调用 —— sko.PSO，接口简洁

原理
    模拟鸟群觅食。每个粒子在解空间中飞行，速度受三部分影响：
        v(t+1) = w * v(t)                      # 惯性：保持原有运动趋势
               + c1 * r1 * (pbest - x)          # 认知项：飞向自己历史最优
               + c2 * r2 * (gbest - x)          # 社会项：飞向群体历史最优
        x(t+1) = x(t) + v(t+1)
    - w 大 -> 全局探索强；w 小 -> 局部开发强。常用 w 从 0.9 线性降到 0.4。
    - c1、c2 通常取 1.5~2.0；c1 偏大重个体经验，c2 偏大重群体协作。

输入格式
    目标函数 func(x) -> float，x 为 numpy 向量；给定上下界 lb/ub。

依赖
    numpy, matplotlib（必需）
    scikit-opt（可选）：  pip install scikit-opt

作者：数学建模国赛模板库
"""

import numpy as np
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
np.random.seed(42)


# =========================================================================
# 手写粒子群算法
# =========================================================================
class PSO:
    """标准粒子群算法，用于连续函数最小化。

    参数
    ----
    func     : 目标函数 func(x)->float
    n_dim    : 变量维度
    lb, ub   : 上下界（可标量可数组）
    pop      : 粒子数量
    max_iter : 迭代次数
    w_max/w_min : 惯性权重上下限（线性递减，兼顾前期探索与后期收敛）
    c1, c2   : 认知因子、社会因子
    """

    def __init__(self, func, n_dim, lb, ub, pop=40, max_iter=200,
                 w_max=0.9, w_min=0.4, c1=1.5, c2=1.5):
        self.func = func
        self.n_dim = n_dim
        self.lb = np.array(lb) * np.ones(n_dim)
        self.ub = np.array(ub) * np.ones(n_dim)
        self.pop = pop
        self.max_iter = max_iter
        self.w_max, self.w_min = w_max, w_min
        self.c1, self.c2 = c1, c2
        # 初始化位置与速度
        self.X = np.random.uniform(self.lb, self.ub, (pop, n_dim))
        v_range = self.ub - self.lb
        self.V = np.random.uniform(-v_range, v_range, (pop, n_dim))
        # 个体历史最优 pbest 与群体历史最优 gbest
        self.pbest_x = self.X.copy()
        self.pbest_y = np.array([func(x) for x in self.X])
        gi = self.pbest_y.argmin()
        self.gbest_x = self.pbest_x[gi].copy()
        self.gbest_y = self.pbest_y[gi]
        self.history = []

    def run(self):
        for it in range(self.max_iter):
            # 惯性权重线性递减：前期大以广搜，后期小以精调
            w = self.w_max - (self.w_max - self.w_min) * it / self.max_iter
            r1 = np.random.rand(self.pop, self.n_dim)
            r2 = np.random.rand(self.pop, self.n_dim)
            # 速度更新（惯性 + 认知 + 社会）
            self.V = (w * self.V
                      + self.c1 * r1 * (self.pbest_x - self.X)
                      + self.c2 * r2 * (self.gbest_x - self.X))
            # 位置更新并限制在可行域内
            self.X = np.clip(self.X + self.V, self.lb, self.ub)
            # 评估与更新 pbest / gbest
            y = np.array([self.func(x) for x in self.X])
            improved = y < self.pbest_y
            self.pbest_x[improved] = self.X[improved]
            self.pbest_y[improved] = y[improved]
            gi = self.pbest_y.argmin()
            if self.pbest_y[gi] < self.gbest_y:
                self.gbest_y = self.pbest_y[gi]
                self.gbest_x = self.pbest_x[gi].copy()
            self.history.append(self.gbest_y)
        return self.gbest_x, self.gbest_y


# =========================================================================
# scikit-opt 调用版（pip install scikit-opt）
# =========================================================================
def demo_sko_pso(func, n_dim, lb, ub):
    try:
        from sko.PSO import PSO as SkoPSO
    except ImportError:
        print('[跳过] 未安装 scikit-opt，运行 pip install scikit-opt 后可用')
        return None
    pso = SkoPSO(func=func, n_dim=n_dim, pop=40, max_iter=200,
                 lb=lb, ub=ub, w=0.8, c1=1.5, c2=1.5)
    pso.run()
    # numpy 2.x 不允许对非 0 维数组直接 float(); 用 np.ravel()[0] 取标量
    print('[sko.PSO] 最优解 =', np.round(pso.gbest_x, 4),
          ' 最优值 =', round(float(np.ravel(pso.gbest_y)[0]), 6))
    return pso.gbest_y_hist


# =========================================================================
# 主程序演示
# =========================================================================
if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   PSO 做连续优化时，目标函数里的参数（成本、距离、需求等）常来自附件：
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   coef = df['系数'].values                   # 从附件读出目标函数参数
    #   def obj(x): return np.sum(coef * x ** 2)   # 目标函数引用附件参数
    #   n_dim = len(coef)                          # 变量维度 = 参数个数
    #   lb, ub = [下界] * n_dim, [上界] * n_dim    # 各维取值范围（也可来自附件列）
    #   pso = PSO(obj, n_dim, lb, ub, ...)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 测试函数：Rastrigin，强多峰，全局最优在原点，值为 0，非常考验跳出局部最优能力
    def rastrigin(x):
        return 10 * len(x) + np.sum(x ** 2 - 10 * np.cos(2 * np.pi * x))

    n_dim = 2
    lb, ub = [-5.12, -5.12], [5.12, 5.12]

    print('=' * 60)
    print('连续函数寻优：Rastrigin 函数（全局最优值 = 0，位于原点）')
    print('=' * 60)
    pso = PSO(rastrigin, n_dim, lb, ub, pop=40, max_iter=200,
              w_max=0.9, w_min=0.4, c1=1.5, c2=1.5)
    bx, by = pso.run()
    print('[手写PSO] 最优解 =', np.round(bx, 4), ' 最优值 =', round(by, 6))
    sko_hist = demo_sko_pso(rastrigin, n_dim, lb, ub)

    # 收敛曲线
    plt.figure(figsize=(8, 5))
    plt.plot(pso.history, label='手写 PSO')
    if sko_hist is not None:
        plt.plot(sko_hist, '--', label='sko.PSO')
    plt.title('PSO 收敛曲线（Rastrigin）')
    plt.xlabel('迭代次数')
    plt.ylabel('全局最优目标值')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('pso_result.png', dpi=150)
    print('\n结果图已保存为 pso_result.png')
    plt.show()
