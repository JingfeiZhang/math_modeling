# -*- coding: utf-8 -*-
"""
==============================================================================
04 相关分析 (Correlation Analysis)
==============================================================================
功能：
    1. Pearson 相关: 度量两变量的【线性】相关(要求近似正态、连续)。
    2. Spearman 秩相关: 基于秩, 度量【单调】关系(非参数, 稳健)。
    3. Kendall tau 相关: 基于一致对/不一致对, 适合小样本或有序分类。
    4. 偏相关(Partial correlation): 控制其他变量后两变量的净相关。
    5. 相关矩阵 + 显著性检验(p 值矩阵) + 相关热力图。

如何选择相关系数:
    - Pearson: 变量连续、近似正态、关系为线性 → 首选。
    - Spearman: 非正态、有序、或非线性但单调关系 → 稳健替代。
    - Kendall: 样本量小、有较多并列(ties)、有序分类数据。
    - 三者取值均在 [-1, 1], 绝对值越大相关越强; 需结合 p 值判断显著性。

适用场景(竞赛):
    - 特征筛选/多重共线性诊断(建模前判断自变量间相关)。
    - 指标关联分析, 如 2022C 玻璃成分之间、成分与类别的相关性。

输入格式: pd.DataFrame(每列一个数值变量)。
输出: 相关系数矩阵、p 值矩阵、α=0.05 显著性结论、热力图。
依赖库: numpy, pandas, scipy, matplotlib, seaborn(可选)
==============================================================================
"""

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt

try:
    import seaborn as sns
    _HAS_SNS = True
except ImportError:
    _HAS_SNS = False

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

ALPHA = 0.05

def pair_correlation(x, y, method='pearson', alpha=ALPHA):
    """
    计算两变量的相关系数及显著性 p 值。
    method: 'pearson' / 'spearman' / 'kendall'
    H0: 两变量不相关(相关系数=0)。
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if method == 'pearson':
        r, p = stats.pearsonr(x, y)
    elif method == 'spearman':
        r, p = stats.spearmanr(x, y)
    elif method == 'kendall':
        r, p = stats.kendalltau(x, y)
    else:
        raise ValueError('method 必须为 pearson/spearman/kendall')

    strength = _strength_desc(abs(r))
    print('【%s 相关】 r = %.4f (%s), p 值 = %.4g' % (method, r, strength, p))
    sig = '显著相关' if p < alpha else '相关不显著'
    print('  结论: 在α=%.2f下 %s' % (alpha, sig))
    return r, p


def _strength_desc(abs_r):
    """相关强度的经验描述。"""
    if abs_r >= 0.8:
        return '极强相关'
    elif abs_r >= 0.6:
        return '强相关'
    elif abs_r >= 0.4:
        return '中等相关'
    elif abs_r >= 0.2:
        return '弱相关'
    return '极弱/无相关'


def corr_matrix(df, method='pearson'):
    """
    计算相关系数矩阵。method: pearson/spearman/kendall。
    返回: 相关系数 DataFrame。
    """
    corr = df.corr(method=method)
    print('=' * 60)
    print('【%s 相关系数矩阵】' % method)
    print(corr.round(4))
    print('=' * 60)
    return corr


def corr_pvalue_matrix(df, method='pearson', alpha=ALPHA):
    """
    计算相关系数的 p 值矩阵, 标注显著性。
    返回: (相关系数矩阵, p值矩阵)。
    """
    cols = df.columns
    n = len(cols)
    corr = np.ones((n, n))
    pval = np.zeros((n, n))
    func = {'pearson': stats.pearsonr, 'spearman': stats.spearmanr,
            'kendall': stats.kendalltau}[method]
    for i in range(n):
        for j in range(n):
            if i != j:
                r, p = func(df[cols[i]].values, df[cols[j]].values)
                corr[i, j] = r
                pval[i, j] = p
    corr_df = pd.DataFrame(corr, index=cols, columns=cols)
    pval_df = pd.DataFrame(pval, index=cols, columns=cols)
    print('\n【%s 相关 p 值矩阵】(p<%.2f 视为显著)' % (method, alpha))
    print(pval_df.round(4))
    # 显著相关对
    print('  显著相关变量对:')
    found = False
    for i in range(n):
        for j in range(i + 1, n):
            if pval[i, j] < alpha:
                print('    %s -- %s : r=%.4f, p=%.4g' %
                      (cols[i], cols[j], corr[i, j], pval[i, j]))
                found = True
    if not found:
        print('    (无显著相关变量对)')
    return corr_df, pval_df


def partial_correlation(df, x, y, covar):
    """
    偏相关: 控制(剔除)covar 变量后, x 与 y 的净相关。
    做法: 分别对 covar 回归 x、y, 取残差再求 Pearson 相关。
    covar: 单个列名 str 或 列名列表。
    """
    if isinstance(covar, str):
        covar = [covar]
    Z = df[covar].values
    Z = np.column_stack([np.ones(len(Z)), Z])   # 加截距项

    def _residual(v):
        beta, *_ = np.linalg.lstsq(Z, v, rcond=None)
        return v - Z @ beta

    rx = _residual(df[x].values)
    ry = _residual(df[y].values)
    r, p = stats.pearsonr(rx, ry)
    print('【偏相关】控制 %s 后, %s 与 %s: r=%.4f, p=%.4g' %
          (covar, x, y, r, p))
    return r, p


def corr_heatmap(corr, title='相关系数热力图', ax=None, cmap='coolwarm'):
    """绘制相关系数热力图(有 seaborn 用 seaborn, 否则用 matplotlib)。"""
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 6))
    if _HAS_SNS:
        sns.heatmap(corr, annot=True, fmt='.2f', cmap=cmap, center=0,
                    square=True, ax=ax, cbar_kws={'shrink': 0.8})
    else:
        im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1)
        ax.set_xticks(range(len(corr.columns)))
        ax.set_yticks(range(len(corr.index)))
        ax.set_xticklabels(corr.columns, rotation=45, ha='right')
        ax.set_yticklabels(corr.index)
        for i in range(len(corr.index)):
            for j in range(len(corr.columns)):
                ax.text(j, i, '%.2f' % corr.values[i, j],
                        ha='center', va='center', fontsize=8)
        plt.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title(title)
    return ax


if __name__ == '__main__':
    np.random.seed(2)
    n = 100
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   相关分析取附件里多个数值列组成 DataFrame，直接对它求相关矩阵：
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   df = df[['指标1', '指标2', '指标3', '指标4']].dropna()  # 选要分析的数值列
    #   # 之后 corr_matrix(df) / corr_pvalue_matrix(df) / 两列 pair_correlation 均可用
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    x1 = np.random.normal(0, 1, n)
    x2 = 0.8 * x1 + np.random.normal(0, 0.6, n)        # 与 x1 强相关
    x3 = -0.5 * x1 + np.random.normal(0, 1, n)         # 与 x1 中等负相关
    x4 = np.random.normal(0, 1, n)                     # 基本独立
    df = pd.DataFrame({'指标1': x1, '指标2': x2, '指标3': x3, '指标4': x4})

    print('\n########## 两变量相关(三种系数对比) ##########')
    pair_correlation(df['指标1'], df['指标2'], method='pearson')
    pair_correlation(df['指标1'], df['指标2'], method='spearman')
    pair_correlation(df['指标1'], df['指标2'], method='kendall')

    print('\n########## 相关矩阵与显著性 ##########')
    corr_p = corr_matrix(df, method='pearson')
    corr_pvalue_matrix(df, method='pearson')

    corr_s = corr_matrix(df, method='spearman')

    print('\n########## 偏相关 ##########')
    # 控制 指标1 后, 指标2 与 指标3 的净相关
    partial_correlation(df, '指标2', '指标3', covar='指标1')

    # ============ 可视化 ============
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    corr_heatmap(corr_p, 'Pearson 相关热力图', ax=axes[0])
    corr_heatmap(corr_s, 'Spearman 相关热力图', ax=axes[1])
    plt.tight_layout()
    plt.savefig('04_相关分析_示例.png', dpi=150, bbox_inches='tight')
    print('\n图已保存: 04_相关分析_示例.png')
    plt.show()


