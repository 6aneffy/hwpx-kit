"""table-clear — 표의 지정 행 범위 셀 내용 비우기.

전면 교체 시 새 내용과 안 맞는 표는 잔존시키지 말고 비워서, 사용자가
빈 칸을 보고 행 삭제/추가 요청을 판단하게 한다 (2026-07-10 사용자 지시).
"""
import json

import pytest

from hwpx_kit.cli import main
from hwpx_kit.commands.table_clear import run_table_clear


@pytest.fixture()
def content_doc(tmp_path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        t = doc.add_table(3, 2)
        for r in range(3):
            for c in range(2):
                t.set_cell_text(r, c, f"내용{r}{c}")
        path = str(tmp_path / "src.hwpx")
        doc.save_to_path(path)
    return path


def _cell_texts(path):
    from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter

    tm = HwpxEngineAdapter.open(path).table_map()
    return {
        (c["row"], c["col"]): (c.get("text") or "").strip()
        for c in tm["tables"][0]["cells"]
    }


def test_clear_rows_keeps_header(content_doc, tmp_path):
    out = str(tmp_path / "o.hwpx")
    result = run_table_clear(content_doc, table=0, rows=[1, 2], out_path=out)
    texts = _cell_texts(out)
    assert texts[(0, 0)] == "내용00"  # 헤더 행 보존
    assert texts[(1, 0)] == "" and texts[(1, 1)] == ""
    assert texts[(2, 0)] == "" and texts[(2, 1)] == ""
    assert result["cleared_cells"] == 4
    # 원본 불변
    assert _cell_texts(content_doc)[(1, 0)] == "내용10"


def test_clear_whole_table_when_rows_omitted(content_doc, tmp_path):
    out = str(tmp_path / "o.hwpx")
    run_table_clear(content_doc, table=0, rows=None, out_path=out)
    assert all(v == "" for v in _cell_texts(out).values())


def test_rejects_bad_index(content_doc, tmp_path):
    out = str(tmp_path / "o.hwpx")
    with pytest.raises(ValueError):
        run_table_clear(content_doc, table=7, rows=None, out_path=out)
    with pytest.raises(ValueError):
        run_table_clear(content_doc, table=0, rows=[9], out_path=out)


def test_cli_table_clear(content_doc, tmp_path, capsys):
    out = str(tmp_path / "o.hwpx")
    code = main(["table-clear", content_doc, "--table", "0", "--rows", "1-2",
                 "--out", out, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0
    assert env["ok"] is True
    assert env["data"]["cleared_cells"] == 4
