"""row-height — 기준 행 높이를 지정 행들에 복사 (사용자가 한글에서 행 추가 후
높이가 안 맞는 케이스의 도구측 정돈).

인덱스는 analyze 출력과 동일하게 0-기준 (table_index, row).
"""
import json

import pytest

from hwpx_kit.cli import main
from hwpx_kit.commands.row_height import run_row_height


@pytest.fixture()
def uneven_doc(tmp_path):
    """3행 표 — 0행만 높이 7200, 나머지 3600 (한글 행 추가 흉내)."""
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        t = doc.add_table(3, 2)
        for c in list(t.rows)[0].cells:
            c.set_size(height=7200)
        t.set_cell_text(0, 0, "제목")
        path = str(tmp_path / "uneven.hwpx")
        doc.save_to_path(path)
    return path


def _row_heights(path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.open(path)
        for p in doc.paragraphs:
            tables = list(p.tables)
            if tables:
                return [list(r.cells)[0].height for r in tables[0].rows]
    raise AssertionError("표 없음")


def test_copy_height_to_rows(uneven_doc, tmp_path):
    out = str(tmp_path / "fixed.hwpx")
    result = run_row_height(uneven_doc, table=0, like=0, rows=[1, 2], out_path=out)
    assert _row_heights(out) == [7200, 7200, 7200]
    assert result["applied_rows"] == [1, 2]
    assert result["height"] == 7200
    # 원본 불변
    assert _row_heights(uneven_doc) == [7200, 3600, 3600]


def test_rejects_same_out_path(uneven_doc):
    with pytest.raises(ValueError):
        run_row_height(uneven_doc, table=0, like=0, rows=[1], out_path=uneven_doc)


def test_rejects_bad_indexes(uneven_doc, tmp_path):
    out = str(tmp_path / "o.hwpx")
    with pytest.raises(ValueError):
        run_row_height(uneven_doc, table=5, like=0, rows=[1], out_path=out)
    with pytest.raises(ValueError):
        run_row_height(uneven_doc, table=0, like=9, rows=[1], out_path=out)
    with pytest.raises(ValueError):
        run_row_height(uneven_doc, table=0, like=0, rows=[9], out_path=out)


def test_cli_row_height_range(uneven_doc, tmp_path, capsys):
    """--rows는 '1-2' 범위와 '1,2' 나열 둘 다."""
    out = str(tmp_path / "o.hwpx")
    code = main(["row-height", uneven_doc, "--table", "0", "--like", "0",
                 "--rows", "1-2", "--out", out, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0
    assert env["ok"] is True
    assert env["data"]["applied_rows"] == [1, 2]
    assert _row_heights(out) == [7200, 7200, 7200]
