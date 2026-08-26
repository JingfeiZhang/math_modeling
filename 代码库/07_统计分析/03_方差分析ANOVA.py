# -*- coding: utf-8 -*-
"""
==============================================================================
03 方差分析 ANOVA (Analysis of Variance)
==============================================================================
功能：
    1. 单因素方差分析(One-way ANOVA): 检验一个分类因素的多个水平
       下, 因变量均值是否有显著差异。
    2. 双因素方差分析(Two-way ANOVA): 两个因素及其交互作用的影响。
    3. 前提检验: 方差齐性(Levene 检验)。
    4. 事后多重比较(Post-hoc): Tukey HSD, 找出到底哪两组存在差异。
    5. 非参数替代: Kruskal-Wallis 检验(不满足正态时使用)。

适用条件 / 使用场景：
    - ANOVA 前提: 各组数据【正态】、【方差齐性(方差相等)】、观测独立。
    - 若违背正态/方差齐 → 用 Kruskal-Wallis 非参数检验。
    - 竞赛场景: 比较多种处理/材料/组别的效果差异, 如不同工艺参数
      对产品性能的影响、不同类别样本的指标差异(2022C 玻璃分类相关分析)。

输入格式:
    - 长格式 DataFrame: 一列数值(因变量) + 一/两列分类(因素)。
    - 或直接传入多个分组的一维数组列表。

输出:
    方差分析表(F 统计量、p 值)、方差齐性结论、事后比较表, 均带中文解释。

依赖库: numpy, pandas, scipy, statsmodels, matplotlib
==============================================================================
"""

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.multicomp import pairwise_tukeyhsd

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

ALPHA = 0.05

def levene_test(*groups, alpha=ALPHA):
    """
    方差齐性检验(Levene): ANOVA 的重要前提。
    H0: 各组方差相等。 p>alpha 表示满足方差齐性。
    """
    stat, p = stats.levene(*groups)
    print('【方差齐性检验 Levene】 H0: 各组方差相等')
    print('  统计量 = %.4f,  p 值 = %.4g' % (stat, p))
    if p > alpha:
        print('  结论: p>%.2f, 满足方差齐性, 可进行标准 ANOVA' % alpha)
    else:
        print('  结论: p<%.2f, 方差不齐! 建议用 Welch-ANOVA 或 Kruskal-Wallis' % alpha)
    return stat, p


def one_way_anova(*groups, alpha=ALPHA, group_names=None):
    """
    单因素方差分析。
    输入: 多个一维数组(每个为一组)。
    H0: 各组均值全部相等; H1: 至少有两组均值不同。
    """
    f, p = stats.f_oneway(*groups)
    if group_names is None:
        group_names = ['组%d' % (i + 1) for i in range(len(groups))]
    print('=' * 60)
    print('【单因素方差分析 One-way ANOVA】 H0: 各组均值相等')
    for name, g in zip(group_names, groups):
        print('  %s: 均值=%.4f, n=%d' % (name, np.mean(g), len(g)))
    print('  F 统计量 = %.4f,  p 值 = %.4g' % (f, p))
    if p < alpha:
        print('  结论: 拒绝H0, 在α=%.2f下各组均值存在【显著差异】' % alpha)
        print('        → 建议做事后多重比较(Tukey HSD)确定具体差异组')
    else:
        print('  结论: 不能拒绝H0, 各组均值无显著差异' )
    print('=' * 60)
    return f, p


def _plain_str_cols(df, cols):
    """把分类列统一转成普通 object 字符串。
       新版 pandas 默认给字符串列 StringDtype, patsy/statsmodels 无法解析,
       会报 'Cannot interpret StringDtype as a data type' —— 这里显式降级。"""
    df = df.copy()
    for c in cols:
        df[c] = df[c].astype(object)   # 注意: 不要再 .astype(str), pandas3 会退回 str dtype
    return df


def one_way_anova_df(df, value_col, group_col, alpha=ALPHA):
    """
    基于 DataFrame(长格式)的单因素方差分析, 输出完整方差分析表。
    df: 含数值列 value_col 和 分类列 group_col。
    """
    df = _plain_str_cols(df, [group_col])
    # C() 表示视为分类变量; 列名需为合法标识符(无空格/中文可用 Q())
    model = ols('%s ~ C(%s)' % (value_col, group_col), data=df).fit()
    table = sm.stats.anova_lm(model, typ=2)
    print('=' * 60)
    print('【单因素方差分析表 (statsmodels)】')
    print(table)
    p = table['PR(>F)'].iloc[0]
    print('  结论: %s' % ('各组存在显著差异(p=%.4g<%.2f)' % (p, alpha) if p < alpha
                          else '各组无显著差异(p=%.4g)' % p))
    print('=' * 60)
    return table


def two_way_anova(df, value_col, factor1, factor2, alpha=ALPHA):
    """
    双因素方差分析(含交互作用)。
    模型: value ~ C(factor1) + C(factor2) + C(factor1):C(factor2)
    分别检验: 因素1主效应、因素2主效应、两者交互效应。
    """
    df = _plain_str_cols(df, [factor1, factor2])
    formula = '%s ~ C(%s) + C(%s) + C(%s):C(%s)' % (
        value_col, factor1, factor2, factor1, factor2)
    model = ols(formula, data=df).fit()
    table = sm.stats.anova_lm(model, typ=2)
    print('=' * 60)
    print('【双因素方差分析表 (含交互作用)】')
    print(table)
    print('-' * 60)
    for idx in table.index[:-1]:  # 最后一行是残差 Residual
        p = table.loc[idx, 'PR(>F)']
        eff = '显著' if p < alpha else '不显著'
        print('  效应 %-22s p=%.4g → %s' % (idx, p, eff))
    print('=' * 60)
    return table


def tukey_posthoc(df, value_col, group_col, alpha=ALPHA):
    """
    Tukey HSD 事后多重比较: ANOVA 显著后, 两两比较找出差异组。
    reject=True 表示该两组均值差异显著。
    """
    res = pairwise_tukeyhsd(df[value_col], df[group_col], alpha=alpha)
    print('=' * 60)
    print('【Tukey HSD 事后多重比较】(reject=True 表示两组差异显著)')
    print(res)
    print('=' * 60)
    return res


def kruskal_wallis(*groups, alpha=ALPHA, group_names=None):
    """
    Kruskal-Wallis 检验(非参数): 单因素 ANOVA 的非参数替代。
    不要求正态/方差齐; H0: 各组分布位置相同。
    """
    h, p = stats.kruskal(*groups)
    print('=' * 60)
    print('【Kruskal-Wallis 检验 (非参数, 多组)】 H0: 各组分布相同')
    print('  H 统计量 = %.4f,  p 值 = %.4g' % (h, p))
    print('  结论: %s' % ('各组存在显著差异(p<%.2f)' % alpha if p < alpha
                          else '各组无显著差异'))
    print('=' * 60)
    return h, p


def plot_group_box(df, value_col, group_col, ax=None):
    """绘制各组箱线图, 直观比较分布差异。"""
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 5))
    groups = df.groupby(group_col)[value_col].apply(list)
    labels = [str(k) for k in groups.index]
    # matplotlib 3.9+ 把 boxplot 的 labels 改名为 tick_labels, 做个兼容
    try:
        ax.boxplot(groups.values, tick_labels=labels)
    except TypeError:
        ax.boxplot(groups.values, labels=labels)
    ax.set_xlabel(group_col)
    ax.set_ylabel(value_col)
    ax.set_title('各组箱线图比较')
    return ax


if __name__ == '__main__':
    np.random.seed(1)

    # ============ 示例1: 单因素 ANOVA ============
    # 三种肥料对作物产量的影响
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   ANOVA 要按分组列把因变量拆成多组比较；双因素/事后比较用长格式 DataFrame：
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 单因素：按'肥料'列拆成各组（组数不限）
    #   fert_A = df[df['肥料'] == 'A']['产量'].values
    #   fert_B = df[df['肥料'] == 'B']['产量'].values
    #   fert_C = df[df['肥料'] == 'C']['产量'].values
    #   # 方差分析表/Tukey/双因素直接用长格式 df（一列数值 + 一/两列分类）：
    #   #   one_way_anova_df(df, value_col='产量', group_col='肥料')
    #   #   two_way_anova(df, value_col='株高', factor1='灌溉', factor2='光照')
    #   #   注意 statsmodels 公式列名需为合法标识符，中文列名可先 df.rename 改英文
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    print('\n########## 单因素方差分析 ##########')
    fert_A = np.random.normal(50, 5, 20)
    fert_B = np.random.normal(55, 5, 20)
    fert_C = np.random.normal(52, 5, 20)
    levene_test(fert_A, fert_B, fert_C)
    one_way_anova(fert_A, fert_B, fert_C, group_names=['肥料A', '肥料B', '肥料C'])

    # 构造长格式 DataFrame 做方差分析表 + 事后比较
    df1 = pd.DataFrame({
        'yield_val': np.concatenate([fert_A, fert_B, fert_C]),
        'fertilizer': ['A'] * 20 + ['B'] * 20 + ['C'] * 20
    })
    one_way_anova_df(df1, 'yield_val', 'fertilizer')
    tukey_posthoc(df1, 'yield_val', 'fertilizer')

    # 非参数替代演示
    print('\n########## 非参数替代: Kruskal-Wallis ##########')
    kruskal_wallis(fert_A, fert_B, fert_C, group_names=['肥料A', '肥料B', '肥料C'])

    # ============ 示例2: 双因素 ANOVA ============
    print('\n########## 双因素方差分析 ##########')
    # 因素: 灌溉(water: 高/低) x 光照(sun: 高/低), 因变量: 株高
    rows = []
    base = {('高', '高'): 60, ('高', '低'): 52, ('低', '高'): 50, ('低', '低'): 40}
    for w in ['高', '低']:
        for s in ['高', '低']:
            vals = np.random.normal(base[(w, s)], 4, 15)
            for v in vals:
                rows.append([v, w, s])
    df2 = pd.DataFrame(rows, columns=['height', 'water', 'sun'])
    two_way_anova(df2, 'height', 'water', 'sun')

    # ============ 可视化 ============
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    plot_group_box(df1, 'yield_val', 'fertilizer', ax=axes[0])
    axes[0].set_title('单因素: 不同肥料产量')
    plot_group_box(df2, 'height', 'water', ax=axes[1])
    axes[1].set_title('双因素(按灌溉): 株高')
    plt.tight_layout()
    plt.savefig('03_ANOVA_示例.png', dpi=150, bbox_inches='tight')
    print('\n图已保存: 03_ANOVA_示例.png')
    plt.show()


