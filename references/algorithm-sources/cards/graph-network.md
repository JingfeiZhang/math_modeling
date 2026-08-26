---
algorithm_card_id: graph-network
source_id: github-jingfeizhang-1
source_commit: 8abaef8c9262017925099d1463ebc78c1ab6a956
source_path: "08_图论与网络模型"
entry_points:
  - path: "08_图论与网络模型/01_Dijkstra单源最短路.py"
    symbol: "dijkstra"
    kind: function
    purpose: "非负权图上的单源最短路径"
    input: "权重矩阵和源节点"
    output: "距离和路径"
    file_sha256: "05b37b1ee5d21c0b625043024ab8fe20246ec89f0c8bf33d51e31e195ad06f8b"
    locator_url: "https://github.com/JingfeiZhang/1/blob/8abaef8c9262017925099d1463ebc78c1ab6a956/08_%E5%9B%BE%E8%AE%BA%E4%B8%8E%E7%BD%91%E7%BB%9C%E6%A8%A1%E5%9E%8B/01_Dijkstra%E5%8D%95%E6%BA%90%E6%9C%80%E7%9F%AD%E8%B7%AF.py"
  - path: "08_图论与网络模型/04_最大流最小割.py"
    symbol: "max_flow_edmonds_karp"
    kind: function
    purpose: "容量网络上的最大流和割证书"
    input: "有向边、容量、源点和汇点"
    output: "最大流值、流量方案和最小割"
    file_sha256: "d4f11bfc634e9b0ce268fd51019168ddcd9e3f62b961803a5061412ffd43216a"
    locator_url: "https://github.com/JingfeiZhang/1/blob/8abaef8c9262017925099d1463ebc78c1ab6a956/08_%E5%9B%BE%E8%AE%BA%E4%B8%8E%E7%BD%91%E7%BB%9C%E6%A8%A1%E5%9E%8B/04_%E6%9C%80%E5%A4%A7%E6%B5%81%E6%9C%80%E5%B0%8F%E5%89%B2.py"
skeleton_path: "references/algorithm-sources/skeletons/network/graph_contract.py"
tags: [graph, network, shortest-path, dijkstra, max-flow, min-cut, mst, routing]
stage_scope: [P1, P2, P3a, P3b]
evidence_status: P1-P3-non-evidence
contest_evidence_eligible: false
allowed_use: [model_direction, assumption_check, baseline_design, risk_probe]
forbidden_use: [formal_evidence, claim_support, figure_contract, submission, release, direct_copy]
language: python
license_status: NO_LICENSE
interface: "nodes and edges with weights/capacities -> paths, flows or connectivity decisions"
baseline_required: [direct-edge-or-greedy, small-instance-enumeration]
baseline_options:
  - {id: direct-edge-or-greedy, when: "路径或网络分配任务", required: true}
  - {id: small-instance-enumeration, when: "可枚举的小图", required: true}
  - {id: capacity-conservation-check, when: "流网络", required: true}
known_risks: ["Dijkstra不能处理负权边", "有向/无向解释必须锁定", "不连通节点不能被当成大权重可达", "最大流必须同时回查容量和流守恒"]
adaptation_required: ["定义节点边和权重单位", "处理不可达和并列路径", "报告最短路或割的证书", "与小规模精确结果对照"]
---

## 适用信号

题面出现道路、物流、通信、依赖关系、资源输送、瓶颈或连通性时使用。先判断目标是最短路、最大流、匹配、生成树还是网络统计。

## 输入输出

输入是节点、边、方向、权重/容量及单位；输出必须保留路径或流量方案、不可达规则、容量约束和可复核证书。

## baseline 与升级

先做直连/贪心或小图枚举，再使用 Dijkstra、Floyd、最大流最小割、MST 或匹配模型。大规模算法必须用小规模精确结果回查。

## 验证要求

检查权重非负性、方向、路径连续性、流守恒、容量上界和源汇定义。报告不可达节点、并列最优处理和至少一个证书或不变量。

## 已知风险

错误的边方向、单位混用、把不可达设为零和遗漏容量守恒会产生看似合理但无效的结果。图结构变化时不能直接复用旧路径结论。

## 停止与回退

若图规模允许枚举，优先保留可证明的精确解；若只能近似，明确算法边界、规模和证据，不写成全局最优。

## 适配步骤

先建立图数据合同，再选图算法、基线和证书，最后设计网络结构、流量或路径的图件。

## 来源与边界

参考固定 commit 的 [08_图论与网络模型](https://github.com/JingfeiZhang/1/tree/8abaef8c9262017925099d1463ebc78c1ab6a956/08_%E5%9B%BE%E8%AE%BA%E4%B8%8E%E7%BD%91%E7%BB%9C%E6%A8%A1%E5%9E%8B)。源无明确许可证，只读学习；不得执行或直接复制代码。
