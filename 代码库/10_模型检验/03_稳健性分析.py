# -*- coding: utf-8 -*-
"""
================================================================================
03 稳健性分析 (Robustness Analysis)
================================================================================
功能：
    面向国赛 C 题“模型检验”第三大件——稳健性(鲁棒性)分析。核心问题是：
    “当数据被扰动/抽样变化/换模型时，结论还稳不稳？”本模板提供三种手段：
      ① 噪声注入：给输入数据加不同强度高斯噪声，看模型系数/预测/指标的偏移。
      ② 重采样：Bootstrap 自助重采样 + 变样本量，看结果分布的离散程度(置信区间)。
      ③ 同类模型对比：多个模型在同一数据上跑，比结果一致性（可选）。
    每种手段都给量化指标（相对变化、标准差、变异系数 CV）并可视化。

适用竞赛场景：
    - 优化/评价/预测/拟合模型建完后必做，说明结论对噪声与抽样的抗干扰能力。
    - 2026 自查表“五-3 稳健性分析”硬性要求。

输入格式：
    - X：特征矩阵 (n_samples, n_features)；y：目标一维 (n_samples,)。
    - fit_predict_func：f(X_train, y_train, X_eval) -> y_pred 的回调（默认线性回归）。

输出：
    - 控制台打印各噪声/样本量下的指标（RMSE/R²）及其波动；
    - 保存 03_稳健性_噪声.png、03_稳健性_bootstrap.png、03_稳健性_模型对比.png。

依赖：numpy, scikit-learn, (可选) matplotlib
================================================================================
"""

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_squared_error, r2_score

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
    plt.rcParams['axes.unicode_minus'] = False
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False


def _default_fit_predict(X_train, y_train, X_eval):
    """默认的建模-预测回调：普通线性回归。用户可替换为自己的模型。"""
    model = LinearRegression()
    model.fit(X_train, y_train)
    return model.predict(X_eval)


# ----------------------------------------------------------------------
# 手段 ①：噪声注入（给输入数据加高斯噪声）
# ----------------------------------------------------------------------
def noise_robustness(X, y, fit_predict_func=None,
                     noise_levels=(0.0, 0.05, 0.1, 0.2, 0.3), n_repeat=30, seed=0):
    """对特征 X 注入不同强度高斯噪声，观察预测精度(RMSE/R²)如何退化。

    参数:
        noise_levels: 噪声强度列表，表示噪声标准差 = level × 该特征本身的标准差。
        n_repeat:     每个噪声强度重复次数（取均值±标准差，抵消随机性）。
    返回:
        dict: {'levels':[...], 'rmse_mean':[...], 'rmse_std':[...],
               'r2_mean':[...], 'r2_std':[...]}
    解读:
        噪声增大时 RMSE 缓慢上升、R² 缓慢下降 = 稳健；断崖式恶化 = 不稳健。
    """
    if fit_predict_func is None:
        fit_predict_func = _default_fit_predict
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    rng = np.random.RandomState(seed)
    col_std = X.std(axis=0)                       # 各特征标准差，用于按比例加噪
    col_std[col_std == 0] = 1.0

    levels, rmse_mean, rmse_std, r2_mean, r2_std = [], [], [], [], []
    print("=" * 64)
    print("稳健性①：输入噪声注入（噪声强度 = level×特征标准差）")
    print("=" * 64)
    for lvl in noise_levels:
        rmses, r2s = [], []
        for _ in range(n_repeat):
            noise = rng.normal(0, 1, X.shape) * col_std * lvl
            X_noisy = X + noise
            y_pred = fit_predict_func(X_noisy, y, X_noisy)
            rmses.append(np.sqrt(mean_squared_error(y, y_pred)))
            r2s.append(r2_score(y, y_pred))
        levels.append(lvl)
        rmse_mean.append(np.mean(rmses)); rmse_std.append(np.std(rmses))
        r2_mean.append(np.mean(r2s)); r2_std.append(np.std(r2s))
        print("  噪声=%4.0f%%   RMSE=%.4f (±%.4f)   R²=%.4f (±%.4f)"
              % (lvl * 100, rmse_mean[-1], rmse_std[-1], r2_mean[-1], r2_std[-1]))

    res = {'levels': levels, 'rmse_mean': rmse_mean, 'rmse_std': rmse_std,
           'r2_mean': r2_mean, 'r2_std': r2_std}
    if _HAS_PLT:
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
            lv = np.array(levels) * 100
            ax1.errorbar(lv, rmse_mean, yerr=rmse_std, marker='o', capsize=4, color='#c0504d')
            ax1.set_xlabel('噪声强度 (%)'); ax1.set_ylabel('RMSE')
            ax1.set_title('噪声—RMSE（上升越慢越稳健）'); ax1.grid(alpha=0.3)
            ax2.errorbar(lv, r2_mean, yerr=r2_std, marker='s', capsize=4, color='#4f81bd')
            ax2.set_xlabel('噪声强度 (%)'); ax2.set_ylabel('R2')
            ax2.set_title('噪声—R2（下降越慢越稳健）'); ax2.grid(alpha=0.3)
            plt.tight_layout(); plt.savefig('03_稳健性_噪声.png', dpi=120); plt.close(fig)
            print("[图已保存] 03_稳健性_噪声.png")
        except Exception as e:
            print("绘图跳过：", e)
    return res


# ----------------------------------------------------------------------
# 手段 ②：Bootstrap 自助重采样 + 变样本量
# ----------------------------------------------------------------------
def bootstrap_robustness(X, y, fit_predict_func=None, n_boot=200, seed=0):
    """Bootstrap 自助重采样：有放回抽样重复建模，看关键指标(R²)的分布。

    分布越集中（标准差/变异系数越小）=结论对样本抽样越不敏感=越稳健。
    返回 R² 的均值、标准差、95% 置信区间。
    """
    if fit_predict_func is None:
        fit_predict_func = _default_fit_predict
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    n = X.shape[0]
    rng = np.random.RandomState(seed)
    r2_list = []
    for _ in range(n_boot):
        idx = rng.randint(0, n, n)                # 有放回抽样
        oob = np.setdiff1d(np.arange(n), idx)     # 袋外样本作评估集
        if oob.size < 2:
            continue
        y_pred = fit_predict_func(X[idx], y[idx], X[oob])
        r2_list.append(r2_score(y[oob], y_pred))
    r2_arr = np.array(r2_list)
    ci_lo, ci_hi = np.percentile(r2_arr, [2.5, 97.5])
    print("=" * 64)
    print("稳健性②：Bootstrap 自助重采样（n_boot=%d，袋外评估）" % n_boot)
    print("=" * 64)
    print("  R² 均值=%.4f   标准差=%.4f   95%%置信区间=[%.4f, %.4f]"
          % (r2_arr.mean(), r2_arr.std(), ci_lo, ci_hi))

    # 变样本量：抽 30%~100% 数据看指标随样本量的稳定性
    fracs = [0.3, 0.5, 0.7, 0.9, 1.0]
    frac_mean, frac_std = [], []
    print("-" * 64)
    print("  变样本量稳定性（每档重采样 %d 次）：" % 50)
    for f in fracs:
        m = max(3, int(n * f))
        vals = []
        for _ in range(50):
            idx = rng.choice(n, m, replace=False) if m <= n else rng.randint(0, n, m)
            if m < n:
                eval_idx = np.setdiff1d(np.arange(n), idx)
                if eval_idx.size < 2:
                    eval_idx = idx
            else:
                eval_idx = idx
            y_pred = fit_predict_func(X[idx], y[idx], X[eval_idx])
            vals.append(r2_score(y[eval_idx], y_pred))
        frac_mean.append(np.mean(vals)); frac_std.append(np.std(vals))
        print("    样本量=%4.0f%%   R²=%.4f (±%.4f)" % (f * 100, frac_mean[-1], frac_std[-1]))

    if _HAS_PLT:
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
            ax1.hist(r2_arr, bins=30, color='#5aa469', alpha=0.75, edgecolor='white')
            ax1.axvline(r2_arr.mean(), color='r', ls='--', lw=1.5, label='均值')
            ax1.axvline(ci_lo, color='gray', ls=':', lw=1.2)
            ax1.axvline(ci_hi, color='gray', ls=':', lw=1.2, label='95%CI')
            ax1.set_xlabel('R2'); ax1.set_ylabel('频数')
            ax1.set_title('Bootstrap R2 分布（越集中越稳健）'); ax1.legend(); ax1.grid(alpha=0.3)
            ax2.errorbar(np.array(fracs) * 100, frac_mean, yerr=frac_std,
                         marker='o', capsize=4, color='#4f81bd')
            ax2.set_xlabel('使用样本量占比 (%)'); ax2.set_ylabel('R2')
            ax2.set_title('样本量—R2（曲线平稳=结论稳定）'); ax2.grid(alpha=0.3)
            plt.tight_layout(); plt.savefig('03_稳健性_bootstrap.png', dpi=120); plt.close(fig)
            print("[图已保存] 03_稳健性_bootstrap.png")
        except Exception as e:
            print("绘图跳过：", e)
    return {'r2_mean': float(r2_arr.mean()), 'r2_std': float(r2_arr.std()),
            'ci': (float(ci_lo), float(ci_hi))}


# ----------------------------------------------------------------------
# 手段 ③：同类模型对比（可选）
# ----------------------------------------------------------------------
def model_comparison_robustness(X, y, models=None, seed=0):
    """用多个同类模型在同一数据上跑，比结论一致性。结果越接近=越稳健。"""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    if models is None:
        models = {
            '线性回归': LinearRegression(),
            '岭回归Ridge': Ridge(alpha=1.0),
            '决策树': DecisionTreeRegressor(max_depth=5, random_state=seed),
        }
    print("=" * 64)
    print("稳健性③：同类模型对比（R² 越接近=结论越不依赖模型选择）")
    print("=" * 64)
    names, r2s = [], []
    for name, model in models.items():
        model.fit(X, y)
        r2 = r2_score(y, model.predict(X))
        names.append(name); r2s.append(r2)
        print("  %-12s R²=%.4f" % (name, r2))
    cv = np.std(r2s) / abs(np.mean(r2s)) if np.mean(r2s) != 0 else np.nan
    print("  R² 变异系数 CV=%.4f（越小说明各模型结论越一致、越稳健）" % cv)

    if _HAS_PLT:
        try:
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.bar(names, r2s, color=['#4f81bd', '#c0504d', '#9bbb59'], alpha=0.85)
            for i, v in enumerate(r2s):
                ax.text(i, v, '%.3f' % v, ha='center', va='bottom')
            ax.set_ylabel('R2'); ax.set_title('同类模型 R2 对比（柱高越接近越稳健）')
            ax.grid(alpha=0.3, axis='y')
            plt.tight_layout(); plt.savefig('03_稳健性_模型对比.png', dpi=120); plt.close(fig)
            print("[图已保存] 03_稳健性_模型对比.png")
        except Exception as e:
            print("绘图跳过：", e)
    return dict(zip(names, r2s))


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   X = df[['特征1','特征2','特征3']].values   # 特征矩阵 (n_samples, k)
    #   y = df['目标列'].values                     # 目标 (n_samples,)
    #   # 若想检验“你自己的模型”而非默认线性回归，自定义一个回调：
    #   #   def my_fp(X_tr, y_tr, X_ev):
    #   #       m = 你的模型(); m.fit(X_tr, y_tr); return m.predict(X_ev)
    #   #   noise_robustness(X, y, fit_predict_func=my_fp)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    rng = np.random.RandomState(42)
    n, k = 150, 3
    X = rng.uniform(0, 10, (n, k))
    true_coef = np.array([2.0, -1.5, 0.8])
    y = X @ true_coef + 5 + rng.normal(0, 1.5, n)

    print("\n########## 稳健性分析三手段演示 ##########")
    noise_robustness(X, y)
    bootstrap_robustness(X, y, n_boot=200)
    model_comparison_robustness(X, y)

    print("\n演示完成。把 X、y 换成你的数据；要检验自己的模型就传 fit_predict_func。")
