# -*- coding: utf-8 -*-
"""
01 Dijkstra：非负权最短路与路径审计
=================================

study-only 模板。最短路算法通常不是难点；正式建模最重要的是确认：节点、边、方向、
权重单位和不可达语义都与现实问题一致。距离/时间/成本不能在同一权重中无说明混用。

Dijkstra 只适用于有限非负边权。若存在负权，应更换算法并重新解释权重语义。
"""

from __future__ import annotations

import heapq
import numpy as np


def build_matrix_from_edges(edges, n, directed=False):
    if not isinstance(n, (int, np.integer)) or n <= 0:
        raise ValueError("n 必须为正整数")
    W = np.full((n, n), np.inf, dtype=float)
    np.fill_diagonal(W, 0.0)
    for edge in edges:
        if len(edge) != 3:
            raise ValueError("每条边必须是 (u,v,w)")
        u, v, w = edge
        if not isinstance(u, (int, np.integer)) or not isinstance(v, (int, np.integer)) or not (0 <= u < n and 0 <= v < n):
            raise ValueError(f"节点编号越界: {(u, v)}")
        w = float(w)
        if not np.isfinite(w) or w < 0:
            raise ValueError(f"Dijkstra 要求有限非负边权，发现 w={w}")
        W[u, v] = min(W[u, v], w)
        if not directed:
            W[v, u] = min(W[v, u], w)
    return W


def validate_weight_matrix(W):
    W = np.asarray(W, dtype=float)
    if W.ndim != 2 or W.shape[0] != W.shape[1]:
        raise ValueError("W 必须为方阵")
    if np.isnan(W).any() or np.isneginf(W).any():
        raise ValueError("W 不能含 NaN/-Inf；无边请用 +Inf")
    finite = np.isfinite(W)
    if np.any(W[finite] < 0):
        raise ValueError("Dijkstra 不允许负权边")
    if not np.allclose(np.diag(W), 0.0):
        raise ValueError("邻接矩阵对角线应为 0")
    return W


def audit_path(W, path):
    """独立重算路径成本；非法边返回 accepted=False。"""
    W = validate_weight_matrix(W)
    if path is None:
        return {"accepted": True, "cost": np.inf, "reason": "unreachable"}
    if len(path) == 0:
        return {"accepted": False, "cost": None, "reason": "empty path"}
    cost = 0.0
    for u, v in zip(path[:-1], path[1:]):
        if not (0 <= u < len(W) and 0 <= v < len(W)) or not np.isfinite(W[u, v]):
            return {"accepted": False, "cost": None, "reason": f"missing edge {u}->{v}"}
        cost += float(W[u, v])
    return {"accepted": True, "cost": cost, "reason": None}


def dijkstra(W, start):
    W = validate_weight_matrix(W)
    n = len(W)
    if not isinstance(start, (int, np.integer)) or not 0 <= start < n:
        raise ValueError("start 越界")

    dist = np.full(n, np.inf)
    dist[start] = 0.0
    prev = np.full(n, -1, dtype=int)
    visited = np.zeros(n, dtype=bool)
    queue = [(0.0, int(start))]

    while queue:
        d, u = heapq.heappop(queue)
        if visited[u]:
            continue
        visited[u] = True
        for v in np.where(np.isfinite(W[u]))[0]:
            if visited[v] or v == u:
                continue
            candidate = d + W[u, v]
            if candidate < dist[v]:
                dist[v] = candidate
                prev[v] = u
                heapq.heappush(queue, (float(candidate), int(v)))

    paths = []
    audit = []
    for end in range(n):
        if not np.isfinite(dist[end]):
            paths.append(None)
            audit.append({"accepted": True, "cost": np.inf, "matches_distance": True})
            continue
        path, cur = [], end
        seen = set()
        while cur != -1:
            if cur in seen:
                raise RuntimeError("前驱链出现环，内部实现错误")
            seen.add(cur)
            path.append(cur)
            cur = int(prev[cur])
        path = path[::-1]
        check = audit_path(W, path)
        check["matches_distance"] = bool(check["accepted"] and np.isclose(check["cost"], dist[end], atol=1e-10, rtol=1e-10))
        paths.append(path)
        audit.append(check)

    if not all(row.get("matches_distance", False) for row in audit):
        raise RuntimeError("路径回查与最短距离不一致")
    return {"dist": dist, "paths": paths, "path_audit": audit, "start": int(start)}


def networkx_crosscheck(edges, n, start, directed=False):
    """可选独立实现交叉核验；缺依赖则显式返回 skipped，不改变主算法身份。"""
    try:
        import networkx as nx
    except ImportError:
        return {"available": False, "reason": "networkx not installed"}
    G = nx.DiGraph() if directed else nx.Graph()
    G.add_nodes_from(range(n))
    for u, v, w in edges:
        w = float(w)
        if G.has_edge(u, v):
            G[u][v]["weight"] = min(float(G[u][v]["weight"]), w)
        else:
            G.add_edge(u, v, weight=w)
    length, paths = nx.single_source_dijkstra(G, start, weight="weight")
    return {
        "available": True,
        "dist": np.array([length.get(i, np.inf) for i in range(n)], dtype=float),
        "paths": [paths.get(i) for i in range(n)],
    }


if __name__ == "__main__":
    edges = [
        (0, 1, 4), (0, 6, 2), (1, 2, 6), (2, 3, 3),
        (2, 5, 5), (3, 4, 2), (4, 5, 1), (5, 6, 4),
    ]
    W = build_matrix_from_edges(edges, 7, directed=False)
    result = dijkstra(W, 0)
    print("dist =", result["dist"])
    print("paths =", result["paths"])
    cross = networkx_crosscheck(edges, 7, 0)
    if cross["available"]:
        print("networkx distance match =", np.allclose(result["dist"], cross["dist"], equal_nan=True))
    print("\n正式论文首先说明边权到底是距离、时间还是成本，并报告不可达节点；算法名称本身不是建模贡献。")
