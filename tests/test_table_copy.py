"""table-copy — 표를 통째 복제해 지정 문단 위치에 삽입.

장(章) 헤더 박스가 실은 1x3 표라서, 장을 N개로 늘리는 요구(8장·30장)는
이 명령으로 해결: 헤더 표 복제 → table-set으로 번호·제목 기입.
원시 XML 삽입은 엔진 저장이 무시하므로(실험 확인), 엔진 등록 경유
생성 후 내용 바꿔치기 방식.
"""
import json

import pytest

from hwpx_kit.cli import main
from hwpx_kit.commands.table_copy import run_table_copy


@pytest.fixture()
def chaptered_doc(tmp_path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        doc.add_paragraph("일장 시작")
        t = doc.add_table(1, 3)
        t.set_cell_text(0, 0, "1")
        t.set_cell_text(0, 2, "추진배경")
        for c in list(t.rows)[0].cells:
            c.set_size(height=5000)
        doc.add_paragraph("여기가 새 장 자리")
        t2 = doc.add_table(2, 2)
        t2.set_cell_text(0, 0, "예산")
        path = str(tmp_path / "src.hwpx")
        doc.save_to_path(path)
    return path


def _tables(path):
    from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter

    return HwpxEngineAdapter.open(path).table_map()["tables"]


def test_copy_after_text(chaptered_doc, tmp_path):
    out = str(tmp_path / "o.hwpx")
    result = run_table_copy(chaptered_doc, table=0, after_text="여기가 새 장 자리", out_path=out)
    tables = _tables(out)
    assert len(tables) == 3
    # 문서 순서: 원본 헤더(0) → 복제본(1, 새 장 자리 문단) → 예산표(2)
    clone = tables[1]
    assert clone["rows"] == 1 and clone["cols"] == 3
    cells = {(c["row"], c["col"]): (c.get("text") or "").strip() for c in clone["cells"]}
    assert cells[(0, 0)] == "1"
    assert cells[(0, 2)] == "추진배경"
    assert result["copied_from"] == 0
    # 원본 불변
    assert len(_tables(chaptered_doc)) == 2


def test_copy_preserves_row_height(chaptered_doc, tmp_path):
    from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter

    out = str(tmp_path / "o.hwpx")
    run_table_copy(chaptered_doc, table=0, after_text="여기가 새 장 자리", out_path=out)
    ad = HwpxEngineAdapter.open(out)
    from hwpx.tools import table_navigation as tn

    with __import__("hwpx_kit.output", fromlist=["quiet_engine"]).quiet_engine():
        tables = tn._collect_document_tables(ad._doc)
        clone = tables[1].table
        assert list(list(clone.rows)[0].cells)[0].height == 5000


def test_copy_rejects_missing_anchor(chaptered_doc, tmp_path):
    with pytest.raises(ValueError, match="문단"):
        run_table_copy(chaptered_doc, table=0, after_text="없는 문장",
                       out_path=str(tmp_path / "o.hwpx"))


def test_copy_rejects_bad_table(chaptered_doc, tmp_path):
    with pytest.raises(ValueError):
        run_table_copy(chaptered_doc, table=9, after_text="여기가 새 장 자리",
                       out_path=str(tmp_path / "o.hwpx"))


def test_cli_table_copy(chaptered_doc, tmp_path, capsys):
    out = str(tmp_path / "o.hwpx")
    code = main(["table-copy", chaptered_doc, "--table", "0",
                 "--after-text", "여기가 새 장 자리", "--out", out, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0
    assert env["ok"] is True
    assert len(_tables(out)) == 3
