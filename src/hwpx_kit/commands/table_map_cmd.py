"""table-map 명령 — 표 셀 상태 덤프 (좌표·텍스트·병합 anchor).

병합 셀 확인을 위해 원시 XML을 파싱하던 우회를 대체하는 정식 검사 명령.
"""
from __future__ import annotations

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter


def run_table_map(path: str, table: int | None = None) -> dict:
    ad = HwpxEngineAdapter.open(path)
    tm = ad.table_map()
    tables = tm.get("tables", [])
    if table is not None:
        if not 0 <= table < len(tables):
            raise ValueError(f"표 인덱스 범위 밖: {table} (표 {len(tables)}개)")
        tables = [tables[table]]
    return {"file": path, "tables": tables}
