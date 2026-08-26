# -*- coding: utf-8 -*-
"""
FP-Growth 关联规则挖掘（购物篮 / 品类共现分析）
================================================================
功能：
    从交易记录中挖掘“哪些商品经常一起卖”，输出频繁项集与关联规则
    （支持度 support、置信度 confidence、提升度 lift）。
    比 Apriori 快（不反复扫库），适合 2023C 这类“品类间销量相关/搭配补货”分析，
    可给单品/品类的联合补货、货架陈列、捆绑定价提供依据。

两套实现，自动择优：
    - 优先用 mlxtend.fpgrowth（已安装则用，标准且带规则生成）
    - 未装则回退到内置的纯 numpy/pandas 手写 Apriori（零依赖必跑）

输入：
    transactions : list[list[str]]，每个子列表是一笔交易的商品集合
    min_support  : 最小支持度（0~1，项集出现频率下限）
    min_conf     : 最小置信度（规则 A->B 的可信度下限）

输出：频繁项集表 + 关联规则表（按 lift 降序）

依赖：pandas；可选 mlxtend（有则更快更标准）
运行：PYTHONIOENCODING=utf-8 python 09_FPGrowth关联规则.py
================================================================
"""
import pandas as pd
from itertools import combinations

try:
    from mlxtend.preprocessing import TransactionEncoder
    from mlxtend.frequent_patterns import fpgrowth, association_rules
    _HAS_MLXTEND = True
except Exception:
    _HAS_MLXTEND = False


def _mine_mlxtend(transactions, min_support, min_conf):
    te = TransactionEncoder()
    arr = te.fit(transactions).transform(transactions)
    df = pd.DataFrame(arr, columns=te.columns_)
    freq = fpgrowth(df, min_support=min_support, use_colnames=True)
    if freq.empty:
        return freq, pd.DataFrame()
    rules = association_rules(freq, metric='confidence', min_threshold=min_conf)
    rules = rules.sort_values('lift', ascending=False)
    return freq, rules


def _mine_apriori(transactions, min_support, min_conf):
    """纯 Python 手写 Apriori 回退实现（无第三方依赖）。"""
    n = len(transactions)
    tsets = [frozenset(t) for t in transactions]

    def support(itemset):
        return sum(1 for t in tsets if itemset <= t) / n

    # 逐层生成频繁项集
    items = sorted({i for t in transactions for i in t})
    freq_sets = {}
    current = [frozenset([i]) for i in items]
    k = 1
    while current:
        kept = [(s, support(s)) for s in current]
        kept = [(s, sup) for s, sup in kept if sup >= min_support]
        if not kept:
            break
        for s, sup in kept:
            freq_sets[s] = sup
        # 生成 k+1 候选（合并共享 k-1 前缀的项集）
        base = [s for s, _ in kept]
        cand = set()
        for a, b in combinations(base, 2):
            u = a | b
            if len(u) == k + 1:
                cand.add(u)
        current = list(cand)
        k += 1

    freq_df = pd.DataFrame(
        [(set(s), sup) for s, sup in freq_sets.items()],
        columns=['itemsets', 'support']).sort_values('support', ascending=False)

    # 由频繁项集生成规则
    rules = []
    for s, sup in freq_sets.items():
        if len(s) < 2:
            continue
        for r in range(1, len(s)):
            for ante in combinations(s, r):
                ante = frozenset(ante)
                cons = s - ante
                conf = sup / freq_sets[ante]
                if conf >= min_conf:
                    lift = conf / freq_sets[cons] if cons in freq_sets else conf / support(cons)
                    rules.append({'antecedents': set(ante), 'consequents': set(cons),
                                  'support': sup, 'confidence': conf, 'lift': lift})
    rules_df = pd.DataFrame(rules)
    if not rules_df.empty:
        rules_df = rules_df.sort_values('lift', ascending=False)
    return freq_df, rules_df


def mine_rules(transactions, min_support=0.3, min_conf=0.6):
    """统一入口：有 mlxtend 用 FP-Growth，否则回退手写 Apriori。"""
    if _HAS_MLXTEND:
        print("[引擎] mlxtend FP-Growth")
        return _mine_mlxtend(transactions, min_support, min_conf)
    print("[引擎] 内置手写 Apriori（未装 mlxtend）")
    return _mine_apriori(transactions, min_support, min_conf)


if __name__ == '__main__':
    # 演示：10 笔蔬菜交易（品类共现）
    transactions = [
        ['花叶类', '辣椒类', '食用菌'],
        ['花叶类', '辣椒类'],
        ['花叶类', '食用菌', '茄类'],
        ['辣椒类', '食用菌'],
        ['花叶类', '辣椒类', '食用菌'],
        ['水生根茎类', '茄类'],
        ['花叶类', '辣椒类', '食用菌', '茄类'],
        ['花叶类', '辣椒类'],
        ['食用菌', '茄类'],
        ['花叶类', '辣椒类', '食用菌'],
    ]
    print("=" * 60)
    print("FP-Growth 关联规则挖掘演示（蔬菜品类共现）")
    print("=" * 60)
    freq, rules = mine_rules(transactions, min_support=0.3, min_conf=0.6)

    print("\n[频繁项集]（support ≥ 0.3）")
    print(freq.to_string(index=False))

    if rules is not None and not rules.empty:
        print("\n[关联规则]（confidence ≥ 0.6，按 lift 降序）")
        cols = ['antecedents', 'consequents', 'support', 'confidence', 'lift']
        show = rules[cols].copy()
        for c in ['support', 'confidence', 'lift']:
            show[c] = show[c].round(3)
        print(show.to_string(index=False))
        print("\n解读：lift>1 表示两者正相关（一起买的概率高于独立），可作联合补货/搭配依据。")
    else:
        print("\n未挖出满足阈值的规则，可降低 min_support / min_conf。")
