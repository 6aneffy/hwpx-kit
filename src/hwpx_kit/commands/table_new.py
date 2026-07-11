"""table-new 명령 — 임의 R×C 새 표를 지정 문단에 생성.

table-copy(같은 크기 복제)와 달리 크기를 지정한다. --like-table로
기존 표의 테두리 서식 참조를 빌려 입히면 템플릿과 어울리는 표가 나온다.
"""
from __future__ import annotations

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter


def run_table_new(
    path: str, rows: int, cols: int, after_text: str | None = None,
    like_table: int | None = None, out_path: str = "",
    after_table: int | None = None,
) -> dict:
    if rows < 1 or cols < 1:
        raise ValueError("rows/cols는 1 이상이어야 합니다.")
    ad = HwpxEngineAdapter.open(path)
    ad.new_table(rows=rows, cols=cols, anchor_text=after_text,
                 like_table=like_table, after_table=after_table)
    out = ad.save_copy(out_path)
    return {
        "file": path,
        "out": out,
        "rows": rows,
        "cols": cols,
        "like_table": like_table,
        "anchor_text": after_text,
    }
