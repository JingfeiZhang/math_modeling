# -*- coding: utf-8 -*-
"""
08 VAR 向量自回归 (Vector AutoRegression)
================================================================
功能：
    面向国赛 C 题的“多个相互影响的时间序列联合预测”。当几条序列彼此
    有反馈关系（如 销量↔损耗↔销售次数、价格↔需求↔进货量）时，单独对每条
    做 ARIMA 会丢掉“互相影响”，VAR 让每个变量同时对【所有变量的滞后值】回归：
        y_t = c + A_1 y_{t-1} + ... + A_p y_{t-p} + e_t   （y_t 为 k 维向量）

    流程：
      1. ADF 平稳性检验；不平稳则差分（VAR 要求平稳，否则考虑 VECM）；
      2. 定阶 p：信息准则 AIC/BIC/HQIC 自动选，或按业务逻辑指定
         （2023C_C126 的经典做法：蔬菜“当日未售隔日难卖”≈2天保质期 → 直接定 2 阶，
          用业务常识定阶，答辩无可辩驳）；
      3. 拟合 + Granger 因果检验（谁影响谁）；
      4. 训练/测试评估 + 向后多步预测；
      5. 可选：脉冲响应 IRF（一个变量受冲击后其它变量怎么反应）。

输入格式：
    - 宽表 DataFrame，每列一个变量，每行一个时间点（等间隔）。

输出：
    - 平稳性结论、最优滞后阶 p、Granger 因果、测试集误差、未来多步预测。

依赖：numpy, pandas, statsmodels, (可选) matplotlib
运行：python 08_VAR向量自回归.py

⚠️ 常见坑（国赛现场高频）：
    - VAR 预测可能出现负值：对销量/进货量这类非负量，预测后需 clip(下限0)，
      或先对数变换 ln(1+y) 建模、预测后 expm1 还原（推荐，天然保证非负）。
    - 序列必须平稳：非平稳直接建 VAR 会伪回归；差分后建模、预测再累加还原。
    - 样本不能太短：参数量 = k²p + k，k 个变量 p 阶就要 k²p 个系数，样本少会过拟合。
"""

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import warnings
import numpy as np
import pandas as pd
warnings.filterwarnings('ignore')

from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

try:
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False

def adf_test(series, name=''):
    """ADF 单位根检验：p<0.05 认为平稳。返回 (是否平稳, p值)。"""
    r = adfuller(series.dropna(), autolag='AIC')
    stat, p = r[0], r[1]
    print(f"  ADF[{name}]: 统计量={stat:.3f}, p={p:.4f} -> {'平稳' if p < 0.05 else '非平稳(建议差分)'}")
    return p < 0.05, p


def make_stationary(df, max_diff=2):
    """逐列检验平稳性；只要有列非平稳就整体差分一次，最多 max_diff 次。
       返回 (平稳后的df, 差分阶数d)。预测时需按 d 累加还原。"""
    d = 0
    cur = df.copy()
    for _ in range(max_diff + 1):
        allst = True
        print(f"[平稳性检验] 差分阶 d={d}")
        for c in cur.columns:
            st, _ = adf_test(cur[c], c)
            allst = allst and st
        if allst:
            print(f"  -> 全部平稳，采用 d={d}\n")
            return cur, d
        cur = cur.diff().dropna()
        d += 1
    print(f"  -> 达最大差分次数，采用 d={d}（仍可能非平稳，考虑 VECM）\n")
    return cur, d


def select_order(df_stat, maxlags=10, force_p=None):
    """按信息准则自动定阶；force_p 不为空则直接用业务逻辑指定的阶。"""
    if force_p is not None:
        print(f"[定阶] 业务逻辑强制 p={force_p}（如蔬菜2天保质期→2阶）\n")
        return force_p
    model = VAR(df_stat)
    maxlags = min(maxlags, len(df_stat) // (df_stat.shape[1] + 1) - 1)
    maxlags = max(maxlags, 1)
    sel = model.select_order(maxlags=maxlags)
    print("[定阶] 各准则建议：")
    print(f"  AIC={sel.aic}, BIC={sel.bic}, HQIC={sel.hqic}, FPE={sel.fpe}")
    p = sel.aic if sel.aic and sel.aic > 0 else 1
    print(f"  -> 采用 AIC 建议 p={p}\n")
    return p


def granger_causality(df, maxlag, verbose=True):
    """两两 Granger 因果检验：X 的滞后是否有助于预测 Y（p<0.05 认为有因果）。"""
    cols = df.columns
    print("[Granger 因果检验] (行→列，p<0.05 表示行变量的历史有助预测列变量)")
    res = pd.DataFrame(np.zeros((len(cols), len(cols))), index=cols, columns=cols)
    for c1 in cols:      # 被预测
        for c2 in cols:  # 预测者
            if c1 == c2:
                res.loc[c2, c1] = np.nan
                continue
            try:
                t = grangercausalitytests(df[[c1, c2]].dropna(), maxlag=maxlag, verbose=False)
                pvals = [t[i + 1][0]['ssr_ftest'][1] for i in range(maxlag)]
                res.loc[c2, c1] = round(min(pvals), 4)
            except Exception:
                res.loc[c2, c1] = np.nan
    if verbose:
        print(res.to_string())
        print()
    return res


def fit_var_forecast(df, force_p=None, test_size=7, n_forecast=7,
                     log_transform=True, maxlags=10):
    """VAR 主流程：对数变换(可选)→平稳化→定阶→拟合→测试评估→未来预测。
       log_transform=True 时对 ln(1+y) 建模，预测 expm1 还原，天然保证非负。"""
    cols = list(df.columns)
    work = np.log1p(df) if log_transform else df.copy()
    if log_transform:
        print("[变换] 已对 ln(1+y) 建模（预测自动还原，保证非负）\n")

    # 留出测试集
    train, test = work.iloc[:-test_size], work.iloc[-test_size:]

    # 平稳化（记录差分阶用于还原）
    train_stat, d = make_stationary(train)
    p = select_order(train_stat, maxlags=maxlags, force_p=force_p)

    # 拟合
    model = VAR(train_stat)
    res = model.fit(p)
    print(f"[拟合] VAR({p})，变量数 k={len(cols)}，估计系数≈{len(cols)**2 * p + len(cols)} 个")

    # Granger 因果（在平稳序列上做）
    if len(train_stat) > p * len(cols) + 10:
        granger_causality(train_stat, maxlag=p)

    # ---- 测试集滚动预测评估（差分序列上预测，再累加还原到原尺度）----
    lag = res.k_ar
    fc_stat = res.forecast(train_stat.values[-lag:], steps=test_size)
    fc_stat = pd.DataFrame(fc_stat, columns=cols)
    fc_level = _invert(fc_stat, train, d, log_transform)
    actual = np.expm1(test) if log_transform else test
    print("\n[测试集评估] (末 %d 期)" % test_size)
    for c in cols:
        a, f = actual[c].values, fc_level[c].values
        mape = np.mean(np.abs((a - f) / np.clip(np.abs(a), 1e-9, None))) * 100
        rmse = np.sqrt(np.mean((a - f) ** 2))
        print(f"  {c}: RMSE={rmse:.3f}, MAPE={mape:.2f}%")

    # ---- 用全量数据重拟合，向后预测 n_forecast 步 ----
    full_stat, d2 = make_stationary(work)
    res2 = VAR(full_stat).fit(p)
    fc2 = pd.DataFrame(res2.forecast(full_stat.values[-res2.k_ar:], steps=n_forecast), columns=cols)
    fc2_level = _invert(fc2, work, d2, log_transform)
    print(f"\n[未来 {n_forecast} 步预测]（已还原到原尺度）")
    print(fc2_level.round(3).to_string())
    return res2, fc2_level


def _invert(fc_diff, hist_before_diff, d, log_transform):
    """把差分预测累加还原到原尺度；再按需 expm1 反对数。hist 为(可能对数后的)未差分序列。"""
    fc = fc_diff.copy()
    for _ in range(d):  # 每差分一次，还原时累加一次上一层最后的水平值
        last = hist_before_diff.iloc[-1]
        fc = fc.cumsum() + last.values
    if log_transform:
        fc = np.expm1(fc)
    return fc.clip(lower=0)  # 非负量兜底


if __name__ == '__main__':
    # ===== 演示：造 3 条相互影响的序列（销量、损耗、销售次数）=====
    rng = np.random.default_rng(42)
    n = 120
    sales = np.zeros(n); loss = np.zeros(n); freq = np.zeros(n)
    sales[:2] = [50, 52]; loss[:2] = [5, 5]; freq[:2] = [30, 31]
    for t in range(2, n):
        # 销量受自身滞后 + 上期销售次数正向影响；损耗滞后销量；次数跟随销量
        sales[t] = 10 + 0.6 * sales[t-1] + 0.3 * freq[t-1] + rng.normal(0, 3)
        loss[t] = 1 + 0.5 * loss[t-1] + 0.05 * sales[t-1] + rng.normal(0, 0.5)
        freq[t] = 5 + 0.5 * freq[t-1] + 0.3 * sales[t-1] + rng.normal(0, 2)
    df = pd.DataFrame({'销量': sales, '损耗': loss, '销售次数': freq})

    print("=" * 64)
    print("VAR 向量自回归演示：销量↔损耗↔销售次数 联合预测")
    print("=" * 64)
    # force_p=2 演示业务定阶（蔬菜2天保质期）；设 None 则自动按 AIC
    res, fc = fit_var_forecast(df, force_p=2, test_size=7, n_forecast=7, log_transform=True)

    if _HAS_PLT:
        try:
            fig, axes = plt.subplots(1, 3, figsize=(15, 4))
            for ax, c in zip(axes, df.columns):
                ax.plot(range(len(df)), df[c], label='历史', color='steelblue')
                ax.plot(range(len(df), len(df) + len(fc)), fc[c], 'r--o', label='预测', ms=3)
                ax.set_title(c); ax.legend(); ax.grid(alpha=0.3)
            plt.tight_layout()
            plt.savefig('VAR_预测.png', dpi=120, bbox_inches='tight')
            print("\n[图] 已保存 VAR_预测.png")
        except Exception as e:
            print(f"绘图跳过: {e}")

