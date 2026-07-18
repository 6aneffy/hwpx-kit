"""table-build — 선언형 원샷 표 생성 + cell-align 정렬.

"이렇게 표 그려줘"용: 스펙 JSON 하나(크기·열폭·병합·헤더 스타일·내용·정렬)로
완성 표를 한 번에. 원시 도구 6단계 오케스트레이션의 실수·승인 비용 제거.
정렬은 엔진 ensure_paragraph_alignment + paraPrIDRef 참조 + dirty (실험 검증 2026-07-12).
"""
import json
import zipfile

import pytest

from hwpx_kit.cli import main
from hwpx_kit.commands.table_build import run_cell_align, run_table_build


@pytest.fixture()
def base_doc(tmp_path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        doc.add_paragraph("일정표 자리")
        path = str(tmp_path / "base.hwpx")
        doc.save_to_path(path)
    return path


def _table(path, index=0):
    from hwpx.document import HwpxDocument
    from hwpx.tools import table_navigation as tn

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        return tn._collect_document_tables(HwpxDocument.open(path))[index].table


SPEC = {
    "rows": 4,
    "cols": 3,
    "col_widths": [1, 2, 2],
    "header_rows": 1,
    "header_color": "#D9E5FF",
    "align": "center",
    "merges": ["1,0:2,0"],
    "cells": {
        "0,0": "시간", "0,1": "월", "0,2": "화",
        "1,0": "오전", "1,1": "이동", "1,2": "아침 식사",
        "3,0": "점심", "3,1": "점심 식사", "3,2": "점심 식사",
    },
}


def test_build_full_spec(base_doc, tmp_path):
    import zipfile

    out = str(tmp_path / "o.hwpx")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(SPEC, ensure_ascii=False), encoding="utf-8")
    result = run_table_build(base_doc, spec_path=str(spec_path),
                             at_text="일정표 자리", out_path=out)
    assert result["rows"] == 4 and result["cols"] == 3
    t = _table(out)
    # 내용
    from hwpx.tools import table_navigation as tn
    assert tn._cell_text(t, 0, 0).strip() == "시간"
    assert tn._cell_text(t, 1, 1).strip() == "이동"
    # 병합
    assert t.cell(1, 0).span == (2, 1)
    # 열폭 비율
    w = [t.cell(0, c).width for c in range(3)]
    assert w[0] < w[1]
    # 헤더 색 + 가운데 정렬이 header.xml에 등록
    hdr = zipfile.ZipFile(out).read("Contents/header.xml").decode("utf-8")
    assert "D9E5FF" in hdr.upper()
    assert 'horizontal="CENTER"' in hdr
    sec = zipfile.ZipFile(out).read("Contents/section0.xml").decode("utf-8")
    assert 'paraPrIDRef' in sec


def test_build_validates(base_doc, tmp_path):
    from hwpx_kit.commands.validate import run_validate

    out = str(tmp_path / "o.hwpx")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(SPEC, ensure_ascii=False), encoding="utf-8")
    run_table_build(base_doc, spec_path=str(spec_path),
                    at_text="일정표 자리", out_path=out)
    assert run_validate(out)["valid"] is True


def test_build_rejects_cell_out_of_range(base_doc, tmp_path):
    bad = dict(SPEC, cells={"9,9": "밖"})
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="범위"):
        run_table_build(base_doc, spec_path=str(spec_path),
                        at_text="일정표 자리", out_path=str(tmp_path / "o.hwpx"))


def test_build_rejects_widths_mismatch(base_doc, tmp_path):
    bad = dict(SPEC, col_widths=[1, 2])
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="열"):
        run_table_build(base_doc, spec_path=str(spec_path),
                        at_text="일정표 자리", out_path=str(tmp_path / "o.hwpx"))


def test_cell_align_existing_table(base_doc, tmp_path):
    import zipfile

    # 표 하나 만들어놓고 정렬만 바꾸기
    out1 = str(tmp_path / "o1.hwpx")
    spec = {"rows": 2, "cols": 2, "cells": {"0,0": "왼쪽글"}}
    sp = tmp_path / "s.json"
    sp.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    run_table_build(base_doc, spec_path=str(sp), at_text="일정표 자리", out_path=out1)

    out2 = str(tmp_path / "o2.hwpx")
    result = run_cell_align(out1, table=0, cell_range="0,0:1,1",
                            align="center", out_path=out2)
    assert result["aligned"] == 4
    hdr = zipfile.ZipFile(out2).read("Contents/header.xml").decode("utf-8")
    assert 'horizontal="CENTER"' in hdr


def test_cli_table_build(base_doc, tmp_path, capsys):
    out = str(tmp_path / "o.hwpx")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(SPEC, ensure_ascii=False), encoding="utf-8")
    code = main(["table-build", base_doc, "--spec", str(spec_path),
                 "--at-text", "일정표 자리", "--out", out, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and env["ok"] is True
    assert env["data"]["rows"] == 4


def test_table_build_fills_usable_page_width(base_doc, tmp_path):
    """생성 표는 가용 페이지 폭(용지폭-좌우여백)의 대부분을 채워야 한다 —
    좁은 기본 폭에 갇히면 열이 좁아 내용이 잘린다 (렌더 검증 실증 2026-07-15)."""
    import re

    out = str(tmp_path / "wide.hwpx")
    spec = {"rows": 4, "cols": 5, "col_widths": [2, 3, 3, 2, 2],
            "cells": {"1,2": "클로드코드 스킬 개론"}}
    sp = tmp_path / "spec.json"
    sp.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    run_table_build(base_doc, spec_path=str(sp), at_text="일정표 자리", out_path=out)

    sec = zipfile.ZipFile(out).read("Contents/section0.xml").decode("utf-8")
    pp = re.search(r'<hp:pagePr[^>]*\bwidth="(\d+)"', sec)
    mg = re.search(r'<hp:margin\b[^>]*\bleft="(\d+)"[^>]*\bright="(\d+)"', sec)
    page_w = int(pp.group(1))
    usable = page_w - int(mg.group(1)) - int(mg.group(2))

    # 표1 행1의 셀 폭 합 (lxml로 정확히)
    from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
    ad = HwpxEngineAdapter.open(out)

    def local(t):
        return t.rsplit("}", 1)[-1]

    tbls = [el for el in ad.section_elements()[0].iter() if el.tag.endswith("}tbl")]
    our = next(t for t in tbls
               if len([c for c in t if local(c.tag) == "tr"]) == 4)
    rows = [c for c in our if local(c.tag) == "tr"]
    row1 = rows[1]
    total = 0
    for tc in row1:
        if local(tc.tag) != "tc":
            continue
        sz = next((c for c in tc if local(c.tag) == "cellSz"), None)
        if sz is not None:
            total += int(sz.get("width", "0"))
    assert total >= usable * 0.9, f"표 폭 {total} < 가용폭 {usable}의 90%"
