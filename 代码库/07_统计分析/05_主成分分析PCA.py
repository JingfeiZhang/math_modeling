# -*- coding: utf-8 -*-
"""
==============================================================================
05 主成分分析 PCA (Principal Component Analysis)
==============================================================================
功能：
    1. 数据标准化(PCA 前必须做, 消除量纲影响)。
    2. PCA 降维: 求主成分、特征值、方差解释率、累计方差解释率。
    3. 主成分个数选择: 碎石图(Scree plot) + 累计方差(常取累计≥85%
       或特征值>1 的主成分)。
    4. 载荷分析(loadings): 主成分与原变量的关系, 用于解释主成分含义。
    5. 降维后数据(主成分得分), 可用于后续聚类/回归/综合评价。

适用条件 / 使用场景:
    - 变量较多且存在相关性(多重共线性)时的降维。
    - PCA 前【必须标准化】; 变量间相关性越强, 降维效果越好
      (可先看 Bartlett 球形检验, p<0.05 说明适合降维)。
    - 竞赛场景: 呼应 2022C 题——玻璃有14种化学成分, 用 PCA 降维
      提取综合指标, 减少变量冗余便于分类/分析; 综合评价指标构建。

输入格式: pd.DataFrame 或 2D array(行=样本, 列=变量/指标)。
输出: 方差解释率表、碎石图、载荷矩阵热力图、降维得分。
依赖库: numpy, pandas, scikit-learn, matplotlib, seaborn(可选)
==============================================================================
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

try:
    import seaborn as sns
    _HAS_SNS = True
except ImportError:
    _HAS_SNS = False

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

def standardize(X):
    """z-score 标准化: 每列 (x-均值)/标准差。PCA 前必做。"""
    scaler = StandardScaler()
    return scaler.fit_transform(X), scaler


def run_pca(df, n_components=None, standardize_data=True):
    """
    执行 PCA。
    参数:
        df : DataFrame 或 2D array, 行=样本 列=变量
        n_components : 保留主成分个数; None 表示保留全部(用于先看方差)
        standardize_data : 是否先标准化(强烈建议 True)
    返回:
        dict, 含 pca 对象、方差解释率、载荷、得分等
    """
    if isinstance(df, pd.DataFrame):
        var_names = list(df.columns)
        X = df.values
    else:
        X = np.asarray(df, dtype=float)
        var_names = ['X%d' % (i + 1) for i in range(X.shape[1])]

    if standardize_data:
        X, _ = standardize(X)

    pca = PCA(n_components=n_components)
    scores = pca.fit_transform(X)          # 主成分得分(降维后数据)

    evr = pca.explained_variance_ratio_    # 各主成分方差解释率
    cum_evr = np.cumsum(evr)               # 累计方差解释率
    eigenvalues = pca.explained_variance_  # 特征值

    # 方差解释率表
    k = len(evr)
    pc_names = ['PC%d' % (i + 1) for i in range(k)]
    var_table = pd.DataFrame({
        '特征值': eigenvalues,
        '方差解释率': evr,
        '累计方差解释率': cum_evr
    }, index=pc_names)

    print('=' * 60)
    print('【PCA 方差解释率】(是否标准化=%s)' % standardize_data)
    print(var_table.round(4))
    # 主成分选择建议
    n_kaiser = int(np.sum(eigenvalues > 1))            # Kaiser 准则: 特征值>1
    n_85 = int(np.argmax(cum_evr >= 0.85) + 1)          # 累计≥85%
    print('-' * 60)
    print('  主成分选择建议:')
    print('    Kaiser准则(特征值>1): 建议保留 %d 个主成分' % n_kaiser)
    print('    累计方差≥85%%: 建议保留 %d 个主成分' % n_85)
    print('=' * 60)

    return {
        'pca': pca, 'scores': scores, 'evr': evr, 'cum_evr': cum_evr,
        'eigenvalues': eigenvalues, 'var_table': var_table,
        'var_names': var_names, 'pc_names': pc_names,
        'n_kaiser': n_kaiser, 'n_85': n_85
    }


def loading_matrix(result):
    """
    计算并打印载荷矩阵(载荷 = 特征向量 * sqrt(特征值)),
    反映每个主成分与原始变量的相关性, 用于解释主成分含义。
    """
    pca = result['pca']
    var_names = result['var_names']
    pc_names = result['pc_names']
    # 载荷 = components_.T * sqrt(eigenvalue)
    loadings = pca.components_.T * np.sqrt(pca.explained_variance_)
    load_df = pd.DataFrame(loadings, index=var_names, columns=pc_names)
    print('\n【载荷矩阵 Loadings】(绝对值大者是该主成分的主导变量)')
    print(load_df.round(4))
    return load_df


def scree_plot(result, ax=None):
    """碎石图: 特征值 + 累计方差解释率, 帮助选主成分个数。"""
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 5))
    x = range(1, len(result['eigenvalues']) + 1)
    ax.plot(x, result['eigenvalues'], 'o-', color='steelblue', label='特征值')
    ax.axhline(1, color='red', ls='--', lw=1, label='特征值=1 (Kaiser)')
    ax.set_xlabel('主成分序号')
    ax.set_ylabel('特征值', color='steelblue')
    ax.set_title('碎石图 Scree Plot')
    ax2 = ax.twinx()
    ax2.plot(x, result['cum_evr'] * 100, 's--', color='darkorange',
             label='累计方差%')
    ax2.axhline(85, color='green', ls=':', lw=1)
    ax2.set_ylabel('累计方差解释率(%)', color='darkorange')
    ax.legend(loc='center right')
    return ax


def plot_loadings(load_df, ax=None):
    """载荷矩阵热力图。"""
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 7))
    if _HAS_SNS:
        sns.heatmap(load_df, annot=True, fmt='.2f', cmap='BuPu', ax=ax)
    else:
        im = ax.imshow(load_df.values, cmap='BuPu', aspect='auto')
        ax.set_xticks(range(len(load_df.columns)))
        ax.set_xticklabels(load_df.columns)
        ax.set_yticks(range(len(load_df.index)))
        ax.set_yticklabels(load_df.index)
        plt.colorbar(im, ax=ax)
    ax.set_title('主成分载荷矩阵')
    return ax


if __name__ == '__main__':
    np.random.seed(3)
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   PCA 输入是"行=样本、列=指标"的数值矩阵，取附件的多个数值列即可：
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   data = df[['指标1', '指标2', '指标3', '指标4', '指标5']].dropna()  # 选数值列
    #   # 注意：run_pca 内部已自动标准化(standardize_data=True)，无需手动 z-score
    #   result = run_pca(data, n_components=None, standardize_data=True)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 模拟 8 个指标, 其中若干高度相关(适合降维)
    n = 120
    f1 = np.random.normal(0, 1, n)   # 潜在因子1
    f2 = np.random.normal(0, 1, n)   # 潜在因子2
    data = pd.DataFrame({
        '指标1': f1 + np.random.normal(0, 0.3, n),
        '指标2': f1 + np.random.normal(0, 0.3, n),
        '指标3': f1 + np.random.normal(0, 0.4, n),
        '指标4': f2 + np.random.normal(0, 0.3, n),
        '指标5': f2 + np.random.normal(0, 0.3, n),
        '指标6': f2 + np.random.normal(0, 0.4, n),
        '指标7': 0.5 * f1 + 0.5 * f2 + np.random.normal(0, 0.5, n),
        '指标8': np.random.normal(0, 1, n),   # 噪声指标
    })

    print('\n########## PCA 降维分析 ##########')
    # 第一步: 保留全部主成分, 查看方差解释率决定保留个数
    result = run_pca(data, n_components=None, standardize_data=True)

    # 第二步: 载荷分析
    load_df = loading_matrix(result)

    # 第三步: 按建议保留主成分, 输出降维后数据
    k = result['n_85']
    print('\n按累计方差≥85%% 保留 %d 个主成分, 降维后数据形状: %s' %
          (k, (result['scores'][:, :k]).shape))
    print('前5个样本的主成分得分:')
    print(pd.DataFrame(result['scores'][:, :k],
                       columns=result['pc_names'][:k]).head().round(4))

    # ============ 可视化 ============
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    scree_plot(result, ax=axes[0])
    plot_loadings(load_df.iloc[:, :k], ax=axes[1])
    plt.tight_layout()
    plt.savefig('05_PCA_示例.png', dpi=150, bbox_inches='tight')
    print('\n图已保存: 05_PCA_示例.png')
    plt.show()


