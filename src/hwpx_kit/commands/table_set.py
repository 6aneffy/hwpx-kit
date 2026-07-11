"""table-set 명령 — 좌표 지정 셀 쓰기 (table-clear의 짝).

비운 셀에는 라벨이 없어 fill의 table: 키가 못 닿는다 — 전면 교체 후
새 항목명을 좌표로 직접 기입. 인덱스는 analyze와 동일한 0-기준.
"""
from __future__ import annotations

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter


def load_assignments_file(path: str) -> list[tuple[int, int, str]]:
    """--data JSON 파일({"R,C": "값"}) → assignments. 셀 대량 기입 시
    셸 명령 길이 한계를 피하는 경로 (fill --data와 같은 철학)."""
    import json

    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        raise ValueError('--data 파일 형식은 {"R,C": "값"} 객체여야 합니다.')
    return parse_assignments([f"{coord}={value}" for coord, value in raw.items()])


def parse_assignments(specs: list[str]) -> list[tuple[int, int, str]]:
    """'R,C=값' 목록 → (row, col, value). 값 안의 '='는 그대로 허용."""
    result = []
    for spec in specs:
        coord, sep, value = spec.partition("=")
        parts = coord.split(",")
        if not sep or len(parts) != 2:
            raise ValueError(f"형식은 'R,C=값' 이어야 합니다: {spec!r}")
        try:
            result.append((int(parts[0].strip()), int(parts[1].strip()), value))
        except ValueError as exc:
            raise ValueError(f"좌표는 정수여야 합니다: {spec!r}") from exc
    return result


def run_table_set(
    path: str, table: int, assignments: list[tuple[int, int, str]], out_path: str
) -> dict:
    ad = HwpxEngineAdapter.open(path)
    count = ad.set_table_cells(table_index=table, assignments=assignments)
    out = ad.save_copy(out_path)
    return {
        "file": path,
        "out": out,
        "table_index": table,
        "set_cells": count,
    }
