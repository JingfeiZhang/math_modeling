# -*- coding: utf-8 -*-
"""
================================================================================
05 残差诊断与假设检验 (Residual Diagnostics & Assumption Tests)
================================================================================
功能：
    回归/预测模型建完后，检验其残差是否满足经典假设。不满足则结论(系数显著性、
    置信区间)可能失真。本模板对残差做四项标准检验，每项给“通过/未通过/需改进”
    判定与改进建议：
      1. 正态性     —— Shapiro-Wilk 检验（残差是否近似正态）。
      2. 方差齐性   —— Levene 检验（把残差按预测值分组，看各组方差是否一致）。
      3. 独立性     —— Durbin-Watson 统计量（残差是否自相关，时序数据尤其重要）。
      4. 异方差     —— Breusch-Pagan 检验（残差方差是否随自变量变化）。
    另可选做游程检验(随机性)。最后打印一份汇总判定表。

适用竞赛场景：
    - 线性/多项式回归、时间序列残差检验；论文里“模型假设检验”小节直接用。
    - 呼应 2026 自查表对模型合理性/误差分析的要求。

输入格式：
    - y_true, y_pred：真实值与预测值（一维，等长）——最常用，内部自动算残差。
    - 或直接传 residuals（残差数组）与 X（自变量矩阵，供 BP 异方差检验，可选）。

输出：
    - 控制台逐项打印统计量、p 值、判定与建议，末尾给汇总表。
    - 保存 05_残差诊断图.png（残差vs预测 + 残差自相关）。

依赖：numpy, scipy, statsmodels, (可选) matplotlib
================================================================================
"""

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np
from scipy import stats

# statsmodels 提供 Durbin-Watson 与 Breusch-Pagan
import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson
from statsmodels.stats.diagnostic import het_breuschpagan

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
    plt.rcParams['axes.unicode_minus'] = False
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False

ALPHA = 0.05   # 显著性水平：p<ALPHA 视为“拒绝原假设”


# ----------------------------------------------------------------------
# 1. 正态性检验：Shapiro-Wilk
# ----------------------------------------------------------------------
def test_normality(resid):
    """Shapiro-Wilk 正态性检验。H0：残差服从正态分布。
    p≥0.05 → 不能拒绝正态（通过）；p<0.05 → 非正态（未通过）。"""
    resid = np.asarray(resid, dtype=float).ravel()
    # Shapiro 对 n>5000 不稳，样本大时抽样
    r = resid if resid.size <= 5000 else np.random.RandomState(0).choice(resid, 5000, replace=False)
    stat, p = stats.shapiro(r)
    passed = p >= ALPHA
    print("① 正态性 (Shapiro-Wilk)   W=%.4f  p=%.4g" % (stat, p))
    if passed:
        print("   判定：通过 —— 残差近似正态，系数显著性/置信区间可信。")
    else:
        print("   判定：未通过 —— 残差非正态。建议：对 y 做对数/Box-Cox 变换、")
        print("        检查异常值、或改用稳健回归；样本大时轻微偏离影响不大。")
    return {'name': '正态性', 'stat': stat, 'p': p, 'passed': passed}


# ----------------------------------------------------------------------
# 2. 方差齐性：Levene（按预测值分箱）
# ----------------------------------------------------------------------
def test_homoscedasticity_levene(resid, y_pred, n_groups=3):
    """Levene 方差齐性检验。把残差按预测值大小分成 n_groups 组，检验各组方差是否相等。
    H0：各组方差相等。p≥0.05 → 方差齐（通过）；p<0.05 → 异方差（未通过）。"""
    resid = np.asarray(resid, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    order = np.argsort(y_pred)
    groups = np.array_split(resid[order], n_groups)
    stat, p = stats.levene(*groups)
    passed = p >= ALPHA
    print("② 方差齐性 (Levene, 按预测值分%d组)   W=%.4f  p=%.4g" % (n_groups, stat, p))
    if passed:
        print("   判定：通过 —— 残差方差稳定，满足同方差假设。")
    else:
        print("   判定：未通过 —— 存在异方差。建议：对 y 做变换、加权最小二乘(WLS)、")
        print("        或用异方差稳健标准误(HC)。")
    return {'name': '方差齐性', 'stat': stat, 'p': p, 'passed': passed}


# ----------------------------------------------------------------------
# 3. 独立性：Durbin-Watson
# ----------------------------------------------------------------------
def test_independence_dw(resid):
    """Durbin-Watson 检验残差自相关。DW∈[0,4]，≈2 表示无自相关（通过）；
    <1.5 正自相关、>2.5 负自相关（未通过，时序数据常见）。"""
    resid = np.asarray(resid, dtype=float).ravel()
    dw = float(durbin_watson(resid))
    passed = 1.5 <= dw <= 2.5
    print("③ 独立性 (Durbin-Watson)   DW=%.4f" % dw)
    if passed:
        print("   判定：通过 —— DW≈2，残差无明显自相关。")
    else:
        direction = '正自相关' if dw < 1.5 else '负自相关'
        print("   判定：未通过 —— 存在%s。建议：时序数据改用 ARIMA/加滞后项、" % direction)
        print("        或用广义最小二乘(GLS)；检查是否漏了时间趋势/季节项。")
    return {'name': '独立性', 'stat': dw, 'p': np.nan, 'passed': passed}


# ----------------------------------------------------------------------
# 4. 异方差：Breusch-Pagan（需自变量 X）
# ----------------------------------------------------------------------
def test_heteroscedasticity_bp(resid, X):
    """Breusch-Pagan 检验：残差方差是否随自变量线性变化。
    H0：同方差。p≥0.05 → 通过；p<0.05 → 异方差（未通过）。需提供自变量矩阵 X。"""
    resid = np.asarray(resid, dtype=float).ravel()
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    Xc = sm.add_constant(X)
    lm_stat, lm_p, f_stat, f_p = het_breuschpagan(resid, Xc)
    passed = lm_p >= ALPHA
    print("④ 异方差 (Breusch-Pagan)   LM=%.4f  p=%.4g" % (lm_stat, lm_p))
    if passed:
        print("   判定：通过 —— 无证据表明存在异方差。")
    else:
        print("   判定：未通过 —— 残差方差随自变量变化(异方差)。建议：y 做对数变换、")
        print("        WLS 加权回归、或用稳健标准误。")
    return {'name': '异方差', 'stat': lm_stat, 'p': lm_p, 'passed': passed}


# ----------------------------------------------------------------------
# 汇总 + 绘图
# ----------------------------------------------------------------------
def diagnose_residuals(y_true=None, y_pred=None, residuals=None, X=None,
                       save_path='05_残差诊断图.png'):
    """一站式残差诊断：传 (y_true, y_pred) 或直接传 residuals。
    若提供 X，则额外做 Breusch-Pagan 异方差检验。"""
    if residuals is None:
        if y_true is None or y_pred is None:
            raise ValueError("请提供 (y_true, y_pred) 或 residuals 之一。")
        y_true = np.asarray(y_true, dtype=float).ravel()
        y_pred = np.asarray(y_pred, dtype=float).ravel()
        residuals = y_true - y_pred
    else:
        residuals = np.asarray(residuals, dtype=float).ravel()
        if y_pred is None:
            # 没给预测值时，用序号占位（残差vs顺序），DW/正态仍有效
            y_pred = np.arange(residuals.size, dtype=float)

    print("=" * 64)
    print("残差诊断与假设检验（显著性水平 α=%.2f）" % ALPHA)
    print("=" * 64)
    results = []
    results.append(test_normality(residuals))
    results.append(test_homoscedasticity_levene(residuals, y_pred))
    results.append(test_independence_dw(residuals))
    if X is not None:
        results.append(test_heteroscedasticity_bp(residuals, X))
    else:
        print("④ 异方差 (Breusch-Pagan)：跳过（未提供自变量 X）。")

    # 汇总表
    print("-" * 64)
    print("汇总判定表：")
    n_pass = 0
    for r in results:
        flag = '通过' if r['passed'] else '未通过(需改进)'
        n_pass += int(r['passed'])
        pstr = ('p=%.4g' % r['p']) if not np.isnan(r['p']) else ('统计量=%.4f' % r['stat'])
        print("   %-8s %-10s (%s)" % (r['name'], flag, pstr))
    print("   通过 %d / %d 项。" % (n_pass, len(results)))
    if n_pass == len(results):
        print("   总体：模型残差满足经典假设，检验通过，结论稳健可信。")
    else:
        print("   总体：部分假设未满足，按上方建议修正后重估，或在论文中说明其影响。")

    # 绘图：残差vs预测 + 残差滞后自相关散点
    if _HAS_PLT:
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
            ax1.scatter(y_pred, residuals, s=18, alpha=0.6, color='#3b78c3')
            ax1.axhline(0, color='r', ls='--', lw=1.5)
            ax1.set_xlabel('预测值/顺序'); ax1.set_ylabel('残差')
            ax1.set_title('残差 vs 预测值（看方差齐性/系统偏差）'); ax1.grid(alpha=0.3)
            # 残差滞后图 e_t vs e_{t-1}，看独立性
            ax2.scatter(residuals[:-1], residuals[1:], s=18, alpha=0.6, color='#5aa469')
            ax2.set_xlabel('残差 e(t-1)'); ax2.set_ylabel('残差 e(t)')
            ax2.set_title('残差滞后图（无规律=独立；有斜率=自相关）'); ax2.grid(alpha=0.3)
            plt.tight_layout(); plt.savefig(save_path, dpi=120); plt.close(fig)
            print("[图已保存] %s" % save_path)
        except Exception as e:
            print("绘图跳过：", e)
    return results


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛模型残差：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   y_true = df['真实列'].values          # 观测值
    #   y_pred = df['预测列'].values          # 你模型的预测值
    #   X = df[['特征1','特征2']].values      # 自变量(做异方差 BP 检验用，可不给)
    #   diagnose_residuals(y_true=y_true, y_pred=y_pred, X=X)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    rng = np.random.RandomState(42)
    n = 150
    X = rng.uniform(0, 10, (n, 2))
    y_true = X @ np.array([2.0, -1.0]) + 5

    print("\n########## 演示 1：良好残差（正态、同方差、独立）##########")
    y_pred_good = y_true + rng.normal(0, 1.0, n)
    diagnose_residuals(y_true=y_true, y_pred=y_pred_good, X=X,
                       save_path='05_残差诊断图_好.png')

    print("\n########## 演示 2：问题残差（异方差 + 自相关）##########")
    # 异方差：噪声随第一个特征放大；自相关：叠加累积项
    hetero_noise = rng.normal(0, 0.3 + 0.5 * X[:, 0], n)
    ar_term = np.cumsum(rng.normal(0, 0.3, n))       # 制造正自相关
    y_pred_bad = y_true + hetero_noise + ar_term
    diagnose_residuals(y_true=y_true, y_pred=y_pred_bad, X=X,
                       save_path='05_残差诊断图_差.png')

    print("\n演示完成。把 y_true、y_pred（及可选 X）换成你模型的输出即可复用。")
