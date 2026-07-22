"""table-sum — 표 셀 합계/평균 결정론 계산 + 착지.

순수 계산(parse_number/compute/format_result)은 한글 불필요.
run_table_sum은 table_map 읽기 + set_table_cells 쓰기 재사용.
"""
import json
from decimal import Decimal

import pytest

from hwpx_kit.cli import main
from hwpx_kit.commands.table_calc import (
    compute,
    format_result,
    parse_cells_spec,
    parse_number,
)


def test_parse_number_comma_and_negative():
    assert parse_number("1,234") == Decimal("1234")
    assert parse_number("△20") == Decimal("-20")
    assert parse_number("1,234.5") == Decimal("1234.5")
    assert parse_number("") is None
    assert parse_number("합계") is None
    assert parse_number("120 원") == Decimal("120")


def test_compute_sum_avg():
    vals = [Decimal("100"), Decimal("120"), Decimal("80")]
    assert compute(vals, "sum") == Decimal("300")
    assert compute(vals, "avg") == Decimal("100")
    with pytest.raises(ValueError, match="숫자 셀이 없"):
        compute([], "sum")


def test_format_result_comma_rounding():
    assert format_result(Decimal("1234"), 0) == "1,234"
    # 사사오입 (은행가 반올림 아님)
    assert format_result(Decimal("2.5"), 0) == "3"
    assert format_result(Decimal("1234.567"), 1) == "1,234.6"


def test_parse_cells_spec():
    assert parse_cells_spec("1,1;2,1;3,1") == [(1, 1), (2, 1), (3, 1)]
    with pytest.raises(ValueError):
        parse_cells_spec("1;2")


@pytest.fixture()
def num_table(tmp_path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        t = doc.add_table(4, 2)
        t.set_cell_text(0, 0, "매출"); t.set_cell_text(0, 1, "100")
        t.set_cell_text(1, 0, "비용"); t.set_cell_text(1, 1, "120")
        t.set_cell_text(2, 0, "기타"); t.set_cell_text(2, 1, "80")
        t.set_cell_text(3, 0, "합계")  # (3,1) 비어 있음 — 합계 착지 대상
        path = str(tmp_path / "num.hwpx")
        doc.save_to_path(path)
    return path


def _cell(path, r, c):
    from hwpx.document import HwpxDocument
    from hwpx.tools import table_navigation as tn

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        t = tn._collect_document_tables(HwpxDocument.open(path))[0].table
        return (tn._cell_text(t, r, c) or "").strip()


def test_run_table_sum(num_table, tmp_path):
    from hwpx_kit.commands.table_calc import run_table_sum

    out = str(tmp_path / "o.hwpx")
    res = run_table_sum(num_table, table=0, cells=[(0, 1), (1, 1), (2, 1)],
                        into=(3, 1), out_path=out)
    assert res["result"] == "300" and res["counted"] == 3
    assert _cell(out, 3, 1) == "300"


def test_run_table_sum_skips_nonnumeric(num_table, tmp_path):
    from hwpx_kit.commands.table_calc import run_table_sum

    out = str(tmp_path / "o.hwpx")
    # (0,0)="매출"(비수치) 포함 → 건너뛰고 나머지 합
    res = run_table_sum(num_table, table=0, cells=[(0, 0), (0, 1), (1, 1)],
                        into=(3, 1), out_path=out)
    assert res["result"] == "220" and res["skipped"] == [[0, 0]]


def test_cli_table_sum(num_table, tmp_path, capsys):
    out = str(tmp_path / "o.hwpx")
    code = main(["table-sum", num_table, "--table", "0",
                 "--cells", "0,1;1,1;2,1", "--into", "3,1",
                 "--out", out, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and env["ok"] is True and env["data"]["result"] == "300"
    assert _cell(out, 3, 1) == "300"
