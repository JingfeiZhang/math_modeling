# -*- coding: utf-8 -*-
"""
================================================================================
模糊综合评价法（Fuzzy Comprehensive Evaluation）
================================================================================
功能：
    针对"评价边界模糊、难以精确量化"的对象，用隶属度刻画其属于各评价等级的
    程度，结合指标权重做模糊合成，得到综合评价等级向量，再折算综合得分。

原理：
    1) 确定因素集 U（指标）与评语集 V（等级，如 优/良/中/差）；
    2) 构造隶属度矩阵 R (m×p)：第 i 个指标对第 k 个等级的隶属度；
    3) 权重向量 A (1×m) 与 R 做模糊合成 B = A ∘ R；
    4) 按最大隶属度原则定级，或用等级分值加权算综合得分。

模糊合成算子（可选，影响结果性质）：
    'M(*,+)'    加权平均型：B_k = Σ a_i * r_ik（最常用，充分利用全部信息，推荐）
    'M(∧,∨)'    主因素决定型：B_k = max_i min(a_i, r_ik)（突出主因素，信息利用少）
    'M(*,∨)'    主因素突出型：B_k = max_i (a_i * r_ik)

适用竞赛场景：
    - 评价指标含大量定性/主观描述（满意度、质量等级、风险等级）
    - 需要给出"属于各等级的程度"而非单一分值时
    - 多层指标可逐层调用（先算子准则，再算总准则）

输入格式：
    方式一（已有隶属度矩阵 R）：直接传 R (m×p) 与权重 A。
    方式二（连续指标值 + 分级边界）：用 build_membership 由数值自动构造 R。

依赖：numpy, pandas
================================================================================
"""

import numpy as np
import pandas as pd

def build_membership(value, levels):
    """由单个连续指标值构造其对各等级的隶属度（梯形/三角隶属函数）。

    参数:
        value  : 该指标归一化到 [0,1] 后的取值
        levels : 各等级的中心节点列表（升序），如 [0.2,0.4,0.6,0.8,1.0]
                 第一个等级用偏小型，最后一个用偏大型，中间用三角型。
    返回:
        长度为 len(levels) 的隶属度向量
    """
    a = list(levels)
    p = len(a)
    r = np.zeros(p)
    for k in range(p):
        if k == 0:  # 第一个等级：偏小型（值越小越属于该等级）
            if value <= a[0]:
                r[k] = 1
            elif value <= a[1]:
                r[k] = (a[1] - value) / (a[1] - a[0])
            else:
                r[k] = 0
        elif k == p - 1:  # 最后等级：偏大型
            if value >= a[k]:
                r[k] = 1
            elif value >= a[k - 1]:
                r[k] = (value - a[k - 1]) / (a[k] - a[k - 1])
            else:
                r[k] = 0
        else:  # 中间等级：三角型
            if a[k - 1] <= value <= a[k]:
                r[k] = (value - a[k - 1]) / (a[k] - a[k - 1])
            elif a[k] <= value <= a[k + 1]:
                r[k] = (a[k + 1] - value) / (a[k + 1] - a[k])
            else:
                r[k] = 0
    return r


def fuzzy_synthesis(A, R, operator='M(*,+)'):
    """模糊合成 B = A ∘ R。

    参数:
        A        : 长度 m 的权重向量（和为 1）
        R        : (m, p) 隶属度矩阵
        operator : 合成算子，见文件头说明
    返回:
        B : 长度 p 的综合评价向量（一般再归一化）
    """
    A = np.array(A, dtype=float)
    R = np.array(R, dtype=float)
    m, p = R.shape
    B = np.zeros(p)

    if operator == 'M(*,+)':
        # 加权平均型：矩阵乘法
        B = A @ R
    elif operator == 'M(∧,∨)':
        # 主因素决定型：先取 min，再取 max
        for k in range(p):
            B[k] = np.max(np.minimum(A, R[:, k]))
    elif operator == 'M(*,∨)':
        # 主因素突出型：先相乘，再取 max
        for k in range(p):
            B[k] = np.max(A * R[:, k])
    else:
        raise ValueError(f'未知算子: {operator}')

    # 归一化，便于按隶属度比较
    if B.sum() != 0:
        B = B / B.sum()
    return B


def fuzzy_evaluate(R, A, level_scores=None, operator='M(*,+)'):
    """对单个对象做模糊综合评价。

    参数:
        R            : (m, p) 隶属度矩阵
        A            : 长度 m 的指标权重
        level_scores : 长度 p 的各等级分值（如 [95,85,75,60]）；给出则算综合得分
        operator     : 模糊合成算子
    返回:
        B          : 综合评价等级向量
        best_level : 最大隶属度对应的等级索引（0 起）
        score      : 综合得分（level_scores 为 None 时返回 None）
    """
    B = fuzzy_synthesis(A, R, operator)
    best_level = int(np.argmax(B))
    score = None
    if level_scores is not None:
        score = float(B @ np.array(level_scores, dtype=float))
    return B, best_level, score


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   模糊综合评价有两种数据入口，按你的附件形态二选一：
    #   方式一｜附件是"专家打分/等级隶属度"表 → 直接读成隶属度矩阵 R (m指标×p等级)：
    #     import pandas as pd
    #     R = pd.read_csv('隶属度矩阵.csv', encoding='gbk').values  # 每行一个指标，每列一个等级
    #     A = [0.3, 0.35, 0.2, 0.15]          # 各指标权重(和为1，可由AHP/熵权法得到)
    #     grade_scores = [95, 85, 75, 60]     # 各等级分值，按你的评语集改
    #   方式二｜附件是"连续指标值"表 → 归一化到[0,1]后用 build_membership 自动构造 R：
    #     df = pd.read_csv('附件1.csv', encoding='gbk')
    #     data = df[['成绩', '表现']].values   # 行=对象 列=指标；需先各列归一化到[0,1]
    #     levels = [0.2, 0.4, 0.6, 0.8, 1.0]   # 各等级中心节点(升序)
    #     A2 = [0.6, 0.4]                      # 指标权重
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 因素集：外观、性能、价格、售后；评语集：优/良/中/差（4 级）
    factors = ['外观', '性能', '价格', '售后']
    grades = ['优', '良', '中', '差']
    grade_scores = [95, 85, 75, 60]

    # 方式一：直接给专家打分统计得到的隶属度矩阵 R (4指标 × 4等级)
    R = np.array([
        [0.5, 0.3, 0.2, 0.0],   # 外观：50%认为优，30%良...
        [0.3, 0.4, 0.2, 0.1],   # 性能
        [0.2, 0.5, 0.2, 0.1],   # 价格
        [0.4, 0.4, 0.1, 0.1],   # 售后
    ])
    A = [0.3, 0.35, 0.2, 0.15]  # 指标权重（可由 AHP/熵权法得到）

    print('===== 模糊综合评价（三种算子对比） =====')
    for op in ['M(*,+)', 'M(∧,∨)', 'M(*,∨)']:
        B, best, score = fuzzy_evaluate(R, A, grade_scores, operator=op)
        s = f'{score:.2f}' if score is not None else '—'
        print(f'算子 {op:8s} -> 等级向量 {np.round(B, 3)} '
              f'| 评定等级：{grades[best]} | 综合得分：{s}')

    # 方式二：由连续指标值自动构造隶属度矩阵（多对象）
    print('\n===== 由连续指标值自动构造隶属度并评价 =====')
    # 3 个学生，2 个指标（已归一化到[0,1]）：成绩、表现
    data = np.array([[0.85, 0.70], [0.55, 0.60], [0.30, 0.45]])
    students = ['学生1', '学生2', '学生3']
    levels = [0.2, 0.4, 0.6, 0.8, 1.0]           # 5 级节点
    lv_names = ['差', '中', '良', '优', '卓越']
    lv_scores = [50, 65, 78, 88, 96]
    A2 = [0.6, 0.4]

    rows = []
    for i, name in enumerate(students):
        R_i = np.array([build_membership(data[i, j], levels)
                        for j in range(data.shape[1])])
        B, best, score = fuzzy_evaluate(R_i, A2, lv_scores)
        rows.append([name, lv_names[best], round(score, 2)])
    print(pd.DataFrame(rows, columns=['对象', '评定等级', '综合得分'])
          .to_string(index=False))

