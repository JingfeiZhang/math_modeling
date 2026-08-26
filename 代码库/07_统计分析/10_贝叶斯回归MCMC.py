# -*- coding: utf-8 -*-
"""
贝叶斯回归 + MCMC（Metropolis-Hastings 手写采样）
================================================================
功能：
    用贝叶斯框架估计回归参数，得到的不是一个点估计，而是参数的“后验分布”，
    从而天然给出参数与预测的不确定性区间（可信区间 credible interval）。
    适合 2023C 这类“价格弹性/需求参数需要带不确定性”的场景，
    也是评委眼里的加分项：能说清“我的系数有多大把握”。

    只用 numpy 手写 Metropolis-Hastings，Windows 零编译、必跑
    （PyMC/Stan 常难装）。若已装 pymc，末尾注释给出等价写法可升级。

模型：
    y = β0 + β1·x + ε,  ε ~ N(0, σ²)
    先验：β ~ N(0, 10²)（弱信息）, σ ~ HalfNormal 近似（对 logσ 采样）
    采样 logσ 保证 σ>0，无需拒绝负值。

输入：x, y（一维数组）；可推广到多元（把 x 换成设计矩阵）
输出：各参数后验均值 / 标准差 / 94% 可信区间；预测带区间

依赖：numpy, pandas；可选 matplotlib（迹线图/后验直方图）
运行：PYTHONIOENCODING=utf-8 python 10_贝叶斯回归MCMC.py
================================================================
"""
import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
    plt.rcParams['axes.unicode_minus'] = False
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False


def _log_post(theta, x, y, beta_sd=100.0, sigma_sd=50.0):
    """对数后验 = 对数似然 + 对数先验。theta=[β0, β1, logσ]。
       beta_sd 取大值 → 弱信息先验（不把系数往 0 拉，让数据说话）。"""
    b0, b1, log_sigma = theta
    sigma = np.exp(log_sigma)
    mu = b0 + b1 * x
    # 似然：正态
    ll = -0.5 * np.sum(((y - mu) / sigma) ** 2) - len(y) * log_sigma
    # 先验：β ~ N(0, beta_sd²) 弱信息；σ ~ HalfNormal(sigma_sd) → 对 logσ 加 jacobian
    lp = -0.5 * (b0**2 + b1**2) / beta_sd**2
    lp += -0.5 * (sigma / sigma_sd) ** 2 + log_sigma   # halfnormal + jacobian
    return ll + lp


def metropolis(x, y, n_samples=20000, burn=4000, step=None, seed=0):
    """随机游走 Metropolis-Hastings。返回 (采样后验 DataFrame, 接受率)。"""
    rng = np.random.default_rng(seed)
    # 用 OLS 作初值，加速收敛
    A = np.column_stack([np.ones_like(x), x])
    b_ols, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ b_ols
    theta = np.array([b_ols[0], b_ols[1], np.log(resid.std() + 1e-6)])
    if step is None:
        step = np.array([1.2, 0.16, 0.1])   # 各维提议步长（调至接受率 0.2~0.5）

    logp = _log_post(theta, x, y)
    samples = np.zeros((n_samples, 3))
    n_acc = 0
    for i in range(n_samples):
        prop = theta + step * rng.standard_normal(3)
        logp_prop = _log_post(prop, x, y)
        if np.log(rng.random()) < logp_prop - logp:   # 接受准则
            theta, logp = prop, logp_prop
            n_acc += 1
        samples[i] = theta

    acc = n_acc / n_samples
    post = samples[burn:]
    df = pd.DataFrame(post, columns=['β0(截距)', 'β1(斜率)', 'logσ'])
    df['σ'] = np.exp(df['logσ'])
    return df, acc


def summarize(df):
    """后验汇总：均值、标准差、94% 可信区间。"""
    rows = []
    for c in ['β0(截距)', 'β1(斜率)', 'σ']:
        s = df[c].values
        rows.append({
            '参数': c, '后验均值': s.mean(), '后验std': s.std(),
            '2.5%': np.percentile(s, 2.5), '97.5%': np.percentile(s, 97.5)})
    return pd.DataFrame(rows)


def predict(df, x_new, n_draw=2000, seed=1):
    """后验预测：对每个采样参数生成预测，返回均值与 95% 预测区间。"""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(df), n_draw)
    b0 = df['β0(截距)'].values[idx]
    b1 = df['β1(斜率)'].values[idx]
    sig = df['σ'].values[idx]
    x_new = np.atleast_1d(x_new)
    preds = np.zeros((n_draw, len(x_new)))
    for j, xv in enumerate(x_new):
        mu = b0 + b1 * xv
        preds[:, j] = mu + sig * rng.standard_normal(n_draw)   # 含观测噪声的后验预测
    return pd.DataFrame({
        'x': x_new,
        '预测均值': preds.mean(axis=0),
        '下界2.5%': np.percentile(preds, 2.5, axis=0),
        '上界97.5%': np.percentile(preds, 97.5, axis=0)})


if __name__ == '__main__':
    # 演示：价格 x → 销量 y，真值 β0=80, β1=-6, σ=4
    rng = np.random.default_rng(7)
    n = 60
    x = rng.uniform(4, 10, n)
    y = 80 - 6 * x + rng.normal(0, 4, n)

    print("=" * 60)
    print("贝叶斯回归 + MCMC（Metropolis-Hastings）演示")
    print("真值: β0=80, β1=-6, σ=4")
    print("=" * 60)
    post, acc = metropolis(x, y, n_samples=20000, burn=4000)
    print(f"[采样] 接受率={acc:.3f}（0.2~0.5 为宜，过低/过高需调 step）\n")

    print("[后验汇总]")
    print(summarize(post).round(3).to_string(index=False))

    print("\n[后验预测] 价格=5,7,9 时的销量（含预测区间）")
    pred = predict(post, [5, 7, 9])
    print(pred.round(3).to_string(index=False))

    print("\n解读：β1 的 94% 可信区间若整体 <0，说明‘涨价降销量’在统计上可信；"
          "\n区间宽度反映把握程度，可直接写进论文的敏感性/不确定性分析。")

    if _HAS_PLT:
        try:
            fig, axes = plt.subplots(1, 3, figsize=(14, 4))
            for ax, c in zip(axes, ['β0(截距)', 'β1(斜率)', 'σ']):
                ax.hist(post[c], bins=40, color='steelblue', alpha=0.8)
                ax.axvline(post[c].mean(), color='red', ls='--', label='后验均值')
                ax.set_title(f'{c} 后验分布'); ax.legend()
            plt.tight_layout()
            plt.savefig('贝叶斯后验分布.png', dpi=120, bbox_inches='tight')
            print("\n[图] 已保存 贝叶斯后验分布.png")
        except Exception as e:
            print(f"绘图跳过: {e}")

    # ===== 若已安装 PyMC，可替换为： =====
    # import pymc as pm
    # with pm.Model() as m:
    #     b0 = pm.Normal('b0', 0, 10); b1 = pm.Normal('b1', 0, 10)
    #     sigma = pm.HalfNormal('sigma', 10)
    #     pm.Normal('y', b0 + b1*x, sigma, observed=y)
    #     idata = pm.sample(2000, tune=1000)
    # pm.summary(idata)
