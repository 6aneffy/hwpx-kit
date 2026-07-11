"""row-height 명령 — 기준 행 높이를 지정 행들에 복사.

사용자가 한글에서 행을 추가하면 기본 높이로 붙어 표가 들쭉날쭉해지는
케이스의 도구측 정돈. 인덱스는 analyze 출력과 동일한 0-기준.
"""
from __future__ import annotations

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter


def parse_rows_spec(spec: str) -> list[int]:
    """'1-3' 범위 / '1,3,5' 나열 / 혼합('1-3,5') → 정렬된 행 목록."""
    rows: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            rows.update(range(int(lo), int(hi) + 1))
        else:
            rows.add(int(part))
    if not rows:
        raise ValueError(f"행 지정이 비었습니다: {spec!r}")
    return sorted(rows)


def run_row_height(path: str, table: int, like: int, rows: list[int], out_path: str) -> dict:
    ad = HwpxEngineAdapter.open(path)
    height = ad.copy_row_height(table_index=table, like=like, rows=rows)
    out = ad.save_copy(out_path)
    return {
        "file": path,
        "out": out,
        "table_index": table,
        "like": like,
        "applied_rows": rows,
        "height": height,
    }
