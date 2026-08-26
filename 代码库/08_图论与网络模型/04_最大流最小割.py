# -*- coding: utf-8 -*-
"""
================================================================================
最大流与最小割（Maximum Flow / Minimum Cut）
================================================================================
功能：
    在「带容量的有向网络」里，求从源点 s 到汇点 t 能通过的最大流量。
    最大流最小割定理：最大流的值 = 最小割的容量（把 s、t 分开、切断所有 s→t
    通路的那组边，其容量之和最小）。最小割能指出网络的「瓶颈边」。
    本模板用 networkx 的 maximum_flow（Edmonds-Karp/Dinic 类算法）实现，
    并给出无 networkx 时的手写 Edmonds-Karp 降级版。

适用竞赛场景：
    - 物流运力：从产地经中转到销地，最多能运多少货（各路段有运力上限）
    - 网络/管道容量：数据/水/电从源到汇的最大吞吐，找瓶颈段
    - 二分图指派/分配：任务-资源匹配可建模为最大流

输入格式：
    有向边列表 edges=[(u, v, cap), ...]，cap=该有向边容量（≥0）
    源点 source、汇点 sink（节点编号 0 起）

输出：
    flow_value : 最大流量
    flow_dict  : 各边实际流量
    min_cut    : 最小割的两侧节点集合与被切断的边

依赖：matplotlib；推荐 networkx（pip install networkx，缺失自动降级到手写版）
================================================================================
"""

from collections import deque, defaultdict

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
    print('[提示] 未安装 networkx，将使用手写 Edmonds-Karp。安装：pip install networkx')


def max_flow_edmonds_karp(edges, n, source, sink):
    """手写 Edmonds-Karp 最大流（BFS 找增广路，残量网络）。

    参数:
        edges  : [(u, v, cap), ...] 有向边及容量
        n      : 节点数
        source : 源点，sink : 汇点
    返回:
        flow_value : 最大流值
        cap        : 残量矩阵（cap[u][v] 为剩余容量，可推实际流量）
    """
    # 容量矩阵（重边累加）
    cap = [[0] * n for _ in range(n)]
    orig = [[0] * n for _ in range(n)]
    for u, v, c in edges:
        cap[u][v] += c
        orig[u][v] += c
    flow_value = 0

    while True:
        # BFS 在残量网络找一条 source→sink 的增广路
        parent = [-1] * n
        parent[source] = source
        q = deque([source])
        while q:
            u = q.popleft()
            for v in range(n):
                if parent[v] == -1 and cap[u][v] > 0:
                    parent[v] = u
                    q.append(v)
        if parent[sink] == -1:
            break                          # 找不到增广路，结束

        # 找增广路上的瓶颈（最小剩余容量）
        bottleneck = float('inf')
        v = sink
        while v != source:
            u = parent[v]
            bottleneck = min(bottleneck, cap[u][v])
            v = u
        # 沿路更新残量（正向减、反向加）
        v = sink
        while v != source:
            u = parent[v]
            cap[u][v] -= bottleneck
            cap[v][u] += bottleneck
            v = u
        flow_value += bottleneck

    return flow_value, cap, orig


def min_cut_from_residual(cap, source, n):
    """由残量网络求最小割：从 source 在残量网络里能到达的点即 S 侧。"""
    reachable = [False] * n
    reachable[source] = True
    q = deque([source])
    while q:
        u = q.popleft()
        for v in range(n):
            if not reachable[v] and cap[u][v] > 0:
                reachable[v] = True
                q.append(v)
    S = {i for i in range(n) if reachable[i]}
    T = {i for i in range(n) if not reachable[i]}
    return S, T


def max_flow_networkx(edges, n, source, sink):
    """networkx 库版：maximum_flow + minimum_cut。返回结果字典。"""
    G = nx.DiGraph()
    G.add_nodes_from(range(n))
    for u, v, c in edges:
        # 若已有该边则容量累加
        if G.has_edge(u, v):
            G[u][v]['capacity'] += c
        else:
            G.add_edge(u, v, capacity=c)
    flow_value, flow_dict = nx.maximum_flow(G, source, sink, capacity='capacity')
    cut_value, (S, T) = nx.minimum_cut(G, source, sink, capacity='capacity')
    return flow_value, flow_dict, cut_value, set(S), set(T)


def plot_flow(edges, n, source, sink, flow_dict, node_names,
              fname='04_最大流网络.png'):
    """画流网络：边标注 '实际流量/容量'，饱和边（流满）红色高亮。"""
    if not HAS_NX:
        print('[提示] 未安装 networkx，跳过绘图。')
        return
    G = nx.DiGraph()
    G.add_nodes_from(range(n))
    cap_map = defaultdict(float)
    for u, v, c in edges:
        cap_map[(u, v)] += c
    for (u, v), c in cap_map.items():
        G.add_edge(u, v, capacity=c)

    pos = nx.spring_layout(G, seed=42)
    plt.figure(figsize=(10, 7))
    colors = []
    for i in range(n):
        if i == source:
            colors.append('lightgreen')
        elif i == sink:
            colors.append('salmon')
        else:
            colors.append('lightblue')
    nx.draw_networkx_nodes(G, pos, node_size=800, node_color=colors)

    # 饱和边（流量=容量）高亮红色，其余灰色
    sat, normal, labels = [], [], {}
    for (u, v), c in cap_map.items():
        f = flow_dict.get(u, {}).get(v, 0)
        labels[(u, v)] = f'{f:g}/{c:g}'
        (sat if abs(f - c) < 1e-9 and c > 0 else normal).append((u, v))
    nx.draw_networkx_edges(G, pos, edgelist=normal, width=1.5,
                           edge_color='gray', arrowstyle='->', arrowsize=18)
    nx.draw_networkx_edges(G, pos, edgelist=sat, width=3,
                           edge_color='red', arrowstyle='->', arrowsize=18)
    nx.draw_networkx_labels(G, pos, labels={i: node_names[i] for i in range(n)},
                            font_size=12)
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_size=9)
    plt.title('最大流网络（边标注 流量/容量，红色=饱和瓶颈边）')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f'[图已保存] {fname}')


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   # 附件为"边表"：三列 起点, 终点, 容量（运力/带宽上限）——有向网络
    #   df = pd.read_csv('附件_运输网.csv', encoding='gbk')  # 乱码换 utf-8
    #   names = sorted(set(df['起点']) | set(df['终点']))
    #   idx = {name: k for k, name in enumerate(names)}
    #   node_names = names
    #   edges = [(idx[r['起点']], idx[r['终点']], float(r['容量']))
    #            for _, r in df.iterrows()]
    #   n = len(names)
    #   source = idx['产地']   # 换成你的源点/汇点名
    #   sink   = idx['销地']
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 物流运输网：s=产地, t=销地, 中间为中转站，边权=路段运力上限（吨/天）
    node_names = ['s', 'A', 'B', 'C', 'D', 't']
    edges = [
        (0, 1, 16), (0, 2, 13),
        (1, 2, 10), (1, 3, 12),
        (2, 1, 4),  (2, 4, 14),
        (3, 2, 9),  (3, 5, 20),
        (4, 3, 7),  (4, 5, 4),
    ]
    n = len(node_names)
    source, sink = 0, 5

    # 手写 Edmonds-Karp
    fv, cap_res, orig = max_flow_edmonds_karp(edges, n, source, sink)
    print(f'\n===== 手写 Edmonds-Karp =====')
    print(f'最大流（{node_names[source]} → {node_names[sink]}）= {fv:g}')
    S, T = min_cut_from_residual(cap_res, source, n)
    print(f'最小割 S 侧={sorted(node_names[i] for i in S)}')
    print(f'最小割 T 侧={sorted(node_names[i] for i in T)}')
    cut_edges = [(u, v, c) for u, v, c in
                 [(a, b, orig[a][b]) for a in S for b in T if orig[a][b] > 0]]
    print('被切断的瓶颈边（最小割）：')
    for u, v, c in cut_edges:
        print(f'  {node_names[u]} → {node_names[v]}  容量 {c:g}')
    print(f'最小割容量 = {sum(c for _, _, c in cut_edges):g}（应等于最大流）')

    # networkx 对照
    if HAS_NX:
        fv2, fdict, cut_val, S2, T2 = max_flow_networkx(edges, n, source, sink)
        print(f'\n===== networkx 库版对照 =====')
        print(f'最大流 = {fv2:g}，最小割容量 = {cut_val:g}')
        print(f'与手写版最大流一致：{abs(fv - fv2) < 1e-9}')
        plot_flow(edges, n, source, sink, fdict, node_names)
