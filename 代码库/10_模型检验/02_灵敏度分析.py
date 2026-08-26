# -*- coding: utf-8 -*-
"""
================================================================================
02 灵敏度分析 (Sensitivity Analysis, OAT 一次一参数扰动)
================================================================================
功能：
    面向国赛 C 题“模型检验”第二大件——灵敏度分析。核心问题是：
    “当模型的关键参数/输入在基准值附近波动时，输出结果变化有多大？”
    本模板提供：
      1. 单参数扰动：对每个参数按 ±10% / ±20% / ±30% 扰动，看输出变化率。
      2. 龙卷风图 (Tornado)：把各参数在给定扰动下引起的输出摆幅横向排序，
         一眼看出“哪个参数最敏感”。
      3. 敏感度曲线：把某参数在连续区间上扫描，画“参数—输出”曲线。
      4. 局部灵敏度系数：S = (Δ输出/输出) / (Δ参数/参数)，无量纲弹性，便于横比。

适用竞赛场景：
    - 优化/评价/预测模型建完后必做：说明结论对参数假设的稳健程度。
    - 2026 自查表“五-3 灵敏度分析”硬性要求。经济类 C 题尤其常考
      （价格、成本、需求弹性对利润的影响）。

输入格式：
    - model_func：一个可调用对象 f(**params) -> 标量输出（你的模型/目标函数）。
    - base_params：dict，各参数的基准取值，如 {'价格':50,'成本':30,'销量':1000}。

输出：
    - 控制台打印各参数在各扰动比例下的输出与变化率、局部灵敏度系数排序；
    - 保存龙卷风图 02_龙卷风图.png 与敏感度曲线 02_敏感度曲线.png。

依赖：numpy, (可选) matplotlib
================================================================================
"""

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
    plt.rcParams['axes.unicode_minus'] = False
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False


# ----------------------------------------------------------------------
# 1. 单参数 OAT 扰动分析
# ----------------------------------------------------------------------
def oat_sensitivity(model_func, base_params, perturb_ratios=(-0.3, -0.2, -0.1, 0.1, 0.2, 0.3)):
    """OAT(One-At-a-Time)一次只动一个参数的灵敏度分析。

    参数:
        model_func:  f(**params) -> 标量。你的模型/目标函数。
        base_params: dict，参数基准值。
        perturb_ratios: 扰动比例元组，默认 ±10%/±20%/±30%。
    返回:
        dict: {参数名: {'ratios':[...], 'outputs':[...], 'rel_changes':[...]}}
        另附 base_output（基准输出）。
    原理:
        固定其它参数为基准值，只让目标参数乘以 (1+ratio)，记录输出变化。
        输出相对变化率 = (扰动后输出 - 基准输出) / |基准输出|。
    """
    base_output = float(model_func(**base_params))
    result = {'__base_output__': base_output}
    print("=" * 64)
    print("单参数灵敏度分析 (OAT)   基准输出 = %.4f" % base_output)
    print("=" * 64)
    for pname, pval in base_params.items():
        ratios, outputs, rel_changes = [], [], []
        for r in perturb_ratios:
            p = dict(base_params)
            p[pname] = pval * (1 + r)
            out = float(model_func(**p))
            ratios.append(r)
            outputs.append(out)
            rel = (out - base_output) / abs(base_output) if base_output != 0 else np.nan
            rel_changes.append(rel)
        result[pname] = {'ratios': ratios, 'outputs': outputs, 'rel_changes': rel_changes}
        # 打印该参数在各扰动下的输出变化率
        print("参数 [%s] 基准=%.4g:" % (pname, pval))
        for r, out, rel in zip(ratios, outputs, rel_changes):
            print("    参数%+4.0f%%  ->  输出=%10.4f   变化率=%+7.2f%%"
                  % (r * 100, out, rel * 100))
    return result


def local_sensitivity_coef(model_func, base_params, eps=0.01):
    """局部灵敏度系数（弹性 elasticity）：S_i = (∂y/y)/(∂x_i/x_i)。

    用中心差分近似偏导。|S| 越大越敏感；S>0 正相关，S<0 负相关。
    eps 为相对步长（默认 1%），太大不准、太小受数值噪声影响。
    """
    base_output = float(model_func(**base_params))
    coefs = {}
    for pname, pval in base_params.items():
        if pval == 0:
            coefs[pname] = np.nan
            continue
        p_hi = dict(base_params); p_hi[pname] = pval * (1 + eps)
        p_lo = dict(base_params); p_lo[pname] = pval * (1 - eps)
        y_hi = float(model_func(**p_hi))
        y_lo = float(model_func(**p_lo))
        # 弹性 = (Δy/y) / (Δx/x)
        dy = (y_hi - y_lo) / base_output if base_output != 0 else np.nan
        dx = 2 * eps
        coefs[pname] = dy / dx
    print("-" * 64)
    print("局部灵敏度系数（弹性，|值|越大越敏感）：")
    for pname, s in sorted(coefs.items(), key=lambda kv: -abs(kv[1]) if not np.isnan(kv[1]) else 0):
        print("    %-10s S = %+8.4f" % (pname, s))
    return coefs


# ----------------------------------------------------------------------
# 2. 龙卷风图（Tornado）
# ----------------------------------------------------------------------
def plot_tornado(model_func, base_params, ratio=0.2, save_path='02_龙卷风图.png'):
    """龙卷风图：在 ±ratio 扰动下，各参数引起的输出上下摆幅横条排序。

    条越长=该参数对输出影响越大（越敏感）。ratio 默认 ±20%。
    """
    base_output = float(model_func(**base_params))
    rows = []
    for pname, pval in base_params.items():
        p_hi = dict(base_params); p_hi[pname] = pval * (1 + ratio)
        p_lo = dict(base_params); p_lo[pname] = pval * (1 - ratio)
        out_hi = float(model_func(**p_hi))
        out_lo = float(model_func(**p_lo))
        span = abs(out_hi - out_lo)
        rows.append((pname, out_lo, out_hi, span))
    rows.sort(key=lambda t: t[3])   # 摆幅从小到大，画出来最敏感的在最上面
    print("-" * 64)
    print("龙卷风图数据（±%.0f%% 扰动，按输出摆幅排序）：" % (ratio * 100))
    for pname, lo, hi, span in reversed(rows):
        print("    %-10s 低=%.4f  高=%.4f  摆幅=%.4f" % (pname, lo, hi, span))

    if not _HAS_PLT:
        print("[提示] 未检测到 matplotlib，跳过绘图。")
        return rows
    try:
        names = [r[0] for r in rows]
        y_pos = np.arange(len(names))
        fig, ax = plt.subplots(figsize=(9, 0.7 * len(names) + 2))
        for i, (pname, lo, hi, span) in enumerate(rows):
            left, right = min(lo, hi), max(lo, hi)
            ax.barh(i, right - base_output, left=base_output,
                    color='#c0504d', alpha=0.8)
            ax.barh(i, left - base_output, left=base_output,
                    color='#4f81bd', alpha=0.8)
        ax.axvline(base_output, color='k', lw=1.2, ls='--', label='基准输出')
        ax.set_yticks(y_pos); ax.set_yticklabels(names)
        ax.set_xlabel('输出值'); ax.set_title('龙卷风图（±%.0f%% 扰动，条越长越敏感）' % (ratio * 100))
        ax.legend(loc='lower right'); ax.grid(alpha=0.3, axis='x')
        plt.tight_layout()
        plt.savefig(save_path, dpi=120)
        plt.close(fig)
        print("[图已保存] %s" % save_path)
    except Exception as e:
        print("绘图跳过：", e)
    return rows


# ----------------------------------------------------------------------
# 3. 敏感度曲线（单参数连续扫描）
# ----------------------------------------------------------------------
def plot_sensitivity_curves(model_func, base_params, scan_ratio=0.4, n_points=41,
                            save_path='02_敏感度曲线.png'):
    """把每个参数在 [基准×(1-scan_ratio), 基准×(1+scan_ratio)] 上连续扫描，
    画“参数取值 — 模型输出”曲线。曲线越陡=越敏感。"""
    base_output = float(model_func(**base_params))
    curves = {}
    for pname, pval in base_params.items():
        xs = np.linspace(pval * (1 - scan_ratio), pval * (1 + scan_ratio), n_points)
        ys = []
        for xv in xs:
            p = dict(base_params); p[pname] = xv
            ys.append(float(model_func(**p)))
        curves[pname] = (xs, np.array(ys))

    if not _HAS_PLT:
        print("[提示] 未检测到 matplotlib，跳过敏感度曲线绘图。")
        return curves
    try:
        # 用“相对基准的百分比变化”统一横纵坐标，便于把多参数画在一张图对比
        fig, ax = plt.subplots(figsize=(9, 6))
        rel_axis = np.linspace(-scan_ratio, scan_ratio, n_points) * 100
        for pname, (xs, ys) in curves.items():
            rel_out = (ys - base_output) / abs(base_output) * 100 if base_output != 0 else ys
            ax.plot(rel_axis, rel_out, marker='o', ms=3, lw=1.8, label=pname)
        ax.axhline(0, color='gray', lw=0.8)
        ax.axvline(0, color='gray', lw=0.8)
        ax.set_xlabel('参数相对基准的变化 (%)')
        ax.set_ylabel('输出相对基准的变化 (%)')
        ax.set_title('敏感度曲线（斜率越陡=该参数越敏感）')
        ax.legend(); ax.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(save_path, dpi=120)
        plt.close(fig)
        print("[图已保存] %s" % save_path)
    except Exception as e:
        print("绘图跳过：", e)
    return curves


# ----------------------------------------------------------------------
# 演示：一个简单的利润模型  利润 = (价格 - 单位成本) * 销量 - 固定成本
# ----------------------------------------------------------------------
def profit_model(价格, 单位成本, 销量, 固定成本):
    """示例模型：利润 = (售价 - 单位成本) × 销量 - 固定成本。
    这是最典型的经济类 C 题目标函数，参数含义直观、便于讲敏感度。"""
    return (价格 - 单位成本) * 销量 - 固定成本


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛模型做灵敏度分析：把下面的 profit_model 换成你的模型函数
    #   - 你的模型必须能写成 f(**params) -> 一个标量输出（利润/成本/评分/预测值…）。
    #   - 若模型是 sklearn 训练好的 model，可包一层：
    #       def my_model(特征1, 特征2, 特征3):
    #           import numpy as np
    #           return float(model.predict(np.array([[特征1,特征2,特征3]]))[0])
    #   - base_params 填各参数的“基准值”（如题目给定的现状/最优解）。
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面你自己的模型后可删除)
    base = {'价格': 50.0, '单位成本': 30.0, '销量': 1000.0, '固定成本': 5000.0}

    print("\n########## 演示：利润模型的灵敏度分析 ##########")
    # 1) 单参数 ±10/20/30% 扰动
    oat_sensitivity(profit_model, base)
    # 2) 局部灵敏度系数（弹性）排序
    local_sensitivity_coef(profit_model, base)
    # 3) 龙卷风图
    plot_tornado(profit_model, base, ratio=0.2)
    # 4) 敏感度曲线
    plot_sensitivity_curves(profit_model, base, scan_ratio=0.4)

    print("\n结论示例：价格与销量对利润最敏感，固定成本影响最小——")
    print("把 profit_model 换成你的模型函数、base 换成基准参数即可复用。")
