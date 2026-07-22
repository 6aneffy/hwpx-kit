"""col-add / col-del — 표 열 추가·삭제 (기준열 서식·폭 승계, 병합 가드).

엔진에 열 API가 없어 어댑터가 tc colAddr 시프트로 구현.
세로 병합 표는 MVP에서 거부. 원시 XML 수정은 dirty 필수 —
재열기 검증이 증발 회귀를 감지한다.
"""
import json

import pytest

from hwpx_kit.cli import main


@pytest.fixture()
def table_doc(tmp_path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        t = doc.add_table(2, 3)
        t.set_cell_text(0, 0, "A"); t.set_cell_text(0, 1, "B"); t.set_cell_text(0, 2, "C")
        t.set_cell_text(1, 0, "1"); t.set_cell_text(1, 1, "2"); t.set_cell_text(1, 2, "3")
        path = str(tmp_path / "src.hwpx")
        doc.save_to_path(path)
    return path


def _grid(path):
    """재열기 후 (row_count, col_count, {(r,c):text})."""
    from hwpx.document import HwpxDocument
    from hwpx.tools import table_navigation as tn

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        t = tn._collect_document_tables(HwpxDocument.open(path))[0].table
        cells = {}
        for r in range(t.row_count):
            for c in range(t.column_count):
                try:
                    cells[(r, c)] = (tn._cell_text(t, r, c) or "").strip()
                except Exception:
                    pass
        return t.row_count, t.column_count, cells


def test_col_add_after_like(table_doc, tmp_path):
    from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter

    out = str(tmp_path / "o.hwpx")
    ad = HwpxEngineAdapter.open(table_doc)
    added = ad.add_table_columns(0, like=1, count=1, at=None)
    ad.save_copy(out)
    rows, cols, cells = _grid(out)
    assert (rows, cols) == (2, 4) and added == 1
    # like=1(B) 다음 삽입: A(0) B(1) 빈(2) C(3밀림)
    assert cells[(0, 0)] == "A" and cells[(0, 1)] == "B"
    assert cells[(0, 2)] == "" and cells[(0, 3)] == "C"
    assert cells[(1, 2)] == "" and cells[(1, 3)] == "3"


def test_col_add_inherits_width(table_doc, tmp_path):
    from hwpx.document import HwpxDocument
    from hwpx.tools import table_navigation as tn

    from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
    from hwpx_kit.output import quiet_engine

    out = str(tmp_path / "o.hwpx")
    ad = HwpxEngineAdapter.open(table_doc)
    ad.add_table_columns(0, like=1, count=1, at=None)
    ad.save_copy(out)
    with quiet_engine():
        t = tn._collect_document_tables(HwpxDocument.open(out))[0].table
        w_like = list(list(t.rows)[0].cells)[1].width
        w_new = list(list(t.rows)[0].cells)[2].width
        assert w_new == w_like  # 기준열 폭 상속


def test_col_add_at_position(table_doc, tmp_path):
    from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter

    out = str(tmp_path / "o.hwpx")
    ad = HwpxEngineAdapter.open(table_doc)
    ad.add_table_columns(0, like=0, count=1, at=0)  # 맨 앞
    ad.save_copy(out)
    rows, cols, cells = _grid(out)
    assert cols == 4
    assert cells[(0, 0)] == "" and cells[(0, 1)] == "A"


def test_col_add_persists_after_write(table_doc, tmp_path):
    """추가 열에 table-set으로 쓰고 재열기까지 살아남는지 (dirty 회귀)."""
    from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
    from hwpx_kit.commands.table_set import run_table_set

    mid = str(tmp_path / "mid.hwpx"); out = str(tmp_path / "o.hwpx")
    ad = HwpxEngineAdapter.open(table_doc)
    ad.add_table_columns(0, like=1, count=1, at=None)
    ad.save_copy(mid)
    run_table_set(mid, table=0, assignments=[(0, 2, "새열"), (1, 2, "99")], out_path=out)
    _, _, cells = _grid(out)
    assert cells[(0, 2)] == "새열" and cells[(1, 2)] == "99"
