"""table-clear 명령 — 표의 지정 행 범위 셀 내용 비우기.

전면 교체 시 새 내용과 안 맞는 표를 잔존시키지 않고 비워서, 사용자가
빈 칸을 보고 행 삭제(한글)나 추가 내용 요청을 판단하게 한다.
행 자체는 남는다(구조 변경 아님). 인덱스는 analyze와 동일한 0-기준.
"""
from __future__ import annotations

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter


def run_table_clear(path: str, table: int, rows: list[int] | None, out_path: str) -> dict:
    ad = HwpxEngineAdapter.open(path)
    cleared = ad.clear_table_rows(table_index=table, rows=rows)
    out = ad.save_copy(out_path)
    return {
        "file": path,
        "out": out,
        "table_index": table,
        "rows": rows,
        "cleared_cells": cleared,
    }
