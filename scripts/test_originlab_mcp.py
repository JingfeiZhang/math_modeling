from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


REQUIRED_TOOLS = {
    "get_origin_info",
    "import_csv",
    "list_worksheets",
    "get_worksheet_info",
    "set_column_designations",
    "set_column_labels",
    "create_plot",
    "list_graphs",
    "apply_publication_style",
    "set_plot_color",
    "set_plot_line_style",
    "set_legend",
    "export_graph",
    "save_project",
    "open_project",
    "get_graph_info",
    "release_origin",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_size(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()[:24]
    if len(data) != 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", data[16:24])


def png_dpi(path: Path) -> tuple[float, float] | None:
    with path.open("rb") as handle:
        if handle.read(8) != b"\x89PNG\r\n\x1a\n":
            return None
        while True:
            length_bytes = handle.read(4)
            if len(length_bytes) != 4:
                return None
            length = struct.unpack(">I", length_bytes)[0]
            chunk_type = handle.read(4)
            chunk_data = handle.read(length)
            handle.read(4)
            if chunk_type == b"pHYs" and len(chunk_data) == 9:
                x_ppm, y_ppm, unit = struct.unpack(">IIB", chunk_data)
                if unit == 1:
                    return x_ppm * 0.0254, y_ppm * 0.0254
            if chunk_type == b"IEND":
                return None


def content_payload(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured
    for item in getattr(result, "content", []):
        text = getattr(item, "text", None)
        if not isinstance(text, str):
            continue
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return {}


async def run(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).resolve()
    output_root = workspace / "output" / "_demos" / "originlab" / "originlab-mcp-smoke"
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = output_root / "report.json"
    python = workspace / ".tools" / "originlab-mcp-venv" / "Scripts" / "python.exe"
    source_root = workspace / "tools" / "originlab-mcp"

    report: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(),
        "mode": "protocol-only" if args.protocol_only else "live",
        "source_commit": "929f538c466b9fe86a83324e002f8f45cf734ee9",
        "python": str(python),
        "status": "FAIL",
        "steps": [],
        "artifacts": {},
        "warnings": [],
    }

    server_env = os.environ.copy()
    server_env.update(
        {
            "PYTHONNOUSERSITE": "1",
            "ORIGINLAB_MCP_ATTACH_EXISTING": "0",
            "ORIGINLAB_MCP_ENABLE_ADVANCED": "0",
        }
    )
    server = StdioServerParameters(
        command=str(python),
        args=["-m", "originlab_mcp.server"],
        env=server_env,
        cwd=source_root,
        encoding="utf-8",
        encoding_error_handler="replace",
    )

    async def call(session: ClientSession, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await session.call_tool(
            name,
            arguments,
            read_timeout_seconds=timedelta(seconds=90),
        )
        payload = content_payload(result)
        step = {
            "tool": name,
            "is_error": bool(getattr(result, "isError", False)),
            "payload": payload,
        }
        report["steps"].append(step)
        if step["is_error"] or payload.get("success") is False:
            raise RuntimeError(f"{name} failed: {payload}")
        return payload

    try:
        async with stdio_client(server, errlog=sys.stderr) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                listed = await session.list_tools()
                tools = {tool.name: tool for tool in listed.tools}
                missing = sorted(REQUIRED_TOOLS - tools.keys())
                advanced_present = "execute_labtalk" in tools
                report["tool_count"] = len(tools)
                report["missing_required_tools"] = missing
                report["advanced_labtalk_present"] = advanced_present
                report["steps"].append(
                    {
                        "tool": "list_tools",
                        "is_error": bool(missing or advanced_present),
                        "payload": {
                            "tool_count": len(tools),
                            "missing": missing,
                            "advanced_labtalk_present": advanced_present,
                        },
                    }
                )
                if missing:
                    raise RuntimeError(f"Missing required MCP tools: {missing}")
                if advanced_present:
                    raise RuntimeError("Unsafe execute_labtalk tool is enabled")

                if args.protocol_only:
                    report["status"] = "PASS"
                    return_code = 0
                else:
                    await call(session, "get_origin_info", {})

                    csv_path = output_root / "smoke_data.csv"
                    csv_path.write_text(
                        "x,Main model,Baseline\n"
                        "0,0.20,0.18\n"
                        "1,0.42,0.31\n"
                        "2,0.68,0.49\n"
                        "3,0.86,0.66\n"
                        "4,0.94,0.77\n"
                        "5,0.97,0.83\n",
                        encoding="utf-8",
                    )
                    imported = await call(session, "import_csv", {"file_path": str(csv_path)})
                    sheet_name = imported.get("data", {}).get("sheet_name")
                    if not sheet_name:
                        raise RuntimeError("CSV import did not return a worksheet name")
                    sheets = await call(session, "list_worksheets", {})
                    sheet_rows = sheets.get("data", {}).get("worksheets", [])
                    if not sheet_rows:
                        report["warnings"].append(
                            {
                                "code": "WORKSHEET_ENUMERATION_INCONSISTENT",
                                "message": "import_csv succeeded but list_worksheets returned zero rows on OriginPro 2025b",
                            }
                        )

                    await call(
                        session,
                        "set_column_designations",
                        {"sheet_name": sheet_name, "designations": "XYY"},
                    )
                    for col, label, units in (
                        (0, "Decision variable x", "a.u."),
                        (1, "Main model", "a.u."),
                        (2, "Baseline", "a.u."),
                    ):
                        await call(
                            session,
                            "set_column_labels",
                            {
                                "sheet_name": sheet_name,
                                "col": col,
                                "lname": label,
                                "units": units,
                            },
                        )
                    await call(session, "get_worksheet_info", {"sheet_name": sheet_name})

                    created = await call(
                        session,
                        "create_plot",
                        {
                            "x_col": 0,
                            "y_cols": [1, 2],
                            "sheet_name": sheet_name,
                            "plot_type": "line_symbol",
                        },
                    )
                    graph_name = created.get("data", {}).get("graph_name")
                    if not graph_name:
                        graphs = await call(session, "list_graphs", {})
                        graph_rows = graphs.get("data", {}).get("graphs", [])
                        if not graph_rows:
                            raise RuntimeError("Origin returned no graphs after create_plot")
                        graph_name = graph_rows[-1]["name"]

                    await call(
                        session,
                        "apply_publication_style",
                        {
                            "graph_name": graph_name,
                            "x_label": "Decision variable x (a.u.)",
                            "y_label": "Response (a.u.)",
                            "font_name": "Arial",
                            "axis_title_size": 16,
                            "tick_font_size": 11,
                            "legend_font_size": 10,
                            "line_width": 1.6,
                            "symbol_size": 6,
                            "show_minor": False,
                        },
                    )
                    await call(
                        session,
                        "set_plot_color",
                        {"graph_name": graph_name, "plot_index": 0, "color": "#5292F7"},
                    )
                    await call(
                        session,
                        "set_plot_color",
                        {"graph_name": graph_name, "plot_index": 1, "color": "#79CAFB"},
                    )
                    await call(
                        session,
                        "set_plot_line_style",
                        {"graph_name": graph_name, "plot_index": 1, "style": "dash"},
                    )
                    await call(
                        session,
                        "set_legend",
                        {
                            "graph_name": graph_name,
                            "visible": True,
                            "position": "top_left",
                            "font_size": 10,
                            "labels": ["Main model", "Baseline"],
                        },
                    )

                    artifacts = {
                        "png": output_root / "originlab_mcp_smoke.png",
                        "pdf": output_root / "originlab_mcp_smoke.pdf",
                        "svg": output_root / "originlab_mcp_smoke.svg",
                        "opju": output_root / "originlab_mcp_smoke.opju",
                    }
                    for fmt in ("png", "pdf", "svg"):
                        await call(
                            session,
                            "export_graph",
                            {
                                "output_path": str(artifacts[fmt]),
                                "graph_name": graph_name,
                                "output_format": fmt,
                                "width": 1800,
                                **({"dpi": 400} if fmt == "png" else {}),
                            },
                        )
                    await call(session, "save_project", {"file_path": str(artifacts["opju"])})
                    await call(
                        session,
                        "open_project",
                        {"file_path": str(artifacts["opju"]), "readonly": True},
                    )
                    await call(session, "get_graph_info", {"graph_name": graph_name})
                    await call(session, "release_origin", {})

                    for name, path in artifacts.items():
                        if not path.is_file() or path.stat().st_size == 0:
                            raise RuntimeError(f"Missing or empty artifact: {path}")
                        report["artifacts"][name] = {
                            "path": str(path),
                            "bytes": path.stat().st_size,
                            "sha256": sha256(path),
                        }
                    dimensions = png_size(artifacts["png"])
                    report["artifacts"]["png"]["pixels"] = list(dimensions) if dimensions else None
                    dpi = png_dpi(artifacts["png"])
                    report["artifacts"]["png"]["dpi"] = (
                        [round(value, 3) for value in dpi] if dpi else None
                    )
                    if dpi is None or min(dpi) < 399:
                        report["warnings"].append(
                            {
                                "code": "PNG_DPI_BELOW_CONTRACT",
                                "message": f"PNG export DPI is {dpi}; Figure Contract requires 400 dpi",
                            }
                        )

                    visible_svg_text = " ".join(
                        text.strip()
                        for text in ET.parse(artifacts["svg"]).getroot().itertext()
                        if text.strip()
                    )
                    missing_labels = [
                        label for label in ("Main model", "Baseline") if label not in visible_svg_text
                    ]
                    if missing_labels:
                        report["warnings"].append(
                            {
                                "code": "LEGEND_LABELS_MISSING",
                                "message": f"Visible SVG text lacks series labels: {missing_labels}",
                            }
                        )

                    pdffonts = shutil.which("pdffonts")
                    if pdffonts:
                        font_audit = subprocess.run(
                            [pdffonts, str(artifacts["pdf"])],
                            capture_output=True,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                            check=False,
                        )
                        font_lines = [
                            line.rstrip()
                            for line in font_audit.stdout.splitlines()
                            if line.strip()
                        ]
                        report["artifacts"]["pdf"]["font_audit"] = font_lines
                        if any("Type 3" in line for line in font_lines):
                            report["warnings"].append(
                                {
                                    "code": "PDF_TYPE3_FONTS",
                                    "message": "PDF contains Type 3 fonts; prefer the SVG export or replace fonts before final submission",
                                }
                            )
                    report["status"] = "PASS_WITH_WARNINGS" if report["warnings"] else "PASS"
                    return_code = 0
    except Exception as exc:
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc()
        return_code = 1
    finally:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return return_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--protocol-only", action="store_true")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
