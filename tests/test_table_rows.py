"""row-add / row-del — 표 행 추가·삭제 (서식 승계, 병합 가드).

python-hwpx에는 행 API가 없어 어댑터가 tr 요소 deepcopy로 구현.
원시 XML 수정은 섹션 dirty 플래그를 안 세워 저장이 원본 바이트를
재사용(증발)하므로, 수정 후 반드시 mark_dirty — 이 테스트의
재열기 검증이 그 회귀를 감지한다.
"""
import json

import pytest

from hwpx_kit.cli import main
from hwpx_kit.commands.table_rows import run_row_add, run_row_del


@pytest.fixture()
def table_doc(tmp_path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        t = doc.add_table(3, 2)
        t.set_cell_text(0, 0, "헤더A")
        t.set_cell_text(0, 1, "헤더B")
        t.set_cell_text(1, 0, "값1")
        t.set_cell_text(2, 0, "값2")
        for c in list(t.rows)[1].cells:
            c.set_size(height=4200)
        path = str(tmp_path / "src.hwpx")
        doc.save_to_path(path)
    return path


@pytest.fixture()
def merged_doc(tmp_path):
    """행0-1 세로 병합(첫 열)이 있는 표."""
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        t = doc.add_table(3, 2)
        t.merge_cells(0, 0, 1, 0)
        t.set_cell_text(2, 0, "아래")
        path = str(tmp_path / "merged.hwpx")
        doc.save_to_path(path)
    return path


def _grid(path):
    """재열기 후 표 상태 — {(r,c): text}, row_count."""
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
        return t.row_count, cells


def test_row_add_after_like(table_doc, tmp_path):
    out = str(tmp_path / "o.hwpx")
    result = run_row_add(table_doc, table=0, like=1, count=2, at=None, out_path=out)
    rows, cells = _grid(out)
    assert rows == 5
    assert result["added"] == 2
    # like 다음에 삽입: 값1(1) → 빈2 → 빈3 → 값2(4로 밀림)
    assert cells[(1, 0)] == "값1"
    assert cells[(2, 0)] == "" and cells[(3, 0)] == ""
    assert cells[(4, 0)] == "값2"
    # 원본 불변
    assert _grid(table_doc)[0] == 3


def test_row_add_at_position(table_doc, tmp_path):
    out = str(tmp_path / "o.hwpx")
    run_row_add(table_doc, table=0, like=1, count=1, at=1, out_path=out)
    rows, cells = _grid(out)
    assert rows == 4
    # at=1: 헤더(0) → 새 빈 행(1) → 값1(2) → 값2(3)
    assert cells[(1, 0)] == ""
    assert cells[(2, 0)] == "값1"


def test_row_add_inherits_height(table_doc, tmp_path):
    from hwpx.document import HwpxDocument
    from hwpx.tools import table_navigation as tn

    from hwpx_kit.output import quiet_engine

    out = str(tmp_path / "o.hwpx")
    run_row_add(table_doc, table=0, like=1, count=1, at=None, out_path=out)
    with quiet_engine():
        t = tn._collect_document_tables(HwpxDocument.open(out))[0].table
        assert list(list(t.rows)[2].cells)[0].height == 4200


def test_row_add_new_row_writable_and_persists(table_doc, tmp_path):
    """추가한 행에 table-set으로 쓰고 저장 → 재열기까지 살아남는지 (dirty 회귀 감지)."""
    from hwpx_kit.commands.table_set import run_table_set

    mid = str(tmp_path / "mid.hwpx")
    out = str(tmp_path / "o.hwpx")
    run_row_add(table_doc, table=0, like=1, count=1, at=None, out_path=mid)
    run_table_set(mid, table=0, assignments=[(2, 0, "새항목"), (2, 1, "10,000")], out_path=out)
    _, cells = _grid(out)
    assert cells[(2, 0)] == "새항목"
    assert cells[(2, 1)] == "10,000"


def test_row_add_rejects_merged_like(merged_doc, tmp_path):
    with pytest.raises(ValueError, match="병합"):
        run_row_add(merged_doc, table=0, like=0, count=1, at=None,
                    out_path=str(tmp_path / "o.hwpx"))


def test_row_add_rejects_insert_inside_merge(merged_doc, tmp_path):
    # 행0-1 병합 사이(at=1)에 끼워넣기 금지
    with pytest.raises(ValueError, match="병합"):
        run_row_add(merged_doc, table=0, like=2, count=1, at=1,
                    out_path=str(tmp_path / "o.hwpx"))


def test_row_add_after_merge_ok(merged_doc, tmp_path):
    # 병합 구간 밖(끝)에 추가는 허용
    out = str(tmp_path / "o.hwpx")
    run_row_add(merged_doc, table=0, like=2, count=1, at=None, out_path=out)
    assert _grid(out)[0] == 4


def test_row_del(table_doc, tmp_path):
    out = str(tmp_path / "o.hwpx")
    result = run_row_del(table_doc, table=0, rows=[1], out_path=out)
    rows, cells = _grid(out)
    assert rows == 2
    assert result["deleted"] == 1
    assert cells[(1, 0)] == "값2"  # 값1 삭제, 값2가 올라옴
    assert _grid(table_doc)[0] == 3  # 원본 불변


def test_row_del_multiple(table_doc, tmp_path):
    out = str(tmp_path / "o.hwpx")
    run_row_del(table_doc, table=0, rows=[1, 2], out_path=out)
    rows, cells = _grid(out)
    assert rows == 1
    assert cells[(0, 0)] == "헤더A"


def test_row_del_rejects_partial_merge(merged_doc, tmp_path):
    # 병합(행0-1)의 일부만 삭제 금지
    with pytest.raises(ValueError, match="병합"):
        run_row_del(merged_doc, table=0, rows=[1], out_path=str(tmp_path / "o.hwpx"))


def test_row_del_whole_merge_ok(merged_doc, tmp_path):
    # 병합 전체(행0,1)를 함께 삭제하는 건 허용
    out = str(tmp_path / "o.hwpx")
    run_row_del(merged_doc, table=0, rows=[0, 1], out_path=out)
    rows, cells = _grid(out)
    assert rows == 1
    assert cells[(0, 0)] == "아래"


def test_row_del_rejects_all_rows(table_doc, tmp_path):
    with pytest.raises(ValueError, match="전부"):
        run_row_del(table_doc, table=0, rows=[0, 1, 2], out_path=str(tmp_path / "o.hwpx"))


def test_cli_row_add(table_doc, tmp_path, capsys):
    out = str(tmp_path / "o.hwpx")
    code = main(["row-add", table_doc, "--table", "0", "--like", "1",
                 "--count", "1", "--out", out, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and env["ok"] is True
    assert _grid(out)[0] == 4


def test_cli_row_del(table_doc, tmp_path, capsys):
    out = str(tmp_path / "o.hwpx")
    code = main(["row-del", table_doc, "--table", "0", "--rows", "2",
                 "--out", out, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and env["ok"] is True
    assert _grid(out)[0] == 2
