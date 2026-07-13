"""cell-merge / cell-split / cell-color / col-width — 표 스타일 조작.

엔진(merge_cells·split_merged_cell·set_cell_shading·set_column_widths)의
저장 생존은 실험으로 확인됨(2026-07-12) — 여기서는 재열기 회귀 + CLI 계약 검증.
"""
import json

import pytest

from hwpx_kit.cli import main
from hwpx_kit.commands.table_style import (
    run_cell_color,
    run_cell_merge,
    run_cell_split,
    run_col_width,
)


@pytest.fixture()
def grid_doc(tmp_path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        t = doc.add_table(3, 3)
        t.set_cell_text(0, 0, "제목")
        t.set_cell_text(1, 0, "값1")
        path = str(tmp_path / "grid.hwpx")
        doc.save_to_path(path)
    return path


def _table(path):
    from hwpx.document import HwpxDocument
    from hwpx.tools import table_navigation as tn

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        return tn._collect_document_tables(HwpxDocument.open(path))[0].table


def test_cell_merge(grid_doc, tmp_path):
    out = str(tmp_path / "o.hwpx")
    result = run_cell_merge(grid_doc, table=0, cell_range="0,0:0,2", out_path=out)
    assert result["merged"] == "0,0:0,2"
    t = _table(out)
    assert t.cell(0, 0).span == (1, 3)
    assert _table(grid_doc).cell(0, 0).span == (1, 1)  # 원본 불변


def test_cell_merge_vertical(grid_doc, tmp_path):
    out = str(tmp_path / "o.hwpx")
    run_cell_merge(grid_doc, table=0, cell_range="0,0:2,0", out_path=out)
    assert _table(out).cell(0, 0).span == (3, 1)


def test_cell_split(grid_doc, tmp_path):
    mid = str(tmp_path / "m.hwpx")
    out = str(tmp_path / "o.hwpx")
    run_cell_merge(grid_doc, table=0, cell_range="0,0:0,2", out_path=mid)
    result = run_cell_split(mid, table=0, cell="0,0", out_path=out)
    assert result["split"] == "0,0"
    assert _table(out).cell(0, 0).span == (1, 1)


def test_cell_color_single_and_range(grid_doc, tmp_path):
    import zipfile

    out = str(tmp_path / "o.hwpx")
    result = run_cell_color(grid_doc, table=0, cell_range="0,0:0,2",
                            color="#FFE9A9", out_path=out)
    assert result["colored"] == 3
    hdr = zipfile.ZipFile(out).read("Contents/header.xml").decode("utf-8")
    assert "FFE9A9" in hdr.upper()


def test_cell_color_rejects_bad_color(grid_doc, tmp_path):
    with pytest.raises(ValueError, match="색"):
        run_cell_color(grid_doc, table=0, cell_range="0,0:0,0",
                       color="노랑", out_path=str(tmp_path / "o.hwpx"))


def test_col_width(grid_doc, tmp_path):
    out = str(tmp_path / "o.hwpx")
    result = run_col_width(grid_doc, table=0, widths=[2, 3, 5], out_path=out)
    assert result["widths"] == [2, 3, 5]
    t = _table(out)
    w = [t.cell(0, c).width for c in range(3)]
    assert w[0] < w[1] < w[2]  # 비율 반영


def test_col_width_rejects_count_mismatch(grid_doc, tmp_path):
    with pytest.raises(ValueError, match="열"):
        run_col_width(grid_doc, table=0, widths=[1, 2],
                      out_path=str(tmp_path / "o.hwpx"))


def test_roundtrip_validate(grid_doc, tmp_path):
    from hwpx_kit.commands.validate import run_validate

    out = str(tmp_path / "o.hwpx")
    run_cell_merge(grid_doc, table=0, cell_range="0,0:0,2", out_path=out)
    out2 = str(tmp_path / "o2.hwpx")
    run_cell_color(out, table=0, cell_range="1,0:1,2", color="#E6F0FF", out_path=out2)
    assert run_validate(out2)["valid"] is True


def test_cli_cell_merge_and_color(grid_doc, tmp_path, capsys):
    out = str(tmp_path / "o.hwpx")
    code = main(["cell-merge", grid_doc, "--table", "0", "--range", "0,0:0,2",
                 "--out", out, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and env["ok"] is True

    out2 = str(tmp_path / "o2.hwpx")
    code = main(["cell-color", out, "--table", "0", "--range", "1,1:1,1",
                 "--color", "#FFE9A9", "--out", out2, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and env["data"]["colored"] == 1


def test_cli_col_width(grid_doc, tmp_path, capsys):
    out = str(tmp_path / "o.hwpx")
    code = main(["col-width", grid_doc, "--table", "0", "--widths", "2,3,5",
                 "--out", out, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and env["ok"] is True
