"""table-build / cell-align — 선언형 원샷 표 생성과 정렬.

"이렇게 표 그려줘"용: 원시 도구(table-new→cell-merge→cell-color→col-width→
table-set) 오케스트레이션을 스펙 JSON 하나로 대체.
"""
from __future__ import annotations

import json

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
from hwpx_kit.commands.table_style import _parse_range


def run_table_build(path: str, spec_path: str, at_text: str | None,
                    out_path: str, after_table: int | None = None) -> dict:
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    ad = HwpxEngineAdapter.open(path)
    info = ad.build_table(spec, anchor_text=at_text, after_table=after_table)
    out = ad.save_copy(out_path)
    return {"file": path, "out": out, **info}


def run_cell_align(path: str, table: int, cell_range: str, align: str,
                   out_path: str) -> dict:
    r1, c1, r2, c2 = _parse_range(cell_range)
    ad = HwpxEngineAdapter.open(path)
    aligned = ad.align_cells(table, r1, c1, r2, c2, align)
    out = ad.save_copy(out_path)
    return {"file": path, "out": out, "table": table,
            "align": align, "aligned": aligned}
