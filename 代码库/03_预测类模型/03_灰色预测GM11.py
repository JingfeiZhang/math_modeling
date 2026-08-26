# -*- coding: utf-8 -*-
"""
03 灰色预测模型 GM(1,1) (Grey Model)
================================================================
功能：
    面向国赛 C 题中的“小样本、贫信息”预测场景（数据点常见 4~15 个）：
      1. 级比检验（判断数据是否适合建 GM(1,1)，含平移变换补救）；
      2. GM(1,1) 建模：一次累加(1-AGO) → 均值生成 → 最小二乘估参 (a,b)；
      3. 时间响应函数还原预测值；
      4. 模型精度检验：相对残差、后验差比 C、小误差概率 P（含精度等级）；
      5. 向后小样本预测 + 预测误差评估 RMSE / MAE / MAPE。

    适用：数据量少、近似指数增长/单调趋势的序列。数据波动剧烈或有明显
    季节性时不适用（应改用 ARIMA / 指数平滑 / 机器学习）。

输入格式：
    - 一维原始序列（list / np.ndarray），要求为正数、等时间间隔、单调性较好。
    - n_predict：向后预测的点数。

输出：
    - 发展系数 a、灰作用量 b、拟合值、预测值、精度等级与误差指标。

依赖：numpy, (可选) matplotlib
运行：python 03_灰色预测GM11.py
"""

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np

try:
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False


def forecast_metrics(y_true, y_pred):
    """预测误差指标：RMSE / MAE / MAPE(%)。"""
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    err = y_true - y_pred
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mae = float(np.mean(np.abs(err)))
    mask = y_true != 0
    mape = float(np.mean(np.abs(err[mask] / y_true[mask])) * 100) if mask.any() else np.nan
    return {'RMSE': rmse, 'MAE': mae, 'MAPE(%)': mape}


# ----------------------------------------------------------------------
# 1. 级比检验：判断序列是否适合建 GM(1,1)
# ----------------------------------------------------------------------
def level_ratio_test(x):
    """级比检验。级比 λ(k)=x(k-1)/x(k) 需全部落在 (e^{-2/(n+1)}, e^{2/(n+1)})。

    返回:
        ok: 是否全部通过；ratios: 级比序列；(lo, hi): 可容覆盖区间。
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    lo, hi = np.exp(-2.0 / (n + 1)), np.exp(2.0 / (n + 1))
    ratios = x[:-1] / x[1:]
    ok = bool(np.all((ratios > lo) & (ratios < hi)))
    print("级比检验：可容覆盖区间=(%.4f, %.4f)" % (lo, hi))
    print("  级比范围=[%.4f, %.4f]  →  %s"
          % (ratios.min(), ratios.max(), '全部通过' if ok else '存在越界(建议平移变换)'))
    return ok, ratios, (lo, hi)


def shift_transform(x, c=None):
    """平移变换：级比检验不通过时，对序列加常数 c，改善数据适配性。"""
    x = np.asarray(x, dtype=float)
    if c is None:
        c = float(np.max(x))    # 常用平移量，可自行调节
    print("  执行平移变换：整体 +%.4f（预测后需减回还原）" % c)
    return x + c, c


# ----------------------------------------------------------------------
# 2. GM(1,1) 建模与预测
# ----------------------------------------------------------------------
def gm11(x, n_predict=3):
    """GM(1,1) 建模并向后预测 n_predict 个点。

    参数:
        x: 一维正序列（原始数据）。
        n_predict: 向后预测点数。
    返回:
        dict：a, b, fitted(拟合值), predict(预测值), C(后验差比),
              P(小误差概率), grade(精度等级)。
    """
    x = np.asarray(x, dtype=float).ravel()
    n = len(x)

    # 1-AGO 一次累加生成
    x1 = np.cumsum(x)
    # 紧邻均值生成 z1
    z1 = (x1[:-1] + x1[1:]) / 2.0
    # 构造最小二乘 B、Y
    B = np.column_stack([-z1, np.ones(n - 1)])
    Y = x[1:].reshape(-1, 1)
    # 估计参数 [a, b]：a 发展系数，b 灰作用量
    a, b = np.linalg.solve(B.T @ B, B.T @ Y).ravel()

    # 时间响应函数：预测累加序列 x1_hat(k+1)
    def x1_hat(k):        # k 从 0 开始
        return (x[0] - b / a) * np.exp(-a * k) + b / a

    # 还原为原始序列的拟合/预测（累减）
    total = n + n_predict
    x1_pred = np.array([x1_hat(k) for k in range(total)])
    x0_pred = np.empty(total)
    x0_pred[0] = x1_pred[0]
    x0_pred[1:] = np.diff(x1_pred)

    fitted = x0_pred[:n]          # 对历史点的拟合
    predict = x0_pred[n:]         # 向后预测

    # ---- 精度检验 ----
    residual = x - fitted
    rel_err = np.abs(residual) / x                 # 相对残差
    S1 = np.std(x, ddof=0)                          # 原序列标准差
    S2 = np.std(residual, ddof=0)                   # 残差标准差
    C = S2 / S1 if S1 > 0 else np.inf               # 后验差比
    # 小误差概率 P
    P = float(np.mean(np.abs(residual - np.mean(residual)) < 0.6745 * S1))

    grade = _accuracy_grade(C, P)

    print("=" * 60)
    print("GM(1,1) 建模结果")
    print("  发展系数 a=%.5f   灰作用量 b=%.5f" % (a, b))
    print("  平均相对残差=%.2f%%" % (np.mean(rel_err) * 100))
    print("  后验差比 C=%.4f   小误差概率 P=%.4f   →  精度等级：%s" % (C, P, grade))
    print("  拟合值：", np.round(fitted, 4))
    print("  预测值：", np.round(predict, 4))

    return {'a': a, 'b': b, 'fitted': fitted, 'predict': predict,
            'C': C, 'P': P, 'grade': grade, 'rel_err': rel_err}


def _accuracy_grade(C, P):
    """依据后验差比 C 与小误差概率 P 判定 GM 精度等级。"""
    if C <= 0.35 and P >= 0.95:
        return '好(1级)'
    elif C <= 0.50 and P >= 0.80:
        return '合格(2级)'
    elif C <= 0.65 and P >= 0.70:
        return '勉强(3级)'
    else:
        return '不合格(4级)'


def gm11_predict(x, n_predict=3, auto_shift=True):
    """带级比检验与自动平移的 GM(1,1) 完整流程（对外主接口）。"""
    print("-" * 60)
    ok, _, _ = level_ratio_test(x)
    c = 0.0
    x_used = np.asarray(x, dtype=float)
    if not ok and auto_shift:
        x_used, c = shift_transform(x_used)
    res = gm11(x_used, n_predict=n_predict)
    if c != 0.0:      # 平移还原
        res['fitted'] = res['fitted'] - c
        res['predict'] = res['predict'] - c
        print("  (已还原平移量) 还原后预测值：", np.round(res['predict'], 4))
    res['shift_c'] = c
    return res


# ----------------------------------------------------------------------
# 演示
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   # 灰色预测适合小样本(4~15点)、单调趋势。附件通常一列年份/日期、一列数值：
    #   df = df.sort_values('年份列')                    # 【务必按时间排序】
    #   data = df['数值列'].values                       # 一维正序列(需为正数)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 示例：近似指数增长的小样本序列（如某地区逐年用电量，单位亿千瓦时）
    data = np.array([2.874, 3.278, 3.337, 3.390, 3.679, 3.996, 4.351, 4.702])

    print("########## 灰色预测 GM(1,1) 演示 ##########")
    print("原始数据（%d 个点）：" % len(data), data)

    # 留最后 2 个点做验证，用前 6 个点建模预测 2 步
    train, test = data[:-2], data[-2:]
    print("\n【留出验证】用前 %d 个点预测后 %d 个点" % (len(train), len(test)))
    res = gm11_predict(train, n_predict=2)
    m = forecast_metrics(test, res['predict'])
    print("  验证集真实值：", test)
    print("  验证集误差：RMSE=%.4f  MAE=%.4f  MAPE=%.2f%%"
          % (m['RMSE'], m['MAE'], m['MAPE(%)']))

    print("\n【全量建模】用全部 %d 个点预测未来 3 个点" % len(data))
    res_full = gm11_predict(data, n_predict=3)

    if _HAS_PLT:
        try:
            n = len(data)
            plt.figure(figsize=(10, 5))
            plt.plot(range(n), data, 'bo-', label='原始数据')
            plt.plot(range(n), res_full['fitted'], 'g^--', label='GM拟合')
            fx = range(n, n + len(res_full['predict']))
            plt.plot(fx, res_full['predict'], 'rs--', label='未来预测')
            plt.title('GM(1,1) 灰色预测'); plt.legend(); plt.grid(alpha=0.3)
            plt.tight_layout(); plt.savefig('03_灰色预测示例.png', dpi=120)
            print("[图已保存] 03_灰色预测示例.png")
        except Exception as e:
            print("绘图跳过：", e)

    print("\n演示完成。GM(1,1) 适合小样本、单调趋势数据；波动大时改用其他模型。")
