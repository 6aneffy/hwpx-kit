"""row-add / row-del 명령 — 표 행 추가·삭제.

python-hwpx에 행 API가 없어 어댑터가 tr deepcopy/제거로 구현.
행 추가는 기준 행(like)의 서식·높이·가로병합을 승계하고 내용은 비운다.
세로 병합에 걸리면 거부 (조용한 표 손상 방지).
"""
from __future__ import annotations

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
from hwpx_kit.commands.row_height import parse_rows_spec


def run_row_add(path: str, table: int, like: int, count: int,
                at: int | None, out_path: str) -> dict:
    ad = HwpxEngineAdapter.open(path)
    added = ad.add_table_rows(table, like=like, count=count, at=at)
    out = ad.save_copy(out_path)
    return {"file": path, "out": out, "table": table, "like": like,
            "at": at if at is not None else like + 1, "added": added}


def run_row_del(path: str, table: int, rows: list[int], out_path: str) -> dict:
    ad = HwpxEngineAdapter.open(path)
    deleted = ad.delete_table_rows(table, rows)
    out = ad.save_copy(out_path)
    return {"file": path, "out": out, "table": table,
            "rows": sorted(set(rows)), "deleted": deleted}
