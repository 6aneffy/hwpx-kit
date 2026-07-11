"""page-break 명령 — 문단(또는 표가 든 문단) 앞 쪽나눔.

hwpx 문단의 pageBreak 속성(기본 0)을 1로 — 끼워넣은 장 헤더가 페이지
중간에 떨어지는 문제의 해결. 대상은 문단 원문 또는 표 인덱스로 지정.
"""
from __future__ import annotations

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter


def run_page_break(path: str, at_text: str | None, table: int | None, out_path: str) -> dict:
    if (at_text is None) == (table is None):
        raise ValueError("--at-text 또는 --table 중 정확히 하나를 지정하세요.")
    ad = HwpxEngineAdapter.open(path)
    applied = ad.set_page_break(at_text=at_text, table_index=table)
    out = ad.save_copy(out_path)
    return {"file": path, "out": out, "at_text": at_text, "table": table, "applied": applied}
