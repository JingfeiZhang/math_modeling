# -*- coding: utf-8 -*-
"""
==============================================================================
02 假设检验 (参数检验 + 非参数检验)
==============================================================================
功能：
    参数检验:
        1. 单样本 t 检验 (样本均值 vs 已知总体均值)
        2. 双样本(独立) t 检验 (两组均值差异, 自动判断方差齐性 → Welch)
        3. 配对 t 检验 (同一对象前后/配对数据)
    非参数检验(不要求正态):
        4. Mann-Whitney U 检验 (独立双样本, 对应独立 t 检验)
        5. Wilcoxon 符号秩检验 (配对样本, 对应配对 t 检验)
    分类数据:
        6. 卡方独立性检验 (列联表, 两分类变量是否独立)
        7. 卡方拟合优度检验 / Fisher 精确检验(2x2 小样本)

参数检验 vs 非参数检验 如何选择:
    - 参数检验(t检验/方差分析): 要求数据近似【正态】; 独立双样本还要求【方差齐性】。
      优点: 正态时功效更高。
    - 非参数检验(Mann-Whitney/Wilcoxon): 不要求正态, 基于秩(排序), 对离群值稳健。
      当样本量小、明显偏态、或正态性检验不通过时使用。
    - 决策流程: 先做正态性检验(见 01 文件) → 正态且方差齐 → 参数检验;
      否则 → 非参数检验。

输入格式:
    一维 array-like(单样本); 两个一维 array(双样本/配对);
    列联表 2D array 或由 pd.crosstab 生成。

输出:
    统计量、p 值、α=0.05 下的中文结论解释。

依赖库: numpy, pandas, scipy
==============================================================================
"""

import numpy as np
import pandas as pd
from scipy import stats

ALPHA = 0.05


def _conclude(p, h1_desc, alpha=ALPHA):
    """根据 p 值给出统一的中文结论。"""
    if p < alpha:
        return '拒绝H0, 在α=%.2f下【显著】: %s' % (alpha, h1_desc)
    return '不能拒绝H0, 在α=%.2f下【不显著】: 无充分证据支持 %s' % (alpha, h1_desc)

def one_sample_ttest(data, popmean, alpha=ALPHA):
    """
    单样本 t 检验: 检验样本均值是否等于已知总体均值 popmean。
    H0: 样本总体均值 = popmean;  H1: 不相等(双侧)。
    前提: 数据近似正态。
    """
    x = np.asarray(data, dtype=float)
    t, p = stats.ttest_1samp(x, popmean)
    print('=' * 60)
    print('【单样本 t 检验】 H0: 均值 = %.4f' % popmean)
    print('  样本均值 = %.4f, n = %d' % (np.mean(x), len(x)))
    print('  t 统计量 = %.4f,  p 值 = %.4g' % (t, p))
    print('  结论: %s' % _conclude(p, '样本均值与 %.4f 存在显著差异' % popmean, alpha))
    print('=' * 60)
    return t, p


def two_sample_ttest(a, b, alpha=ALPHA):
    """
    独立双样本 t 检验: 比较两独立组的均值。
    自动用 Levene 检验判断方差齐性:
        方差齐 → 标准 t 检验; 方差不齐 → Welch t 检验(equal_var=False)。
    前提: 两组数据近似正态。
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    lev_stat, lev_p = stats.levene(a, b)          # H0: 方差相等
    equal_var = lev_p > alpha
    t, p = stats.ttest_ind(a, b, equal_var=equal_var)
    print('=' * 60)
    print('【独立双样本 t 检验】 H0: 两组均值相等')
    print('  组A均值=%.4f(n=%d), 组B均值=%.4f(n=%d)' % (np.mean(a), len(a), np.mean(b), len(b)))
    print('  Levene方差齐性: 统计量=%.4f, p=%.4g → %s' %
          (lev_stat, lev_p, '方差齐(用标准t)' if equal_var else '方差不齐(用Welch t)'))
    print('  t 统计量 = %.4f,  p 值 = %.4g' % (t, p))
    print('  结论: %s' % _conclude(p, '两组均值存在显著差异', alpha))
    print('=' * 60)
    return t, p


def paired_ttest(x, y, alpha=ALPHA):
    """
    配对 t 检验: 同一对象的两次测量(如治疗前后)。
    H0: 配对差值的均值 = 0。 前提: 差值近似正态。
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    t, p = stats.ttest_rel(x, y)
    diff = x - y
    print('=' * 60)
    print('【配对 t 检验】 H0: 配对差值均值 = 0')
    print('  差值均值 = %.4f, n对 = %d' % (np.mean(diff), len(diff)))
    print('  t 统计量 = %.4f,  p 值 = %.4g' % (t, p))
    print('  结论: %s' % _conclude(p, '配对前后存在显著差异', alpha))
    print('=' * 60)
    return t, p


def mann_whitney(a, b, alpha=ALPHA):
    """
    Mann-Whitney U 检验(非参数): 独立双样本, t 检验的非参数替代。
    不要求正态; H0: 两总体分布相同(位置无差异)。
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    u, p = stats.mannwhitneyu(a, b, alternative='two-sided')
    print('=' * 60)
    print('【Mann-Whitney U 检验 (非参数, 独立双样本)】')
    print('  组A中位数=%.4f, 组B中位数=%.4f' % (np.median(a), np.median(b)))
    print('  U 统计量 = %.4f,  p 值 = %.4g' % (u, p))
    print('  结论: %s' % _conclude(p, '两组分布(位置)存在显著差异', alpha))
    print('=' * 60)
    return u, p


def wilcoxon_signed(x, y, alpha=ALPHA):
    """
    Wilcoxon 符号秩检验(非参数): 配对样本, 配对 t 检验的非参数替代。
    不要求正态; H0: 配对差值的分布关于 0 对称(无差异)。
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    w, p = stats.wilcoxon(x, y)
    print('=' * 60)
    print('【Wilcoxon 符号秩检验 (非参数, 配对)】')
    print('  差值中位数 = %.4f' % np.median(x - y))
    print('  W 统计量 = %.4f,  p 值 = %.4g' % (w, p))
    print('  结论: %s' % _conclude(p, '配对前后存在显著差异', alpha))
    print('=' * 60)
    return w, p


def chi2_independence(table, alpha=ALPHA):
    """
    卡方独立性检验: 两个分类变量是否独立。
    输入 table: 列联表(2D array 或 DataFrame)。
    当 2x2 且样本量小(期望频数<5)时自动提示改用 Fisher。
    H0: 两变量相互独立。
    """
    table = np.asarray(table)
    correction = table.shape == (2, 2)   # 2x2 用 Yates 连续性校正
    chi2, p, dof, expected = stats.chi2_contingency(table, correction=correction)
    print('=' * 60)
    print('【卡方独立性检验】 H0: 两分类变量相互独立')
    print('  卡方统计量 = %.4f, 自由度 = %d, p 值 = %.4g' % (chi2, dof, p))
    if (expected < 5).any():
        print('  * 注意: 存在期望频数<5, 若为2x2建议用 Fisher 精确检验')
    print('  结论: %s' % _conclude(p, '两分类变量存在显著关联(不独立)', alpha))
    print('=' * 60)
    return chi2, p, dof, expected


def chi2_goodness(observed, expected=None, alpha=ALPHA):
    """
    卡方拟合优度检验: 观测频数是否符合某理论分布。
    expected 缺省为均匀分布。 H0: 观测符合理论分布。
    """
    observed = np.asarray(observed, dtype=float)
    chi2, p = stats.chisquare(observed, expected)
    print('=' * 60)
    print('【卡方拟合优度检验】 H0: 观测频数符合理论分布')
    print('  卡方统计量 = %.4f,  p 值 = %.4g' % (chi2, p))
    print('  结论: %s' % _conclude(p, '观测分布与理论分布存在显著偏离', alpha))
    print('=' * 60)
    return chi2, p


def fisher_exact_test(table, alpha=ALPHA):
    """Fisher 精确检验: 仅适用于 2x2 列联表, 小样本(期望频数<5)时优于卡方。"""
    table = np.asarray(table)
    odds, p = stats.fisher_exact(table, alternative='two-sided')
    print('=' * 60)
    print('【Fisher 精确检验 (2x2)】')
    print('  优势比 OR = %.4f,  p 值 = %.4g' % (odds, p))
    print('  结论: %s' % _conclude(p, '两变量存在显著关联', alpha))
    print('=' * 60)
    return odds, p


if __name__ == '__main__':
    np.random.seed(0)

    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   假设检验的关键是"按分组列把一列指标拆成几组"再比较：
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   weights = df['重量'].dropna().values          # 单样本：直接取一列
    #   # 独立双样本：按分组列拆成两组（如按'组别'列的 A/B 分组）
    #   group_a = df[df['组别'] == 'A']['指标'].values
    #   group_b = df[df['组别'] == 'B']['指标'].values
    #   # 配对样本：同一对象两次测量，取两列（如治疗前/后）
    #   before = df['治疗前'].values;  after = df['治疗后'].values
    #   # 卡方独立性：两个分类列先做列联表
    #   contingency = pd.crosstab(df['性别'], df['是否购买']).values
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    print('\n########## 参数检验示例 ##########')
    # 单样本: 检验某产品重量均值是否为 100
    weights = np.random.normal(102, 5, 30)
    one_sample_ttest(weights, popmean=100)

    # 独立双样本: 两种工艺的产品强度
    group_a = np.random.normal(50, 6, 40)
    group_b = np.random.normal(54, 6, 40)
    two_sample_ttest(group_a, group_b)

    # 配对: 培训前后成绩
    before = np.random.normal(70, 8, 25)
    after = before + np.random.normal(3, 4, 25)
    paired_ttest(after, before)

    print('\n########## 非参数检验示例(偏态数据) ##########')
    # 偏态数据, 不满足正态假设 → 用非参数
    skew_a = np.random.exponential(5, 30)
    skew_b = np.random.exponential(7, 30)
    mann_whitney(skew_a, skew_b)
    wilcoxon_signed(after, before)

    print('\n########## 分类数据检验示例 ##########')
    # 卡方独立性: 性别 x 是否购买
    contingency = np.array([[30, 20],
                            [15, 35]])
    chi2_independence(contingency)

    # 卡方拟合优度: 骰子是否均匀
    dice = np.array([18, 22, 16, 14, 12, 18])
    chi2_goodness(dice)

    # Fisher 精确检验(小样本 2x2)
    small_table = np.array([[8, 2],
                            [1, 5]])
    fisher_exact_test(small_table)


