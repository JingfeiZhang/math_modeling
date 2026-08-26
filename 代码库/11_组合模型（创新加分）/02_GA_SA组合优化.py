# -*- coding: utf-8 -*-
"""
================================================================================
遗传算法 + 模拟退火 组合优化（GA + SA Hybrid）
================================================================================
功能：
    把遗传算法(GA)的"全局搜索、种群多样性"与模拟退火(SA)的"局部精修、跳出
    局部最优"组合成两阶段混合优化器：
      1. 阶段一 GA：种群进化(选择+交叉+变异+精英保留)，在整个空间广撒网，
         快速逼近全局最优所在的区域，避免陷入单个局部极小；
      2. 阶段二 SA：以 GA 的最优个体为起点，按温度递减做局部随机扰动搜索，
         以一定概率接受劣解从而跨越小沟壑，把解进一步精修到更优。
    组合动机：GA 后期易早熟、精度有限；SA 收敛依赖初值。两者串联=GA 保证不早熟、
    SA 保证收敛精度，是复杂/非凸函数优化的经典创新组合。纯 numpy 实现，轻量。

适用竞赛场景：
    - 连续函数全局优化、参数标定，尤其多峰、非凸、易早熟收敛的问题；
    - 思路可迁移到路径/调度等组合优化（把编码与邻域算子换成排列即可）。

输入格式：
    - 目标函数 func(x)（默认求最小值）、变量维度、各维取值上下界 bounds。

输出：
    - 最优解 x*、最优目标值 f(x*)、GA 与 SA 两阶段收敛曲线。

依赖：numpy, (可选) matplotlib
运行：python 02_GA_SA组合优化.py
================================================================================
"""

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np

try:
    import matplotlib
    matplotlib.use('Agg')            # 无界面环境安全（测试用；用户本地可删）
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']  # 中文
    plt.rcParams['axes.unicode_minus'] = False                        # 负号
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False


# ----------------------------------------------------------------------
# 阶段一：遗传算法（全局搜索）
# ----------------------------------------------------------------------
def genetic_algorithm(func, bounds, size_pop=60, max_iter=120,
                      prob_cross=0.8, prob_mut=0.15, rng=None):
    """实数编码 GA（最小化 func）。

    参数:
        bounds: 形如 [(lo1,hi1),(lo2,hi2),...] 的各维上下界。
        size_pop: 种群大小(50~200,大则搜索广但慢)。
        max_iter: 进化代数(看收敛曲线是否变平)。
        prob_cross: 交叉概率(0.6~0.9)。
        prob_mut : 变异概率(0.05~0.2,大则防早熟但收敛慢)。
    返回: best_x, best_f, history(每代最优值)。
    """
    rng = rng or np.random.default_rng(0)
    bounds = np.asarray(bounds, dtype=float)
    dim = len(bounds)
    lo, hi = bounds[:, 0], bounds[:, 1]

    pop = rng.uniform(lo, hi, size=(size_pop, dim))       # 初始化种群
    fit = np.array([func(ind) for ind in pop])
    history = []

    for _ in range(max_iter):
        # --- 选择：锦标赛（每次随机挑2个取更优）---
        idx = rng.integers(0, size_pop, size=(size_pop, 2))
        winners = np.where(fit[idx[:, 0]] < fit[idx[:, 1]], idx[:, 0], idx[:, 1])
        parents = pop[winners]

        # --- 交叉：算术交叉 ---
        children = parents.copy()
        for i in range(0, size_pop - 1, 2):
            if rng.random() < prob_cross:
                alpha = rng.random()
                children[i] = alpha * parents[i] + (1 - alpha) * parents[i + 1]
                children[i + 1] = alpha * parents[i + 1] + (1 - alpha) * parents[i]

        # --- 变异：高斯扰动 ---
        mut_mask = rng.random((size_pop, dim)) < prob_mut
        noise = rng.normal(0, (hi - lo) * 0.1, size=(size_pop, dim))
        children = np.where(mut_mask, children + noise, children)
        children = np.clip(children, lo, hi)              # 越界拉回

        child_fit = np.array([func(ind) for ind in children])

        # --- 精英保留：父代最优替换子代最差，防止最优解丢失 ---
        best_i = int(np.argmin(fit))
        worst_j = int(np.argmax(child_fit))
        children[worst_j] = pop[best_i]
        child_fit[worst_j] = fit[best_i]

        pop, fit = children, child_fit
        history.append(float(fit.min()))

    best_i = int(np.argmin(fit))
    return pop[best_i], float(fit[best_i]), history


# ----------------------------------------------------------------------
# 阶段二：模拟退火（局部精修）
# ----------------------------------------------------------------------
def simulated_annealing(func, x0, bounds, T0=1.0, T_min=1e-4,
                        alpha=0.95, L=40, rng=None):
    """从 x0 出发的 SA 局部精修（最小化 func）。

    参数:
        x0 : 起点(用 GA 的最优解, 实现"全局定位+局部精修")。
        T0 : 初始温度(越高越敢接受劣解, 探索更广)。
        T_min: 终止温度。
        alpha: 降温系数(0.90~0.99, 越接近1越慢越精)。
        L  : 每个温度的迭代次数(链长)。
    返回: best_x, best_f, history。
    """
    rng = rng or np.random.default_rng(1)
    bounds = np.asarray(bounds, dtype=float)
    lo, hi = bounds[:, 0], bounds[:, 1]
    scale = (hi - lo)

    x = np.array(x0, dtype=float)
    f = func(x)
    best_x, best_f = x.copy(), f
    history = []
    T = T0
    while T > T_min:
        for _ in range(L):
            # 邻域扰动：步长随温度收缩，温度越低搜索越精细
            x_new = np.clip(x + rng.normal(0, scale * 0.1 * T, size=x.shape), lo, hi)
            f_new = func(x_new)
            df = f_new - f
            # Metropolis 准则：更优必接受；更差按 exp(-df/T) 概率接受
            if df < 0 or rng.random() < np.exp(-df / max(T, 1e-12)):
                x, f = x_new, f_new
                if f < best_f:
                    best_x, best_f = x.copy(), f
        history.append(best_f)
        T *= alpha
    return best_x, best_f, history


# ----------------------------------------------------------------------
# 组合优化器：GA 定位 + SA 精修
# ----------------------------------------------------------------------
def ga_sa_optimize(func, bounds, ga_kw=None, sa_kw=None, seed=42):
    """两阶段混合优化：GA 全局搜索 -> SA 局部精修。"""
    rng = np.random.default_rng(seed)
    ga_kw = ga_kw or {}
    sa_kw = sa_kw or {}
    ga_x, ga_f, ga_hist = genetic_algorithm(func, bounds, rng=rng, **ga_kw)
    sa_x, sa_f, sa_hist = simulated_annealing(func, ga_x, bounds, rng=rng, **sa_kw)
    return {'ga_x': ga_x, 'ga_f': ga_f, 'ga_hist': ga_hist,
            'best_x': sa_x, 'best_f': sa_f, 'sa_hist': sa_hist}


# ----------------------------------------------------------------------
# 演示
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例目标函数】改成你的问题
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   cost = df['成本'].values                        # 附件里的系数读成向量
    #   def func(x):                                    # x 是决策变量向量
    #       return float(np.sum(cost * x))              # 目标(默认最小化)
    #   bounds = [(0, 100)] * len(cost)                 # 每个变量的取值范围
    #   # 求最大值就 return -目标; 有约束可对违反量加大惩罚项
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例目标函数】(仅供演示，替换为上面的真实问题后可删除)
    # Rastrigin 函数：经典多峰非凸，布满局部极小，全局最优在原点 f=0，
    # 单一算法极易陷入局部最优，正好检验 GA+SA 组合的价值。
    def rastrigin(x):
        x = np.asarray(x, dtype=float)
        A = 10.0
        return float(A * len(x) + np.sum(x ** 2 - A * np.cos(2 * np.pi * x)))

    dim = 5
    bounds = [(-5.12, 5.12)] * dim

    print("########## GA + SA 组合优化演示 ##########")
    print("测试函数：%d 维 Rastrigin（多峰非凸，全局最优 f*=0 @ 原点）" % dim)

    res = ga_sa_optimize(rastrigin, bounds,
                         ga_kw=dict(size_pop=80, max_iter=150),
                         sa_kw=dict(T0=2.0, alpha=0.96, L=50))

    print("\n阶段一 GA（全局搜索）最优值   ： %.5f" % res['ga_f'])
    print("阶段二 SA（局部精修）最优值   ： %.5f" % res['best_f'])
    print("组合最优解 x* ≈", np.round(res['best_x'], 4))
    print("SA 相比 GA 进一步降低了 %.5f（精修增益）"
          % (res['ga_f'] - res['best_f']))

    # 对照：只用 GA 不接 SA，说明组合的价值
    print("\n【对照】单独运行 GA vs GA+SA：组合模型通常给出更低(更优)的目标值。")

    if _HAS_PLT:
        try:
            plt.figure(figsize=(10, 5))
            ga_h = res['ga_hist']
            sa_h = res['sa_hist']
            plt.plot(range(len(ga_h)), ga_h, 'b-', label='阶段一 GA 收敛')
            # SA 曲线接在 GA 之后画，直观展示"接力精修"
            x_sa = range(len(ga_h), len(ga_h) + len(sa_h))
            plt.plot(x_sa, sa_h, 'r-', label='阶段二 SA 精修')
            plt.axvline(len(ga_h) - 0.5, color='gray', ls=':', alpha=0.6,
                        label='GA→SA 交接')
            plt.xlabel('迭代'); plt.ylabel('当前最优目标值')
            plt.title('GA + SA 组合优化收敛过程（Rastrigin）')
            plt.legend(); plt.grid(alpha=0.3)
            plt.tight_layout()
            plt.savefig('02_GA_SA示例.png', dpi=120)
            print("\n[图已保存] 02_GA_SA示例.png")
        except Exception as e:
            print("绘图跳过：", e)

    print("\n演示完成。要点：GA 全局定位防早熟，SA 局部精修提精度，串联互补。")
