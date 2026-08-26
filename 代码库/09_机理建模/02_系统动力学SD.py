# -*- coding: utf-8 -*-
"""
================================================================================
系统动力学 SD（System Dynamics：SIR 传染病三仓室模型）
================================================================================
功能：
    用系统动力学"存量-流量"思想搭建 SIR 三仓室传染病模型并数值求解：
      - 存量(Stock)：S 易感者、I 感染者、R 康复者（随时间累积的量）；
      - 流量(Flow)：S→I 的感染流、I→R 的康复流（改变存量的速率）；
      - 用 odeint 求解常微分方程组，观察疫情随时间演化。

    系统动力学的核心：把复杂系统抽象成若干"存量"（水池）和连接它们的
    "流量"（水管），流量由存量和参数（反馈回路）决定，从而刻画系统的
    动态行为与拐点。SIR 是最经典的入门范例。

适用竞赛场景：
    - 传播/扩散类：疫情、谣言、新产品/新技术的市场渗透；
    - 存量系统：库存-销售-补货、人口结构、水库蓄水、资金池流动；
    - 需要分析"某参数变化如何改变系统长期走势与峰值"的问题。

输入格式：
    - 初始存量 S0, I0, R0（人数）；
    - 参数 beta（接触/传染率）、gamma（恢复率）；
    - 时间网格 t。

输出：
    - S/I/R 三条随时间变化曲线、感染峰值及其出现时间、基本再生数 R0。

依赖：numpy, scipy, (可选) matplotlib
运行：python 02_系统动力学SD.py
================================================================================
"""

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np
from scipy.integrate import odeint

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
# SIR 存量-流量模型
# ----------------------------------------------------------------------
def sir_model(y, t, beta, gamma):
    """SIR 三仓室微分方程组（存量-流量表示）。

    存量 y = [S, I, R]，总人数 N = S + I + R（本模型 N 守恒）。
    参数含义：
        beta  接触率/传染率：一个感染者单位时间有效传染的比例强度。
              beta 越大传播越快、峰值越高、来得越早。
        gamma 恢复率：单位时间内康复(移出)的比例；平均患病期 = 1/gamma。
              gamma 越大病程越短、疫情越快平息。
    流量：
        感染流 S→I = beta*S*I/N ；康复流 I→R = gamma*I 。
    """
    S, I, R = y
    N = S + I + R
    infect_flow = beta * S * I / N     # 感染流（存量 S 减少、I 增加）
    recover_flow = gamma * I           # 康复流（存量 I 减少、R 增加）
    dSdt = -infect_flow
    dIdt = infect_flow - recover_flow
    dRdt = recover_flow
    return [dSdt, dIdt, dRdt]


def simulate_sir(S0, I0, R0, beta, gamma, t):
    """求解 SIR 模型，返回 S, I, R 三条曲线及关键指标。"""
    y0 = [float(S0), float(I0), float(R0)]
    sol = odeint(sir_model, y0, t, args=(beta, gamma))
    S, I, R = sol[:, 0], sol[:, 1], sol[:, 2]

    R0_num = beta / gamma                       # 基本再生数
    peak_idx = int(np.argmax(I))
    peak_I = float(I[peak_idx])
    peak_t = float(t[peak_idx])
    return {'S': S, 'I': I, 'R': R,
            'R0': R0_num, 'peak_I': peak_I, 'peak_t': peak_t}


# ----------------------------------------------------------------------
# 演示
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 系统动力学一般不是直接"读一列数据",而是用附件确定:
    #   #   (1) 初始存量: 如 S0=总人口-初始感染, I0=首日确诊, R0=0
    #   #   (2) 用实测感染曲线拟合参数 beta,gamma(可借 01_微分方程模型.py 的
    #   #       fit_ode_params 思路,把 sir_model 作为 rhs 反推参数)
    #   N = df['总人口'].iloc[0]; I0 = df['初始感染'].iloc[0]
    #   S0, R0 = N - I0, 0
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 一个 10000 人的封闭社区，初始 5 人感染
    N = 10000
    I0, R0 = 5, 0
    S0 = N - I0 - R0
    beta = 0.35          # 接触率：可调，↑则传播更猛
    gamma = 0.1          # 恢复率：平均患病期 = 1/gamma = 10 天
    t = np.linspace(0, 160, 161)     # 模拟 160 天

    print("########## 系统动力学 SD：SIR 传染病模型演示 ##########")
    print("存量初值：S0=%d, I0=%d, R0=%d  (总人数 N=%d)" % (S0, I0, R0, N))
    print("流量参数：接触率 beta=%.3f, 恢复率 gamma=%.3f (平均病程 %.0f 天)"
          % (beta, gamma, 1.0 / gamma))

    res = simulate_sir(S0, I0, R0, beta, gamma, t)
    print("\n基本再生数 R0 = beta/gamma = %.2f  (%s)"
          % (res['R0'], '>1 会爆发流行' if res['R0'] > 1 else '<=1 疫情消退'))
    print("感染高峰：第 %.0f 天，同时感染约 %d 人"
          % (res['peak_t'], round(res['peak_I'])))
    print("最终累计康复(经历过感染) ≈ %d 人" % round(res['R'][-1]))

    print("\n【前 10 天存量演化】")
    for i in range(10):
        print("  第%2d天：S=%5d  I=%4d  R=%4d"
              % (t[i], round(res['S'][i]), round(res['I'][i]), round(res['R'][i])))

    # 演示参数敏感性：换一个更大的接触率看峰值变化
    res2 = simulate_sir(S0, I0, R0, beta=0.5, gamma=gamma, t=t)
    print("\n【参数敏感性】接触率 beta 0.35 -> 0.50：")
    print("  感染峰值 %d -> %d 人；峰值出现 第%.0f天 -> 第%.0f天"
          % (round(res['peak_I']), round(res2['peak_I']),
             res['peak_t'], res2['peak_t']))

    if _HAS_PLT:
        try:
            plt.figure(figsize=(10, 5))
            plt.plot(t, res['S'], 'b-', label='易感者 S')
            plt.plot(t, res['I'], 'r-', label='感染者 I')
            plt.plot(t, res['R'], 'g-', label='康复者 R')
            plt.axvline(res['peak_t'], color='red', ls=':', alpha=0.6,
                        label='感染高峰 第%.0f天' % res['peak_t'])
            plt.xlabel('时间（天）'); plt.ylabel('人数')
            plt.title('系统动力学 SIR 模型（beta=%.2f, gamma=%.2f, R0=%.2f）'
                      % (beta, gamma, res['R0']))
            plt.legend(); plt.grid(alpha=0.3)
            plt.tight_layout()
            plt.savefig('02_系统动力学SIR示例.png', dpi=120)
            print("\n[图已保存] 02_系统动力学SIR示例.png")
        except Exception as e:
            print("绘图跳过：", e)

    print("\n演示完成。SD 建模要点：先画存量-流量图，再把每条流量写成微分方程求解。")
