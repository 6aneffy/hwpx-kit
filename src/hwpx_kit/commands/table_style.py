"""cell-merge / cell-split / cell-color / col-width — 표 스타일 조작.

전부 엔진 네이티브 API 래핑 (merge_cells·split_merged_cell·
set_cell_shading·set_column_widths) — 저장 생존 실험 확인(2026-07-12).
"""
from __future__ import annotations

import re

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter

_HEX_COLOR = re.compile(r"^#?[0-9A-Fa-f]{6}$")


def _parse_cell(spec: str) -> tuple[int, int]:
    try:
        r, c = spec.split(",")
        return int(r), int(c)
    except ValueError:
        raise ValueError(f"셀 좌표 형식은 'R,C': {spec!r}") from None


def _parse_range(spec: str) -> tuple[int, int, int, int]:
    """'R1,C1:R2,C2' → (r1, c1, r2, c2). 단일 셀은 'R,C:R,C'."""
    try:
        start, end = spec.split(":")
    except ValueError:
        raise ValueError(f"범위 형식은 'R1,C1:R2,C2': {spec!r}") from None
    r1, c1 = _parse_cell(start)
    r2, c2 = _parse_cell(end)
    if r2 < r1 or c2 < c1:
        raise ValueError(f"범위의 끝이 시작보다 앞섬: {spec!r}")
    return r1, c1, r2, c2


def _get_table(ad: HwpxEngineAdapter, table_index: int):
    from hwpx.tools import table_navigation as tn

    tables = tn._collect_document_tables(ad._doc)
    if not 0 <= table_index < len(tables):
        raise ValueError(f"표 인덱스 범위 밖: {table_index} (표 {len(tables)}개)")
    return tables[table_index].table


def run_cell_merge(path: str, table: int, cell_range: str, out_path: str) -> dict:
    r1, c1, r2, c2 = _parse_range(cell_range)
    ad = HwpxEngineAdapter.open(path)
    ad.merge_cells(table, r1, c1, r2, c2)
    out = ad.save_copy(out_path)
    return {"file": path, "out": out, "table": table, "merged": cell_range}


def run_cell_split(path: str, table: int, cell: str, out_path: str) -> dict:
    r, c = _parse_cell(cell)
    ad = HwpxEngineAdapter.open(path)
    created = ad.split_cell(table, r, c)
    out = ad.save_copy(out_path)
    return {"file": path, "out": out, "table": table, "split": cell,
            "restored_cells": created}


def run_cell_color(path: str, table: int, cell_range: str, color: str,
                   out_path: str) -> dict:
    from hwpx_kit.output import quiet_engine

    if not _HEX_COLOR.match(color):
        raise ValueError(f"색은 6자리 hex로: #FFE9A9 (받은 값: {color!r})")
    if not color.startswith("#"):
        color = "#" + color
    r1, c1, r2, c2 = _parse_range(cell_range)
    ad = HwpxEngineAdapter.open(path)
    colored = 0
    with quiet_engine():
        t = _get_table(ad, table)
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                t.set_cell_shading(r, c, color)
                colored += 1
    out = ad.save_copy(out_path)
    return {"file": path, "out": out, "table": table,
            "color": color, "colored": colored}


def run_col_width(path: str, table: int, widths: list[float], out_path: str) -> dict:
    from hwpx_kit.output import quiet_engine

    ad = HwpxEngineAdapter.open(path)
    with quiet_engine():
        t = _get_table(ad, table)
        if len(widths) != t.column_count:
            raise ValueError(
                f"열 수 불일치: 표는 {t.column_count}열, 지정은 {len(widths)}개")
        t.set_column_widths(widths)
    out = ad.save_copy(out_path)
    return {"file": path, "out": out, "table": table, "widths": widths}
