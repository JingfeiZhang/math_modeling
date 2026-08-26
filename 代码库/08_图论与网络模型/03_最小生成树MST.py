# -*- coding: utf-8 -*-
"""
================================================================================
最小生成树（Minimum Spanning Tree, MST）—— Prim 与 Kruskal
================================================================================
功能：
    在「连通带权无向图」中，找一棵连接所有节点、总边权最小的树（无环、n-1 条边）。
    两种经典算法：
      - Prim   ：从一个点出发，每次贪心地把"离当前树最近的点"并进来（适合稠密图）
      - Kruskal：把所有边按权从小到大排序，用并查集逐条选不成环的边（适合稀疏图）
    两者结果的总权重一定相同（可能有多棵等权 MST）。

适用竞赛场景：
    - 管网/供水/电网/通信网铺设：用最小总成本把所有站点连通
    - 道路/光缆规划：以最小里程连接所有城镇
    - 聚类预处理：MST 断开最长边可做层次聚类

输入格式：
    邻接矩阵 W（无边=inf/0）或边列表 edges=[(u,v,w),...]；图需连通（无向）

输出：
    mst_edges  : MST 的边列表 [(u, v, w), ...]
    total_cost : MST 总权重

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


def prim(edges, n, start=0):
    """手写 Prim 算法（邻接表 + 每轮扫描找最小连接边）。

    参数:
        edges : 无向图边列表 [(u, v, w), ...]
        n     : 节点数
        start : 起始节点
    返回:
        mst_edges : [(u, v, w), ...]，total_cost : 总权重
    思想：维护"已在树中"的点集，每次在跨越集合的边里选权最小的一条。
    """
    # 构邻接表
    adj = {i: [] for i in range(n)}
    for u, v, w in edges:
        adj[u].append((v, w))
        adj[v].append((u, w))

    in_tree = [False] * n
    in_tree[start] = True
    mst_edges, total = [], 0.0
    for _ in range(n - 1):
        best = None                       # (权重, u, v)：跨集合最小边
        for u in range(n):
            if not in_tree[u]:
                continue
            for v, w in adj[u]:
                if not in_tree[v] and (best is None or w < best[0]):
                    best = (w, u, v)
        if best is None:
            print('[警告] 图不连通，无法生成覆盖所有点的生成树。')
            break
        w, u, v = best
        in_tree[v] = True
        mst_edges.append((u, v, w))
        total += w
    return mst_edges, total


def kruskal(edges, n):
    """手写 Kruskal 算法（边排序 + 并查集判环）。

    参数:
        edges : 无向图边列表 [(u, v, w), ...]
        n     : 节点数
    返回:
        mst_edges : [(u, v, w), ...]，total_cost : 总权重
    思想：边按权升序，逐条加入；若两端已连通（成环）则跳过，用并查集判断。
    """
    parent = list(range(n))

    def find(x):                          # 并查集查根（带路径压缩）
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    mst_edges, total = [], 0.0
    for u, v, w in sorted(edges, key=lambda e: e[2]):   # 按权升序
        ru, rv = find(u), find(v)
        if ru != rv:                      # 不成环才选
            parent[ru] = rv
            mst_edges.append((u, v, w))
            total += w
    if len(mst_edges) < n - 1:
        print('[警告] 图不连通，得到的是最小生成森林。')
    return mst_edges, total


def mst_networkx(edges, n, algorithm='kruskal'):
    """networkx 库版对照，返回 (mst_edges, total_cost)。"""
    G = nx.Graph()
    G.add_nodes_from(range(n))
    for u, v, w in edges:
        G.add_edge(u, v, weight=w)
    T = nx.minimum_spanning_tree(G, algorithm=algorithm, weight='weight')
    mst_edges = [(u, v, d['weight']) for u, v, d in T.edges(data=True)]
    total = sum(w for _, _, w in mst_edges)
    return mst_edges, total


def plot_mst(edges, n, mst_edges, node_names, fname='03_最小生成树MST.png'):
    """画原图（灰）+ MST 边（红色加粗）。"""
    if not HAS_NX:
        print('[提示] 未安装 networkx，跳过绘图。')
        return
    G = nx.Graph()
    G.add_nodes_from(range(n))
    for u, v, w in edges:
        G.add_edge(u, v, weight=w)
    pos = nx.spring_layout(G, seed=42)
    plt.figure(figsize=(10, 7))
    nx.draw_networkx_nodes(G, pos, node_size=800, node_color='lightblue')
    nx.draw_networkx_edges(G, pos, width=1, alpha=0.35, edge_color='gray')

    mst_pairs = {frozenset((u, v)) for u, v, _ in mst_edges}
    hl = [(u, v) for u, v in G.edges() if frozenset((u, v)) in mst_pairs]
    nx.draw_networkx_edges(G, pos, edgelist=hl, width=3, edge_color='red')

    nx.draw_networkx_labels(G, pos, labels={i: node_names[i] for i in range(n)},
                            font_size=12)
    edge_labels = {(u, v): f"{d['weight']:g}" for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=9)
    plt.title('最小生成树 MST（红色加粗为选中的铺设线路）')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f'[图已保存] {fname}')


def print_mst(mst_edges, total, node_names, title):
    """打印 MST 结果。"""
    print(f'\n===== {title} =====')
    for u, v, w in mst_edges:
        print(f'  {node_names[u]} —— {node_names[v]}  权重 {w:g}')
    print(f'  总成本 = {total:g}')


if __name__ == '__main__':
    # ========================================================================
    # 👉 用你自己的国赛附件数据：把下面【示例数据】整段注释掉，改用这段
    #   import pandas as pd
    #   # 附件为"边表"：三列 起点, 终点, 权重（铺设成本/距离）——MST 用无向图
    #   df = pd.read_csv('附件_候选线路.csv', encoding='gbk')  # 乱码换 utf-8
    #   names = sorted(set(df['起点']) | set(df['终点']))
    #   idx = {name: k for k, name in enumerate(names)}
    #   node_names = names
    #   edges = [(idx[r['起点']], idx[r['终点']], float(r['权重']))
    #            for _, r in df.iterrows()]
    #   n = len(names)
    #   # 语义：把所有站点连通的最小总铺设成本，即 MST 总权重
    #   详见 01_数据预处理与可视化/00_CSV数据导入完全指南.py
    # ------------------------------------------------------------------------
    # 【示例数据】(仅供演示，替换为上面的真实数据后可删除)
    # 6 个村镇的候选供水管线，边权=铺设成本（万元），求连通全部的最小成本
    node_names = ['V1', 'V2', 'V3', 'V4', 'V5', 'V6']
    edges = [
        (0, 1, 6), (0, 2, 1), (0, 3, 5),
        (1, 2, 5), (1, 4, 3),
        (2, 3, 5), (2, 4, 6), (2, 5, 4),
        (3, 5, 2),
        (4, 5, 6),
    ]
    n = len(node_names)

    # 手写 Prim
    e_prim, c_prim = prim(edges, n, start=0)
    print_mst(e_prim, c_prim, node_names, '手写 Prim')

    # 手写 Kruskal
    e_krus, c_krus = kruskal(edges, n)
    print_mst(e_krus, c_krus, node_names, '手写 Kruskal')

    print(f'\nPrim 与 Kruskal 总成本一致：{abs(c_prim - c_krus) < 1e-9}')

    # networkx 对照
    if HAS_NX:
        e_nx, c_nx = mst_networkx(edges, n, algorithm='kruskal')
        print_mst(e_nx, c_nx, node_names, 'networkx 库版对照')
        print(f'与手写版总成本一致：{abs(c_krus - c_nx) < 1e-9}')

    # 可视化
    plot_mst(edges, n, e_krus, node_names)
