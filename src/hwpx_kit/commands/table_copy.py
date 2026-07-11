"""table-copy 명령 — 표 통째 복제를 지정 문단에 삽입.

장(章) 헤더 박스는 1x3 표라서, 장을 임의 개수로 늘리는 요구는
"헤더 표 복제(table-copy) → 번호·제목 기입(table-set)" 조합으로 해결.
삽입 위치는 fill의 text: 철학대로 문단 원문으로 지정.
"""
from __future__ import annotations

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter


def run_table_copy(path: str, table: int, after_text: str | None, out_path: str,
                   after_table: int | None = None) -> dict:
    ad = HwpxEngineAdapter.open(path)
    info = ad.copy_table(table_index=table, anchor_text=after_text, after_table=after_table)
    out = ad.save_copy(out_path)
    return {
        "file": path,
        "out": out,
        "copied_from": table,
        "anchor_text": after_text,
        "after_table": after_table,
        **info,
    }
