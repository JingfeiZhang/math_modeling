from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.corpus.miner import build_paper_card, validate_paper_card


PAPERS: dict[str, dict[str, Any]] = {
    "cumcm-2024-a163": {
        "title": "基于几何模型的板凳龙运动路径问题",
        "problem": "A",
        "abstract": ["问题背景与目标", "五个子问题的方法链", "位置、速度和约束结论", "关键词"],
        "models": [(4, "用阿基米德螺线和极坐标描述龙头与龙身把手位置"), (13, "以位置迭代和速度迭代计算盘入过程的整队状态"), (26, "复用几何迭代计算调头路径前后关键时刻的位置"), (28, "用速度比和最大速度约束确定龙头允许速度")],
        "validations": [(13, "同页给出全局/局部几何图以及关键把手位置和速度表"), (26, "在统一单位的关键时刻表中检查多节点位置演化"), (28, "以最大速度诊断曲线检查限制条件并在模型评价中说明计算复杂度")],
        "figures": [(4, "mechanism", "板凳龙盘入几何示意", "固定板凳实体、螺线和碰撞点的语义编码"), (13, "multi-panel", "盘入终止时刻全局与局部视图", "全局状态、局部放大和数值表互补"), (26, "trajectory", "调头过程关键时刻位置图", "用相同坐标与颜色比较时刻变化"), (28, "diagnostic", "关键把手最大速度曲线", "把速度约束的激活位置显式化")],
        "rules": ["机理题的每个几何约束应配变量清晰的示意图", "主结果用全局图、局部放大和关键数值表联合表达", "统一实体颜色和参考线颜色以支持跨页追踪"],
        "risks": ["本地只缓存官方展示的前 30/45 页，结尾与附录未进入本次视觉复核", "并排图标题存在断行，默认折线图字号和留白仍可改进"],
    },
    "cumcm-2024-b159": {
        "title": "生产过程中的决策优化设计",
        "problem": "B",
        "abstract": ["生产决策背景", "四个子问题的统计与优化模型", "最优利润和稳健性结论", "关键词"],
        "models": [(1, "用假设检验设计抽样检测方案"), (3, "把零配件、半成品和成品组织为状态-决策结构"), (13, "枚举检测与拆解策略并以期望利润最大化选方案"), (19, "用 Beta-Binomial 后验更新次品率并重算决策"), (22, "改变先验参数检查期望利润对超参数的敏感性")],
        "validations": [(13, "用 16 种方案乘 6 种情景的完整矩阵比较并逐列标记最优值"), (19, "在相同决策表结构下比较贝叶斯更新后的方案变化"), (22, "分别扰动 alpha 与 beta 并观察期望利润曲线的稳定性")],
        "figures": [(3, "schematic", "多工序生产层级示意", "用最少节点解释零配件到成品的依赖"), (13, "decision-table", "全方案全情景期望利润矩阵", "用单一强调色标出各情景最优方案"), (22, "sensitivity", "先验参数单因素敏感性曲线", "把参数变化和结论稳定性放在模型评价之前")],
        "rules": ["离散决策题应给出完整候选方案与情景矩阵", "复杂推导必须落到可执行的检测或拆解决策", "灵敏度图与最终模型评价应形成闭环"],
        "risks": ["本地只缓存官方展示的前 30/37 页，结尾与附录未进入本次视觉复核", "灵敏度图接近软件默认样式且没有不确定性带"],
    },
    "cumcm-2024-c038": {
        "title": "基于差分遗传算法的农作物种植策略优化",
        "problem": "C",
        "abstract": ["种植规划背景与数据", "确定性 DEGA 模型", "CVaR 与相关性扩展", "量化收益、敏感性和关键词"],
        "models": [(3, "用四象限路线图组织确定性、风险和相关性三层模型"), (21, "用差分进化遗传算法求解地块-作物-季节种植矩阵"), (29, "将 CVaR 风险项嵌入 DEGA 形成风险约束优化"), (32, "在同一利润口径下比较风险与非风险模型")],
        "validations": [(1, "摘要同时报告基准、风险情景与敏感性结果"), (23, "用年度利润和累计利润曲线检查优化结果与算法收敛"), (32, "在一致视觉编码下比较 CVaR 与非风险方案的累计利润" )],
        "figures": [(3, "flowchart", "四象限总体思路框架", "显示问题之间的模型递进而非只列算法名"), (21, "heatmap", "分季节地块-作物种植方案矩阵", "用稀疏热力图表达组合优化方案"), (23, "multi-panel", "年度利润与累计利润收敛图", "区分经济结果和求解过程证据"), (29, "flowchart", "CVaR-DEGA 求解流程", "显示风险函数如何进入搜索循环"), (32, "comparison", "风险与非风险累计利润比较", "在相同尺度下呈现稳健性代价")],
        "rules": ["摘要同时给最优值、对照值和风险情景值", "组合方案先用矩阵图表达结构，再用表格给精确数值", "收敛曲线只能证明算法行为，不能替代基线比较"],
        "risks": ["本地只缓存官方展示的前 33/61 页，后半正文与附录未进入本次视觉复核", "高维热力图标签密集，利润图仍保留科学计数标记"],
    },
    "cumcm-2024-d033": {
        "title": "反潜航空深弹命中概率的优化问题",
        "problem": "D",
        "abstract": ["反潜深弹背景", "三问概率模型和优化变量", "最大命中概率与参数结论", "关键词"],
        "models": [(4, "用二维正态分布描述潜艇水平定位误差"), (7, "按引爆深度把命中区域分段并建立二维积分概率"), (10, "将投弹落点和深度写入命中概率积分并求最大值"), (20, "用粗网格与细网格搜索定位最优引爆深度"), (21, "把九枚深弹的相交命中区域拆分并求联合概率")],
        "validations": [(20, "先用大步长搜索再在峰值附近缩小步长，检查最优深度是否稳定"), (22, "给出九弹方案的概率结果并单列模型优缺点和推广边界"), (24, "附录公开积分与搜索代码，使正文概率表达可定位到实现")],
        "figures": [(7, "mechanism", "不同引爆深度下的命中区域", "用几何阴影把分段积分边界可视化"), (10, "distribution", "正态分布与积分范围示意", "把定位误差分布和命中区间连接起来"), (20, "sensitivity", "命中概率随引爆深度的粗细步长曲线", "用两级搜索确认峰值位置"), (21, "mechanism", "九枚深弹命中范围相切示意", "将联合概率的空间分区和炸弹编号对齐")],
        "rules": ["分段积分前先画出每个积分域及其边界", "数值优化用粗搜加局部细搜呈现峰值稳定性", "附录代码必须能映射到正文公式和图件"],
        "risks": ["论文主要以解析积分和网格搜索验证，缺少外部基线或仿真对照", "部分长公式可移入附录以改善正文节奏"],
    },
    "cumcm-2024-e010": {
        "title": "交通流量管控",
        "problem": "E",
        "abstract": ["交通拥堵背景", "四问的数据、预测和优化模型", "车速、停车需求与管控效果", "关键词"],
        "models": [(1, "用 K-means、DBSCAN 和 GMM 识别交通时段并用 XGBoost 估计流量"), (12, "通过车牌轨迹匹配与去重获得转向流量"), (16, "用 Webster 配时和遗传算法求干线协调信号方案"), (19, "结合车辆轨迹、巡游判定和泊松需求估计停车位"), (26, "比较管控前后流量、等待时间和车速")],
        "validations": [(7, "用共享坐标的小多图比较多个周区间的日内流量形态"), (19, "在同一页比较优化前后车速并把结果落回真实路网"), (26, "汇总管控前后指标并在模型评价中指出数据和稳健性限制")],
        "figures": [(7, "small-multiples", "四周日内流量小多图", "固定坐标比较周期复现性"), (12, "flowchart", "车牌轨迹匹配与去重流程", "将分支判断从长段伪代码中分离"), (16, "time-space", "多路口干线协调时距图", "在同一坐标展示相位和车辆轨迹"), (19, "map", "优化前后车速与真实路网", "把节点编号重新连接到空间对象")],
        "rules": ["时序题用共享坐标轴的小多图检查周期性", "匹配和去重算法优先用判断流程图", "空间结论必须回到地图或拓扑图验证"],
        "risks": ["本地只缓存官方展示的前 30/39 页，尾页与附录未进入本次视觉复核", "部分图保留绘图窗口或终端截图，跨图字号和配色不统一"],
    },
    "cumcm-2024-e061": {
        "title": "基于多目标优化的交通管理评估分析",
        "problem": "E",
        "abstract": ["景区交通背景与数据", "四问聚类、优化和需求模型", "配时、停车位与管控效果数字", "关键词"],
        "models": [(4, "汇总交叉口方向流量并用 K-means 划分低中高峰时段"), (7, "用 PSO 估计转向比例并建立马尔可夫决策过程"), (10, "用 DQN 搜索不同时段的信号相位配时"), (11, "由轨迹速度和重复访问识别巡游车辆"), (13, "用泊松分布的分位数估计临时停车位需求"), (14, "建立流量、等待时间和车速的管控前后评价指标")],
        "validations": [(10, "用相位时间表和各方向平均等待时间比较优化策略"), (14, "用统一百分比口径比较管控前后流量、等待时间和车速"), (15, "对交通流量、转向比例和信号时长做敏感度与误差来源分析")],
        "figures": [(4, "line", "交叉口 24 小时流量趋势", "先展示峰谷结构再进行时段聚类"), (11, "distribution", "巡游车辆速度分布直方图", "把巡游判定阈值和速度分布联系起来"), (13, "line", "每日巡游车辆数量趋势", "支撑停车需求的时间变化判断"), (14, "comparison", "管控前后指标评价", "用一致口径连接优化方案和业务效果")],
        "rules": ["聚类必须用特征统计解释类别语义", "优化结果同时报告相位方案和等待时间", "管控前后指标使用同一口径、单位和比较范围"],
        "risks": ["DQN 与 PSO 的基线比较和重复运行证据不足", "多路段结果图需要更统一的颜色、字号和不确定性表达"],
    },
}


def _manifest_digest(manifest: Mapping[str, Any]) -> str:
    pages = [{"page": item["page"], "url": item["url"], "sha256": item["sha256"]} for item in manifest["pages"]]
    payload = json.dumps(pages, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _verify_pages(root: Path, paper_id: str, manifest: Mapping[str, Any]) -> None:
    page_root = root / "corpus" / "raw" / paper_id
    if int(manifest["cached_pages"]) != len(manifest["pages"]):
        raise ValueError(f"cached page count mismatch: {paper_id}")
    for item in manifest["pages"]:
        data = (page_root / item["file"]).read_bytes()
        if len(data) != int(item["bytes"]):
            raise ValueError(f"page byte count mismatch: {paper_id} p.{item['page']}")
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError(f"page SHA-256 mismatch: {paper_id} p.{item['page']}")


def build_card(root: Path, paper_id: str) -> dict[str, Any]:
    spec = PAPERS[paper_id]
    manifest_path = root / "corpus" / "raw" / paper_id / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _verify_pages(root, paper_id, manifest)
    cached = int(manifest["cached_pages"])
    reported = int(manifest["reported_total_pages"])
    complete = cached == reported

    def render(page: int) -> str:
        if page < 1 or page > cached:
            raise ValueError(f"evidence page outside local cache: {paper_id} p.{page}")
        return f"corpus/raw/{paper_id}/page-{page:02d}.jpg"

    page_evidence = [{"page": 1, "tags": ["abstract", "layout"], "observation": f"摘要按“{'；'.join(spec['abstract'])}”组织。", "derivation": "visual", "locator": "official page image 1", "render": render(1)}]
    for page, description in spec["models"]:
        page_evidence.append({"page": page, "tags": ["model_chain"], "observation": description, "derivation": "visual", "locator": f"official page image {page}", "render": render(page)})
    for page, description in spec["validations"]:
        page_evidence.append({"page": page, "tags": ["validation"], "observation": description, "derivation": "visual", "locator": f"official page image {page}", "render": render(page)})

    record = {
        "paper_id": paper_id,
        "identity": {"contest": "CUMCM", "year": 2024, "problem": spec["problem"], "team_id": paper_id.rsplit("-", 1)[-1].upper(), "title": spec["title"]},
        "source": {"url": manifest["source_url"], "publisher": "official", "accessible": True, "fulltext": True, "access": "public_page_images"},
        "award_evidence": {"verified": True, "official_url": manifest["source_url"], "contest": "CUMCM", "year": 2024, "problem": spec["problem"], "team_id": paper_id.rsplit("-", 1)[-1].upper(), "title": spec["title"], "award": "全国大学生数学建模竞赛组委会官方论文展示"},
        "pdf": {"sha256": _manifest_digest(manifest), "pages": cached, "local_path": manifest_path.relative_to(root).as_posix(), "kind": "official_page_image_set", "source_pdf_available": False, "derived_review_pdf": "", "reported_total_pages": reported, "cached_pages": cached},
        "review_status": "evidence_deep_read" if complete else "evidence_reviewed",
        "page_evidence": page_evidence,
        "abstract_structure": [{"page": 1, "order": index + 1, "role": role, "locator": "official page image 1"} for index, role in enumerate(spec["abstract"])],
        "model_chain": [{"step": index + 1, "page": page, "description": description, "locator": f"official page image {page}"} for index, (page, description) in enumerate(spec["models"])],
        "validation_chain": [{"step": index + 1, "page": page, "description": description, "locator": f"official page image {page}"} for index, (page, description) in enumerate(spec["validations"])],
        "figures": [{"page": page, "role": "model explanation" if kind in {"flowchart", "mechanism", "schematic"} else "result evidence", "chart_type": kind, "caption": caption, "lesson": lesson, "locator": f"official page image {page}", "render": render(page), "visual_checked": True} for page, kind, caption, lesson in spec["figures"]],
        "code_links": [],
        "transferable_rules": [{"rule": rule, "evidence_page": spec["figures"][min(index, len(spec["figures"]) - 1)][0]} for index, rule in enumerate(spec["rules"])],
        "risks": [*spec["risks"], "官方展示标签不等同于独立奖级声明；卡片不推断具体奖项。"],
        "provenance": {"source_manifest": manifest_path.relative_to(root).as_posix(), "source_artifact_kind": "official_page_images", "derived_review_pdf": False, "reported_total_pages": reported, "cached_pages": cached, "coverage": cached / reported, "visual_review": "selected evidence pages complete", "review_scope": "full cached set" if complete else "cached prefix and selected evidence pages", "page_image_manifest_sha256": _manifest_digest(manifest)},
    }
    return build_paper_card(record, require_deep_read=complete)


def migrate(root: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for paper_id in PAPERS:
        card = build_card(root, paper_id)
        errors = validate_paper_card(card, require_deep_read=card["review_status"] == "evidence_deep_read")
        if errors:
            raise ValueError(f"{paper_id}: {'; '.join(errors)}")
        target = root / "corpus" / "cards" / f"{paper_id}.json"
        target.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        records.append({"paper_id": paper_id, "authenticity": card["authenticity"]["level"], "review_status": card["review_status"], "cached_pages": card["pdf"]["cached_pages"], "reported_total_pages": card["pdf"]["reported_total_pages"], "card": target.relative_to(root).as_posix()})
    report = {"schema_version": 1, "program": "2024 official CUMCM page-image cards migrated to paper_card v3", "selected": len(records), "authenticity_counts": {"A": sum(item["authenticity"] == "A" for item in records)}, "review_status_counts": {status: sum(item["review_status"] == status for item in records) for status in sorted({item["review_status"] for item in records})}, "records": records, "source_pdf_policy": "No official source PDF is claimed. pdf.sha256 hashes the ordered official page-image manifest; derived_review_pdf remains empty."}
    report_path = root / "corpus" / "manifests" / "cumcm-2024-official-v3.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate six 2024 official CUMCM page-image cards to paper_card v3.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    print(json.dumps(migrate(args.root.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
