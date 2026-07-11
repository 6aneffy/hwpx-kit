"""page-break — 문단/표 앞 쪽나눔 (hp:p pageBreak 속성, 실증 2026-07-10).

끼워넣은 장 헤더가 페이지 중간에 떨어지는 문제의 해결: 장 헤더 표가 든
문단에 pageBreak=1을 심으면 새 쪽에서 시작한다.
"""
import json

import pytest

from hwpx_kit.cli import main
from hwpx_kit.commands.page_break import run_page_break


@pytest.fixture()
def doc(tmp_path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        d = HwpxDocument.new()
        d.add_paragraph("일장 내용")
        d.add_paragraph("새 장 시작 문단")
        t = d.add_table(1, 3)
        t.set_cell_text(0, 2, "장제목")
        path = str(tmp_path / "src.hwpx")
        d.save_to_path(path)
    return path


def _page_break_flags(path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        d = HwpxDocument.open(path)
        return {(p.text or "").strip(): p.element.get("pageBreak") for p in d.paragraphs}


def test_break_at_text(doc, tmp_path):
    out = str(tmp_path / "o.hwpx")
    result = run_page_break(doc, at_text="새 장 시작 문단", table=None, out_path=out)
    flags = _page_break_flags(out)
    assert flags["새 장 시작 문단"] in ("1", "true")
    assert flags["일장 내용"] in ("0", None)
    assert result["applied"] == 1


def test_break_before_table(doc, tmp_path):
    """표 인덱스로 지정 — 표가 앵커된 문단(텍스트 없음)에 쪽나눔."""
    out = str(tmp_path / "o.hwpx")
    result = run_page_break(doc, at_text=None, table=0, out_path=out)
    assert result["applied"] == 1
    # 표 문단의 pageBreak 확인
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        d = HwpxDocument.open(out)
        table_paras = [p for p in d.paragraphs if list(p.tables)]
        assert table_paras and table_paras[0].element.get("pageBreak") in ("1", "true")


def test_requires_exactly_one_target(doc, tmp_path):
    with pytest.raises(ValueError):
        run_page_break(doc, at_text=None, table=None, out_path=str(tmp_path / "o.hwpx"))
    with pytest.raises(ValueError):
        run_page_break(doc, at_text="x", table=0, out_path=str(tmp_path / "o.hwpx"))


def test_cli_page_break(doc, tmp_path, capsys):
    out = str(tmp_path / "o.hwpx")
    code = main(["page-break", doc, "--table", "0", "--out", out, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and env["ok"] is True
