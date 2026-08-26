# -*- coding: utf-8 -*-
"""
==============================================================================
01 描述性统计与分布检验
==============================================================================
功能：
    1. 描述性统计：均值、中位数、方差、标准差、极差、四分位数、
       变异系数、偏度(skewness)、峰度(kurtosis)。
    2. 正态性检验：Shapiro-Wilk 检验、Kolmogorov-Smirnov(K-S) 检验、
       D'Agostino 正态性检验、QQ 图。
    3. 分布拟合：对数据拟合常见分布(正态/指数/伽马/对数正态等)，
       用 K-S 检验挑选最优分布。

适用条件 / 使用场景：
    - 建模第一步的数据探索(EDA)，判断数据是否服从正态分布，
      从而决定后续用【参数检验】还是【非参数检验】。
    - 偏度 skew≈0 且峰度 kurt≈0(费雪定义)、且正态性检验 p>0.05 时可认为近似正态。
    - 竞赛场景：任意题目拿到数据后先做描述性统计，
      如 2021A/2022C 题的原始数据清洗与分布判断。

输入格式：
    - 一维数据：np.ndarray 或 pd.Series
    - 多列数据：pd.DataFrame(每列一个变量)

输出：
    - 打印统计量表格、各正态性检验的统计量 + p 值 + α=0.05 下结论
    - 可选：直方图+核密度图、QQ 图、最优分布拟合曲线

依赖库：numpy, pandas, scipy, matplotlib
==============================================================================
"""

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt

# ------------------------- 中文显示配置 -------------------------
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']  # 中文黑体
plt.rcParams['axes.unicode_minus'] = False                        # 正常显示负号

ALPHA = 0.05  # 全局显著性水平

def describe_stats(data, name='变量'):
    """
    计算并打印一维数据的描述性统计量。
    参数:
        data : 一维 array-like
        name : 变量名(用于打印)
    返回:
        dict, 包含各统计量
    """
    x = np.asarray(data, dtype=float)
    x = x[~np.isnan(x)]  # 去除缺失值
    n = len(x)
    mean = np.mean(x)
    std = np.std(x, ddof=1)          # 样本标准差(除以 n-1)
    res = {
        '样本量n': n,
        '均值mean': mean,
        '中位数median': np.median(x),
        '方差var': np.var(x, ddof=1),
        '标准差std': std,
        '最小值min': np.min(x),
        '最大值max': np.max(x),
        '极差range': np.ptp(x),
        '下四分位Q1': np.percentile(x, 25),
        '上四分位Q3': np.percentile(x, 75),
        '四分位距IQR': np.percentile(x, 75) - np.percentile(x, 25),
        '变异系数CV': std / mean if mean != 0 else np.nan,  # 无量纲离散程度
        '偏度skew': stats.skew(x),        # >0 右偏, <0 左偏, ≈0 对称
        '峰度kurt': stats.kurtosis(x),    # 费雪定义, 正态=0; >0 尖峰厚尾
    }
    print('=' * 60)
    print('【描述性统计】变量: %s' % name)
    print('-' * 60)
    for k, v in res.items():
        print('  %-14s : %.4f' % (k, v) if isinstance(v, float) else '  %-14s : %d' % (k, v))
    print('=' * 60)
    return res


def normality_tests(data, name='变量', alpha=ALPHA):
    """
    对一维数据做多种正态性检验。
    原假设 H0: 数据服从正态分布。 p>alpha 则不拒绝 H0(近似正态)。
    包含: Shapiro-Wilk(推荐小样本 n<50)、K-S 检验、D'Agostino K^2。
    返回: pd.DataFrame 汇总结果
    """
    x = np.asarray(data, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    rows = []

    # 1) Shapiro-Wilk: 小样本(3<=n<=5000)最灵敏
    if 3 <= n <= 5000:
        s_stat, s_p = stats.shapiro(x)
        rows.append(['Shapiro-Wilk', s_stat, s_p])

    # 2) K-S 检验: 用样本均值和标准差作为参照正态分布参数
    #    传入冻结分布的 cdf(而非 'norm'+args), 兼容新版 scipy 的参数传递
    ref_norm = stats.norm(loc=np.mean(x), scale=np.std(x, ddof=1))
    ks_stat, ks_p = stats.kstest(x, ref_norm.cdf)
    rows.append(['Kolmogorov-Smirnov', ks_stat, ks_p])

    # 3) D'Agostino & Pearson: 基于偏度和峰度, 需 n>=20
    if n >= 20:
        d_stat, d_p = stats.normaltest(x)
        rows.append(["D'Agostino-K2", d_stat, d_p])

    df = pd.DataFrame(rows, columns=['检验方法', '统计量', 'p值'])
    df['是否正态(α=%.2f)' % alpha] = df['p值'].apply(lambda p: '是' if p > alpha else '否')

    print('\n【正态性检验】变量: %s  (H0: 服从正态分布)' % name)
    print(df.to_string(index=False))
    concl = '数据近似服从正态分布 → 后续可用参数检验' if (df['p值'] > alpha).all() \
        else '至少一种检验拒绝正态 → 谨慎, 建议配合QQ图并考虑非参数检验'
    print('  结论: %s' % concl)
    return df


def qq_plot(data, name='变量', ax=None):
    """绘制 QQ 图: 点接近对角线则近似正态。"""
    x = np.asarray(data, dtype=float)
    x = x[~np.isnan(x)]
    if ax is None:
        fig, ax = plt.subplots(figsize=(5, 5))
    stats.probplot(x, dist='norm', plot=ax)
    ax.set_title('QQ图 - %s' % name)
    return ax


def fit_best_distribution(data, name='变量',
                          candidates=('norm', 'expon', 'gamma', 'lognorm', 'uniform')):
    """
    对数据拟合多个候选分布, 用 K-S 检验统计量选出最优拟合分布。
    K-S 统计量越小、p 值越大, 拟合越好。
    返回: 按拟合优度排序的 DataFrame
    """
    x = np.asarray(data, dtype=float)
    x = x[~np.isnan(x)]
    rows = []
    for dist_name in candidates:
        dist = getattr(stats, dist_name)
        try:
            params = dist.fit(x)                       # 极大似然估计分布参数
            ks_stat, ks_p = stats.kstest(x, dist_name, args=params)
            rows.append([dist_name, ks_stat, ks_p, params])
        except Exception as e:
            print('  分布 %s 拟合失败: %s' % (dist_name, e))
    df = pd.DataFrame(rows, columns=['分布', 'KS统计量', 'p值', '参数'])
    df = df.sort_values('KS统计量').reset_index(drop=True)  # 统计量小者优先
    print('\n【分布拟合】变量: %s  (KS统计量越小拟合越好)' % name)
    print(df[['分布', 'KS统计量', 'p值']].to_string(index=False))
    print('  最优拟合分布: %s' % df.loc[0, '分布'])
    return df


def plot_hist_kde(data, name='变量', ax=None):
    """绘制直方图 + 核密度估计曲线 + 拟合正态曲线。"""
    x = np.asarray(data, dtype=float)
    x = x[~np.isnan(x)]
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(x, bins=20, density=True, alpha=0.6, color='#69b3a2', label='直方图')
    # 核密度估计
    kde = stats.gaussian_kde(x)
    xs = np.linspace(x.min(), x.max(), 200)
    ax.plot(xs, kde(xs), 'r-', lw=2, label='核密度KDE')
    # 拟合正态曲线
    mu, sigma = np.mean(x), np.std(x, ddof=1)
    ax.plot(xs, stats.norm.pdf(xs, mu, sigma), 'b--', lw=2, label='拟合正态')
    ax.set_title('分布图 - %s' % name)
    ax.legend()
    return ax


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   描述统计/正态性检验/分布拟合的输入是一维数值序列，取附件某一列即可：
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   normal_data = df['指标A'].dropna().values      # 取一列做描述统计/正态检验
    #   skewed_data = df['指标B'].dropna().values      # 再取一列对比（如偏态数据）
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    np.random.seed(42)
    normal_data = np.random.normal(loc=50, scale=8, size=200)      # 正态样本
    skewed_data = np.random.exponential(scale=5, size=200)         # 右偏(指数)样本

    print('\n########## 示例1: 近似正态数据 ##########')
    describe_stats(normal_data, name='正态样本')
    normality_tests(normal_data, name='正态样本')
    fit_best_distribution(normal_data, name='正态样本')

    print('\n\n########## 示例2: 右偏(指数)数据 ##########')
    describe_stats(skewed_data, name='偏态样本')
    normality_tests(skewed_data, name='偏态样本')
    fit_best_distribution(skewed_data, name='偏态样本')

    # ============ 可视化 ============
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    plot_hist_kde(normal_data, '正态样本', ax=axes[0, 0])
    qq_plot(normal_data, '正态样本', ax=axes[0, 1])
    plot_hist_kde(skewed_data, '偏态样本', ax=axes[1, 0])
    qq_plot(skewed_data, '偏态样本', ax=axes[1, 1])
    plt.tight_layout()
    plt.savefig('01_分布检验_示例.png', dpi=150, bbox_inches='tight')
    print('\n图已保存: 01_分布检验_示例.png')
    plt.show()


