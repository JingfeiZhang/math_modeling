# -*- coding: utf-8 -*-
"""
================================================================================
微分方程机理模型（ODE Model：Logistic 增长 + 通用参数拟合）
================================================================================
功能：
    面向国赛 C 题中"能写出变化率规律"的机理问题（增长/衰减/资源消耗）：
      1. Logistic 种群增长模型 dN/dt = r*N*(1 - N/K)，含环境承载力 K；
      2. 通用 ODE 求解框架（scipy.integrate.solve_ivp / odeint）；
      3. 参数拟合：用最小二乘从实测数据反推微分方程参数（r, K 等）；
      4. 画"实测点 + 拟合曲线 + 外推预测"对比图。

    机理建模区别于纯数据拟合：它先根据物理/生物/经济规律写出微分方程，
    再用数据标定少量可解释参数，因此外推更可靠、结论更有说服力。

适用竞赛场景：
    - 种群/用户/销量的有限增长（有天花板 K），如"某商品渗透率随时间的 S 形增长"；
    - 资源消耗、药物代谢、放射衰减等指数衰减过程；
    - 已知变化速率与当前状态的关系，需从少量观测反推速率参数并外推。

输入格式：
    - t_data：一维时间点（等距或不等距均可）；
    - y_data：一维对应观测值（与 t_data 等长）。

输出：
    - 拟合得到的参数（如 r, K）、拟合曲线、外推预测值、拟合优度 R^2。

依赖：numpy, scipy, (可选) matplotlib
运行：python 01_微分方程模型.py
================================================================================
"""

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares

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
# 1. Logistic 种群增长模型（带承载力 K）
# ----------------------------------------------------------------------
def logistic_rhs(t, y, r, K):
    """Logistic 微分方程右端：dN/dt = r*N*(1 - N/K)。

    参数含义：
        r: 内禀增长率（越大增长越快）；
        K: 环境承载力/上限（数量最终趋于 K）。
    """
    N = y[0]
    return [r * N * (1.0 - N / K)]


def solve_logistic(t_eval, N0, r, K):
    """给定参数求解 Logistic 模型在 t_eval 上的数值解。"""
    t_span = (float(np.min(t_eval)), float(np.max(t_eval)))
    sol = solve_ivp(logistic_rhs, t_span, [N0], t_eval=t_eval,
                    args=(r, K), method='RK45', rtol=1e-8, atol=1e-8)
    return sol.y[0]


# ----------------------------------------------------------------------
# 2. 通用 ODE 求解框架 + 参数拟合（最小二乘反推参数）
# ----------------------------------------------------------------------
def fit_ode_params(rhs, t_data, y_data, p0, y0=None, bounds=None):
    """通用：用最小二乘从数据反推 ODE 参数。

    参数:
        rhs   : 微分方程右端函数 rhs(t, y, *params)，y 为状态向量(list)。
        t_data: 观测时间点（一维）。
        y_data: 观测值（一维，对应第 0 个状态变量）。
        p0    : 待拟合参数初值，如 [r, K]。
        y0    : 初始状态；None 时用第一个观测值 [y_data[0]]。
        bounds: 参数上下界元组 (lower, upper)，默认全部 (0, +inf)。
    返回:
        dict：params(拟合参数), y_fit(拟合曲线), R2(拟合优度), success。

    调参说明：
        - p0 初值要尽量贴近量纲（K 取观测最大值的 1~2 倍、r 取 0.1~1 常收敛好）；
        - 参数应有明确物理含义且个数尽量少（1~3 个），避免过拟合；
        - 若不收敛，检查数据是否单调/单位是否统一，或换初值 p0。
    """
    t_data = np.asarray(t_data, dtype=float).ravel()
    y_data = np.asarray(y_data, dtype=float).ravel()
    if y0 is None:
        y0 = [y_data[0]]
    if bounds is None:
        bounds = (0.0, np.inf)

    def simulate(params):
        t_span = (float(t_data.min()), float(t_data.max()))
        sol = solve_ivp(rhs, t_span, y0, t_eval=t_data,
                        args=tuple(params), method='RK45',
                        rtol=1e-8, atol=1e-8)
        if not sol.success or sol.y.shape[1] != len(t_data):
            # 求解失败时返回大残差，引导优化器远离该区域
            return np.full_like(y_data, 1e6)
        return sol.y[0]

    def residual(params):
        return simulate(params) - y_data

    res = least_squares(residual, p0, bounds=bounds, method='trf')
    y_fit = simulate(res.x)

    ss_res = float(np.sum((y_data - y_fit) ** 2))
    ss_tot = float(np.sum((y_data - np.mean(y_data)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan

    return {'params': res.x, 'y_fit': y_fit, 'R2': r2,
            'success': bool(res.success), 'y0': y0}


# ----------------------------------------------------------------------
# 演示
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 机理建模需要"时间-数值"两列，务必按时间排序：
    #   df = df.sort_values('时间列')
    #   t_data = df['时间列'].values.astype(float)   # 一维时间（如 0,1,2... 或年份）
    #   y_data = df['数值列'].values.astype(float)   # 一维观测值（数量/浓度/销量等）
    #   # 若时间是年份，建议整体减去起始年份变成 0,1,2...，数值更稳定
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 用"真参数 + 噪声"造一组 S 形增长数据（如某产品用户数，单位万人）
    rng = np.random.default_rng(42)
    r_true, K_true, N0_true = 0.55, 1000.0, 50.0
    t_data = np.arange(0, 15, dtype=float)          # 0~14 期
    y_clean = solve_logistic(t_data, N0_true, r_true, K_true)
    y_data = y_clean * (1 + rng.normal(0, 0.04, size=t_data.shape))  # 加 4% 噪声

    print("########## 微分方程机理模型（Logistic 增长）演示 ##########")
    print("观测点数：%d   （真参数 r=%.2f, K=%.0f 仅用于造数据）"
          % (len(t_data), r_true, K_true))

    # ---- 参数拟合：从数据反推 r, K ----
    # 初值：K 取观测最大值的 1.5 倍，r 取 0.3（常见量级）
    p0 = [0.3, float(np.max(y_data)) * 1.5]
    fit = fit_ode_params(logistic_rhs, t_data, y_data, p0=p0)
    r_hat, K_hat = fit['params']
    print("\n【参数拟合结果】(最小二乘从数据反推微分方程参数)")
    print("  增长率 r = %.4f" % r_hat)
    print("  承载力 K = %.2f" % K_hat)
    print("  拟合优度 R^2 = %.4f   收敛=%s" % (fit['R2'], fit['success']))

    # ---- 用拟合模型向后外推预测 ----
    t_future = np.arange(0, 22, dtype=float)        # 外推到第 21 期
    y_future = solve_logistic(t_future, fit['y0'][0], r_hat, K_hat)
    print("\n【外推预测】第 15~21 期预测值：")
    for tt, yy in zip(t_future[15:], y_future[15:]):
        print("  t=%2d  ->  %.2f" % (tt, yy))

    if _HAS_PLT:
        try:
            plt.figure(figsize=(10, 5))
            plt.scatter(t_data, y_data, c='b', zorder=3, label='实测数据')
            plt.plot(t_future, y_future, 'r-', label='Logistic 拟合+外推')
            plt.axhline(K_hat, color='gray', ls='--', alpha=0.7,
                        label='承载力 K=%.0f' % K_hat)
            plt.axvline(t_data[-1], color='green', ls=':', alpha=0.6,
                        label='预测起点')
            plt.xlabel('时间'); plt.ylabel('数量')
            plt.title('微分方程机理模型：Logistic 增长拟合与预测')
            plt.legend(); plt.grid(alpha=0.3)
            plt.tight_layout()
            plt.savefig('01_微分方程示例.png', dpi=120)
            print("\n[图已保存] 01_微分方程示例.png")
        except Exception as e:
            print("绘图跳过：", e)

    print("\n演示完成。机理建模要点：先按规律写微分方程，再用数据标定少量可解释参数。")
