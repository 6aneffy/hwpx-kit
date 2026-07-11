"""table-map(표 셀 덤프) + table-new(임의 크기 새 표) — 실사용 테스트에서 나온 요구.

- table-map: 병합 셀 확인을 원시 XML 파싱으로 하던 것을 정식 명령으로
- table-new: 복제가 아니라 R×C 지정 생성, --like-table로 기존 표 서식 차용
"""
import json

import pytest

from hwpx_kit.cli import main


@pytest.fixture()
def doc_with_table(tmp_path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        doc.add_paragraph("본문 시작")
        t = doc.add_table(2, 3)
        t.set_cell_text(0, 0, "헤더")
        doc.add_paragraph("여기 아래 새 표")
        path = str(tmp_path / "src.hwpx")
        doc.save_to_path(path)
    return path


def _last_json(capsys):
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def _tables(path):
    from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter

    return HwpxEngineAdapter.open(path).table_map()["tables"]


def test_table_map_lists_cells(doc_with_table, capsys):
    code = main(["table-map", doc_with_table, "--json"])
    env = _last_json(capsys)
    assert code == 0
    tables = env["data"]["tables"]
    assert len(tables) == 1
    cells = {(c["row"], c["col"]): c for c in tables[0]["cells"]}
    assert cells[(0, 0)]["text"] == "헤더"
    assert "is_anchor" in cells[(0, 0)]


def test_table_map_single_table_filter(doc_with_table, capsys):
    code = main(["table-map", doc_with_table, "--table", "0", "--json"])
    env = _last_json(capsys)
    assert code == 0
    assert len(env["data"]["tables"]) == 1


def test_table_new_creates_sized_table(doc_with_table, tmp_path, capsys):
    out = str(tmp_path / "o.hwpx")
    code = main(["table-new", doc_with_table, "--rows", "4", "--cols", "2",
                 "--after-text", "여기 아래 새 표", "--out", out, "--json"])
    env = _last_json(capsys)
    assert code == 0
    assert env["data"]["rows"] == 4 and env["data"]["cols"] == 2

    code = main(["table-map", out, "--json"])
    env = _last_json(capsys)
    tables = env["data"]["tables"]
    assert len(tables) == 2
    new_t = tables[1]
    assert new_t["rows"] == 4 and new_t["cols"] == 2


def test_table_new_like_table_borrows_style(doc_with_table, tmp_path):
    """--like-table: 기준 표의 테두리 서식 참조(borderFillIDRef)를 새 표 셀에 입힌다."""
    from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
    from hwpx_kit.commands.table_new import run_table_new

    out = str(tmp_path / "o.hwpx")
    run_table_new(doc_with_table, rows=2, cols=2, after_text="여기 아래 새 표",
                  like_table=0, out_path=out)
    ad = HwpxEngineAdapter.open(out)
    from hwpx.tools import table_navigation as tn

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        tables = tn._collect_document_tables(ad._doc)
        src_ref = list(list(tables[0].table.rows)[0].cells)[0].element.get("borderFillIDRef")
        new_ref = list(list(tables[1].table.rows)[0].cells)[0].element.get("borderFillIDRef")
    assert src_ref is not None
    assert new_ref == src_ref


def test_table_copy_after_table(doc_with_table, tmp_path):
    """표 사이에 문단이 없을 때 — --after-table로 표 뒤에 직접 삽입 (3차 실사용 요구)."""
    from hwpx_kit.commands.table_copy import run_table_copy

    out = str(tmp_path / "o.hwpx")
    result = run_table_copy(doc_with_table, table=0, after_text=None,
                            after_table=0, out_path=out)
    assert result["after_table"] == 0
    tables = _tables(out)
    assert len(tables) == 2
    # 복제본이 원본 바로 뒤 (같은 문단) — 문서 순서상 index 1
    assert tables[1]["rows"] == 2 and tables[1]["cols"] == 3


def test_table_new_after_table(doc_with_table, tmp_path):
    from hwpx_kit.commands.table_new import run_table_new

    out = str(tmp_path / "o.hwpx")
    run_table_new(doc_with_table, rows=3, cols=2, after_table=0, out_path=out)
    tables = _tables(out)
    assert len(tables) == 2
    assert tables[1]["rows"] == 3 and tables[1]["cols"] == 2


def test_outline_maps_paragraphs_and_tables(doc_with_table, capsys):
    code = main(["outline", doc_with_table, "--json"])
    env = _last_json(capsys)
    assert code == 0
    paras = env["data"]["paragraphs"]
    texts = [p["text"] for p in paras]
    assert "본문 시작" in texts and "여기 아래 새 표" in texts
    tabled = [p for p in paras if p.get("tables")]
    assert tabled and tabled[0]["tables"][0]["table_index"] == 0
    assert tabled[0]["tables"][0]["rows"] == 2
