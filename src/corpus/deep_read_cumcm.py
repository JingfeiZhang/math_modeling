from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader

from src.corpus.miner import build_paper_card, git_blob_sha1, validate_paper_card


ZHANWEN_COMMIT = "cd5be91735ebf11d5ee52eb170e86a6d07131977"
PERSON_COMMIT = "8783d0d822f89f98aa6182dd933cc2e9f3e2ddce"


@dataclass(frozen=True)
class Selection:
    paper_id: str
    year: int
    problem: str
    source_id: str
    repository: str
    commit: str
    path: str
    blob_sha: str
    expected_bytes: int

    @property
    def source_url(self) -> str:
        encoded = urllib.parse.quote(self.path, safe="/")
        repo = self.repository.removeprefix("https://github.com/")
        return f"https://raw.githubusercontent.com/{repo}/{self.commit}/{encoded}"

    @property
    def blob_url(self) -> str:
        repo = self.repository.removeprefix("https://github.com/")
        return f"https://api.github.com/repos/{repo}/git/blobs/{self.blob_sha}"


def _s(
    year: int,
    problem: str,
    label: str,
    source_id: str,
    path: str,
    blob_sha: str,
    expected_bytes: int,
) -> Selection:
    if source_id == "personqianduixue-math-model":
        repository = "https://github.com/personqianduixue/Math_Model"
        commit = PERSON_COMMIT
    else:
        repository = "https://github.com/zhanwen/MathModel"
        commit = ZHANWEN_COMMIT
    return Selection(f"cumcm-{year}-{problem.lower()}-{label.lower()}", year, problem, source_id, repository, commit, path, blob_sha, expected_bytes)


SELECTIONS: tuple[Selection, ...] = (
    _s(2012, "A", "a441", "personqianduixue-math-model", "2-1国赛题目+论文/2012/A441.pdf", "c47d14f1eb3e4b691f414718704cb09a74f04bff", 913961),
    _s(2012, "B", "b077", "personqianduixue-math-model", "2-1国赛题目+论文/2012/B077/B077.pdf", "cf7292cde264ee32dbadd79cbb87a3bdb50d834e", 410426),
    _s(2013, "C", "c048", "personqianduixue-math-model", "2-1国赛题目+论文/2013/C048/1C2302/成都工业学院 专5 C 肖瑜琳 刘新燕 黄龙.pdf", "42e7c6d454de85b66d90321efde3839e6f8add88", 913379),
    _s(2013, "A", "a056", "personqianduixue-math-model", "2-1国赛题目+论文/2013/A056/5486/5486.pdf", "29ce09bd0b75f5ff763168407005295d2af714bc", 1824385),
    _s(2014, "B", "b009", "personqianduixue-math-model", "2-1国赛题目+论文/2014/B009/B16046004_程双泽_李君昌_陈凌勤/B16046004_程双泽_李君昌_陈凌勤.pdf", "89f592540d083ebccd0bbd6a8da934b8f7b58ccb", 1048457),
    _s(2014, "A", "a305", "personqianduixue-math-model", "2-1国赛题目+论文/2014/A305/A10009072_吉张鹤轩_杨升_陈同广/A10009072_吉张鹤轩_杨升_陈同广.pdf", "56100fa1d940da3d7f3ef97385a878d54e000346", 1426258),
    _s(2015, "A", "a095", "personqianduixue-math-model", "2-1国赛题目+论文/2015/A095.pdf", "6437c9a1bbec1da6fc257d385f1c470fd6022488", 1610191),
    _s(2015, "B", "b013", "personqianduixue-math-model", "2-1国赛题目+论文/2015/B013.pdf", "f703326d337a604a126f7780c63ca01ff1317dd9", 1154846),
    _s(2016, "D", "d056", "personqianduixue-math-model", "2-1国赛题目+论文/2016/D056.pdf", "fd305c521bafcd3c70c8f8a0c453b0d494d016df", 3973988),
    _s(2016, "B", "b067", "personqianduixue-math-model", "2-1国赛题目+论文/2016/B067.pdf", "a66571a5023e5c3f86dd97458a3e3a44adb04f87", 811809),
    _s(2017, "B", "b264", "personqianduixue-math-model", "2-1国赛题目+论文/2017/B264.pdf", "9606abcf5d0fd328a05f0b54aac2b45aadbe5d5d", 738431),
    _s(2017, "A", "a156", "personqianduixue-math-model", "2-1国赛题目+论文/2017/A156.pdf", "2d0233be1296c9ef5b624e0920cd374689eaa57d", 1192412),
    _s(2018, "C", "c101", "personqianduixue-math-model", "2-1国赛题目+论文/2018/C101.pdf", "3edbbaf80e11edf49c9dde88fcc25f388857ade6", 580211),
    _s(2018, "B", "b334", "personqianduixue-math-model", "2-1国赛题目+论文/2018/B334.pdf", "2185da8cceff0876c10ca260e585ffdfe12f2529", 594103),
    _s(2019, "B", "b057", "personqianduixue-math-model", "2-1国赛题目+论文/2019/B057.pdf", "a679c4aabe628416fed50175c307baa9bce51a37", 2177928),
    _s(2019, "E", "e038", "personqianduixue-math-model", "2-1国赛题目+论文/2019/E038.pdf", "237a4696ffb91e231587a818fe93eda02d92a009", 1971619),
    _s(2020, "A", "a212", "personqianduixue-math-model", "2-1国赛题目+论文/2020/A212.pdf", "65468e70b144c90207b33bb1027e0374c61b07c4", 11590988),
    _s(2020, "D", "d011", "personqianduixue-math-model", "2-1国赛题目+论文/2020/D011.pdf", "f587309b4db296f4a458c2f72fc57dbe9c2cb758", 9217498),
)


def _json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _fetch(url: str) -> bytes:
    last_error: OSError | None = None
    for attempt in range(1, 4):
        headers = {"User-Agent": "math-modeling-paper-miner/1"}
        if "/git/blobs/" in url:
            headers["Accept"] = "application/vnd.github.raw+json"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return response.read()
        except OSError as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(attempt * 2)
    assert last_error is not None
    raise last_error


def validate_selections(tree_paths: Mapping[str, Path]) -> None:
    trees: dict[str, dict[str, dict[str, Any]]] = {}
    for source_id, tree_path in tree_paths.items():
        payload = json.loads(tree_path.read_text(encoding="utf-8"))
        trees[source_id] = {entry["path"]: entry for entry in payload["entries"]}
    for selection in SELECTIONS:
        entry = trees.get(selection.source_id, {}).get(selection.path)
        if entry is None:
            raise ValueError(f"selection is absent from pinned tree: {selection.paper_id}")
        if entry["blob_sha"] != selection.blob_sha or int(entry["bytes"]) != selection.expected_bytes:
            raise ValueError(f"pinned tree metadata changed for {selection.paper_id}")
    years = [selection.year for selection in SELECTIONS]
    if len(SELECTIONS) != 18 or any(years.count(year) != 2 for year in range(2012, 2021)):
        raise ValueError("historical selection must contain two CUMCM papers per year from 2012 through 2020")
    if any(selection.source_id != "personqianduixue-math-model" for selection in SELECTIONS):
        raise ValueError("historical CUMCM selection cannot use the zhanwen GMCM mirror")


def cache_pdfs(root: Path, *, fetcher=_fetch) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for selection in SELECTIONS:
        paper_root = root / "corpus" / "raw" / selection.paper_id
        prior_manifest_path = paper_root / "source_manifest.json"
        if prior_manifest_path.exists():
            prior = json.loads(prior_manifest_path.read_text(encoding="utf-8"))
            prior_pdf = prior.get("pdf", {})
            prior_object = root / str(prior_pdf.get("object", ""))
            if (
                prior_object.is_file()
                and prior_pdf.get("git_blob_sha") == selection.blob_sha
                and int(prior_pdf.get("bytes", -1)) == selection.expected_bytes
                and _sha256(prior_object.read_bytes()) == prior_pdf.get("sha256")
            ):
                records.append(prior)
                continue
        fetch_errors: list[str] = []
        content: bytes | None = None
        for url in (selection.blob_url, selection.source_url):
            try:
                content = fetcher(url)
                break
            except OSError as exc:
                fetch_errors.append(f"{url}: {exc}")
        if content is None:
            raise OSError("; ".join(fetch_errors))
        if len(content) != selection.expected_bytes:
            raise ValueError(f"byte count mismatch for {selection.paper_id}")
        if git_blob_sha1(content) != selection.blob_sha:
            raise ValueError(f"Git blob SHA mismatch for {selection.paper_id}")
        if not content.startswith(b"%PDF"):
            raise ValueError(f"downloaded artifact is not PDF: {selection.paper_id}")
        digest = _sha256(content)
        object_path = root / "corpus" / "raw" / "objects" / "sha256" / digest[:2] / f"{digest}.pdf"
        if not object_path.exists():
            object_path.parent.mkdir(parents=True, exist_ok=True)
            object_path.write_bytes(content)
        source_manifest = {
            "schema_version": 1,
            "paper_id": selection.paper_id,
            "contest": "CUMCM",
            "year": selection.year,
            "problem_id": selection.problem,
            "source": {
                "repository": selection.repository,
                "commit": selection.commit,
                "path": selection.path,
                "url": selection.source_url,
                "accessed": date.today().isoformat(),
                "authenticity_level": "C",
                "authenticity_note": "Community mirror full text; no independent official award locator recorded.",
            },
            "pdf": {
                "object": object_path.relative_to(root).as_posix(),
                "bytes": len(content),
                "git_blob_sha": selection.blob_sha,
                "sha256": digest,
            },
            "render": {"status": "pending", "pages": []},
        }
        _json_write(paper_root / "source_manifest.json", source_manifest)
        records.append(source_manifest)
    return records


def _resolve_command(name: str) -> list[str]:
    command = shutil.which(name)
    if not command:
        raise RuntimeError(f"required PDF command not found: {name}")
    if command.lower().endswith((".cmd", ".bat")):
        wrapper = Path(command).resolve()
        if "dependencies" in {part.casefold() for part in wrapper.parts}:
            dependencies = next(parent for parent in wrapper.parents if parent.name.casefold() == "dependencies")
            native = dependencies / "native" / "poppler" / "Library" / "bin" / f"{name}.exe"
            if native.is_file():
                return [str(native)]
        return ["cmd.exe", "/d", "/c", command]
    return [command]


def _run(command: Sequence[str]) -> None:
    completed = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode != 0:
        error = completed.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}\n{error}")


def _contact_sheets(images: list[Path], target_dir: Path) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    output: list[Path] = []
    font = ImageFont.load_default()
    for offset in range(0, len(images), 8):
        group = images[offset : offset + 8]
        thumb_width, thumb_height = 480, 680
        sheet = Image.new("RGB", (thumb_width * 4, (thumb_height + 30) * 2), "white")
        draw = ImageDraw.Draw(sheet)
        for index, image_path in enumerate(group):
            with Image.open(image_path) as image:
                image.thumbnail((thumb_width - 12, thumb_height - 12))
                x = (index % 4) * thumb_width + (thumb_width - image.width) // 2
                y = (index // 4) * (thumb_height + 30) + 24 + (thumb_height - image.height) // 2
                sheet.paste(image.convert("RGB"), (x, y))
                draw.text(((index % 4) * thumb_width + 8, (index // 4) * (thumb_height + 30) + 5), image_path.stem, fill="black", font=font)
        start = offset + 1
        end = offset + len(group)
        target = target_dir / f"contact-{start:02d}-{end:02d}.jpg"
        sheet.save(target, "JPEG", quality=86, optimize=True)
        output.append(target)
    return output


def render_and_extract(root: Path) -> list[dict[str, Any]]:
    pdftoppm = _resolve_command("pdftoppm")
    pdftotext = _resolve_command("pdftotext")
    results: list[dict[str, Any]] = []
    for selection in SELECTIONS:
        manifest_path = root / "corpus" / "raw" / selection.paper_id / "source_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        pdf_path = root / manifest["pdf"]["object"]
        reader = PdfReader(pdf_path)
        page_count = len(reader.pages)
        paper_raw = manifest_path.parent
        extracted_path = paper_raw / "extracted-layout.txt"
        _run([*pdftotext, "-layout", str(pdf_path), str(extracted_path)])
        page_texts = extracted_path.read_text(encoding="utf-8", errors="replace").split("\f")
        if page_texts and not page_texts[-1].strip():
            page_texts.pop()
        render_dir = root / "corpus" / "rendered" / selection.paper_id / "pages"
        render_dir.mkdir(parents=True, exist_ok=True)
        expected = [render_dir / f"page-{page:02d}.jpg" for page in range(1, page_count + 1)]
        if not all(path.exists() for path in expected):
            prefix = render_dir / "page"
            _run([*pdftoppm, "-jpeg", "-r", "110", "-jpegopt", "quality=82", str(pdf_path), str(prefix)])
            generated = sorted(render_dir.glob("page-*.jpg"))
            for index, source in enumerate(generated, start=1):
                target = render_dir / f"page-{index:02d}.jpg"
                if source != target:
                    source.replace(target)
        images = [path for path in expected if path.exists()]
        if len(images) != page_count:
            raise RuntimeError(f"rendered page count mismatch for {selection.paper_id}: {len(images)} != {page_count}")
        contacts = _contact_sheets(images, root / "corpus" / "rendered" / selection.paper_id)
        pages = [
            {
                "page": index,
                "file": image.relative_to(root).as_posix(),
                "sha256": _sha256(image.read_bytes()),
                "bytes": image.stat().st_size,
                "text_characters": len(page_texts[index - 1].strip()) if index <= len(page_texts) else 0,
            }
            for index, image in enumerate(images, start=1)
        ]
        manifest["pdf"]["pages"] = page_count
        manifest["text"] = {
            "file": extracted_path.relative_to(root).as_posix(),
            "sha256": _sha256(extracted_path.read_bytes()),
            "extracted_pages": len(page_texts),
            "method": "pdftotext-layout",
        }
        manifest["render"] = {
            "status": "complete",
            "method": "pdftoppm-jpeg-110dpi",
            "pages": pages,
            "contact_sheets": [path.relative_to(root).as_posix() for path in contacts],
            "visual_review": "pending",
        }
        _json_write(manifest_path, manifest)
        results.append(manifest)
    return results


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip(" \t.-")


def _page_lines(text: str) -> list[str]:
    return [line for raw in text.splitlines() if len(line := _clean_line(raw)) >= 4]


def _find_candidates(page_texts: Sequence[str], pattern: re.Pattern[str], limit: int) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    seen: set[str] = set()
    for page, text in enumerate(page_texts, start=1):
        for line in _page_lines(text):
            if not pattern.search(line) or len(line) > 150:
                continue
            normalized = re.sub(r"[^\w\u4e00-\u9fff]", "", line).casefold()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            found.append((page, line))
            if len(found) >= limit:
                return found
    return found


MODEL_RE = re.compile(r"模型|算法|规划|回归|预测|聚类|评价|仿真|模拟|拟合|网络|方程|优化")
VALIDATION_RE = re.compile(r"检验|敏感性|稳健|误差|残差|比较|对比|验证|评价|优点|缺点|拟合度|置信")
FIGURE_RE = re.compile(r"(?:图|Figure|Fig\.)\s*[0-9一二三四五六七八九十]+", re.IGNORECASE)
CONCLUSION_RE = re.compile(r"结论|总结|模型评价|优缺点|推广|改进")


MANUAL_EVIDENCE: dict[str, dict[str, Any]] = {
    "cumcm-2012-b-b077": {
        "title": "太阳能小屋的设计",
        "abstract_page": 3,
        "abstract_blocks": ["设计任务与约束", "按四个问题概括辐射计算、阵列组合和外观设计", "摘要报告方案结果并比较经济性", "关键词"],
        "models": [
            (6, "建立太阳辐射在倾斜面上的几何关系并定义方位角与倾角"),
            (8, "将太阳直射、散射和地面反射辐射分量合成为倾斜面总辐射"),
            (11, "把光伏组件排布转化为矩形分割与一刀切组合问题"),
            (17, "遍历倾角并以年发电量最大为目标选择最佳倾角"),
            (20, "建立小屋屋面光伏阵列的排布与逆变器配置模型"),
        ],
        "validations": [
            (16, "用 CAD 几何面积与模型计算面积互相核对组件排布"),
            (23, "用汇总表比较三种方案的发电量、利润和回收年限"),
            (24, "模型评价明确讨论理想气象、计算精度和实际应用限制"),
        ],
        "figures": [
            (6, "mechanism", "太阳辐射几何关系示意图", "在公式推导前固定太阳、屋面和角度符号"),
            (12, "layout", "光伏电池矩形分割与排布示意", "用空间示意连接组合算法与可制造排布"),
            (17, "flowchart", "最佳倾角遍历计算流程", "把目标函数、循环搜索和输出条件显式化"),
            (22, "schematic", "小屋外观与光伏铺设设计图", "把数值排布结果转成可检查的工程方案"),
        ],
        "conclusions": [(24, "模型评价将结论限制在理想气象数据、组件参数和几何近似条件内")],
    },
    "cumcm-2012-a-a441": {
        "title": "葡萄酒的评价",
        "abstract_page": 1,
        "abstract_blocks": ["研究对象与评价任务", "按四个问题概括统计方法", "摘要给出评价一致性与影响关系结论", "关键词"],
        "models": [
            (4, "先用分布图检查两组评分数据的形态"),
            (5, "用 Q-Q 图和正态性检验决定后续检验路线"),
            (7, "采用非参数秩和检验判断两组评分是否有显著差异"),
            (10, "建立多元线性回归连接理化指标与评分"),
            (13, "用相关分析筛选理化指标与评分的关系"),
        ],
        "validations": [
            (5, "正态性图形诊断和检验共同支撑检验方法选择"),
            (12, "单列模型检验并讨论残差与样本数限制"),
            (20, "报告回归系数显著性并在下一页给出模型评价"),
            (21, "明确列出模型优缺点和解释边界"),
        ],
        "figures": [
            (4, "distribution", "评分分布直方图", "在正式检验前展示分布形态"),
            (5, "diagnostic", "Q-Q 图", "把正态性假设诊断可视化"),
        ],
        "conclusions": [(21, "模型评价说明回归解释仍受变量选择与样本条件约束")],
    },
    "cumcm-2019-b-b057": {
        "title": "同心鼓“同心协力”策略探究",
        "abstract_page": 1,
        "abstract_blocks": ["任务背景", "按问题给出一维与二维动力学模型", "摘要给出操作策略参数", "关键词"],
        "models": [
            (4, "以分阶段运动方程描述球的加速、碰撞和抛起过程"),
            (8, "用受力图、转动惯量和力矩平衡建立二维刚体模型"),
            (12, "将动力学方程数值化并分阶段求解绳力与倾角"),
            (18, "在原模型上加入误差消除策略并重新求解"),
        ],
        "validations": [
            (7, "用数量级和几何条件检查理想状态假设的合理性"),
            (15, "汇总不同情形的计算结果以比较策略"),
            (21, "模型评价明确指出刚性绳、忽略空气阻力等边界"),
        ],
        "figures": [
            (6, "line", "恒力与作用时间关系曲线", "把策略参数间的单调关系直接可视化"),
            (8, "mechanism", "鼓绳受力与几何关系示意", "在推导力矩方程前固定符号和方向"),
            (20, "line", "改进策略下的倾角时间曲线", "展示误差消除阶段的动态响应"),
            (21, "line", "球速度随时间变化曲线", "检查一个周期内的运动边界"),
        ],
        "conclusions": [(21, "模型评价将结论限制在理想化绳鼓结构与忽略阻力的条件内")],
        "watermark": True,
    },
    "cumcm-2019-e-e038": {
        "title": "基于打折力度概念的“薄利多销”模型",
        "abstract_page": 1,
        "abstract_blocks": ["零售促销背景与四问任务", "定义营业额、利润率与打折力度", "分问题概括相关检验、稳健回归和分类比较", "关键词"],
        "models": [
            (5, "用商品销售额和流水成本构造逐日营业额与利润率"),
            (7, "定义结合折扣率、限购量和购买量的打折力度指标"),
            (8, "用 Pearson 相关检验和稳健加权二次回归分析打折力度与营业额"),
            (10, "用相关检验和稳健回归分析打折力度与商品利润率"),
            (11, "按价格弹性对商品分类后比较打折力度的作用差异"),
        ],
        "validations": [
            (8, "同时报告散点分布、Pearson 检验和 Fisher Z 检验以核对相关关系"),
            (10, "对营业额与利润率分别拟合并说明相关关系的条件差异"),
            (13, "模型评价讨论缺失数据处理、指标近似和不同品类的适用边界"),
        ],
        "figures": [
            (3, "flowchart", "四个问题的模型路线图", "在正文开端展示数据处理、指标定义和分组分析的依赖关系"),
            (4, "distribution", "订单有效性与流水成本缺失占比", "先量化数据质量问题再进入建模"),
            (8, "scatter", "打折力度与营业额散点及检验结果", "将点云、相关系数与显著性证据同页呈现"),
            (10, "fit-curve", "打折力度与利润率的稳健回归曲线", "用拟合线说明方向并在正文限定适用区间"),
            (11, "bar", "商品类别销售结构", "用排序类别图支撑后续分组建模"),
        ],
        "conclusions": [(13, "模型评价说明促销结论受缺失数据、指标定义和商品类别差异约束")],
        "watermark": True,
    },
    "cumcm-2020-a-a212": {
        "title": "回焊炉温曲线优化控制",
        "abstract_page": 1,
        "abstract_blocks": ["工业背景与四问任务", "热传导与拟合方法", "单目标和多目标优化结果", "关键词"],
        "models": [
            (5, "由热传导微分方程建立炉温与焊接区域温度关系"),
            (7, "求解分段温区的温度分布并形成递推计算"),
            (8, "用最小二乘拟合未知换热参数"),
            (10, "把峰值、斜率与高温持续时间写成约束优化模型"),
            (13, "采用模拟退火搜索满足约束的传送速度"),
            (14, "建立兼顾峰值温度与高温面积的多目标优化模型"),
        ],
        "validations": [
            (9, "用拟合曲线与附件实测数据对比检查温度模型"),
            (11, "计算峰值、升降温斜率和高温区间检查工艺约束"),
            (16, "把多目标优化曲线与前一问方案放在同图比较"),
            (17, "模型评价列出分区近似、PCB 厚度和环境因素等限制"),
        ],
        "figures": [
            (5, "flowchart", "传热模型求解流程", "用流程图连接参数拟合、温区递推和结果输出"),
            (9, "fit-curve", "拟合与附件数据对比曲线", "显示模型对真实温度数据的贴合程度"),
            (11, "line", "炉温曲线与关键时间区间", "把峰值和斜率约束放到同一温度轨迹上"),
            (13, "flowchart", "模拟退火求解流程", "解释随机搜索和接受准则的执行顺序"),
            (16, "comparison", "多目标优化前后温度曲线", "在同一坐标系比较方案差异"),
        ],
        "conclusions": [(17, "推广部分指出模型需针对不同炉型和 PCB 参数重新校准")],
        "watermark": True,
    },
    "cumcm-2020-d-d011": {
        "title": "基于接触式轮廓仪测量数据的工件形状自动标注方法",
        "abstract_page": 1,
        "abstract_blocks": ["轮廓测量背景与四问任务", "按问题概括差分识别、滤波拟合、坐标校正和全局修复", "摘要说明自动标注方案的输出", "关键词"],
        "models": [
            (5, "用一阶与二阶差分识别直线段和圆弧段的候选边界"),
            (6, "在滑动窗口中滤除高频扰动并拟合直线与圆弧参数"),
            (10, "通过直线拟合估计倾斜角并以旋转矩阵校正水平位置"),
            (12, "将多次测量先旋转到统一坐标系再按几何对应关系拼接"),
            (15, "采用局部数据修复与全局圆弧拟合完成缺损轮廓标注"),
        ],
        "validations": [
            (8, "把滤波后的数据、拟合直线和圆弧参数放在同页检查分段效果"),
            (11, "以校正后各水平线的均方偏差比较坐标修正准确性"),
            (16, "汇总多个圆弧参数并用修复前后曲线比较几何一致性"),
            (17, "模型评价列出分段模型、旋转校正和参数阈值的优点与限制"),
        ],
        "figures": [
            (5, "diagnostic", "一阶与二阶差分数据图", "用导数阶次的互补响应定位轮廓突变"),
            (8, "fit-curve", "直线段与圆弧段拟合结果", "把原始点、拟合曲线和几何参数组合为验证图"),
            (14, "comparison", "坐标旋转校正前后曲线", "用并列小图检查多次测量能否对齐"),
            (16, "error-plot", "多组圆弧拟合误差曲线", "以一致坐标和参数表比较修复稳定性"),
        ],
        "conclusions": [(17, "模型评价将自动标注结论限制在分段直线/圆弧假设和阈值参数条件内")],
        "watermark": True,
    },
}


def _chart_type(caption: str) -> str:
    tests = (
        ("流程", "flowchart"), ("散点", "scatter"), ("热力", "heatmap"), ("网络", "network"),
        ("分布", "distribution"), ("拟合", "fit-curve"), ("预测", "forecast"), ("误差", "error-plot"),
        ("敏感", "sensitivity"), ("轨迹", "trajectory"), ("柱状", "bar"), ("曲线", "line"),
    )
    return next((kind for token, kind in tests if token in caption), "result-figure")


def _abstract_blocks(text: str) -> tuple[list[str], str]:
    lines = _page_lines(text)
    joined = "".join(lines)
    blocks: list[str] = ["问题背景和任务概括"]
    if re.search(r"问题[一二三四1234]|首先|其次|然后|最后", joined):
        blocks.append("按子问题顺序陈述方法与结果")
    if re.search(r"\d+(?:\.\d+)?%|误差|准确|提升|结果", joined):
        blocks.append("摘要包含量化结果或结果判断")
    if "关键词" in joined:
        blocks.append("末尾列出关键词")
    density = f"摘要页可提取文本约 {len(text.strip())} 字符；观察项仅概括可见结构，不复用论文具体结论。"
    return blocks, density


def _title_from_page(text: str, fallback: str) -> str:
    lines = _page_lines(text)
    for line in lines[:12]:
        cleaned = line.replace("�", "").strip()
        if not (4 <= len(cleaned) <= 60):
            continue
        if any(token in cleaned for token in ("摘要", "关键词", "承诺书", "编号", "评阅")):
            continue
        if re.search(r"[\u4e00-\u9fff]", cleaned):
            return cleaned
    return fallback


def _assert_cumcm_identity(page_texts: Sequence[str], selection: Selection) -> None:
    cover_text = "".join(page_texts[:3]).replace(" ", "")
    rejected = ("中国研究生数学建模竞赛", "全国研究生数学建模竞赛", "研究生数学建模竞赛", "研究生创新实践")
    if any(token in cover_text for token in rejected):
        raise ValueError(f"graduate-contest paper cannot enter CUMCM set: {selection.paper_id}")


def _first_page_dhash(path: Path) -> str:
    with Image.open(path) as image:
        gray = image.convert("L").resize((9, 8))
        values = list(gray.getdata())
    bits = 0
    for row in range(8):
        for column in range(8):
            bits = (bits << 1) | int(values[row * 9 + column] > values[row * 9 + column + 1])
    return f"{bits:016x}"


def build_card(root: Path, selection: Selection, *, visual_reviewed: bool) -> dict[str, Any]:
    raw_dir = root / "corpus" / "raw" / selection.paper_id
    manifest = json.loads((raw_dir / "source_manifest.json").read_text(encoding="utf-8"))
    text_path = root / manifest["text"]["file"]
    page_texts = text_path.read_text(encoding="utf-8", errors="replace").split("\f")
    if page_texts and not page_texts[-1].strip():
        page_texts.pop()
    _assert_cumcm_identity(page_texts, selection)
    manual = MANUAL_EVIDENCE.get(selection.paper_id, {})
    abstract_page = int(manual.get("abstract_page") or next((index for index, text in enumerate(page_texts, start=1) if "摘要" in text[:2500]), 1))
    abstract_text = page_texts[abstract_page - 1] if page_texts else ""
    blocks, _ = _abstract_blocks(abstract_text)
    if manual.get("abstract_blocks"):
        blocks = list(manual["abstract_blocks"])
    model_candidates = list(manual.get("models") or _find_candidates(page_texts, MODEL_RE, 6))
    validation_candidates = list(manual.get("validations") or _find_candidates(page_texts, VALIDATION_RE, 5))
    figure_candidates = _find_candidates(page_texts, FIGURE_RE, 8)
    conclusion_candidates = list(manual.get("conclusions") or _find_candidates(page_texts, CONCLUSION_RE, 3))

    evidence_pages: list[dict[str, Any]] = [{
        "page": abstract_page,
        "tags": ["abstract", "layout"],
        "observation": f"摘要页呈现“{'；'.join(blocks)}”的组织结构。",
        "derivation": "mixed" if visual_reviewed else "text",
        "locator": f"PDF p.{abstract_page}",
        "render": manifest["render"]["pages"][abstract_page - 1]["file"],
    }]
    for page, line in model_candidates[:4]:
        evidence_pages.append({"page": page, "tags": ["model_chain"], "observation": f"页面明确呈现模型步骤：{line[:110]}", "derivation": "mixed" if visual_reviewed else "text", "locator": f"PDF p.{page}", "render": manifest["render"]["pages"][page - 1]["file"]})
    for page, line in validation_candidates[:3]:
        evidence_pages.append({"page": page, "tags": ["validation"], "observation": f"页面明确呈现验证或评价步骤：{line[:110]}", "derivation": "mixed" if visual_reviewed else "text", "locator": f"PDF p.{page}", "render": manifest["render"]["pages"][page - 1]["file"]})
    for page, line in conclusion_candidates[:2]:
        evidence_pages.append({"page": page, "tags": ["conclusion_boundary"], "observation": f"结尾部分呈现结论边界：{line[:100]}", "derivation": "mixed" if visual_reviewed else "text", "locator": f"PDF p.{page}", "render": manifest["render"]["pages"][page - 1]["file"]})

    if manual.get("figures"):
        figures = [{"page": page, "role": role, "chart_type": kind, "caption": caption, "lesson": lesson, "locator": f"PDF p.{page}", "render": manifest["render"]["pages"][page - 1]["file"], "visual_checked": visual_reviewed} for page, kind, caption, lesson in manual["figures"] for role in ("model explanation" if kind in {"flowchart", "mechanism"} else "result evidence",)]
    else:
        figures = [
            {
                "page": page,
                "role": "model explanation" if "流程" in line or "模型" in line else "result evidence",
                "chart_type": _chart_type(line),
                "caption": line[:100],
                "lesson": f"图题“{line[:90]}”把图件与对应论证定位在同一证据页；迁移时应保留变量、单位和图注。",
                "locator": f"PDF p.{page}",
                "render": manifest["render"]["pages"][page - 1]["file"],
                "visual_checked": visual_reviewed,
            }
            for page, line in figure_candidates[:6]
        ]
    risks = [
        "上游目录声称为优秀论文，但尚无独立官方结果页或队号匹配证据；真实性保持 C。",
        "未执行论文关联代码，不能据正文反推具体实现或复现性。",
    ]
    if not visual_reviewed:
        risks.append("全页已渲染，但接触表尚未完成逐页人工视觉确认。")
    if not validation_candidates:
        risks.append("文本提取中未定位到明确的验证、稳健性或误差关键词，验证链可能较弱或需人工复核。")
    if not figures:
        risks.append("文本层未识别出可靠图题；不能据此推断论文没有图件。")
    if manual.get("watermark"):
        risks.append("渲染页带有第三方镜像水印；视觉布局可学习，但该副本不是官方展示原件。")

    first_page = root / manifest["render"]["pages"][0]["file"]
    title = str(manual.get("title") or _title_from_page(abstract_text, f"CUMCM {selection.year} {selection.problem} 题镜像论文（标题待核）"))
    source = {
        "url": selection.source_url,
        "publisher": "mirror",
        "accessible": True,
        "fulltext": True,
        "access": "public",
        "repository": selection.repository,
        "commit": selection.commit,
        "path": selection.path,
    }
    award_evidence = {
        "verified": False,
        "official_url": "",
        "contest": "CUMCM",
        "year": selection.year,
        "problem": selection.problem,
        "team_id": "",
        "title": title,
        "award": "上游社区目录标注为优秀论文（未独立核验）",
    }

    record = {
        "schema_version": "3.0",
        "paper_id": selection.paper_id,
        "identity": {"contest": "CUMCM", "year": selection.year, "problem": selection.problem, "team_id": "", "title": title},
        "source": source,
        "award_evidence": award_evidence,
        "pdf": {
            "sha256": manifest["pdf"]["sha256"],
            "pages": manifest["pdf"]["pages"],
            "local_path": manifest["pdf"]["object"],
            "first_page_phash": _first_page_dhash(first_page),
            "text_sha256": manifest["text"]["sha256"],
        },
        "review_status": "evidence_deep_read",
        "page_evidence": evidence_pages,
        "abstract_structure": [{"page": abstract_page, "order": index + 1, "role": block, "locator": f"PDF p.{abstract_page}"} for index, block in enumerate(blocks)],
        "model_chain": [{"step": index + 1, "page": page, "description": line[:130], "locator": f"PDF p.{page}"} for index, (page, line) in enumerate(model_candidates)],
        "validation_chain": [{"step": index + 1, "page": page, "description": line[:130], "locator": f"PDF p.{page}"} for index, (page, line) in enumerate(validation_candidates)],
        "figures": figures,
        "code_links": [],
        "transferable_rules": [
            {"rule": "摘要按真实子问题顺序把方法与结果配对", "evidence_page": abstract_page},
            {"rule": "模型链按问题、假设、模型、求解、结果组织，而不是堆叠算法名称", "evidence_page": model_candidates[0][0] if model_candidates else abstract_page},
            {"rule": "结果图应在同页正文说明论证作用，并补齐变量、单位、基线与不确定性", "evidence_page": figures[0]["page"] if figures else abstract_page},
            {"rule": "结论只复述已验证主张，并单列适用边界、缺点和改进方向", "evidence_page": conclusion_candidates[0][0] if conclusion_candidates else abstract_page},
        ],
        "risks": risks,
        "provenance": {
            "repository": selection.repository,
            "commit": selection.commit,
            "git_blob_sha": selection.blob_sha,
            "bytes": selection.expected_bytes,
            "accessed": manifest["source"]["accessed"],
            "extraction": manifest["text"],
            "render": {"method": manifest["render"]["method"], "pages": manifest["pdf"]["pages"], "contact_sheets": manifest["render"]["contact_sheets"], "visual_review": "complete" if visual_reviewed else "pending"},
            "authenticity_policy": "filename and directory claims are excluded from A/B evidence",
        },
    }
    return build_paper_card(record)


def _validate_card(card: Mapping[str, Any]) -> list[str]:
    errors = validate_paper_card(card)
    for field in ("page_evidence", "abstract_structure", "model_chain", "validation_chain", "figures", "transferable_rules"):
        if not card.get(field):
            errors.append(f"{field} is empty")
    return errors


def build_cards(root: Path, *, visual_reviewed: bool) -> dict[str, Any]:
    card_root = root / "corpus" / "cards" / "deep-read-cumcm"
    cards: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for selection in SELECTIONS:
        try:
            card = build_card(root, selection, visual_reviewed=visual_reviewed)
            errors = _validate_card(card)
            if errors:
                raise ValueError("; ".join(errors))
            path = card_root / f"{selection.paper_id}.json"
            _json_write(path, card)
            cards.append(card)
            deep_errors = validate_paper_card(card, require_deep_read=True)
            records.append({"paper_id": selection.paper_id, "status": card["review_status"], "visual_review": card["provenance"]["render"]["visual_review"], "authenticity": card["authenticity"]["level"], "card": path.relative_to(root).as_posix(), "schema_valid": True, "require_deep_read_valid": not deep_errors, "require_deep_read_errors": deep_errors, "errors": []})
        except (OSError, RuntimeError, ValueError, KeyError, IndexError) as exc:
            records.append({"paper_id": selection.paper_id, "status": "blocked", "authenticity": "C", "errors": [str(exc)]})
    content_reviewed = sum(record.get("visual_review") == "complete" for record in records)
    schema_valid = sum(record.get("schema_valid") is True for record in records)
    deep_read = sum(record.get("require_deep_read_valid") is True for record in records)
    manifest = {
        "schema_version": 1,
        "program": "CUMCM historical mirror set: two papers per year from 2012 through 2020",
        "target": 18,
        "selected": len(SELECTIONS),
        "schema_valid_count": schema_valid,
        "content_reviewed_count": content_reviewed,
        "evidence_deep_read_count": deep_read,
        "content_evidence_deep_read_count": deep_read,
        "award_verified_deep_read_count": 0,
        "evidence_deep_read_rule": "Content depth and award authenticity are separate: these full-text cards can pass content evidence while remaining authenticity C.",
        "source_counts": dict(sorted({source: sum(item.source_id == source for item in SELECTIONS) for source in {item.source_id for item in SELECTIONS}}.items())),
        "year_counts": {str(year): sum(item.year == year for item in SELECTIONS) for year in range(2012, 2021)},
        "records": records,
        "blockers": [
            "No independent official award/result locator has yet been matched to these 18 mirror files.",
            "Repository path names that contain 优秀论文 are discovery metadata only and cannot upgrade authenticity.",
        ],
    }
    _json_write(root / "corpus" / "manifests" / "cumcm-deep-read.json", manifest)
    return manifest


def mark_visual_review(root: Path) -> None:
    for selection in SELECTIONS:
        manifest_path = root / "corpus" / "raw" / selection.paper_id / "source_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["render"]["visual_review"] = "complete"
        _json_write(manifest_path, manifest)


def _tree_paths(root: Path) -> dict[str, Path]:
    upstream = root / "corpus" / "upstream" / "sources"
    return {
        "zhanwen-mathmodel": upstream / "zhanwen-mathmodel" / ZHANWEN_COMMIT / "git_tree.json",
        "personqianduixue-math-model": upstream / "personqianduixue-math-model" / PERSON_COMMIT / "git_tree.json",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Curate and inspect the 18-paper historical CUMCM deep-reading set.")
    parser.add_argument("action", choices=("download", "render", "build-cards", "mark-visual-reviewed", "all"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--visual-reviewed", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        validate_selections(_tree_paths(root))
        if args.action in {"download", "all"}:
            cache_pdfs(root)
        if args.action in {"render", "all"}:
            render_and_extract(root)
        if args.action == "mark-visual-reviewed":
            mark_visual_review(root)
            result = build_cards(root, visual_reviewed=True)
        elif args.action in {"build-cards", "all"}:
            result = build_cards(root, visual_reviewed=args.visual_reviewed)
        else:
            result = {"status": "PASS", "action": args.action, "papers": len(SELECTIONS)}
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
