# -*- coding: utf-8 -*-
"""
竞赛级图表集（04_常用可视化模板.py 的进阶补充）
==============================================================================
功能：
    收录数学建模论文里"能加分、显专业"的进阶图表，04 里没有的都在这。
    每种封装成独立函数，中文标签、统一配色、存 PNG，复制即用。
        1. plot_waterfall     瀑布图（增减分解：如利润构成、贡献度）
        2. plot_pareto        帕累托图（80/20 分析：主次因素排序）
        3. plot_surface3d     3D 曲面图（响应曲面、双参数灵敏度）
        4. plot_scatter3d     3D 散点图（三变量关系/聚类）
        5. plot_violin        小提琴图（分布形状对比，优于箱线图）
        6. plot_bubble        气泡图（三维信息：x,y + 大小）
        7. plot_scatter_matrix 矩阵散点图（多变量两两关系总览）
        8. plot_stacked_bar   堆叠/百分比堆叠柱状图（构成分析）
        9. plot_kde           核密度估计图（平滑分布）
       10. plot_contour       等高线图（场分布/等值线）

适用竞赛场景：
    - 灵敏度分析用 3D 曲面/等高线；结果构成用瀑布/堆叠；主因分析用帕累托
    - 分布对比用小提琴/KDE；多指标关系总览用矩阵散点/气泡

输出：每个函数把图存成 PNG（不用 plt.show，适配无界面测试）。

依赖：numpy, pandas, matplotlib（3D 用 mpl_toolkits，随 matplotlib 自带）
==============================================================================
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')            # 无界面环境安全；本地想弹窗可删这行
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  注册 3d 投影

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# 论文级配色（对色盲友好，打印也清晰）
COLORS = ['#1b9e77', '#d95f02', '#7570b3', '#e7298a', '#66a61e', '#e6ab02']


def plot_waterfall(labels, values, title='瀑布图', ylabel='数值', save='waterfall.png'):
    """瀑布图：展示从起点经若干增减到终点的累积过程。
    labels: 各步骤名称（列表）；values: 各步骤的增减量（正=增，负=减）。
    末尾自动加一根"合计"总柱。适合利润构成、成本分解、贡献度拆解。
    """
    values = np.asarray(values, dtype=float)
    cum = np.concatenate([[0], np.cumsum(values)])   # 每根柱的起始高度
    fig, ax = plt.subplots(figsize=(9, 5))
    for i, v in enumerate(values):
        color = COLORS[4] if v >= 0 else COLORS[1]   # 增绿 减橙
        ax.bar(i, v, bottom=cum[i], color=color, edgecolor='black', width=0.6)
        ax.text(i, cum[i] + v / 2, f'{v:+.1f}', ha='center', va='center', fontsize=9)
    # 合计柱
    total = cum[-1]
    ax.bar(len(values), total, color=COLORS[2], edgecolor='black', width=0.6)
    ax.text(len(values), total / 2, f'{total:.1f}', ha='center', va='center',
            fontsize=9, color='white')
    ax.set_xticks(range(len(values) + 1))
    ax.set_xticklabels(list(labels) + ['合计'], rotation=20)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(save, dpi=300)
    plt.close(fig)
    print(f'[已保存] {save}')


def plot_pareto(labels, values, title='帕累托图', save='pareto.png'):
    """帕累托图：柱状（各因素频数，降序）+ 折线（累计百分比），标 80% 线。
    用于找"关键少数"（占 80% 影响的少数因素）。labels/values 一一对应。
    """
    order = np.argsort(values)[::-1]
    labels = np.asarray(labels)[order]
    values = np.asarray(values, dtype=float)[order]
    cum_pct = np.cumsum(values) / values.sum() * 100

    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.bar(range(len(values)), values, color=COLORS[0], edgecolor='black')
    ax1.set_ylabel('频数/数值', color=COLORS[0])
    ax1.set_xticks(range(len(values)))
    ax1.set_xticklabels(labels, rotation=30, ha='right')

    ax2 = ax1.twinx()
    ax2.plot(range(len(values)), cum_pct, color=COLORS[1], marker='o', lw=2)
    ax2.axhline(80, color='gray', ls='--', lw=1)
    ax2.text(len(values) - 1, 82, '80% 线', color='gray', ha='right')
    ax2.set_ylabel('累计百分比 (%)', color=COLORS[1])
    ax2.set_ylim(0, 105)
    ax1.set_title(title)
    fig.tight_layout()
    fig.savefig(save, dpi=300)
    plt.close(fig)
    print(f'[已保存] {save}')


def plot_surface3d(x, y, z_func, title='3D 曲面图', save='surface3d.png',
                   xlabel='参数1', ylabel='参数2', zlabel='目标值'):
    """3D 曲面图：z = z_func(X, Y)。灵敏度分析、响应曲面首选。
    x, y: 一维网格坐标；z_func: 接收网格 (X, Y) 返回 Z 的函数。
    """
    X, Y = np.meshgrid(x, y)
    Z = z_func(X, Y)
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111, projection='3d')
    surf = ax.plot_surface(X, Y, Z, cmap='viridis', edgecolor='none', alpha=0.9)
    fig.colorbar(surf, shrink=0.6, aspect=12)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_zlabel(zlabel)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(save, dpi=300)
    plt.close(fig)
    print(f'[已保存] {save}')


def plot_scatter3d(x, y, z, groups=None, title='3D 散点图', save='scatter3d.png'):
    """3D 散点图：三个变量的空间分布，可按 groups 分类着色（聚类可视化）。"""
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection='3d')
    if groups is None:
        ax.scatter(x, y, z, c=COLORS[0], s=30)
    else:
        for i, g in enumerate(np.unique(groups)):
            m = np.asarray(groups) == g
            ax.scatter(np.asarray(x)[m], np.asarray(y)[m], np.asarray(z)[m],
                       c=COLORS[i % len(COLORS)], s=30, label=f'类{g}')
        ax.legend()
    ax.set_xlabel('X'); ax.set_ylabel('Y'); ax.set_zlabel('Z')
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(save, dpi=300)
    plt.close(fig)
    print(f'[已保存] {save}')


def plot_violin(data_groups, labels, title='小提琴图', ylabel='数值', save='violin.png'):
    """小提琴图：比箱线图多展示分布形状（密度）。
    data_groups: 列表，每个元素是一组一维数据；labels: 各组名称。
    """
    fig, ax = plt.subplots(figsize=(8, 5))
    parts = ax.violinplot(data_groups, showmeans=True, showmedians=True)
    for i, pc in enumerate(parts['bodies']):
        pc.set_facecolor(COLORS[i % len(COLORS)])
        pc.set_alpha(0.7)
    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(save, dpi=300)
    plt.close(fig)
    print(f'[已保存] {save}')


def plot_bubble(x, y, size, labels=None, title='气泡图', save='bubble.png',
                xlabel='X', ylabel='Y'):
    """气泡图：x,y 定位 + size 编码第三维（如 GDP-寿命-人口）。size 会归一化到合适半径。"""
    size = np.asarray(size, dtype=float)
    s = 100 + 900 * (size - size.min()) / (np.ptp(size) + 1e-12)
    fig, ax = plt.subplots(figsize=(8, 6))
    sc = ax.scatter(x, y, s=s, c=size, cmap='plasma', alpha=0.6, edgecolor='black')
    fig.colorbar(sc, label='气泡大小对应值')
    if labels is not None:
        for xi, yi, li in zip(x, y, labels):
            ax.annotate(str(li), (xi, yi), fontsize=8, ha='center')
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(save, dpi=300)
    plt.close(fig)
    print(f'[已保存] {save}')


def plot_scatter_matrix(df, title='矩阵散点图', save='scatter_matrix.png'):
    """矩阵散点图：DataFrame 各数值列两两散点 + 对角线直方图。多变量关系总览。"""
    axes = pd.plotting.scatter_matrix(df, figsize=(9, 9), diagonal='hist',
                                      color=COLORS[2], hist_kwds={'color': COLORS[0]})
    for ax in axes.ravel():
        ax.xaxis.label.set_rotation(20)
        ax.yaxis.label.set_rotation(0)
        ax.yaxis.label.set_ha('right')
    plt.suptitle(title)
    plt.tight_layout()
    plt.savefig(save, dpi=300)
    plt.close('all')
    print(f'[已保存] {save}')


def plot_stacked_bar(categories, series_dict, title='堆叠柱状图',
                     percent=False, ylabel='数值', save='stacked_bar.png'):
    """堆叠柱状图。categories: x 轴分类；series_dict: {系列名: [各分类的值]}。
    percent=True 时画百分比堆叠（每根柱归一化到 100%），用于构成占比分析。
    """
    names = list(series_dict.keys())
    mat = np.array([series_dict[n] for n in names], dtype=float)  # (系列, 分类)
    if percent:
        mat = mat / mat.sum(axis=0, keepdims=True) * 100
    fig, ax = plt.subplots(figsize=(9, 5))
    bottom = np.zeros(mat.shape[1])
    for i, n in enumerate(names):
        ax.bar(categories, mat[i], bottom=bottom, label=n,
               color=COLORS[i % len(COLORS)], edgecolor='white')
        bottom += mat[i]
    ax.set_ylabel('百分比 (%)' if percent else ylabel)
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(save, dpi=300)
    plt.close(fig)
    print(f'[已保存] {save}')


def plot_kde(data_groups, labels, title='核密度估计图', xlabel='数值', save='kde.png'):
    """核密度图（KDE）：平滑的分布曲线，比直方图更适合多组分布对比。"""
    from scipy.stats import gaussian_kde
    fig, ax = plt.subplots(figsize=(8, 5))
    for i, (d, lab) in enumerate(zip(data_groups, labels)):
        d = np.asarray(d, dtype=float)
        kde = gaussian_kde(d)
        xs = np.linspace(d.min(), d.max(), 200)
        ax.plot(xs, kde(xs), color=COLORS[i % len(COLORS)], lw=2, label=lab)
        ax.fill_between(xs, kde(xs), alpha=0.2, color=COLORS[i % len(COLORS)])
    ax.set_xlabel(xlabel); ax.set_ylabel('密度'); ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(save, dpi=300)
    plt.close(fig)
    print(f'[已保存] {save}')


def plot_contour(x, y, z_func, title='等高线图', save='contour.png',
                 xlabel='参数1', ylabel='参数2'):
    """等高线图：z=z_func(X,Y) 的等值线（俯视响应面/场分布）。填充+标注等高线。"""
    X, Y = np.meshgrid(x, y)
    Z = z_func(X, Y)
    fig, ax = plt.subplots(figsize=(8, 6))
    cf = ax.contourf(X, Y, Z, levels=20, cmap='viridis')
    cs = ax.contour(X, Y, Z, levels=8, colors='white', linewidths=0.6)
    ax.clabel(cs, inline=True, fontsize=8)
    fig.colorbar(cf, label='目标值')
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    fig.tight_layout()
    fig.savefig(save, dpi=300)
    plt.close(fig)
    print(f'[已保存] {save}')


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】替换即可，函数都是通用的。
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   然后把 df 的列传给对应函数，例如：
    #     plot_pareto(df['因素'].tolist(), df['影响值'].values)
    #     plot_violin([df[df['组']==g]['值'].values for g in df['组'].unique()], ...)
    #   详见 00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为真实数据后可删除)
    rng = np.random.default_rng(42)

    plot_waterfall(['基础', '产品A', '产品B', '成本', '税费'],
                   [100, 40, 30, -25, -15], title='利润构成瀑布图')

    plot_pareto(['缺陷A', '缺陷B', '缺陷C', '缺陷D', '缺陷E', '缺陷F'],
                [50, 30, 12, 5, 2, 1], title='质量缺陷帕累托图')

    plot_surface3d(np.linspace(-3, 3, 60), np.linspace(-3, 3, 60),
                   lambda X, Y: np.sin(np.sqrt(X**2 + Y**2)),
                   title='响应曲面示例')

    g = rng.integers(0, 3, 60)
    plot_scatter3d(rng.normal(g, 0.5), rng.normal(g, 0.5), rng.normal(g, 0.5),
                   groups=g, title='3D 聚类散点')

    plot_violin([rng.normal(0, 1, 200), rng.normal(1, 1.5, 200), rng.normal(-1, 0.6, 200)],
                ['方案A', '方案B', '方案C'])

    plot_bubble(rng.uniform(0, 10, 12), rng.uniform(0, 10, 12),
                rng.uniform(1, 100, 12), labels=range(1, 13))

    plot_scatter_matrix(pd.DataFrame(rng.normal(size=(80, 4)),
                                     columns=['指标1', '指标2', '指标3', '指标4']))

    plot_stacked_bar(['2021', '2022', '2023', '2024'],
                     {'华东': [30, 35, 40, 45], '华南': [20, 22, 28, 30],
                      '华北': [15, 18, 20, 25]}, percent=True,
                     title='区域销量百分比堆叠')

    plot_kde([rng.normal(0, 1, 300), rng.normal(2, 1.2, 300)], ['对照组', '实验组'])

    plot_contour(np.linspace(-3, 3, 80), np.linspace(-3, 3, 80),
                 lambda X, Y: -(X**2 + Y**2), title='目标函数等高线')

    print('\n竞赛级图表集：全部示例已生成 PNG。')

