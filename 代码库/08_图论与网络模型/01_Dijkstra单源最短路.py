# -*- coding: utf-8 -*-
"""
================================================================================
Dijkstra 单源最短路径算法（Dijkstra Shortest Path）
================================================================================
功能：
    求从一个「源点」出发到图中所有其他节点的最短路径（距离 + 具体路径节点序列）。
    核心思想：贪心 + 优先队列。每次从"未确定"的节点里取出当前距离源点最近的点，
    确定它的最短距离，再用它去松弛（更新）邻居的距离，直到所有点确定。
    只适用于「非负权」图（有负权用 Bellman-Ford / SPFA）。

适用竞赛场景：
    - 物流/交通网：求配送中心到各需求点的最短运距、最短时间路径
    - 管网/线路：求某源点到各节点的最小铺设/传输代价路径
    - 任何"给一张带权图，问某点到其他点怎么走最近"的子问题

输入格式：
    方式一 邻接矩阵 W：二维数组，W[i][j] = i→j 的边权，无边用 np.inf（对角线 0）
    方式二 边列表 edges：[(u, v, w), ...]，u→v 权重 w；无向图每条边正反都加
    起点 start：源节点编号（0 起）

输出：
    dist  : 源点到各节点的最短距离（list）
    paths : 源点到各节点的最短路径节点序列（list[list]，不可达为 None）

依赖：numpy, matplotlib；可选 networkx（pip install networkx，缺失自动降级到手写版）
================================================================================
"""

import heapq
import numpy as np

import matplotlib
matplotlib.use('Agg')            # 无界面环境安全（测试用；用户本地可删）
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']  # 中文
plt.rcParams['axes.unicode_minus'] = False                        # 负号

# networkx 为可选依赖：装了就用库版对照，没装则仅用手写版（优雅降级）
try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False
    print('[提示] 未安装 networkx，将只运行手写版。安装：pip install networkx')


def build_matrix_from_edges(edges, n, directed=False):
    """把边列表 [(u,v,w),...] 转成邻接矩阵（无边=inf，对角=0）。

    参数:
        edges    : [(u, v, w), ...] 边列表，节点编号从 0 起
        n        : 节点总数
        directed : True 有向图（只加 u→v）；False 无向图（u↔v 都加）
    """
    W = np.full((n, n), np.inf)
    np.fill_diagonal(W, 0.0)
    for u, v, w in edges:
        W[u][v] = min(W[u][v], w)        # 有重边取最小
        if not directed:
            W[v][u] = min(W[v][u], w)
    return W


def dijkstra(W, start):
    """手写 Dijkstra（基于 heapq 优先队列，含前驱记录用于回溯路径）。

    参数:
        W     : (n, n) 邻接矩阵，W[u][v]=边权，无边为 np.inf
        start : 源节点编号
    返回:
        dist  : list，源点到各节点最短距离（不可达为 inf）
        paths : list，源点到各节点的路径节点序列（不可达为 None）
    复杂度：O((V+E) logV)，比朴素 O(V^2) 版在稀疏图上更快。
    """
    W = np.asarray(W, dtype=float)
    n = W.shape[0]
    dist = [float('inf')] * n
    dist[start] = 0.0
    prev = [-1] * n                       # 前驱数组，用于回溯具体路径
    visited = [False] * n
    pq = [(0.0, start)]                    # 优先队列元素 (当前距离, 节点)

    while pq:
        d, u = heapq.heappop(pq)          # 取出当前距离最小的未确定节点
        if visited[u]:
            continue                      # 惰性删除：已确定的旧记录跳过
        visited[u] = True
        for v in range(n):                # 松弛 u 的所有邻居
            w = W[u][v]
            if w != np.inf and not visited[v] and d + w < dist[v]:
                dist[v] = d + w
                prev[v] = u               # 记录 v 的最短路来自 u
                heapq.heappush(pq, (dist[v], v))

    # 用前驱数组回溯每个终点的完整路径
    paths = []
    for end in range(n):
        if dist[end] == float('inf'):
            paths.append(None)            # 不可达
            continue
        path, cur = [], end
        while cur != -1:
            path.append(cur)
            cur = prev[cur]
        paths.append(path[::-1])          # 回溯得到的是终点→起点，反转
    return dist, paths


def dijkstra_networkx(edges, n, start, directed=False):
    """networkx 库版对照（结果应与手写版一致）。返回 (dist, paths)。"""
    G = nx.DiGraph() if directed else nx.Graph()
    G.add_nodes_from(range(n))
    for u, v, w in edges:
        G.add_edge(u, v, weight=w)
    # single_source_dijkstra 一次返回距离字典和路径字典
    length, path = nx.single_source_dijkstra(G, start, weight='weight')
    dist = [length.get(i, float('inf')) for i in range(n)]
    paths = [path.get(i, None) for i in range(n)]
    return dist, paths


def plot_graph(edges, n, start, paths, node_names, directed=False,
               fname='01_Dijkstra最短路.png'):
    """画出图，并把从源点出发的所有最短路径用红色高亮。"""
    if not HAS_NX:
        print('[提示] 未安装 networkx，跳过绘图。')
        return
    G = nx.DiGraph() if directed else nx.Graph()
    G.add_nodes_from(range(n))
    for u, v, w in edges:
        G.add_edge(u, v, weight=w)

    pos = nx.spring_layout(G, seed=42)    # 固定 seed 保证布局可复现
    plt.figure(figsize=(10, 7))
    # 源点标绿，其余浅蓝
    colors = ['lightgreen' if i == start else 'lightblue' for i in range(n)]
    nx.draw_networkx_nodes(G, pos, node_size=800, node_color=colors)
    nx.draw_networkx_edges(G, pos, width=1, alpha=0.4, edge_color='gray')

    # 收集所有最短路径上的边并高亮
    tree_edges = set()
    for p in paths:
        if p and len(p) > 1:
            for a, b in zip(p[:-1], p[1:]):
                tree_edges.add((a, b) if directed else frozenset((a, b)))
    hl = [(u, v) for u, v in G.edges()
          if ((u, v) in tree_edges) or (frozenset((u, v)) in tree_edges)]
    nx.draw_networkx_edges(G, pos, edgelist=hl, width=3, edge_color='red')

    nx.draw_networkx_labels(G, pos, labels={i: node_names[i] for i in range(n)},
                            font_size=12)
    edge_labels = {(u, v): f"{d['weight']:g}" for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=9)
    plt.title(f'Dijkstra 最短路径（源点 {node_names[start]}，红色为最短路径树）')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f'[图已保存] {fname}')


def print_result(dist, paths, start, node_names, title):
    """统一打印最短路径结果。"""
    print(f'\n===== {title}（源点 {node_names[start]}）=====')
    for i in range(len(dist)):
        if i == start:
            continue
        if paths[i] is None:
            print(f'  → {node_names[i]}: 不可达')
        else:
            route = ' -> '.join(node_names[j] for j in paths[i])
            print(f'  → {node_names[i]}: 距离={dist[i]:g}, 路径: {route}')


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   # 附件通常是"边表"格式，三列：起点, 终点, 权重（如 距离/耗时/成本）
    #   df = pd.read_csv('附件_路网.csv', encoding='gbk')  # 乱码换 utf-8 / gb18030
    #   # 把节点名映射成 0..n-1 的整数编号（Dijkstra 用整数下标）
    #   names = sorted(set(df['起点']) | set(df['终点']))
    #   idx = {name: k for k, name in enumerate(names)}
    #   node_names = names
    #   edges = [(idx[r['起点']], idx[r['终点']], float(r['权重']))
    #            for _, r in df.iterrows()]
    #   n = len(names)
    #   directed = False       # 单行道/有向网改 True
    #   start = idx['配送中心'] # 换成你的源点名
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 7 个地点 A-G 的无向路网，边权=两地距离（公里）
    node_names = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    edges = [
        (0, 1, 4), (0, 6, 2),
        (1, 2, 6),
        (2, 3, 3), (2, 5, 5),
        (3, 4, 2),
        (4, 5, 1),
        (5, 6, 4),
    ]
    n = len(node_names)
    directed = False           # 无向图
    start = 0                  # 从 A 出发

    # 由边列表构邻接矩阵，跑手写版
    W = build_matrix_from_edges(edges, n, directed)
    dist, paths = dijkstra(W, start)
    print_result(dist, paths, start, node_names, '手写 Dijkstra（heapq 优先队列）')

    # networkx 库版对照
    if HAS_NX:
        d2, p2 = dijkstra_networkx(edges, n, start, directed)
        print_result(d2, p2, start, node_names, 'networkx 库版对照')
        same = all(abs(a - b) < 1e-9 for a, b in zip(dist, d2))
        print(f'\n两种实现距离结果一致：{same}')

    # 可视化：把最短路径树高亮
    plot_graph(edges, n, start, paths, node_names, directed)
