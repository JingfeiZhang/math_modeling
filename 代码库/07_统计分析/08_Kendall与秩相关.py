# -*- coding: utf-8 -*-
"""
================================================================================
Kendall 与秩相关分析（Kendall's τ / Spearman ρ / Pearson r 三者对比）
================================================================================
功能：
    衡量两个变量的相关性，并对比三种系数的适用场景：
      - Pearson  r ：线性相关，要求近似正态、连续数据，对异常值敏感。
      - Spearman ρ：秩相关，衡量单调关系（非必线性），对异常值稳健。
      - Kendall  τ：基于"和谐/不和谐对"，适合小样本、有序分类、多平局数据，
                     结论最稳健但计算量略大。
    并给出显著性 p 值，判断相关是否统计显著。

适用竞赛场景：
    - C 题里判断指标间相关性/共线性、做特征筛选、验证"某因素与结果是否相关"。
    - 数据是等级/有序、样本小、或有明显异常值时，优先看 Kendall/Spearman 而非 Pearson。

输入格式：
    x, y : 两个等长的一维数值序列（list / numpy 数组 / DataFrame 某列）。

输出：三种相关系数及其 p 值，附适用性说明与散点图。

依赖：numpy, scipy, matplotlib
================================================================================
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')            # 无界面环境安全；本地想弹窗可删这行
import matplotlib.pyplot as plt
from scipy import stats

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


def kendall_tau_manual(x, y):
    """手写 Kendall τ-a：τ = (和谐对数 - 不和谐对数) / 总对数 C(n,2)。
    和谐对：(x_i-x_j) 与 (y_i-y_j) 同号；不和谐：异号。用于理解原理。
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    concordant = discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            s = np.sign(x[i] - x[j]) * np.sign(y[i] - y[j])
            if s > 0:
                concordant += 1
            elif s < 0:
                discordant += 1
            # s==0 为平局，τ-a 不计入
    total = n * (n - 1) / 2
    return (concordant - discordant) / total if total else np.nan


def correlation_report(x, y):
    """计算三种相关系数与 p 值，返回字典。"""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    pear_r, pear_p = stats.pearsonr(x, y)
    spear_r, spear_p = stats.spearmanr(x, y)
    ken_r, ken_p = stats.kendalltau(x, y)   # 带平局修正的 τ-b
    return {
        'Pearson':  (pear_r, pear_p),
        'Spearman': (spear_r, spear_p),
        'Kendall':  (ken_r, ken_p),
        'Kendall手写τa': (kendall_tau_manual(x, y), None),
    }


def plot_relation(x, y, save='kendall_scatter.png'):
    """散点图 + 秩散点图，直观看线性 vs 单调关系。"""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].scatter(x, y, color='#1b9e77', edgecolor='black')
    axes[0].set_title('原始散点（看线性关系）')
    axes[0].set_xlabel('X'); axes[0].set_ylabel('Y'); axes[0].grid(alpha=0.3)
    rx = stats.rankdata(x); ry = stats.rankdata(y)
    axes[1].scatter(rx, ry, color='#d95f02', edgecolor='black')
    axes[1].set_title('秩散点（看单调关系）')
    axes[1].set_xlabel('X 的秩'); axes[1].set_ylabel('Y 的秩'); axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(save, dpi=300)
    plt.close(fig)
    print(f'[已保存] {save}')


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   x = df['指标A'].values     # 第一个变量列
    #   y = df['指标B'].values     # 第二个变量列（与 x 等长）
    #   若要做整张相关矩阵：df[['A','B','C']].corr(method='kendall')
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(单调但非线性关系; 替换为真实数据后可删除)
    rng = np.random.default_rng(0)
    x = np.linspace(1, 10, 30)
    y = np.log(x) + rng.normal(0, 0.15, 30)   # 单调递增、非线性

    rep = correlation_report(x, y)
    print('相关性分析结果（|系数|越接近1相关性越强, p<0.05 为显著）')
    print('=' * 58)
    for name, (r, p) in rep.items():
        p_str = '—' if p is None else f'p={p:.4g} {"显著✔" if p < 0.05 else "不显著"}'
        print(f'{name:16s} 系数={r:+.4f}  {p_str}')
    print('=' * 58)
    print('选用建议：数据近正态且线性→Pearson；有序/有异常值/单调→Spearman；')
    print('          小样本/多平局/等级数据→Kendall（结论最稳健）。')
    plot_relation(x, y)
