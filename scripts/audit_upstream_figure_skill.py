#!/usr/bin/env python3
"""Create a pinned, read-only inventory and static-risk report for an upstream figure skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPOSITORY = "https://github.com/TingxiYu/academic-figure-skill"
PINNED_COMMIT = "1df9940dd01ac939f072b12fe28d6353b79b90f9"
SOURCE_EXTENSIONS = {".py", ".r", ".R", ".m", ".ps1", ".sh"}
RISK_PATTERNS: dict[str, tuple[str, ...]] = {
    "network": (r"requests\.", r"httpx\.", r"urllib", r"socket\.", r"curl\b", r"wget\b"),
    "process": (r"subprocess", r"os\.system", r"Popen\s*\(", r"Start-Process", r"Rscript\b"),
    "destructive_io": (r"shutil\.rmtree", r"\.unlink\s*\(", r"Remove-Item", r"rm\s+-rf"),
    "dynamic_execution": (r"\beval\s*\(", r"\bexec\s*\(", r"source\s*\("),
    "gui": (r"plt\.show\s*\(", r"tkinter", r"\bggsave\s*\(", r"\.show\s*\(\s*\)"),
    "absolute_path": (r"[A-Za-z]:[\\/]", r"/home/", r"/Users/"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(source: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(source), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def inventory(source: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(p for p in source.rglob("*") if p.is_file() and ".git" not in p.parts):
        relative = path.relative_to(source).as_posix()
        blob = None
        try:
            blob = git(source, "hash-object", "--", relative)
        except subprocess.CalledProcessError:
            pass
        rows.append({
            "path": relative,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "git_blob_sha": blob,
        })
    return rows


def static_risks(source: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in sorted(p for p in source.rglob("*") if p.is_file() and p.suffix in SOURCE_EXTENSIONS and ".git" not in p.parts):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for category, patterns in RISK_PATTERNS.items():
            matches = [
                {"pattern": pattern, "count": len(re.findall(pattern, text, flags=re.IGNORECASE | re.MULTILINE))}
                for pattern in patterns
                if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
            ]
            if matches:
                findings.append({
                    "path": path.relative_to(source).as_posix(),
                    "category": category,
                    "matches": matches,
                    "execution_policy": "blocked_until_manual_review",
                })
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/academic_figure_skill_source_manifest.json"))
    parser.add_argument("--report", type=Path, default=Path("reports/academic_figure_skill_review.md"))
    args = parser.parse_args()
    source = args.source.resolve()
    if not (source / ".git").is_dir():
        raise SystemExit(f"Not a Git repository: {source}")
    commit = git(source, "rev-parse", "HEAD")
    if commit != PINNED_COMMIT:
        raise SystemExit(f"Pinned commit mismatch: expected {PINNED_COMMIT}, got {commit}")
    files = inventory(source)
    risks = static_risks(source)
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload = {
        "schema_version": 1,
        "repository": REPOSITORY,
        "commit": PINNED_COMMIT,
        "license": "Apache-2.0",
        "source_root": str(source),
        "generated_at": generated,
        "file_count": len(files),
        "files": files,
        "static_risk_count": len(risks),
        "static_risks": risks,
        "execution_policy": "reference_only; do not execute upstream scripts as contest evidence",
        "adopted": [
            "figure brief and one-core-conclusion rule",
            "physical-size-first composition",
            "vector-first export and editable text",
            "statistical and data-integrity reporting",
            "four-round visual QA",
        ],
        "rejected": [
            "Nature/CNS palette defaults",
            "five-point minimum type",
            "300 dpi default",
            "R as a required runtime",
            "unreviewed copy-first scripts and simulated data",
        ],
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = [
        "# academic-figure-skill 来源审查",
        "",
        f"- 来源：{REPOSITORY}",
        f"- 固定提交：`{PINNED_COMMIT}`",
        "- 许可证：Apache-2.0",
        f"- 文件数：{len(files)}",
        f"- 静态风险项：{len(risks)}（全部默认禁止直接执行）",
        "",
        "## 吸收内容",
        "",
        "问题驱动的 Figure Brief、最终物理尺寸优先、矢量优先导出、统计与数据完整性说明、反模式/代码/视觉/渲染四轮 QA。",
        "",
        "## 本地改写",
        "",
        "赛事图件使用 `journal-spectrum-v2`、CUMCM 正文尺寸、8 pt 最小字号、PDF/SVG/400 dpi PNG；Python 为默认数据后端，MATLAB 按任务选用。",
        "",
        "## 风险处理",
        "",
        "上游代码只做静态索引。包含网络、进程、删除、动态执行、GUI 或绝对路径的脚本必须人工审查后才能提取构图规则，不能直接作为竞赛证据。",
        "",
        f"机器清单：`{output.as_posix()}`",
    ]
    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"passed": True, "commit": commit, "file_count": len(files), "risk_count": len(risks), "manifest": str(output), "report": str(report_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
