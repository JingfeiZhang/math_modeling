# -*- coding: utf-8 -*-
"""
================================================================================
Floyd 全源最短路径算法（Floyd-Warshall）
================================================================================
功能：
    一次性求出图中「任意两点之间」的最短距离与具体路径。
    核心思想：动态规划。逐个把节点 k 当作"中转站"，尝试用 i→k→j 去更新 i→j 的
    最短距离；k 遍历完所有节点后，dist[i][j] 即为全局最短。
    可处理负权边（但不能有负权环），代码简单，适合中小规模稠密图。

适用竞赛场景：
    - 需要"所有点对之间"距离的问题：如任意两城市间最短运距矩阵
    - 后续要用到距离矩阵的模型：设施选址、聚类、网络中心度分析
    - 节点数不大（≲ 400），一次算全所有点对，比多次 Dijkstra 写起来更省事

输入格式：
    邻接矩阵 W：二维数组，W[i][j]=i→j 边权，无边 np.inf，对角线 0
    或边列表 edges：[(u, v, w), ...]

输出：
    dist : (n, n) 最短距离矩阵
    可用 reconstruct_path 取任意两点的具体路径节点序列

依赖：numpy, matplotlib；可选 networkx（pip install networkx，缺失自动降级）
================================================================================
"""

import numpy as np

import matplotlib
matplotlib.use('Agg')            # 无界面环境安全（测试用；用户本地可删）
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']  # 中文
plt.rcParams['axes.unicode_minus'] = False                        # 负号

try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False
    print('[提示] 未安装 networkx，将只运行手写版。安装：pip install networkx')


def build_matrix_from_edges(edges, n, directed=False):
    """把边列表 [(u,v,w),...] 转成邻接矩阵（无边=inf，对角=0）。"""
    W = np.full((n, n), np.inf)
    np.fill_diagonal(W, 0.0)
    for u, v, w in edges:
        W[u][v] = min(W[u][v], w)
        if not directed:
            W[v][u] = min(W[v][u], w)
    return W


def floyd(W):
    """手写 Floyd-Warshall（三重循环）+ next 矩阵用于重建路径。

    参数:
        W : (n, n) 邻接矩阵，无边为 np.inf，对角为 0
    返回:
        dist : (n, n) 最短距离矩阵
        nxt  : (n, n) 后继矩阵，nxt[i][j]=从 i 走向 j 的下一步节点（-1 不可达）
    复杂度：O(n^3)。注意 k 必须是最外层循环。
    """
    W = np.asarray(W, dtype=float)
    n = W.shape[0]
    dist = W.copy()
    # nxt[i][j]：i 到 j 最短路上，i 的下一个节点。初始化为 j（若 i、j 直接相连）
    nxt = np.full((n, n), -1, dtype=int)
    for i in range(n):
        for j in range(n):
            if i != j and dist[i][j] != np.inf:
                nxt[i][j] = j

    # 核心：k 为中转节点，必须放最外层
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]
                    nxt[i][j] = nxt[i][k]   # i 先朝着 k 的方向走
    # 检测负权环：对角线出现负值即存在负环
    if np.any(np.diag(dist) < 0):
        print('[警告] 检测到负权环，最短路径无意义！')
    return dist, nxt


def reconstruct_path(nxt, u, v):
    """用后继矩阵重建 u→v 的具体路径节点序列。不可达返回 None。"""
    if nxt[u][v] == -1:
        return None
    path = [u]
    while u != v:
        u = nxt[u][v]
        if u == -1:
            return None
        path.append(u)
    return path


def floyd_networkx(edges, n, directed=False):
    """networkx 库版对照，返回 (n, n) 距离矩阵。"""
    G = nx.DiGraph() if directed else nx.Graph()
    G.add_nodes_from(range(n))
    for u, v, w in edges:
        G.add_edge(u, v, weight=w)
    # 返回 {i: {j: dist}} 嵌套字典
    length = dict(nx.all_pairs_dijkstra_path_length(G, weight='weight'))
    D = np.full((n, n), np.inf)
    for i in range(n):
        for j, d in length[i].items():
            D[i][j] = d
    return D


def plot_heatmap(dist, node_names, fname='02_Floyd距离矩阵热力图.png'):
    """把全源最短距离矩阵画成热力图（inf 显示为空白）。"""
    n = len(node_names)
    masked = np.ma.masked_invalid(dist)   # 屏蔽 inf/nan
    plt.figure(figsize=(8, 6.5))
    cmap = plt.cm.viridis.copy()
    cmap.set_bad(color='lightgray')       # 不可达格子灰色
    im = plt.imshow(masked, cmap=cmap)
    plt.colorbar(im, label='最短距离')
    plt.xticks(range(n), node_names)
    plt.yticks(range(n), node_names)
    plt.xlabel('终点')
    plt.ylabel('起点')
    # 在每个格子标注数值
    for i in range(n):
        for j in range(n):
            if np.isfinite(dist[i][j]):
                plt.text(j, i, f'{dist[i][j]:g}', ha='center', va='center',
                         color='white', fontsize=9)
    plt.title('Floyd 全源最短距离矩阵热力图')
    plt.tight_layout()
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f'[图已保存] {fname}')


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   # 附件通常是"边表"：三列 起点, 终点, 权重（距离/耗时/成本）
    #   df = pd.read_csv('附件_路网.csv', encoding='gbk')  # 乱码换 utf-8 / gb18030
    #   names = sorted(set(df['起点']) | set(df['终点']))
    #   idx = {name: k for k, name in enumerate(names)}
    #   node_names = names
    #   edges = [(idx[r['起点']], idx[r['终点']], float(r['权重']))
    #            for _, r in df.iterrows()]
    #   n = len(names)
    #   directed = False       # 单向网改 True
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 5 个地点的有向图（含单向路），边权=距离
    node_names = ['A', 'B', 'C', 'D', 'E']
    edges = [
        (0, 1, 3), (0, 3, 7),
        (1, 0, 8), (1, 2, 2),
        (2, 3, 1), (2, 4, 4),
        (3, 4, 5),
        (4, 1, 6),
    ]
    n = len(node_names)
    directed = True

    W = build_matrix_from_edges(edges, n, directed)
    dist, nxt = floyd(W)

    # 打印距离矩阵
    print('\n===== Floyd 全源最短距离矩阵 =====')
    header = '     ' + ' '.join(f'{x:>5}' for x in node_names)
    print(header)
    for i in range(n):
        row = f'{node_names[i]:>3}: '
        for j in range(n):
            row += f'{"∞":>5} ' if dist[i][j] == np.inf else f'{dist[i][j]:>5g} '
        print(row)

    # 打印几对关键路径（含具体节点序列）
    print('\n===== 关键路径详情 =====')
    for u, v in [(0, 4), (4, 2), (1, 3)]:
        p = reconstruct_path(nxt, u, v)
        if p is None:
            print(f'  {node_names[u]} → {node_names[v]}: 不可达')
        else:
            route = ' -> '.join(node_names[x] for x in p)
            print(f'  {node_names[u]} → {node_names[v]}: 距离={dist[u][v]:g}, 路径: {route}')

    # networkx 对照
    if HAS_NX:
        D2 = floyd_networkx(edges, n, directed)
        same = np.allclose(np.nan_to_num(dist, posinf=1e18),
                           np.nan_to_num(D2, posinf=1e18))
        print(f'\n与 networkx 库版距离矩阵一致：{same}')

    # 距离矩阵热力图
    plot_heatmap(dist, node_names)
