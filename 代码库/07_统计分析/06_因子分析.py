# -*- coding: utf-8 -*-
"""
==============================================================================
06 因子分析 (Factor Analysis, FA)
==============================================================================
功能：
    1. 适用性检验: KMO 检验(>0.6 适合) + Bartlett 球形检验(p<0.05 适合)。
    2. 因子个数确定: 特征值>1 / 碎石图 / 累计方差解释率。
    3. 因子提取 + 因子旋转(varimax 方差最大正交旋转, 使载荷更易解释)。
    4. 因子载荷矩阵: 每个因子由哪些原始变量主导。
    5. 因子得分: 用少数公共因子表示样本, 可用于综合评价/排名。

PCA 与因子分析的区别(重要):
    - PCA: 主成分是原始变量的线性组合, 目标是【最大化方差、降维】,
      不假设潜在结构; 主成分 = 变量的加权和。
    - 因子分析: 假设存在少数【潜在公共因子】驱动观测变量,
      观测变量 = 公共因子的线性组合 + 特殊因子(误差), 目标是
      【解释变量间的相关结构、发现潜在维度】; 常配合旋转做因子命名。
    - 一句话: PCA 重在降维压缩, FA 重在解释潜在因子结构。

适用条件:
    - 变量间需有一定相关性(KMO>0.6, Bartlett 显著)才适合做因子分析。
    - 数据建议先标准化。
    - 竞赛场景: 问卷/多指标数据提取潜在维度; 综合评价体系构建。

输入格式: pd.DataFrame(行=样本, 列=变量)。
输出: KMO/Bartlett 结论、因子方差贡献、旋转载荷矩阵、因子得分。
依赖库: numpy, pandas, scipy, statsmodels, matplotlib(均为常用库)。
    因子提取 + 旋转 + 因子得分用成熟库 **statsmodels** 的
    multivariate.factor.Factor(主轴法 + varimax/promax 旋转), 稳定可靠;
    KMO、Bartlett 两项适用性检验主流库无现成合一接口, 用标准公式实现。
    (曾用 factor_analyzer, 但其 0.5.1 与 sklearn>=1.8 的 check_array
     force_all_finite 形参冲突会崩, 且上游未修复, 故改用 statsmodels。)
==============================================================================
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import chi2 as _chi2_dist
from statsmodels.multivariate.factor import Factor

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

try:
    import seaborn as sns
    _HAS_SNS = True
except ImportError:
    _HAS_SNS = False


# ============ 适用性检验(标准公式) ============
def calculate_bartlett_sphericity(df):
    """Bartlett 球形检验。H0: 相关矩阵为单位阵。返回 (卡方, p)。"""
    X = np.asarray(df, dtype=float)
    n, p = X.shape
    R = np.corrcoef(X, rowvar=False)
    det = max(np.linalg.det(R), 1e-12)          # 防 log(0)
    chi_sq = -((n - 1) - (2 * p + 5) / 6) * np.log(det)
    dof = p * (p - 1) / 2
    return chi_sq, _chi2_dist.sf(chi_sq, dof)


def calculate_kmo(df):
    """KMO 取样适当性检验。返回 (各变量KMO数组, 总体KMO)。
       用相关矩阵逆得偏相关: partial_ij = -Rinv_ij/√(Rinv_ii·Rinv_jj)。"""
    R = np.corrcoef(np.asarray(df, dtype=float), rowvar=False)
    Rinv = np.linalg.pinv(R)
    d = np.sqrt(np.outer(np.diag(Rinv), np.diag(Rinv)))
    partial = -Rinv / d
    np.fill_diagonal(partial, 0.0)
    R0 = R.copy(); np.fill_diagonal(R0, 0.0)
    r2_all, p2_all = R0 ** 2, partial ** 2
    kmo_model = r2_all.sum() / (r2_all.sum() + p2_all.sum())
    kmo_var = r2_all.sum(axis=0) / (r2_all.sum(axis=0) + p2_all.sum(axis=0))
    return kmo_var, kmo_model


class _FA:
    """statsmodels.Factor 的轻量包装, 统一本文件用到的接口。
       提取=主轴法(method='pa'), 旋转=varimax(默认)。"""
    def __init__(self, n_factors=2, rotation='varimax'):
        self.n_factors = n_factors
        self.rotation = rotation

    def fit(self, df):
        X = np.asarray(df, dtype=float)
        # Kaiser 准则所需的原始相关矩阵特征值(降序)
        self._corr_eigvals = np.sort(
            np.linalg.eigvalsh(np.corrcoef(X, rowvar=False)))[::-1]
        self._res = Factor(X, n_factor=self.n_factors, method='pa').fit()
        if self.rotation:
            self._res.rotate(self.rotation)
        L = np.asarray(self._res.loadings).copy()
        # 统一符号: 每个因子最大绝对载荷取正, 便于解释与对比
        self._signs = np.ones(L.shape[1])
        for j in range(L.shape[1]):
            if L[np.argmax(np.abs(L[:, j])), j] < 0:
                self._signs[j] = -1
                L[:, j] *= -1
        self.loadings_ = L
        self._X = X
        return self

    def get_eigenvalues(self):
        # 返回原始相关矩阵特征值(供 Kaiser 特征值>1 准则)
        return self._corr_eigvals, self._corr_eigvals

    def get_factor_variance(self):
        ss = np.sum(self.loadings_ ** 2, axis=0)      # 各因子 SS 载荷
        prop = ss / self.loadings_.shape[0]
        return ss, prop, np.cumsum(prop)

    def get_communalities(self):
        return np.sum(self.loadings_ ** 2, axis=1)     # 各变量共同度

    def transform(self, df):
        """因子得分(statsmodels 回归法 factor_scoring), 与载荷同步符号。"""
        sc = np.asarray(self._res.factor_scoring(np.asarray(df, dtype=float)))
        return sc * self._signs      # 与 loadings_ 的符号翻转保持一致

def adequacy_test(df, alpha=0.05):
    """
    因子分析适用性检验。
    - Bartlett 球形检验: H0=相关矩阵为单位阵(变量间不相关)。
      p<alpha 说明变量相关, 适合因子分析。
    - KMO: 取值 0~1, >0.6 适合, >0.8 很适合, <0.5 不适合。
    """
    chi2, p = calculate_bartlett_sphericity(df)
    kmo_all, kmo_model = calculate_kmo(df)
    print('=' * 60)
    print('【因子分析适用性检验】')
    print('  Bartlett 球形检验: 卡方=%.4f, p=%.4g → %s' %
          (chi2, p, '适合(p<%.2f, 变量相关)' % alpha if p < alpha
           else '不适合(变量近似不相关)'))
    print('  KMO 值 = %.4f → %s' %
          (kmo_model, _kmo_desc(kmo_model)))
    suitable = (p < alpha) and (kmo_model > 0.6)
    print('  综合结论: %s进行因子分析' % ('适合' if suitable else '【不建议】'))
    print('=' * 60)
    return chi2, p, kmo_model, suitable


def _kmo_desc(kmo):
    if kmo >= 0.9:
        return '极佳'
    elif kmo >= 0.8:
        return '很适合'
    elif kmo >= 0.7:
        return '适合'
    elif kmo >= 0.6:
        return '尚可'
    return '不适合(建议KMO>0.6)'


def choose_n_factors(df):
    """
    通过特征值确定因子个数(特征值>1 准则)。
    返回: (特征值数组, 建议因子数)
    """
    fa = _FA(n_factors=df.shape[1], rotation=None)
    fa.fit(df)
    ev, v = fa.get_eigenvalues()   # ev=原始特征值
    n_factors = int(np.sum(ev > 1))
    print('\n【因子个数确定】特征值:')
    print('  ', np.round(ev, 4))
    print('  特征值>1 的因子数 = %d (建议因子个数)' % n_factors)
    return ev, n_factors


def run_factor_analysis(df, n_factors, rotation='varimax'):
    """
    执行因子分析。
    参数:
        n_factors : 公共因子个数
        rotation  : 旋转方法, 'varimax'(方差最大正交旋转, 最常用)
                    可选 'promax'(斜交)、None(不旋转)
    返回: dict
    """
    fa = _FA(n_factors=n_factors, rotation=rotation)
    fa.fit(df)

    var_names = list(df.columns)
    factor_names = ['因子%d' % (i + 1) for i in range(n_factors)]

    # 因子方差贡献
    variance = fa.get_factor_variance()  # (方差, 方差比例, 累计比例)
    var_table = pd.DataFrame(
        np.array(variance),
        index=['方差(SS载荷)', '方差解释率', '累计方差解释率'],
        columns=factor_names)
    print('\n【因子方差贡献】(旋转=%s)' % rotation)
    print(var_table.round(4))

    # 载荷矩阵
    loadings = pd.DataFrame(fa.loadings_, index=var_names, columns=factor_names)
    print('\n【旋转后因子载荷矩阵】(绝对值大者为该因子主导变量)')
    print(loadings.round(4))
    # 每个因子的主导变量
    print('  因子解释:')
    for fac in factor_names:
        dominant = loadings[fac].abs().sort_values(ascending=False)
        top = dominant[dominant > 0.5].index.tolist()
        print('    %s 主要由: %s' % (fac, top if top else '(无载荷>0.5变量)'))

    # 因子得分
    scores = fa.transform(df)
    scores_df = pd.DataFrame(scores, columns=factor_names)

    # 共同度(communality): 变量方差被公共因子解释的比例
    communalities = pd.Series(fa.get_communalities(), index=var_names,
                              name='共同度')

    return {'fa': fa, 'loadings': loadings, 'var_table': var_table,
            'scores': scores_df, 'communalities': communalities,
            'factor_names': factor_names}


def composite_score(result, var_table):
    """
    用因子方差解释率作为权重, 计算综合因子得分(常用于综合评价排名)。
    综合得分 = Σ(因子得分 * 该因子方差解释率) / 累计方差解释率
    """
    scores = result['scores']
    ratios = var_table.loc['方差解释率'].values
    weights = ratios / ratios.sum()
    comp = (scores.values * weights).sum(axis=1)
    print('\n【综合因子得分】(按方差解释率加权, 可用于样本排名)')
    print('  权重:', dict(zip(result['factor_names'], np.round(weights, 4))))
    return pd.Series(comp, name='综合得分')


def plot_fa(ev, loadings, ax=None):
    """左: 碎石图; 右: 载荷热力图(传入两个 ax 时)。"""
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 5))
    x = range(1, len(ev) + 1)
    ax.plot(x, ev, 'o-', color='steelblue')
    ax.axhline(1, color='red', ls='--', lw=1, label='特征值=1')
    ax.set_xlabel('因子序号')
    ax.set_ylabel('特征值')
    ax.set_title('碎石图')
    ax.legend()
    return ax


def plot_loadings_heatmap(loadings, ax=None):
    if ax is None:
        fig, ax = plt.subplots(figsize=(5, 7))
    if _HAS_SNS:
        sns.heatmap(loadings, annot=True, fmt='.2f', cmap='BuPu', ax=ax)
    else:
        im = ax.imshow(loadings.values, cmap='BuPu', aspect='auto')
        ax.set_xticks(range(len(loadings.columns)))
        ax.set_xticklabels(loadings.columns)
        ax.set_yticks(range(len(loadings.index)))
        ax.set_yticklabels(loadings.index)
        plt.colorbar(im, ax=ax)
    ax.set_title('因子载荷矩阵')
    return ax


if __name__ == '__main__':
    np.random.seed(4)
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   因子分析输入同样是"行=样本、列=变量"的数值矩阵，取附件多个数值列：
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   data = df[['数学', '物理', '化学', '跑步', '跳远', '引体']].dropna()  # 选数值列
    #   # 先 adequacy_test(data) 看 KMO>0.6 且 Bartlett p<0.05 才适合做因子分析
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 两个潜在公共因子驱动 6 个观测变量
    n = 150
    factor1 = np.random.normal(0, 1, n)   # 潜在因子1(如"学术能力")
    factor2 = np.random.normal(0, 1, n)   # 潜在因子2(如"体能")
    data = pd.DataFrame({
        '数学': factor1 + np.random.normal(0, 0.4, n),
        '物理': factor1 + np.random.normal(0, 0.4, n),
        '化学': factor1 + np.random.normal(0, 0.5, n),
        '跑步': factor2 + np.random.normal(0, 0.4, n),
        '跳远': factor2 + np.random.normal(0, 0.4, n),
        '引体': factor2 + np.random.normal(0, 0.5, n),
    })

    print('\n########## 因子分析流程 ##########')
    # 第一步: 适用性检验
    adequacy_test(data)

    # 第二步: 确定因子个数
    ev, n_factors = choose_n_factors(data)

    # 第三步: 因子分析 + varimax 旋转
    result = run_factor_analysis(data, n_factors=n_factors, rotation='varimax')

    print('\n【各变量共同度】')
    print(result['communalities'].round(4))

    # 第四步: 综合得分与排名
    comp = composite_score(result, result['var_table'])
    print('  前5名样本(综合得分):')
    print(comp.sort_values(ascending=False).head().round(4))

    # ============ 可视化 ============
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    plot_fa(ev, result['loadings'], ax=axes[0])
    plot_loadings_heatmap(result['loadings'], ax=axes[1])
    plt.tight_layout()
    plt.savefig('06_因子分析_示例.png', dpi=150, bbox_inches='tight')
    print('\n图已保存: 06_因子分析_示例.png')
    plt.show()


