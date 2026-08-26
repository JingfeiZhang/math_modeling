# -*- coding: utf-8 -*-
"""
常用可视化模板
==============================================================================
功能：
    数学建模论文最常用的 7 类图表，每种封装成独立函数，中文标签、
    统一配色、可直接改数据出图。竞赛写论文时复制对应函数即可。
        1. plot_line       折线图（趋势/时间序列，支持多条线）
        2. plot_bar        柱状图（分类对比，支持分组簇状）
        3. plot_scatter    散点图（两变量关系，支持分类着色）
        4. plot_box        箱线图（分布与异常值）
        5. plot_heatmap    热力图（相关矩阵/二维强度）
        6. plot_radar      雷达图（多维指标对比，评价类常用）
        7. plot_dual_axis  双轴图（两个不同量纲指标同图对比）

输入格式：见各函数 docstring，主要接收 numpy 数组 / list / DataFrame。

输出：直接弹出 matplotlib 图窗（可自行加 plt.savefig 导出）。

依赖库：numpy, pandas, matplotlib, seaborn
==============================================================================
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 论文级配色（对色盲友好，打印也清晰）
COLORS = ['#1b9e77', '#d95f02', '#7570b3', '#e7298a', '#66a61e', '#e6ab02']


def plot_line(x, ys, labels=None, title='折线图', xlabel='X', ylabel='Y'):
    """
    折线图。x 为横轴序列；ys 为一条(一维)或多条(二维,每行一条)数据；
    labels 为各条线的图例名称列表。
    """
    ys = np.atleast_2d(ys)
    plt.figure(figsize=(9, 5))
    for i, y in enumerate(ys):
        lab = labels[i] if labels else f'系列{i + 1}'
        plt.plot(x, y, marker='o', ms=4, lw=2, color=COLORS[i % len(COLORS)], label=lab)
    plt.xlabel(xlabel); plt.ylabel(ylabel); plt.title(title, fontsize=14)
    plt.grid(alpha=0.3); plt.legend(); plt.tight_layout()
    plt.show()


def plot_bar(categories, values, labels=None, title='柱状图',
             xlabel='类别', ylabel='数值'):
    """
    柱状图。categories 为分类标签；values 为一维(单组)或二维(多组簇状,每行一组)；
    labels 为各组图例。自动在柱顶标注数值。
    """
    values = np.atleast_2d(values)
    n_group, n_cat = values.shape
    x = np.arange(n_cat)
    width = 0.8 / n_group
    plt.figure(figsize=(9, 5))
    for i, v in enumerate(values):
        lab = labels[i] if labels else f'组{i + 1}'
        bars = plt.bar(x + i * width, v, width, color=COLORS[i % len(COLORS)], label=lab)
        for b in bars:
            plt.text(b.get_x() + b.get_width() / 2, b.get_height(),
                     f'{b.get_height():.1f}', ha='center', va='bottom', fontsize=9)
    plt.xticks(x + width * (n_group - 1) / 2, categories)
    plt.xlabel(xlabel); plt.ylabel(ylabel); plt.title(title, fontsize=14)
    plt.grid(alpha=0.3, axis='y'); plt.legend(); plt.tight_layout()
    plt.show()


def plot_scatter(x, y, c=None, title='散点图', xlabel='X', ylabel='Y'):
    """
    散点图。x, y 为两变量数据；c 可为分类标签数组（按类别着色并加图例）。
    """
    plt.figure(figsize=(8, 6))
    if c is None:
        plt.scatter(x, y, s=35, color=COLORS[0], alpha=0.7)
    else:
        c = np.asarray(c)
        for i, cat in enumerate(np.unique(c)):
            m = c == cat
            plt.scatter(np.asarray(x)[m], np.asarray(y)[m], s=35, alpha=0.7,
                        color=COLORS[i % len(COLORS)], label=str(cat))
        plt.legend()
    plt.xlabel(xlabel); plt.ylabel(ylabel); plt.title(title, fontsize=14)
    plt.grid(alpha=0.3); plt.tight_layout()
    plt.show()


def plot_box(df, title='箱线图', ylabel='数值'):
    """
    箱线图。df 为 DataFrame，每列画一个箱体，展示分布与异常值（红星）。
    """
    plt.figure(figsize=(9, 5))
    df.boxplot(sym='r*', patch_artist=True,
               boxprops=dict(facecolor='#1b9e77', color='#7570b3'),
               medianprops=dict(color='darkblue', linewidth=2))
    plt.ylabel(ylabel); plt.title(title, fontsize=14)
    plt.grid(alpha=0.3); plt.tight_layout()
    plt.show()


def plot_heatmap(matrix, xlabels=None, ylabels=None,
                 title='热力图', cmap='coolwarm', annot=True):
    """
    热力图。matrix 为二维数组或 DataFrame（如相关矩阵）；
    xlabels/ylabels 为坐标标签（DataFrame 会自动取列/行名）。
    """
    plt.figure(figsize=(8, 6))
    sns.heatmap(matrix, annot=annot, fmt='.2f', cmap=cmap, square=True,
                linewidths=0.5, xticklabels=xlabels if xlabels else 'auto',
                yticklabels=ylabels if ylabels else 'auto')
    plt.title(title, fontsize=14)
    plt.tight_layout()
    plt.show()


def plot_radar(values, dims, labels=None, title='雷达图'):
    """
    雷达图。dims 为各维度名称；values 为一维(单对象)或二维(多对象,每行一个)；
    labels 为对象图例。适合多维指标对比（评价类模型展示）。
    建议先把各维度归一化到同一量纲再画。
    """
    values = np.atleast_2d(values)
    n = len(dims)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]                       # 闭合
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    for i, v in enumerate(values):
        data = np.concatenate([v, v[:1]])      # 闭合
        lab = labels[i] if labels else f'对象{i + 1}'
        ax.plot(angles, data, lw=2, color=COLORS[i % len(COLORS)], label=lab)
        ax.fill(angles, data, alpha=0.15, color=COLORS[i % len(COLORS)])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dims)
    ax.set_title(title, fontsize=14, pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1))
    plt.tight_layout()
    plt.show()


def plot_dual_axis(x, y1, y2, y1_label='指标1', y2_label='指标2',
                   xlabel='X', title='双轴图'):
    """
    双 Y 轴图。左右轴分别画两个不同量纲的指标（如销量 vs 价格）。
    x 横轴；y1 左轴数据；y2 右轴数据。
    """
    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.plot(x, y1, marker='o', lw=2, color=COLORS[0], label=y1_label)
    ax1.set_xlabel(xlabel); ax1.set_ylabel(y1_label, color=COLORS[0])
    ax1.tick_params(axis='y', labelcolor=COLORS[0])
    ax1.grid(alpha=0.3)

    ax2 = ax1.twinx()
    ax2.plot(x, y2, marker='s', lw=2, color=COLORS[1], label=y2_label)
    ax2.set_ylabel(y2_label, color=COLORS[1])
    ax2.tick_params(axis='y', labelcolor=COLORS[1])

    lines1, lab1 = ax1.get_legend_handles_labels()
    lines2, lab2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, lab1 + lab2, loc='upper left')
    plt.title(title, fontsize=14)
    plt.tight_layout()
    plt.show()


# ============================ 演示 ============================

if __name__ == '__main__':
    np.random.seed(3)

    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面各图的【示例数据】注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 按每张图需要，从 df 取出对应数据传给绘图函数，例如：
    #   months  = df['月份'].tolist()                    # 折线/柱状图横轴
    #   sales_a = df['产品A销量'].values                 # plot_line 的一条线
    #   x = df['特征X'].values; y = df['特征Y'].values   # plot_scatter 两变量
    #   cls = df['类别'].values                          # 散点分类着色
    #   plot_box(df[['指标1','指标2','指标3']])           # 箱线图/热力图直接传df
    #   plot_heatmap(df[['指标1','指标2','指标3']].corr())# 相关矩阵热力图
    #   dims = ['价格','质量','服务']                    # 雷达图维度名
    #   详见 00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)

    # 1. 折线图：两条时间序列
    months = [f'{m}月' for m in range(1, 13)]
    sales_a = np.random.randint(50, 100, 12)
    sales_b = np.random.randint(40, 90, 12)
    plot_line(months, [sales_a, sales_b], labels=['产品A', '产品B'],
              title='月度销量趋势', xlabel='月份', ylabel='销量')

    # 2. 柱状图：分组簇状
    cats = ['一季度', '二季度', '三季度', '四季度']
    plot_bar(cats, [[120, 150, 130, 170], [100, 140, 160, 150]],
             labels=['2023', '2024'], title='季度营收对比', ylabel='营收(万元)')

    # 3. 散点图：分类着色
    x = np.random.normal(0, 1, 150)
    y = x * 1.5 + np.random.normal(0, 1, 150)
    cls = np.random.choice(['A', 'B', 'C'], 150)
    plot_scatter(x, y, c=cls, title='变量关系散点图', xlabel='特征X', ylabel='特征Y')

    # 4. 箱线图
    df = pd.DataFrame({'指标1': np.random.normal(50, 10, 100),
                       '指标2': np.random.normal(60, 15, 100),
                       '指标3': np.random.normal(45, 8, 100)})
    plot_box(df, title='各指标分布箱线图')

    # 5. 热力图：相关矩阵
    corr = df.corr()
    plot_heatmap(corr, title='指标相关系数热力图')

    # 6. 雷达图：多对象多维对比
    dims = ['价格', '质量', '服务', '口碑', '物流']
    plot_radar([[0.8, 0.6, 0.9, 0.7, 0.5], [0.6, 0.9, 0.7, 0.8, 0.9]],
               dims, labels=['方案A', '方案B'], title='方案多维评价雷达图')

    # 7. 双轴图
    plot_dual_axis(months, sales_a, np.random.uniform(20, 50, 12),
                   y1_label='销量', y2_label='单价(元)',
                   xlabel='月份', title='销量与单价双轴对比')

