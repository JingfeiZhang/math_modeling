# -*- coding: utf-8 -*-
"""
================================================================================
动态规划 DP（Dynamic Programming）
================================================================================
功能：
    求解具有"最优子结构 + 重叠子问题"的多阶段决策最优化问题。核心是找到
    状态定义与状态转移方程，把大问题拆成子问题、用表格自底向上递推，避免
    重复计算。常用于：背包、最短路、资源分阶段分配、序列决策（最长子序列）等。

用 DP 的判断条件：
    1) 最优子结构：大问题最优解由子问题最优解组合而成。
    2) 无后效性：某阶段状态一旦确定，后续决策只依赖当前状态，与如何到达无关。
    3) 重叠子问题：子问题被反复求解（区别于分治），故用表存起来。

本模板含三个经典模型（均附状态转移方程）：
    A. 0-1 背包：dp[i][w] = 前 i 件物品、容量 w 时的最大价值
    B. 最短路（Floyd 全源最短路）：dp[k][i][j] 允许经过前 k 个中转点的 i->j 最短距离
    C. 最长递增子序列 LIS：dp[i] = 以第 i 个元素结尾的最长递增子序列长度

依赖：numpy（仅示例数据用），标准库
================================================================================
"""

import numpy as np


def knapsack_dp(values, weights, capacity):
    """0-1 背包（动态规划，可回溯选中物品）。

    状态定义：dp[i][w] = 只考虑前 i 件物品、背包容量为 w 时能获得的最大价值。
    状态转移：
        不选第 i 件：dp[i][w] = dp[i-1][w]
        选第 i 件(需 w>=weights[i-1]): dp[i-1][w-weights[i-1]] + values[i-1]
        dp[i][w] = max(上面两者)
    边界：dp[0][*] = 0（没有物品价值为 0）

    参数:
        values, weights : 各物品价值 / 重量列表
        capacity        : 背包容量（整数）
    返回:
        best   : 最大总价值
        chosen : 选中物品索引列表
    """
    n = len(values)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        wi, vi = weights[i - 1], values[i - 1]
        for w in range(capacity + 1):
            dp[i][w] = dp[i - 1][w]                       # 不选第 i 件
            if w >= wi:                                    # 容量够则考虑选
                dp[i][w] = max(dp[i][w], dp[i - 1][w - wi] + vi)

    # 回溯：从 dp[n][capacity] 反推哪些物品被选中
    chosen, w = [], capacity
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:   # 价值变化说明第 i 件被选
            chosen.append(i - 1)
            w -= weights[i - 1]
    chosen.reverse()
    return dp[n][capacity], chosen


def floyd_shortest_path(dist):
    """Floyd-Warshall 全源最短路（任意两点间最短距离）。

    状态定义：dp[i][j] = 当前允许中转点集合下 i 到 j 的最短距离。
    状态转移（逐个放开中转点 k）：
        dp[i][j] = min(dp[i][j], dp[i][k] + dp[k][j])
    适合稠密图、需要所有点对距离的场景（如选址、配送）。

    参数:
        dist : (n, n) 邻接矩阵，dist[i][j] 为 i->j 边权，不可达用 np.inf，对角线 0
    返回:
        d    : (n, n) 最短距离矩阵
        nxt  : 路径重建矩阵，nxt[i][j] 为从 i 到 j 的下一跳
    """
    d = np.array(dist, dtype=float).copy()
    n = d.shape[0]
    nxt = [[j if d[i][j] < np.inf else None for j in range(n)] for i in range(n)]
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
                    nxt[i][j] = nxt[i][k]   # 更新下一跳
    return d, nxt


def reconstruct_path(nxt, i, j):
    """根据 Floyd 的 nxt 矩阵重建 i 到 j 的具体路径。"""
    if nxt[i][j] is None:
        return []
    path = [i]
    while i != j:
        i = nxt[i][j]
        path.append(i)
    return path


def longest_increasing_subsequence(arr):
    """最长递增子序列 LIS（动态规划 O(n^2)）。

    状态定义：dp[i] = 以 arr[i] 结尾的最长递增子序列长度。
    状态转移：dp[i] = max(dp[j] + 1)  对所有 j < i 且 arr[j] < arr[i]；否则 dp[i]=1
    参数:
        arr : 数值序列
    返回:
        length : LIS 长度
        seq    : 一个 LIS 具体序列
    """
    n = len(arr)
    if n == 0:
        return 0, []
    dp = [1] * n
    prev = [-1] * n
    for i in range(n):
        for j in range(i):
            if arr[j] < arr[i] and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
                prev[i] = j
    end = int(np.argmax(dp))
    seq = []
    while end != -1:
        seq.append(arr[end])
        end = prev[end]
    seq.reverse()
    return max(dp), seq


if __name__ == '__main__':
    print('=' * 60)
    print('模型A：0-1 背包（动态规划）')
    print('=' * 60)
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   动态规划的输入（物品价值/重量、图的邻接矩阵、序列）都可来自附件。
    #   import pandas as pd
    #   df = pd.read_csv('附件1.csv', encoding='gbk')  # 乱码就换 utf-8 / gb18030
    #   values = df['价值'].values                # 背包：各物品价值
    #   weights = df['重量'].values               # 背包：各物品重量（须为整数）
    #   capacity = 50                             # 容量上限（整数）
    #   # 最短路：把附件的距离/邻接表读成方阵 graph（无边处填 np.inf）
    #   #   graph = pd.read_csv('距离矩阵.csv', encoding='gbk', index_col=0).values
    #   # 最长递增子序列：arr = df['某时间序列列'].values
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    values = [60, 100, 120, 80]
    weights = [10, 20, 30, 15]
    capacity = 50
    best, chosen = knapsack_dp(values, weights, capacity)
    print(f'容量 {capacity}，最大价值 = {best}，选中物品索引 = {chosen}')
    print('（与 02_整数规划的背包结果应一致，DP 适合容量为整数的小规模问题）')

    print('\n' + '=' * 60)
    print('模型B：Floyd 全源最短路')
    print('=' * 60)
    INF = np.inf
    graph = [
        [0,   3,   INF, 7],
        [8,   0,   2,   INF],
        [5,   INF, 0,   1],
        [2,   INF, INF, 0],
    ]
    d, nxt = floyd_shortest_path(graph)
    print('最短距离矩阵：')
    print(np.where(d == INF, -1, d))
    print('节点 0 -> 2 最短距离:', d[0][2], '，路径:', reconstruct_path(nxt, 0, 2))

    print('\n' + '=' * 60)
    print('模型C：最长递增子序列 LIS')
    print('=' * 60)
    arr = [10, 9, 2, 5, 3, 7, 101, 18]
    length, seq = longest_increasing_subsequence(arr)
    print(f'序列 {arr}')
    print(f'LIS 长度 = {length}，一个 LIS = {seq}')
