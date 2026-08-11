from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "corpus" / "raw"


@dataclass(frozen=True)
class Paper:
    paper_id: str
    year: int
    problem: str
    title: str
    source_url: str


PAPERS = (
    Paper(
        paper_id="cumcm-2024-a163",
        year=2024,
        problem="A",
        title="基于几何模型的板凳龙运动路径问题",
        source_url=(
            "https://dxs.moe.gov.cn/zx/a/"
            "hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024atlw/241104/1977935.shtml"
        ),
    ),
    Paper(
        paper_id="cumcm-2024-b159",
        year=2024,
        problem="B",
        title="生产过程中的决策优化设计",
        source_url=(
            "https://dxs.moe.gov.cn/zx/a/"
            "hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024btlw/241104/1977943.shtml"
        ),
    ),
    Paper(
        paper_id="cumcm-2024-c038",
        year=2024,
        problem="C",
        title="基于差分遗传算法的农作物种植策略优化",
        source_url=(
            "https://dxs.moe.gov.cn/zx/a/"
            "hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024ctlw/241104/1977952.shtml"
        ),
    ),
    Paper(
        paper_id="cumcm-2024-e010",
        year=2024,
        problem="E",
        title="交通流量管控",
        source_url=(
            "https://dxs.moe.gov.cn/zx/a/"
            "hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024etlw/241104/1977967.shtml"
        ),
    ),
    Paper(
        paper_id="cumcm-2025-a196",
        year=2025,
        problem="A",
        title="多情形下无人机烟幕遮蔽策略的建模与优化研究",
        source_url=(
            "https://dxs.moe.gov.cn/zx/a/"
            "hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025atlw/251101/2022729.shtml"
        ),
    ),
    Paper(
        paper_id="cumcm-2025-c132",
        year=2025,
        problem="C",
        title="基于统计建模与元学习的NIPT检测决策优化与异常识别",
        source_url=(
            "https://dxs.moe.gov.cn/zx/a/"
            "hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025ctlw/251101/2022740.shtml"
        ),
    ),
    Paper(
        paper_id="cumcm-2024-a242",
        year=2024,
        problem="A",
        title="2024高教社杯全国大学生数学建模竞赛A题论文展示（A242）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024atlw/241104/1977939.shtml",
    ),
    Paper(
        paper_id="cumcm-2024-a178",
        year=2024,
        problem="A",
        title="2024高教社杯全国大学生数学建模竞赛A题论文展示（A178）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024atlw/241104/1977937.shtml",
    ),
    Paper(
        paper_id="cumcm-2024-a016",
        year=2024,
        problem="A",
        title="2024高教社杯全国大学生数学建模竞赛A题论文展示（A016）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024atlw/241104/1977931.shtml",
    ),
    Paper(
        paper_id="cumcm-2024-a053",
        year=2024,
        problem="A",
        title="2024高教社杯全国大学生数学建模竞赛A题论文展示（A053）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024atlw/241104/1977933.shtml",
    ),
    Paper(
        paper_id="cumcm-2024-b195",
        year=2024,
        problem="B",
        title="2024高教社杯全国大学生数学建模竞赛B题论文展示（B195）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024btlw/241104/1977945.shtml",
    ),
    Paper(
        paper_id="cumcm-2024-b196",
        year=2024,
        problem="B",
        title="2024高教社杯全国大学生数学建模竞赛B题论文展示（B196）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024btlw/241104/1977950.shtml",
    ),
    Paper(
        paper_id="cumcm-2024-c234",
        year=2024,
        problem="C",
        title="2024高教社杯全国大学生数学建模竞赛C题论文展示（C234）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024ctlw/241104/1977963.shtml",
    ),
    Paper(
        paper_id="cumcm-2024-c063",
        year=2024,
        problem="C",
        title="2024高教社杯全国大学生数学建模竞赛C题论文展示（C063）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024ctlw/241104/1977958.shtml",
    ),
    Paper(
        paper_id="cumcm-2024-c094",
        year=2024,
        problem="C",
        title="2024高教社杯全国大学生数学建模竞赛C题论文展示（C094）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024ctlw/241104/1977961.shtml",
    ),
    Paper(
        paper_id="cumcm-2024-d033",
        year=2024,
        problem="D",
        title="2024高教社杯全国大学生数学建模竞赛D题论文展示（D033）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024dtlw/241104/1977965.shtml",
    ),
    Paper(
        paper_id="cumcm-2024-e218",
        year=2024,
        problem="E",
        title="2024高教社杯全国大学生数学建模竞赛E题论文展示（E218）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024etlw/241104/1977971.shtml",
    ),
    Paper(
        paper_id="cumcm-2024-e061",
        year=2024,
        problem="E",
        title="2024高教社杯全国大学生数学建模竞赛E题论文展示（E061）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024etlw/241104/1977969.shtml",
    ),
    Paper(
        paper_id="cumcm-2025-b060",
        year=2025,
        problem="B",
        title="2025高教社杯全国大学生数学建模竞赛B题论文展示（B060）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025btlw/251101/2022733.shtml",
    ),
    Paper(
        paper_id="cumcm-2025-b157",
        year=2025,
        problem="B",
        title="2025高教社杯全国大学生数学建模竞赛B题论文展示（B157）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025btlw/251107/2023197.shtml",
    ),
    Paper(
        paper_id="cumcm-2025-c023",
        year=2025,
        problem="C",
        title="2025高教社杯全国大学生数学建模竞赛C题论文展示（C023）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025ctlw/251101/2022736.shtml",
    ),
    Paper(
        paper_id="cumcm-2025-d037",
        year=2025,
        problem="D",
        title="2025高教社杯全国大学生数学建模竞赛D题论文展示（D037）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025dtlw/251101/2022742.shtml",
    ),
    Paper(
        paper_id="cumcm-2025-e030",
        year=2025,
        problem="E",
        title="2025高教社杯全国大学生数学建模竞赛E题论文展示（E030）",
        source_url="https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025etlw/251101/2022744.shtml",
    ),
)


class PaperImageParser(HTMLParser):
    def __init__(self, display_id: str) -> None:
        super().__init__()
        self.display_id = display_id.upper()
        self.images: list[tuple[int, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        attributes = dict(attrs)
        alt = attributes.get("alt") or ""
        src = attributes.get("src") or ""
        prefix = f"{self.display_id}_页面_"
        if not alt.startswith(prefix) or not src.startswith("https://"):
            return
        page_text = alt.removeprefix(prefix).removesuffix(".jpg")
        if page_text.isdigit():
            self.images.append((int(page_text), alt, src))


def fetch(url: str, attempts: int = 4) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "MathModelingCorpus/1.0 (+academic layout study)"},
    )
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read()
        except (TimeoutError, urllib.error.URLError) as exc:
            if attempt == attempts:
                raise RuntimeError(f"Unable to fetch {url}: {exc}") from exc
            time.sleep(attempt * 1.5)
    raise AssertionError("unreachable")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def collect(paper: Paper, max_pages: int, delay: float = 0.15, refresh: bool = False) -> dict[str, object]:
    display_id = paper.paper_id.rsplit("-", maxsplit=1)[-1]
    html = fetch(paper.source_url).decode("utf-8", errors="replace")
    parser = PaperImageParser(display_id)
    parser.feed(html)
    images = sorted(set(parser.images), key=lambda item: item[0])
    if not images:
        raise RuntimeError(f"No paper images found at {paper.source_url}")

    paper_dir = RAW_ROOT / paper.paper_id
    paper_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for page_number, alt, url in images[:max_pages]:
        target = paper_dir / f"page-{page_number:02d}.jpg"
        data = target.read_bytes() if target.exists() and not refresh else fetch(url)
        if target.exists() and not refresh:
            expected = next((item for item in json.loads((paper_dir / "source_manifest.json").read_text(encoding="utf-8")).get("pages", []) if item.get("page") == page_number), None) if (paper_dir / "source_manifest.json").is_file() else None
            if expected and hashlib.sha256(data).hexdigest() != expected.get("sha256"):
                data = fetch(url)
        if data[:2] != b"\xff\xd8":
            raise RuntimeError(f"Downloaded asset is not JPEG: {url}")
        temp = target.with_suffix(".jpg.tmp")
        temp.write_bytes(data)
        os.replace(temp, target)
        records.append(
            {
                "page": page_number,
                "alt": alt,
                "url": url,
                "file": target.name,
                "bytes": len(data),
                "sha256": sha256(data),
            }
        )
        print(f"{paper.paper_id}: {page_number:02d}/{min(max_pages, len(images)):02d}")
        if delay:
            time.sleep(delay)

    manifest: dict[str, object] = {
        "schema_version": 2,
        "competition": "CUMCM",
        "year": paper.year,
        "problem": paper.problem,
        "display_id": display_id.upper(),
        "title": paper.title,
        "award_or_label": "全国大学生数学建模竞赛组委会官方论文展示",
        "access": "public_page_images",
        "source_url": paper.source_url,
        "source_notice": "仅用于学习版式与绘图；遵守官方页面的转载声明。",
        "reported_total_pages": len(images),
        "cached_pages": len(records),
        "coverage": round(len(records) / len(images), 4),
        "collection_status": "complete" if len(records) == len(images) else "partial",
        "pages": records,
    }
    temp_manifest = paper_dir / "source_manifest.json.tmp"
    temp_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp_manifest, paper_dir / "source_manifest.json")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cache official CUMCM paper page images.")
    parser.add_argument("--max-pages", type=int, default=10000)
    parser.add_argument("--delay", type=float, default=0.15)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument(
        "--paper",
        action="append",
        choices=[paper.paper_id for paper in PAPERS],
        help="Collect only selected paper IDs; may be repeated.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.max_pages < 1:
        raise SystemExit("--max-pages must be positive")
    selected = [paper for paper in PAPERS if not args.paper or paper.paper_id in args.paper]
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    manifests = [collect(paper, args.max_pages, delay=args.delay, refresh=args.refresh) for paper in selected]
    print(json.dumps({"papers": len(manifests), "max_pages": args.max_pages}))


if __name__ == "__main__":
    main()
