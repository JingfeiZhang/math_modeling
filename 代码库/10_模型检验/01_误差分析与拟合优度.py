# -*- coding: utf-8 -*-
"""
================================================================================
01 误差分析与拟合优度 (Error Analysis & Goodness-of-Fit)
================================================================================
功能：
    面向国赛 C 题“模型检验”环节的第一大件——误差分析。给定真实值 y_true 与
    模型预测值 y_pred，一次性算全套误差/拟合优度指标，并画出四张诊断图：
      1. 误差指标：R²、调整 R²、MAE、MSE、RMSE、MAPE、SMAPE、最大误差、解释方差
      2. 残差图（残差 vs 预测值，看是否有系统性偏差/异方差）
      3. 残差分布直方图（叠正态曲线，看误差是否近似正态、有无偏态）
      4. Q-Q 图（残差正态性的图形检验）
      5. 真实值 vs 预测值散点图（含 y=x 参考线，越贴近对角线越好）

适用竞赛场景：
    - 任何回归/预测模型建完后的“检验”步骤：回归、时间序列、随机森林、神经网络…
    - 2026 自查表“五-3 误差分析”硬性要求，是论文“建模→求解→检验→分析”闭环的检验环。

输入格式：
    - y_true：真实值，一维数组/Series，长度 n。
    - y_pred：模型预测值，一维数组/Series，长度 n（与 y_true 一一对应）。
    - 可选 n_params：模型自变量/参数个数，用于计算“调整 R²”（不给则按 1）。

输出：
    - 控制台打印全套误差指标表；
    - 保存诊断四联图 PNG：01_误差诊断图.png。

依赖：numpy, scipy, (可选) matplotlib
================================================================================
"""

import sys
# 兼容 Windows GBK 控制台：把标准输出切到 UTF-8，避免 R²/± 等字符报 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np
from scipy import stats

# matplotlib 为可选依赖：无图形环境时自动降级为“只算不画”
try:
    import matplotlib
    matplotlib.use('Agg')            # 无界面环境安全（测试用；用户本地可删）
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']  # 中文
    plt.rcParams['axes.unicode_minus'] = False                        # 负号
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False


# ----------------------------------------------------------------------
# 全套误差 / 拟合优度指标
# ----------------------------------------------------------------------
def error_metrics(y_true, y_pred, n_params=1):
    """计算回归/预测的全套误差与拟合优度指标。

    参数:
        y_true:  真实值序列（一维）
        y_pred:  预测值序列（一维，与 y_true 等长）
        n_params: 模型自变量个数 k（用于调整 R²）。默认 1。
    返回:
        dict，包含 R2 / 调整R2 / MAE / MSE / RMSE / MAPE(%) / SMAPE(%) /
        MaxError / ExplainedVar 等。
    指标含义速记:
        - R²(决定系数): 模型解释了因变量多少方差, 越接近 1 越好, 可能为负(比均值还差)。
        - 调整R²: 惩罚自变量个数, 多元/对比不同复杂度模型时看它更公平。
        - MAE(平均绝对误差): 与 y 同量纲, 直观。
        - MSE/RMSE(均方误差/其平方根): RMSE 与 y 同量纲, 对大误差更敏感。
        - MAPE(平均绝对百分比误差): 无量纲(%), 便于跨量纲比较; y 有 0 值时不稳。
        - SMAPE(对称 MAPE): 缓解 MAPE 在真实值偏小时爆炸的问题。
    """
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    if y_true.shape != y_pred.shape:
        raise ValueError("y_true 与 y_pred 长度必须一致：%s vs %s"
                         % (y_true.shape, y_pred.shape))
    n = y_true.size
    err = y_true - y_pred

    mae = float(np.mean(np.abs(err)))
    mse = float(np.mean(err ** 2))
    rmse = float(np.sqrt(mse))
    max_err = float(np.max(np.abs(err)))

    # MAPE：排除真实值为 0 的点避免除零
    mask = y_true != 0
    mape = float(np.mean(np.abs(err[mask] / y_true[mask])) * 100) if mask.any() else np.nan
    # SMAPE：对称百分比误差，分母用 |真实|+|预测|
    denom = np.abs(y_true) + np.abs(y_pred)
    smask = denom != 0
    smape = float(np.mean(2 * np.abs(err[smask]) / denom[smask]) * 100) if smask.any() else np.nan

    # R² 与调整 R²
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    # 调整 R² = 1 - (1-R²)(n-1)/(n-k-1)
    if ss_tot > 0 and (n - n_params - 1) > 0:
        adj_r2 = 1 - (1 - r2) * (n - 1) / (n - n_params - 1)
    else:
        adj_r2 = np.nan

    # 解释方差得分（与 R² 类似，但不含系统性偏差项）
    var_y = float(np.var(y_true))
    explained_var = 1 - float(np.var(err)) / var_y if var_y > 0 else np.nan

    return {
        'R2': r2, '调整R2': adj_r2, 'MAE': mae, 'MSE': mse, 'RMSE': rmse,
        'MAPE(%)': mape, 'SMAPE(%)': smape, 'MaxError': max_err,
        '解释方差': explained_var, '样本数n': n,
    }


def print_error_report(y_true, y_pred, n_params=1, name='模型'):
    """打印格式化的误差分析报告，并给出简单的拟合优度评级。"""
    m = error_metrics(y_true, y_pred, n_params=n_params)
    print("=" * 64)
    print("误差分析报告 —— %s" % name)
    print("=" * 64)
    print("  样本数 n           = %d" % m['样本数n'])
    print("  R² (决定系数)      = %.4f" % m['R2'])
    print("  调整 R²            = %.4f" % m['调整R2'])
    print("  MAE (平均绝对误差) = %.4f" % m['MAE'])
    print("  MSE (均方误差)     = %.4f" % m['MSE'])
    print("  RMSE(均方根误差)   = %.4f" % m['RMSE'])
    print("  MAPE (%%)           = %.2f%%" % m['MAPE(%)'])
    print("  SMAPE(%%)           = %.2f%%" % m['SMAPE(%)'])
    print("  最大绝对误差       = %.4f" % m['MaxError'])
    print("  解释方差得分       = %.4f" % m['解释方差'])
    # 拟合优度评级（经验阈值，论文里可作参考）
    r2 = m['R2']
    if np.isnan(r2):
        grade = '无法评级(y 方差为 0)'
    elif r2 >= 0.9:
        grade = '优（R²≥0.9，拟合很好）'
    elif r2 >= 0.75:
        grade = '良（0.75≤R²<0.9）'
    elif r2 >= 0.5:
        grade = '中（0.5≤R²<0.75，可接受但有改进空间）'
    else:
        grade = '差（R²<0.5，需重选模型或加特征）'
    print("  拟合优度评级       : %s" % grade)
    print("-" * 64)
    return m


# ----------------------------------------------------------------------
# 诊断四联图：残差图 / 残差直方图 / Q-Q 图 / 真实vs预测
# ----------------------------------------------------------------------
def plot_diagnostics(y_true, y_pred, save_path='01_误差诊断图.png', name='模型'):
    """绘制误差诊断四联图。无 matplotlib 时自动跳过。"""
    if not _HAS_PLT:
        print("[提示] 未检测到 matplotlib，跳过绘图（计算不受影响）。")
        return
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    resid = y_true - y_pred
    try:
        fig, axes = plt.subplots(2, 2, figsize=(13, 10))

        # (1) 残差 vs 预测值：理想是随机散布在 0 线两侧、无喇叭口/曲线趋势
        ax = axes[0, 0]
        ax.scatter(y_pred, resid, s=18, alpha=0.6, color='#3b78c3')
        ax.axhline(0, color='r', lw=1.5, ls='--')
        ax.set_xlabel('预测值'); ax.set_ylabel('残差 (真实-预测)')
        ax.set_title('残差图（应无系统性趋势/喇叭口）'); ax.grid(alpha=0.3)

        # (2) 残差分布直方图 + 正态密度曲线
        ax = axes[0, 1]
        ax.hist(resid, bins=max(10, int(np.sqrt(resid.size))), density=True,
                alpha=0.65, color='#5aa469', edgecolor='white')
        mu, sigma = float(np.mean(resid)), float(np.std(resid))
        if sigma > 0:
            xs = np.linspace(resid.min(), resid.max(), 200)
            ax.plot(xs, stats.norm.pdf(xs, mu, sigma), 'r-', lw=2, label='正态拟合')
            ax.legend()
        ax.set_xlabel('残差'); ax.set_ylabel('密度')
        ax.set_title('残差分布直方图（应近似正态、居中于0）'); ax.grid(alpha=0.3)

        # (3) Q-Q 图：残差分位数 vs 正态分位数，点贴近直线说明近似正态
        ax = axes[1, 0]
        stats.probplot(resid, dist='norm', plot=ax)
        ax.set_title('残差 Q-Q 图（点贴近红线=近似正态）'); ax.grid(alpha=0.3)

        # (4) 真实 vs 预测：点越贴近 y=x 越好
        ax = axes[1, 1]
        ax.scatter(y_true, y_pred, s=18, alpha=0.6, color='#c3733b')
        lo = min(y_true.min(), y_pred.min())
        hi = max(y_true.max(), y_pred.max())
        ax.plot([lo, hi], [lo, hi], 'r--', lw=1.5, label='y=x 理想线')
        ax.set_xlabel('真实值'); ax.set_ylabel('预测值')
        ax.set_title('真实值 vs 预测值（越贴近对角线越好）')
        ax.legend(); ax.grid(alpha=0.3)

        fig.suptitle('误差诊断四联图 —— %s' % name, fontsize=14)
        plt.tight_layout(rect=(0, 0, 1, 0.97))
        plt.savefig(save_path, dpi=120)
        plt.close(fig)
        print("[图已保存] %s" % save_path)
    except Exception as e:
        print("绘图跳过：", e)


# ----------------------------------------------------------------------
# 演示：自带示例数据
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 误差分析只需要“真实值”和“模型预测值”两列（预测值来自你已建好的模型）
    #   y_true = df['真实列'].values      # 观测/真实值 (n,)
    #   y_pred = df['预测列'].values      # 你的模型输出的预测值 (n,)
    #   # 若预测值还没算：先用 03_预测类模型 里的模型 model.predict(X) 得到 y_pred
    #   n_params = 3                       # 你模型里自变量/参数的个数，用于调整R²
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    rng = np.random.RandomState(42)
    n = 120
    x = np.linspace(0, 10, n)
    y_true = 2.5 * x + 3.0                      # 真实规律
    # 模拟一个还不错的模型预测：真实值上叠加正态误差
    y_pred = y_true + rng.normal(0, 1.6, n)

    print("\n########## 演示 1：拟合较好的模型 ##########")
    print_error_report(y_true, y_pred, n_params=1, name='线性预测(好)')
    plot_diagnostics(y_true, y_pred, save_path='01_误差诊断图.png', name='线性预测(好)')

    print("\n########## 演示 2：存在系统性偏差的模型（对比看残差图）##########")
    # 故意制造异方差 + 系统性偏差：误差随 x 增大而放大，且整体偏低
    y_pred_bad = y_true - 0.05 * x ** 2 + rng.normal(0, 0.5 + 0.4 * x, n)
    print_error_report(y_true, y_pred_bad, n_params=1, name='线性预测(有偏差)')
    plot_diagnostics(y_true, y_pred_bad, save_path='01_误差诊断图_差.png', name='线性预测(有偏差)')

    print("\n演示完成。把 y_true、y_pred 换成你模型的真实值与预测值即可复用。")
