# -*- coding: utf-8 -*-
"""
==============================================================================
07 Mann-Kendall 趋势检验与突变检验
==============================================================================
功能：
    1. MK 趋势检验(Mann-Kendall Trend Test): 非参数方法, 检验时间序列
       是否存在【单调上升/下降趋势】。输出 Z 统计量、p 值、趋势方向、
       Kendall Tau。
    2. Sen's 斜率估计(Theil-Sen): 稳健估计趋势变化速率。
    3. MK 突变检验(UF-UB 法): 检测序列的【突变点/转折点】发生时间。

适用条件 / 使用场景:
    - 非参数方法, 【不要求数据正态分布】, 对离群值稳健。
    - 要求数据近似独立(存在显著自相关时结论偏乐观, 需预白化处理)。
    - 适用于时间序列: 水文、气象、环境、经济等长期趋势与突变分析。
    - 竞赛场景: 时间序列趋势判断、变化点识别(如温度/流量/浓度随时间变化)。

方法原理:
    - 趋势检验: 统计所有数据对中"后值>前值"与"后值<前值"的差 S,
      标准化为 Z; |Z|>1.96 (α=0.05) 则趋势显著。
    - 突变检验: 正序构造统计量曲线 UF, 逆序构造 UB;
      两曲线在置信区间(±1.96)内的交点即为可能的突变点。

输入格式: 一维时间序列 array-like(按时间先后排列)。
输出: Z、p、趋势方向、Sen斜率、突变点位置, 均带中文结论。
依赖库: numpy, pandas, scipy, matplotlib (纯手写实现, 无需 pymannkendall)
==============================================================================
"""

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

ALPHA = 0.05

def mk_trend_test(data, alpha=ALPHA):
    """
    Mann-Kendall 趋势检验(标准实现, 含并列值校正)。
    H0: 序列无趋势(独立同分布); H1: 存在单调趋势。

    计算:
        S    = Σ_{i<j} sign(x_j - x_i)
        VAR  = [n(n-1)(2n+5) - Σ t_p(t_p-1)(2t_p+5)] / 18   (t_p 为并列组大小)
        Z    = (S-1)/sqrt(VAR) if S>0; (S+1)/sqrt(VAR) if S<0; 0 if S=0
    返回: dict(trend, z, p, S, var_s, tau)
    """
    x = np.asarray(data, dtype=float)
    n = len(x)
    # 计算 S
    s = 0
    for i in range(n - 1):
        s += np.sum(np.sign(x[i + 1:] - x[i]))

    # 方差(考虑并列值 ties)
    unique, counts = np.unique(x, return_counts=True)
    tie_term = np.sum(counts * (counts - 1) * (2 * counts + 5))
    var_s = (n * (n - 1) * (2 * n + 5) - tie_term) / 18.0

    # 连续性校正后的 Z
    if s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0.0

    p = 2 * (1 - stats.norm.cdf(abs(z)))     # 双侧 p 值
    tau = s / (0.5 * n * (n - 1))            # Kendall Tau

    if p < alpha:
        trend = '上升(显著)' if z > 0 else '下降(显著)'
    else:
        trend = '无显著趋势'

    print('=' * 60)
    print('【Mann-Kendall 趋势检验】 H0: 序列无趋势')
    print('  样本量 n = %d' % n)
    print('  S 统计量 = %.1f,  方差 VAR = %.2f' % (s, var_s))
    print('  Z 统计量 = %.4f,  p 值 = %.4g' % (z, p))
    print('  Kendall Tau = %.4f' % tau)
    print('  临界值(α=%.2f): |Z|>%.3f 显著' % (alpha, stats.norm.ppf(1 - alpha / 2)))
    print('  结论: 序列存在【%s】趋势' % trend)
    print('=' * 60)
    return {'trend': trend, 'z': z, 'p': p, 'S': s, 'var_s': var_s, 'tau': tau}


def sens_slope(data):
    """
    Sen's slope(Theil-Sen 斜率): 稳健的趋势速率估计。
    取所有数据对斜率 (x_j-x_i)/(j-i) 的中位数, 对离群值稳健。
    """
    x = np.asarray(data, dtype=float)
    n = len(x)
    slopes = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            slopes.append((x[j] - x[i]) / (j - i))
    slope = np.median(slopes)
    print('【Sen 斜率估计】趋势变化速率 = %.4f / 单位时间' % slope)
    print('  (>0 上升, <0 下降; 表示每个时间步的中位变化量)')
    return slope


def _uf_statistic(data):
    """
    构造 MK 突变检验的标准化统计量序列 UF(正序累积秩)。
    Sk[i] = 第 i 点前面所有点中比它小的个数的累积;
    E[i]  = i(i-1)/4 ,  Var[i] = i(i-1)(2i+5)/72 ;
    UF[i] = (Sk[i]-E[i]) / sqrt(Var[i]) 。
    (注: 此为教科书标准版, 每步重新计数, 修正了部分参考代码累加不重置的问题)
    """
    x = np.asarray(data, dtype=float)
    n = len(x)
    Sk = np.zeros(n)
    UF = np.zeros(n)
    s = 0
    for i in range(1, n):
        # 统计 x[i] 比前面 x[0..i-1] 中多少个大
        s += np.sum(x[i] > x[:i])
        Sk[i] = s
        E = i * (i + 1) / 4.0                       # 均值 (索引从0, 第i点前有i个点)
        Var = i * (i + 1) * (2 * (i + 1) + 5) / 72.0  # 方差
        UF[i] = (Sk[i] - E) / np.sqrt(Var) if Var > 0 else 0.0
    return UF


def mk_mutation_test(data, alpha=ALPHA):
    """
    MK 突变检验(UF-UB 法): 识别序列突变点。
    UFk: 正序统计量; UBk: 逆序统计量(取负后翻转对齐时间轴)。
    UF 与 UB 曲线在置信区间(±临界值)内的交点即为可能突变点。
    返回: dict(UFk, UBk, mutation_points, conf)
    """
    x = np.asarray(data, dtype=float)
    n = len(x)
    UFk = _uf_statistic(x)
    UBk = _uf_statistic(x[::-1])       # 逆序
    UBk = -UBk[::-1]                    # 取负并翻转回时间轴

    conf = stats.norm.ppf(1 - alpha / 2)  # 置信限, α=0.05 → 1.96

    # 找交点: UF-UB 变号处
    diff = UFk - UBk
    all_crossings = []      # 所有交叉点
    mutation_points = []    # 落在置信区间内的可信突变点
    for i in range(1, n):
        if diff[i] * diff[i - 1] < 0:      # 相邻两点异号 → 交叉
            all_crossings.append(i)
            if abs(UFk[i]) < conf:         # 交点在置信区间内更可信
                mutation_points.append(i)

    print('=' * 60)
    print('【Mann-Kendall 突变检验 (UF-UB 法)】')
    print('  置信限(α=%.2f): ±%.3f' % (alpha, conf))
    print('  所有 UF/UB 交叉点(索引): %s' % (all_crossings if all_crossings else '无'))
    if mutation_points:
        print('  落在置信区间内的可信突变点(索引): %s' % mutation_points)
        print('  → 这些时刻序列统计特征发生显著转折')
    elif all_crossings:
        print('  交叉点均落在置信区间外: 通常说明序列以【单调趋势】为主,')
        print('    而非突变(交点位置可作为趋势起始的参考)')
    else:
        print('  未检测到 UF/UB 交叉点')
    print('=' * 60)
    return {'UFk': UFk, 'UBk': UBk, 'mutation_points': mutation_points,
            'all_crossings': all_crossings, 'conf': conf}


def plot_mutation(data, mut_result, ax=None, time_index=None):
    """绘制 UF/UB 曲线 + 置信限 + 突变点标注。"""
    UFk = mut_result['UFk']
    UBk = mut_result['UBk']
    conf = mut_result['conf']
    n = len(UFk)
    t = np.arange(n) if time_index is None else np.asarray(time_index)

    if ax is None:
        fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(t, UFk, 'r-', label='UF (正序)')
    ax.plot(t, UBk, 'b-', label='UB (逆序)')
    ax.axhline(conf, color='gray', ls='--', label='置信限 ±%.2f' % conf)
    ax.axhline(-conf, color='gray', ls='--')
    ax.axhline(0, color='k', lw=0.5)
    for mp in mut_result['mutation_points']:
        ax.axvline(t[mp], color='green', ls=':')
        ax.annotate('突变点', xy=(t[mp], 0), xytext=(t[mp], conf + 0.5),
                    color='green', ha='center',
                    arrowprops=dict(arrowstyle='->', color='green'))
    ax.set_xlabel('时间')
    ax.set_ylabel('统计量 UF/UB')
    ax.set_title('MK 突变检验')
    ax.legend()
    return ax


if __name__ == '__main__':
    np.random.seed(5)
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   MK 检验输入是一维时间序列（按时间先后排列），取附件某一列即可：
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   df = df.sort_values('年份')                # 务必先按时间排好序
    #   series = df['观测值'].dropna().values      # 取出待检验的一维序列
    #   t = np.arange(len(series))                 # 时间轴（画图用）
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    n = 60
    t = np.arange(n)
    # 前30期在均值20附近波动, 第30期起均值突然跳到28 → 典型突变(阶跃)
    series = np.concatenate([
        np.random.normal(20, 2, 30),                 # 突变前
        np.random.normal(28, 2, 30)                  # 突变后(均值阶跃上升)
    ])

    print('\n########## MK 趋势检验 ##########')
    mk_trend_test(series)
    sens_slope(series)

    print('\n########## MK 突变检验 ##########')
    mut = mk_mutation_test(series)

    # 对比: 纯随机无趋势序列
    print('\n########## 对照: 无趋势随机序列 ##########')
    noise = np.random.normal(20, 2, n)
    mk_trend_test(noise)

    # ============ 可视化 ============
    fig, axes = plt.subplots(2, 1, figsize=(10, 9))
    axes[0].plot(t, series, 'o-', color='steelblue', ms=3)
    axes[0].set_title('原始时间序列(前段平稳, 后段上升)')
    axes[0].set_xlabel('时间')
    axes[0].set_ylabel('观测值')
    for mp in mut['mutation_points']:
        axes[0].axvline(mp, color='green', ls=':')
    plot_mutation(series, mut, ax=axes[1])
    plt.tight_layout()
    plt.savefig('07_MK检验_示例.png', dpi=150, bbox_inches='tight')
    print('\n图已保存: 07_MK检验_示例.png')
    plt.show()


