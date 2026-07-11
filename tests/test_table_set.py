"""table-set — 좌표 지정 셀 쓰기 (table-clear의 짝).

비운 셀에는 라벨이 없어 fill의 table: 키로 못 쓴다 — 전면 교체 후
새 항목(예산 항목명 등)을 앉힐 때 좌표로 직접 기입.
"""
import json

import pytest

from hwpx_kit.cli import main
from hwpx_kit.commands.table_set import parse_assignments, run_table_set


@pytest.fixture()
def blank_doc(tmp_path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        doc.add_table(3, 2)
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


def test_parse_assignments():
    assert parse_assignments(["1,0=강사료", "2,3=10회"]) == [(1, 0, "강사료"), (2, 3, "10회")]
    assert parse_assignments(["0,1=a=b"]) == [(0, 1, "a=b")]  # 값 속 = 허용
    with pytest.raises(ValueError):
        parse_assignments(["1=x"])


def test_set_cells(blank_doc, tmp_path):
    out = str(tmp_path / "o.hwpx")
    result = run_table_set(blank_doc, table=0,
                           assignments=[(0, 0, "구분"), (1, 0, "강사료"), (1, 1, "10회")],
                           out_path=out)
    texts = _cell_texts(out)
    assert texts[(0, 0)] == "구분"
    assert texts[(1, 0)] == "강사료"
    assert texts[(1, 1)] == "10회"
    assert result["set_cells"] == 3
    assert _cell_texts(blank_doc)[(0, 0)] == ""  # 원본 불변


def test_rejects_bad_coords(blank_doc, tmp_path):
    out = str(tmp_path / "o.hwpx")
    with pytest.raises(ValueError):
        run_table_set(blank_doc, table=0, assignments=[(9, 0, "x")], out_path=out)


def test_cli_table_set(blank_doc, tmp_path, capsys):
    out = str(tmp_path / "o.hwpx")
    code = main(["table-set", blank_doc, "--table", "0",
                 "--set", "1,0=강사료", "--set", "1,1=10회", "--out", out, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0
    assert env["data"]["set_cells"] == 2
    assert _cell_texts(out)[(1, 0)] == "강사료"


def test_table_set_with_data_file(blank_doc, tmp_path):
    """--data JSON 파일 입력 — 셀 대량 기입 시 명령 길이 한계(셸 965B) 회피.

    실사용 테스트(2026-07-10)에서 커리큘럼 21행 기입이 --set 40개로
    2.3KB 명령이 되어 셸 파서가 깨진 사고의 근본 해결.
    """
    import json as _json

    data_file = tmp_path / "cells.json"
    data_file.write_text(_json.dumps({"0,0": "구분", "1,0": "강사료", "1,1": "10회"},
                                     ensure_ascii=False), encoding="utf-8")
    out = str(tmp_path / "o.hwpx")
    code = main(["table-set", blank_doc, "--table", "0",
                 "--data", str(data_file), "--out", out, "--json"])
    assert code == 0
    texts = _cell_texts(out)
    assert texts[(0, 0)] == "구분" and texts[(1, 0)] == "강사료" and texts[(1, 1)] == "10회"


def test_table_set_requires_set_or_data(blank_doc, tmp_path, capsys):
    code = main(["table-set", blank_doc, "--table", "0",
                 "--out", str(tmp_path / "o.hwpx"), "--json"])
    assert code == 1
