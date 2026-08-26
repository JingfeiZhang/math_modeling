# -*- coding: utf-8 -*-
"""
缺失值与异常值处理模板
==============================================================================
功能：
    数学建模拿到数据的第一步。本模板封装两大类常用操作：
    一、缺失值处理
        1. detect_missing      缺失值检测（统计每列缺失数量与比例）
        2. drop_missing        删除含缺失值的行/列
        3. fill_stat           均值 / 中位数 / 众数填充
        4. fill_ffill_bfill    前向 / 后向填充（时间序列常用）
        5. fill_interpolate    插值填充（线性/二次/三次）
    二、异常值检测
        1. detect_outlier_3sigma   3σ 准则（适合近似正态数据）
        2. detect_outlier_iqr      箱线图 IQR 准则（无分布假设，最稳健）
        3. detect_outlier_lof      LOF 局部离群因子（多维、密度型异常）
        4. remove_outlier_iqr      按 IQR 剔除异常行

输入格式：
    pandas.DataFrame，列为数值型指标（含缺失/异常）。
    示例数据在 __main__ 中自动生成，直接运行即可看到全流程演示。

输出：
    处理后的 DataFrame / 异常值布尔掩码；同时弹出箱线图与散点图可视化。

依赖库：numpy, pandas, matplotlib, scikit-learn
==============================================================================
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.neighbors import LocalOutlierFactor

# matplotlib 中文字体设置（Windows 黑体），避免中文和负号乱码
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


# ============================ 一、缺失值处理 ============================

def detect_missing(df):
    """
    缺失值检测。
    输入：df —— DataFrame
    输出：DataFrame，每列的缺失数量与缺失比例
    """
    miss_count = df.isnull().sum()
    miss_ratio = df.isnull().mean()
    result = pd.DataFrame({'缺失数量': miss_count, '缺失比例': miss_ratio.round(4)})
    return result


def drop_missing(df, axis=0, how='any', thresh=None):
    """
    删除含缺失值的行或列。
    axis=0 删行，axis=1 删列；how='any' 有缺失就删，'all' 全缺失才删；
    thresh 指定非缺失值的最小个数（优先于 how）。
    """
    return df.dropna(axis=axis, how=how, thresh=thresh)


def fill_stat(df, cols=None, method='mean'):
    """
    用统计量填充缺失值。
    method: 'mean' 均值 / 'median' 中位数 / 'mode' 众数
    均值适合近似正态数据，中位数抗异常值，众数适合离散/分类型指标。
    """
    df = df.copy()
    cols = cols if cols is not None else df.columns
    for c in cols:
        if method == 'mean':
            fill_val = df[c].mean()
        elif method == 'median':
            fill_val = df[c].median()
        elif method == 'mode':
            fill_val = df[c].mode().iloc[0]
        else:
            raise ValueError("method 只能是 'mean' / 'median' / 'mode'")
        df[c] = df[c].fillna(fill_val)
    return df


def fill_ffill_bfill(df, method='ffill'):
    """
    前向/后向填充，适合时间序列（用相邻时刻的值补齐）。
    method='ffill' 用前一个值填充；'bfill' 用后一个值填充。
    注意：ffill 补不了开头的缺失，bfill 补不了结尾的缺失，可两者连用。
    """
    # pandas 3.0 移除了 fillna(method=)，改用独立的 ffill()/bfill()
    return df.bfill() if method == 'bfill' else df.ffill()


def fill_interpolate(df, cols=None, method='linear', order=None):
    """
    插值填充缺失值。
    method: 'linear' 线性 / 'quadratic' 二次 / 'cubic' 三次 / 'polynomial'（配合 order）
    适合有趋势的连续数据，比统计量填充更贴合曲线走势。
    """
    df = df.copy()
    cols = cols if cols is not None else df.columns
    for c in cols:
        if method == 'polynomial':
            df[c] = df[c].interpolate(method='polynomial', order=order)
        else:
            df[c] = df[c].interpolate(method=method)
    # 插值可能补不了首尾，再用前后向兜底(pandas 3.0 用 bfill()/ffill())
    df = df.bfill().ffill()
    return df


# ============================ 二、异常值检测 ============================

def detect_outlier_3sigma(series, n_sigma=3):
    """
    3σ 准则：偏离均值超过 n_sigma 倍标准差的点视为异常。
    适合近似正态分布的数据。返回布尔 Series（True=异常）。
    """
    mean, std = series.mean(), series.std()
    lower, upper = mean - n_sigma * std, mean + n_sigma * std
    return (series < lower) | (series > upper), (lower, upper)


def detect_outlier_iqr(series, k=1.5):
    """
    箱线图 IQR 准则：超出 [Q1-k*IQR, Q3+k*IQR] 的点视为异常。
    无需分布假设，最稳健。k 默认 1.5（k=3 为极端异常）。
    返回布尔 Series 与上下边界。
    """
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - k * iqr, q3 + k * iqr
    return (series < lower) | (series > upper), (lower, upper)


def detect_outlier_lof(df, n_neighbors=20, contamination='auto'):
    """
    LOF 局部离群因子：基于局部密度识别多维异常点。
    n_neighbors 近邻数（数据少调小，20 为经验默认）；
    contamination 异常比例（'auto' 或 0~0.5 的浮点）。
    返回布尔 Series（True=异常）与 LOF 负分（越小越异常）。
    """
    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=contamination)
    labels = lof.fit_predict(df.values)          # -1 为异常，1 为正常
    scores = lof.negative_outlier_factor_        # 负离群因子
    mask = pd.Series(labels == -1, index=df.index)
    return mask, scores


def remove_outlier_iqr(df, cols=None, k=1.5):
    """
    对指定列按 IQR 准则逐列剔除异常行，返回过滤后的 DataFrame。
    """
    df = df.copy()
    cols = cols if cols is not None else df.columns
    for c in cols:
        mask, _ = detect_outlier_iqr(df[c], k=k)
        df = df[~mask]
    return df


# ============================ 演示 ============================

if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # df 直接就是本模板要的输入（行=样本 列=数值型指标，可含缺失/异常）
    #   # 只保留要清洗的数值列，例如：
    #   # df = df[['销量', '价格', '评分']]
    #   # 后面演示里用到的列名（如 df_filled['销量']）也要改成你自己的列名
    #   详见 00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # -------- 构造示例数据：含缺失值与异常值 --------
    np.random.seed(0)
    n = 100
    df = pd.DataFrame({
        '销量': np.random.normal(100, 15, n),
        '价格': np.random.normal(50, 8, n),
        '评分': np.random.normal(4.0, 0.5, n),
    })
    # 人为植入缺失值
    df.loc[[3, 20, 55], '销量'] = np.nan
    df.loc[[10, 30], '价格'] = np.nan
    # 人为植入异常值
    df.loc[5, '销量'] = 300
    df.loc[8, '销量'] = -50
    df.loc[15, '价格'] = 200

    print('=== 1. 缺失值检测 ===')
    print(detect_missing(df), '\n')

    # -------- 缺失值填充：数值列用中位数（抗异常），演示插值 --------
    df_filled = fill_stat(df, method='median')
    print('=== 2. 中位数填充后剩余缺失 ===')
    print(df_filled.isnull().sum().sum(), '个\n')

    df_interp = fill_interpolate(df, method='linear')
    print('=== 3. 线性插值填充后剩余缺失 ===')
    print(df_interp.isnull().sum().sum(), '个\n')

    # -------- 异常值检测（在已填充数据上进行）--------
    mask_3s, bound_3s = detect_outlier_3sigma(df_filled['销量'])
    print('=== 4. 3σ 检测「销量」异常 ===')
    print('边界:', np.round(bound_3s, 2), '异常数:', mask_3s.sum())

    mask_iqr, bound_iqr = detect_outlier_iqr(df_filled['销量'])
    print('=== 5. IQR 检测「销量」异常 ===')
    print('边界:', np.round(bound_iqr, 2), '异常数:', mask_iqr.sum())

    mask_lof, scores = detect_outlier_lof(df_filled, n_neighbors=20)
    print('=== 6. LOF 多维异常检测 ===')
    print('异常数:', mask_lof.sum(), '\n')

    df_clean = remove_outlier_iqr(df_filled)
    print('=== 7. IQR 剔除异常后样本量 ===')
    print(f'{len(df_filled)} -> {len(df_clean)}')

    # -------- 可视化：箱线图 + 3σ 散点图 --------
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    df_filled.boxplot(ax=axes[0], sym='r*', patch_artist=True)
    axes[0].set_title('各指标箱线图（红星为IQR异常点）', fontsize=13)
    axes[0].set_ylabel('数值')

    y = df_filled['销量'].values
    axes[1].scatter(range(len(y)), y, s=18, c='#1b9e77', alpha=0.8, label='销量')
    axes[1].scatter(np.where(mask_3s)[0], y[mask_3s.values], s=60,
                    c='red', marker='*', label='3σ异常点')
    axes[1].axhline(bound_3s[0], color='#bf0000', ls='--')
    axes[1].axhline(bound_3s[1], color='#bf0000', ls='--')
    axes[1].set_title('销量 3σ 异常检测', fontsize=13)
    axes[1].set_xlabel('样本序号')
    axes[1].set_ylabel('销量')
    axes[1].legend()
    plt.tight_layout()
    plt.show()

