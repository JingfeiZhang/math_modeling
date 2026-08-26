# -*- coding: utf-8 -*-
"""
================================================================================
秩和比综合评价法（Rank Sum Ratio, RSR）
================================================================================
功能：
    将各指标数据转化为"秩"（排名），用加权秩和比 RSR 做综合评价与分档排序。
    对异常值不敏感、不要求数据分布，适合医疗卫生、社会经济等评价。

原理：
    1) 编秩：对每个指标把 n 个对象编秩（整秩用 rank，非整秩用线性插值）；
    2) 计算 RSR = Σ(权重 × 秩) / n，越大越好；
    3) 概率单位 Probit：由 RSR 累计频率经正态逆变换得到；
    4) 回归：RSR 对 Probit 做线性回归，得修正 RSR（Regression）；
    5) 分档：按 Probit 阈值（如 [2,4,6,8] 分 3 档）对修正 RSR 分级排序。

整秩 vs 非整秩：
    full_rank=True  整秩：直接用平均秩次，适合样本量大、分布均匀
    full_rank=False 非整秩：按数值线性插值编秩（默认），保留数值间距信息

适用竞赛场景：
    - 多指标综合评价且希望"分档分级"（优/良/中/差）而非仅排序
    - 数据含异常值、量纲差异大、不服从正态时更稳健

输入格式：
    df : DataFrame，行=对象，列=指标（成本型指标需先正向化，如取倒数）。
    weight : 指标权重列表，默认等权。

依赖：numpy, pandas, scipy
================================================================================
"""

import numpy as np
import pandas as pd
from scipy import stats

def rsr(df, weight=None, threshold=None, full_rank=False):
    """秩和比综合评价主函数。

    参数:
        df        : DataFrame，行=对象，列=指标（均需为"越大越好"）
        weight    : 指标权重列表，默认等权
        threshold : 分档的 Probit 阈值，默认 [2,4,6,8]（分 3 档）
        full_rank : True 整秩 / False 非整秩（默认）
    返回:
        Result       : 含原始值、秩、RSR、Probit、修正RSR、分档 的表
        Distribution : RSR 分布与回归中间表
        reg          : 回归系数 (斜率, 截距)
    """
    df = df.copy()
    n, m = df.shape
    Result = pd.DataFrame(index=df.index)

    # 1) 编秩
    ranks = pd.DataFrame(index=df.index)
    for col in df.columns:
        Result[f'原值_{col}'] = df[col]
        if full_rank:
            ranks[col] = df[col].rank(method='average')  # 整秩：平均秩次
        else:
            # 非整秩：按数值线性映射到 [1, n]
            rng = df[col].max() - df[col].min()
            rng = rng if rng != 0 else 1e-12
            ranks[col] = 1 + (n - 1) * (df[col] - df[col].min()) / rng

    # 2) 计算 RSR（加权秩和比）
    if weight is None:
        weight = np.ones(m) / m
    weight = np.array(weight, dtype=float)
    weight = weight / weight.sum()
    Result['RSR'] = (ranks.values * weight).sum(axis=1) / n

    # 3) 构造 RSR 分布表，计算 Probit
    RSR = Result['RSR']
    rank_dict = dict(zip(RSR.values, RSR.rank().values))  # RSR -> 其秩次
    Dist = pd.DataFrame(index=sorted(RSR.unique()))
    Dist['f'] = RSR.value_counts().sort_index()           # 频数
    Dist['Σf'] = Dist['f'].cumsum()                        # 累计频数
    Dist['R_bar'] = [rank_dict[i] for i in Dist.index]     # 平均秩次
    Dist['p_cum'] = Dist['R_bar'] / n                      # 累计频率
    Dist.iat[-1, -1] = 1 - 1 / (4 * n)                     # 修正末项，避免 Probit 发散
    Dist['Probit'] = 5 - stats.norm.isf(Dist['p_cum'])     # 累计频率 -> 概率单位

    # 4) RSR 对 Probit 线性回归：RSR = a·Probit + b
    reg = np.polyfit(Dist['Probit'], Dist.index, deg=1)
    if reg[1] >= 0:
        print(f'回归方程：RSR = {reg[0]:.4f}·Probit + {reg[1]:.4f}')
    else:
        print(f'回归方程：RSR = {reg[0]:.4f}·Probit - {abs(reg[1]):.4f}')

    # 5) 代入回归得修正 RSR，并按 Probit 阈值分档
    Result['Probit'] = Result['RSR'].map(lambda v: Dist.at[v, 'Probit'])
    Result['RSR_修正'] = np.polyval(reg, Result['Probit'])
    if threshold is None:
        threshold = [2, 4, 6, 8]
    cut_points = np.polyval(reg, threshold)   # 阈值对应的修正 RSR 边界
    Result['分档'] = pd.cut(Result['RSR_修正'], cut_points,
                          labels=range(1, len(threshold)))  # 档次(数值越大越优)
    Result['排名'] = Result['RSR_修正'].rank(ascending=False, method='min').astype(int)
    return Result.sort_values('排名'), Dist, reg


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   data = pd.read_csv('附件1.csv', encoding='gbk', index_col=0)  # 乱码就换 utf-8 / gb18030
    #   # data 直接就是本模板输入(行=对象、列=指标)；index_col=0 把对象名列设为行索引
    #   # 只保留要评价的指标列，例如：
    #   # data = data[['产前检查率', '孕妇死亡率', '围产儿死亡率']]
    #   # ★ 成本型(越小越好)指标必须先手动正向化再传入，例如取倒数：
    #   #   data['孕妇死亡率'] = 1 / data['孕妇死亡率']
    #   # 调用时 weight 按指标顺序给权重，threshold 定分档的 Probit 阈值：
    #   #   rsr(data, weight=[0.4, 0.3, 0.3], threshold=[2, 4, 6, 8])
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # ------------------- 示例：10 家医院妇幼保健评价 -------------------
    data = pd.DataFrame({
        '产前检查率': [99.54, 96.52, 99.36, 92.83, 91.71, 95.35, 96.09, 99.27, 94.76, 84.80],
        '孕妇死亡率': [60.27, 59.67, 43.91, 58.99, 35.40, 44.71, 49.81, 31.69, 22.91, 81.49],
        '围产儿死亡率': [16.15, 20.10, 15.60, 17.04, 15.01, 13.93, 17.43, 13.89, 19.87, 23.63],
    }, index=list('ABCDEFGHIJ'))

    # 两个死亡率是成本型指标（越小越好），取倒数正向化
    data['孕妇死亡率'] = 1 / data['孕妇死亡率']
    data['围产儿死亡率'] = 1 / data['围产儿死亡率']

    print('===== 秩和比 RSR 综合评价 =====')
    result, dist, reg = rsr(data, weight=[0.4, 0.3, 0.3], threshold=[2, 4, 6, 8])
    print('\n评价结果（按排名）:')
    print(result[['RSR', 'RSR_修正', '分档', '排名']].round(4).to_string())
    print(f'\n最优对象：{result.index[0]}（第 1 名，第 '
          f'{result.iloc[0]["分档"]} 档）')

