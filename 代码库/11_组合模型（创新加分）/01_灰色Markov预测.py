# -*- coding: utf-8 -*-
"""
================================================================================
灰色-马尔可夫组合预测（Grey-Markov：GM(1,1) 定趋势 + 马尔可夫链修正）
================================================================================
功能：
    把灰色预测的"趋势外推"能力与马尔可夫链的"状态转移修正"能力组合起来：
      1. GM(1,1) 对小样本序列做趋势预测（一次累加→最小二乘估参→时间响应还原）；
      2. 计算实际值相对 GM 拟合值的相对残差，把残差按大小划分为若干"状态区间"；
      3. 统计历史状态转移频率得到马尔可夫转移矩阵，据最近状态预测下一期落在哪个状态，
         用该状态的残差中点去修正 GM 的趋势预测值。
    结论：GM 管大方向，Markov 管围绕趋势的上下波动，组合后对"有趋势又有波动"
    的小样本序列比单用 GM 更准。纯 numpy 实现，轻量、可复现。

适用竞赛场景：
    - 小样本（10~30 点）且围绕上升/下降趋势上下波动的序列：
      如商品月销量、原材料价格、客流量等的短期预测。

输入格式：
    - 一维正序列（list / np.ndarray），等时间间隔、整体有趋势但含波动。

输出：
    - GM 趋势预测、马尔可夫状态划分与转移矩阵、组合修正后的预测值。

依赖：numpy, (可选) matplotlib
运行：python 01_灰色Markov预测.py
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
    matplotlib.use('Agg')            # 无界面环境安全（测试用；用户本地可删）
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']  # 中文
    plt.rcParams['axes.unicode_minus'] = False                        # 负号
    _HAS_PLT = True
except Exception:
    _HAS_PLT = False


# ----------------------------------------------------------------------
# 1. GM(1,1) 趋势预测
# ----------------------------------------------------------------------
def gm11(x, n_predict=1):
    """GM(1,1) 建模并向后预测 n_predict 个点，返回拟合值与预测值。"""
    x = np.asarray(x, dtype=float).ravel()
    n = len(x)
    x1 = np.cumsum(x)                          # 1-AGO 一次累加
    z1 = (x1[:-1] + x1[1:]) / 2.0              # 紧邻均值
    B = np.column_stack([-z1, np.ones(n - 1)])
    Y = x[1:].reshape(-1, 1)
    a, b = np.linalg.solve(B.T @ B, B.T @ Y).ravel()   # 发展系数 a、灰作用量 b

    total = n + n_predict
    x1_hat = (x[0] - b / a) * np.exp(-a * np.arange(total)) + b / a
    x0_hat = np.empty(total)
    x0_hat[0] = x1_hat[0]
    x0_hat[1:] = np.diff(x1_hat)
    return {'a': a, 'b': b, 'fitted': x0_hat[:n], 'predict': x0_hat[n:]}


# ----------------------------------------------------------------------
# 2. 马尔可夫残差状态划分与转移矩阵
# ----------------------------------------------------------------------
def build_states(rel_resid, n_states=4):
    """把相对残差序列等分为 n_states 个状态区间。

    参数:
        rel_resid: 相对残差序列 (实际-拟合)/拟合。
        n_states : 状态数（区间个数），常用 3~5；样本少用 3，样本多可用 4~5。
    返回:
        edges(区间边界), mids(各状态残差中点), state_seq(每期所属状态索引)。
    """
    rel_resid = np.asarray(rel_resid, dtype=float)
    lo, hi = rel_resid.min(), rel_resid.max()
    # 稍微外扩边界，避免最值恰好落在边界上分不进区间
    span = (hi - lo) if hi > lo else 1.0
    lo -= span * 1e-6
    hi += span * 1e-6
    edges = np.linspace(lo, hi, n_states + 1)
    mids = (edges[:-1] + edges[1:]) / 2.0       # 每个状态用中点代表其残差水平
    # np.digitize 返回 1..n_states，转成 0..n_states-1
    state_seq = np.clip(np.digitize(rel_resid, edges) - 1, 0, n_states - 1)
    return edges, mids, state_seq


def transition_matrix(state_seq, n_states):
    """由状态序列统计一步转移概率矩阵 P[i,j]=P(下一步=j | 当前=i)。"""
    P = np.zeros((n_states, n_states))
    for cur, nxt in zip(state_seq[:-1], state_seq[1:]):
        P[cur, nxt] += 1.0
    row_sum = P.sum(axis=1, keepdims=True)
    # 没有出现过的状态行：设为均匀分布，避免除零
    for i in range(n_states):
        if row_sum[i, 0] == 0:
            P[i, :] = 1.0 / n_states
        else:
            P[i, :] /= row_sum[i, 0]
    return P


# ----------------------------------------------------------------------
# 3. 灰色-马尔可夫组合预测（主接口）
# ----------------------------------------------------------------------
def grey_markov(x, n_predict=1, n_states=4):
    """灰色-马尔可夫组合预测。

    步骤: GM(1,1) 出趋势 → 算相对残差 → 划状态、建转移矩阵 →
          由最近状态预测下一状态 → 用该状态残差中点修正 GM 预测值。

    调参说明:
        - n_states 状态数: 样本少(<15)用 3, 中等用 4, 较多用 5;
          太多会导致每个状态样本过少、转移矩阵不稳。
        - 组合只对"有趋势+围绕趋势波动"的数据有增益; 纯单调无波动时
          残差极小, 马尔可夫修正≈0, 退化为普通 GM。
    """
    x = np.asarray(x, dtype=float).ravel()
    n = len(x)

    gm = gm11(x, n_predict=n_predict)
    fitted = gm['fitted']
    rel_resid = (x - fitted) / fitted                       # 相对残差

    edges, mids, state_seq = build_states(rel_resid, n_states)
    P = transition_matrix(state_seq, n_states)

    # 从最近状态出发逐步预测未来状态，取转移概率最大的状态
    gm_pred = gm['predict']
    cur_state = int(state_seq[-1])
    corrected = np.empty(n_predict)
    pred_states = []
    for k in range(n_predict):
        next_state = int(np.argmax(P[cur_state]))
        pred_states.append(next_state)
        # 用预测状态的残差中点修正: 实际≈GM趋势×(1+相对残差)
        corrected[k] = gm_pred[k] * (1.0 + mids[next_state])
        cur_state = next_state

    return {'gm': gm, 'rel_resid': rel_resid, 'edges': edges, 'mids': mids,
            'state_seq': state_seq, 'P': P, 'gm_predict': gm_pred,
            'corrected': corrected, 'pred_states': pred_states, 'fitted': fitted}


# ----------------------------------------------------------------------
# 演示
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   df = df.sort_values('时间列')                   # 【务必按时间排序】
    #   data = df['数值列'].values.astype(float)        # 一维正序列(需为正)
    #   # 适合: 有整体趋势又上下波动的小样本(如月销量/价格)
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 上升趋势 + 明显波动的小样本（如某商品逐月销量，单位百件）
    rng = np.random.default_rng(7)
    base = 50 * np.exp(0.05 * np.arange(20))           # 指数上升趋势
    data = base * (1 + rng.normal(0, 0.06, size=20))   # 叠加 6% 波动

    print("########## 灰色-马尔可夫组合预测演示 ##########")
    print("序列长度：%d  （有上升趋势 + 波动）" % len(data))

    # 留最后 3 个点做验证
    train, test = data[:-3], data[-3:]
    res = grey_markov(train, n_predict=3, n_states=4)

    print("\n【GM(1,1) 趋势】发展系数 a=%.4f" % res['gm']['a'])
    print("平均相对残差 = %.2f%%（残差越大，马尔可夫修正越有价值）"
          % (np.mean(np.abs(res['rel_resid'])) * 100))
    print("\n马尔可夫转移矩阵 P（行=当前状态，列=下一状态）：")
    print(np.round(res['P'], 3))
    print("最近所处状态：%d  ->  预测未来状态序列：%s"
          % (res['state_seq'][-1], res['pred_states']))

    # 对比两种预测与真实值
    def metrics(y_true, y_pred):
        e = np.asarray(y_true) - np.asarray(y_pred)
        return (float(np.sqrt(np.mean(e ** 2))),
                float(np.mean(np.abs(e / y_true)) * 100))
    rmse_gm, mape_gm = metrics(test, res['gm_predict'])
    rmse_gk, mape_gk = metrics(test, res['corrected'])

    print("\n【留出验证：预测最后 3 期】")
    print("  真实值      ：", np.round(test, 2))
    print("  单用GM      ：", np.round(res['gm_predict'], 2),
          " RMSE=%.2f MAPE=%.2f%%" % (rmse_gm, mape_gm))
    print("  灰色-马尔可夫：", np.round(res['corrected'], 2),
          " RMSE=%.2f MAPE=%.2f%%" % (rmse_gk, mape_gk))
    better = "组合模型更优" if rmse_gk < rmse_gm else "本例组合与GM相近"
    print("  ->", better, "（马尔可夫修正了 GM 系统性偏差）")

    if _HAS_PLT:
        try:
            n = len(train)
            plt.figure(figsize=(10, 5))
            plt.plot(range(len(data)), data, 'ko-', ms=4, label='真实数据')
            plt.plot(range(n), res['fitted'], 'g^--', ms=4, label='GM拟合')
            fx = range(n, n + 3)
            plt.plot(fx, res['gm_predict'], 'bs--', label='GM预测')
            plt.plot(fx, res['corrected'], 'r*--', ms=10, label='灰色-马尔可夫修正')
            plt.axvline(n - 0.5, color='gray', ls=':', alpha=0.6)
            plt.xlabel('期'); plt.ylabel('数值')
            plt.title('灰色-马尔可夫组合预测')
            plt.legend(); plt.grid(alpha=0.3)
            plt.tight_layout()
            plt.savefig('01_灰色Markov示例.png', dpi=120)
            print("\n[图已保存] 01_灰色Markov示例.png")
        except Exception as e:
            print("绘图跳过：", e)

    print("\n演示完成。要点：GM 定趋势、Markov 修波动，适合小样本+波动序列。")
