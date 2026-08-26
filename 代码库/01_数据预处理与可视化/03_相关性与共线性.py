# -*- coding: utf-8 -*-
"""
相关性分析与多重共线性检验模板
==============================================================================
功能：
    回归/评价建模前的变量筛选与诊断。
    一、相关性分析
        1. corr_matrix        Pearson / Spearman 相关系数矩阵
        2. corr_heatmap       相关系数热力图
        3. corr_test          单对变量的相关系数 + 显著性 p 值
    二、多重共线性检验
        1. calc_vif           计算各自变量方差膨胀因子 VIF
        2. plot_vif           VIF 柱状图（含阈值参考线）
        3. drop_high_vif      逐步剔除 VIF 最大的变量直至全部达标

判断标准：
    相关系数 |r| > 0.8 通常提示强相关（可能共线）。
    VIF < 10 可接受，10~100 中等共线，>100 严重共线。

输入格式：
    pandas.DataFrame，列为数值型自变量。

输出：
    相关系数矩阵 / VIF 表；弹出热力图与 VIF 柱状图。

依赖库：numpy, pandas, matplotlib, seaborn, statsmodels
==============================================================================
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from statsmodels.stats.outliers_influence import variance_inflation_factor

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


# ============================ 一、相关性分析 ============================

def corr_matrix(df, method='pearson'):
    """
    计算相关系数矩阵。
    method='pearson' 皮尔逊（线性相关，要求近似正态）；
    method='spearman' 斯皮尔曼（秩相关，衡量单调关系，抗异常、无分布假设）。
    """
    return df.corr(method=method)


def corr_heatmap(df, method='pearson', title='相关系数矩阵', cmap='coolwarm'):
    """绘制相关系数热力图。annot 显示数值，便于快速定位强相关变量对。"""
    corr = df.corr(method=method)
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt='.2f', cmap=cmap,
                square=True, linewidths=0.5, vmin=-1, vmax=1)
    plt.title(title, fontsize=14)
    plt.tight_layout()
    plt.show()
    return corr


def corr_test(x, y, method='pearson'):
    """
    单对变量相关性检验，返回 (相关系数, p值)。
    p < 0.05 说明相关性显著。method='pearson' 或 'spearman'。
    """
    if method == 'pearson':
        r, p = stats.pearsonr(x, y)
    elif method == 'spearman':
        r, p = stats.spearmanr(x, y)
    else:
        raise ValueError("method 只能是 'pearson' / 'spearman'")
    return r, p


# ============================ 二、多重共线性检验 ============================

def calc_vif(df):
    """
    计算各自变量的方差膨胀因子 VIF。
    VIF = 1/(1-R^2)，R^2 为该变量对其余变量回归的判定系数。
    返回按 VIF 降序排列的 DataFrame。
    """
    X = df.values.astype(float)
    vif = [variance_inflation_factor(X, i) for i in range(X.shape[1])]
    res = pd.DataFrame({'变量': df.columns, 'VIF': np.round(vif, 3)})
    return res.sort_values('VIF', ascending=False).reset_index(drop=True)


def plot_vif(df, title='各自变量方差膨胀因子 VIF'):
    """绘制 VIF 柱状图，并标注 10 / 100 两条共线性参考线。"""
    vif_df = calc_vif(df)
    plt.figure(figsize=(9, 6))
    plt.bar(vif_df['变量'], vif_df['VIF'], color='#bf0000', width=0.6)
    plt.axhline(10, color='black', ls=':', lw=1.4)
    plt.axhline(100, color='black', ls=':', lw=1.4)
    plt.text(0, 12, '中等共线性(VIF=10)', color='black', fontsize=11)
    plt.text(0, 102, '严重共线性(VIF=100)', color='black', fontsize=11)
    for i, v in enumerate(vif_df['VIF']):
        plt.text(i, v, round(v, 1), ha='center', va='bottom', fontsize=11)
    plt.xlabel('自变量')
    plt.ylabel('VIF')
    plt.title(title, fontsize=14)
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.show()
    return vif_df


def drop_high_vif(df, thresh=10.0):
    """
    逐步剔除 VIF 最大的变量，直到所有变量 VIF < thresh。
    返回 (保留后的 DataFrame, 被剔除的变量列表)。
    """
    df = df.copy()
    dropped = []
    while df.shape[1] > 1:
        vif_df = calc_vif(df)
        max_vif = vif_df['VIF'].iloc[0]
        if max_vif < thresh:
            break
        drop_var = vif_df['变量'].iloc[0]
        dropped.append((drop_var, round(max_vif, 2)))
        df = df.drop(columns=[drop_var])
    return df, dropped


# ============================ 演示 ============================

if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 只保留要做相关性/共线性诊断的数值型自变量列：
    #   df = df[['广告投入', '曝光量', '气温', '综合指数']]
    #   # corr_test 的单对变量也从 df 取，如 df['广告投入'], df['曝光量']
    #   详见 00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    np.random.seed(2)
    n = 200
    x1 = np.random.normal(0, 1, n)
    x2 = x1 * 0.95 + np.random.normal(0, 0.1, n)   # 与 x1 强相关（制造共线）
    x3 = np.random.normal(0, 1, n)
    x4 = x1 + x3 + np.random.normal(0, 0.2, n)     # 由 x1,x3 线性组合而成
    df = pd.DataFrame({'广告投入': x1, '曝光量': x2, '气温': x3, '综合指数': x4})

    print('=== Pearson 相关系数矩阵 ===')
    print(corr_matrix(df, 'pearson').round(3), '\n')

    r, p = corr_test(df['广告投入'], df['曝光量'])
    print('=== 广告投入 vs 曝光量 相关检验 ===')
    print(f'r={r:.3f}, p={p:.3e}（p<0.05 显著相关）\n')

    print('=== VIF 检验 ===')
    print(calc_vif(df), '\n')

    kept, dropped = drop_high_vif(df, thresh=10)
    print('=== 逐步剔除高共线变量 ===')
    print('剔除:', dropped)
    print('保留:', list(kept.columns))

    # 可视化：热力图 + VIF 柱状图
    corr_heatmap(df, method='pearson')
    plot_vif(df)
