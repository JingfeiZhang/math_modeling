# -*- coding: utf-8 -*-
"""
================================================================================
蒙特卡洛模拟（Monte Carlo Simulation）
================================================================================
功能：
    用大量随机抽样来近似求解难以解析计算的问题。核心思想：用频率估计概率、
    用随机采样的平均近似期望/积分。适用于：数值积分、求 π、随机搜索优化、
    以及"含不确定性参数"的风险模拟与灵敏度分析。

在国赛 C 题中的价值（不确定性处理）：
    2024 C 题（农作物种植）等题目中，未来产量、价格、需求存在随机波动。
    蒙特卡洛可对这些不确定参数按分布反复抽样，评估某个决策方案的期望收益、
    收益分布、风险（如亏损概率、VaR），从而做出稳健决策。这是把"确定性
    优化"升级为"随机/鲁棒优化"的常用手段。

四个模板：
    1) 蒙特卡洛求定积分（含收敛性：误差随样本数 N 以 1/sqrt(N) 下降）
    2) 蒙特卡洛估计 π（单位圆投点法，最经典的演示）
    3) 蒙特卡洛随机搜索求全局最优（无梯度，适合复杂/非光滑目标的粗搜）
    4) 蒙特卡洛风险模拟（不确定收益的期望、分布、亏损概率与 VaR）

依赖：numpy
================================================================================
"""

import numpy as np


def mc_integrate(func, a, b, n=100000, seed=42):
    """蒙特卡洛求一元定积分 ∫_a^b func(x) dx。

    原理：积分 = 区间长度 (b-a) × 被积函数在区间上的平均值；
          用 n 个均匀随机点估计该平均值。
    误差随 n 以 O(1/sqrt(n)) 下降（与维度无关，高维积分优势明显）。
    """
    rng = np.random.default_rng(seed)
    x = rng.uniform(a, b, n)
    fx = func(x)
    integral = (b - a) * np.mean(fx)
    # 标准误差估计（可用于给积分值加置信区间）
    std_err = (b - a) * np.std(fx) / np.sqrt(n)
    return integral, std_err


def mc_estimate_pi(n=1000000, seed=42):
    """投点法估计圆周率 π。

    在单位正方形 [0,1]x[0,1] 内随机撒点，落在 1/4 单位圆内的比例 ≈ π/4，
    故 π ≈ 4 × (圆内点数 / 总点数)。
    """
    rng = np.random.default_rng(seed)
    x = rng.random(n)
    y = rng.random(n)
    inside = (x ** 2 + y ** 2) <= 1.0    # 是否落在 1/4 圆内
    return 4.0 * np.mean(inside)


def mc_optimize(func, bounds, n=200000, mode='min', seed=42):
    """蒙特卡洛随机搜索求全局最优（无需梯度）。

    原理：在可行域内均匀撒 n 个随机点，直接取目标最好的点作为近似最优。
    优点：实现简单、不怕非光滑/多峰；缺点：维度高时效率低（维度灾难），
    适合做粗搜或给梯度类方法(03)/智能算法(06)提供初值。

    参数:
        func   : 目标函数，接受一维数组 x
        bounds : [(lb, ub), ...] 各维取值范围
        mode   : 'min' 最小化 / 'max' 最大化
    返回:
        best_x, best_val
    """
    rng = np.random.default_rng(seed)
    dim = len(bounds)
    lows = np.array([b[0] for b in bounds])
    highs = np.array([b[1] for b in bounds])
    # 一次性生成 n×dim 的随机采样点
    samples = rng.uniform(lows, highs, size=(n, dim))
    vals = np.array([func(x) for x in samples])
    idx = np.argmin(vals) if mode == 'min' else np.argmax(vals)
    return samples[idx], vals[idx]


def mc_risk_simulation(n=100000, seed=42):
    """蒙特卡洛风险模拟：不确定参数下某决策方案的收益分布与风险。

    情景（呼应 C 题不确定性）：某种植/投资方案，收益 = 单价 × 产量 − 成本。
        单价 price ~ 正态分布（市场波动）
        产量 yield ~ 正态分布（天气等因素）
        成本 cost  为固定值
    对不确定参数反复抽样，得到收益的分布，进而评估：
        - 期望收益、收益标准差（波动/风险大小）
        - 亏损概率 P(利润 < 0)
        - VaR（在险价值，如 5% 分位数，代表"最坏 5% 情形下的收益")

    返回:
        dict：期望、标准差、亏损概率、5% 分位 VaR、收益样本
    """
    rng = np.random.default_rng(seed)
    price = rng.normal(loc=10.0, scale=2.0, size=n)     # 单价：均值10，波动2
    yield_ = rng.normal(loc=1000.0, scale=150.0, size=n)  # 产量：均值1000
    cost = 8000.0                                        # 固定成本
    profit = price * yield_ - cost                       # 每次抽样的利润

    return {
        'mean_profit': np.mean(profit),               # 期望收益
        'std_profit': np.std(profit),                 # 收益波动（风险）
        'loss_prob': np.mean(profit < 0),             # 亏损概率
        'VaR_5%': np.percentile(profit, 5),           # 5% 分位在险价值
        'profit_samples': profit,
    }


if __name__ == '__main__':
    print('=' * 60)
    print('模板1：蒙特卡洛求定积分  ∫_0^1 e^(x^2) dx  （无解析原函数）')
    print('=' * 60)
    val, err = mc_integrate(lambda x: np.exp(x ** 2), 0, 1, n=200000)
    print(f'积分近似值 = {val:.6f} ± {err:.6f}（参考值约 1.46265）')

    print('\n' + '=' * 60)
    print('模板2：蒙特卡洛估计 π（收敛性演示）')
    print('=' * 60)
    for n in [1000, 100000, 5000000]:
        pi_hat = mc_estimate_pi(n)
        print(f'  N={n:>8}  ->  π ≈ {pi_hat:.5f}  (误差 {abs(pi_hat-np.pi):.5f})')
    print('样本越多越接近 π=3.14159，误差以 1/sqrt(N) 量级下降。')

    print('\n' + '=' * 60)
    print('模板3：蒙特卡洛随机搜索求最优')
    print('=' * 60)
    # 目标：min f(x,y) = (x-3)^2 + (y+1)^2 + sin(5x)  在 [-5,5]^2 上（多峰）
    def f(v):
        return (v[0] - 3) ** 2 + (v[1] + 1) ** 2 + np.sin(5 * v[0])
    best_x, best_v = mc_optimize(f, [(-5, 5), (-5, 5)], n=300000, mode='min')
    print(f'近似最优解 x = {np.round(best_x, 4)}，最优值 = {best_v:.4f}')
    print('（随机搜索给粗略最优，可作为 03 梯度法或 06 智能算法的初值）')

    print('\n' + '=' * 60)
    print('模板4：蒙特卡洛风险模拟（不确定收益 -> 期望/风险/VaR）')
    print('=' * 60)
    # ========================================================================
    # 👉 用你自己的国赛附件数据：蒙特卡洛的关键是"用附件历史数据估计分布参数"
    #   mc_risk_simulation 内部把单价/产量的均值(loc)、标准差(scale)写死了；
    #   比赛时应先读附件历史数据，估出这些分布参数，再填回函数（或改成参数传入）：
    #   import pandas as pd
    #   df = pd.read_csv('附件_历史价格产量.csv', encoding='gbk')  # 乱码换 utf-8/gb18030
    #   price_mu, price_sigma = df['单价'].mean(), df['单价'].std()   # 单价分布参数
    #   yield_mu, yield_sigma = df['产量'].mean(), df['产量'].std()   # 产量分布参数
    #   # 然后把 mc_risk_simulation 里的 loc/scale 换成上面这些估计值即可
    #   # （区间型参数可用 min/max 估计均匀分布：rng.uniform(low, high, n)）
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(内部分布参数仅供演示，替换为附件估计的参数后可删除本注释)
    r = mc_risk_simulation(n=200000)
    print(f"期望收益     = {r['mean_profit']:.2f}")
    print(f"收益标准差   = {r['std_profit']:.2f}  （越大风险越高）")
    print(f"亏损概率     = {r['loss_prob'] * 100:.2f}%")
    print(f"5% VaR       = {r['VaR_5%']:.2f}  （最坏5%情形下收益不低于此值）")
    print('\n应用：对不同种植/投资方案各跑一次模拟，比较期望收益与风险，')
    print('      选择"高期望、低亏损概率"的稳健方案，即随机规划的核心思路。')
