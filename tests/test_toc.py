"""toc — 목차 후보 탐지·서식·삽입 + 한글 COM 쪽번호."""
import importlib.util
import zipfile

import pytest

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
from hwpx_kit.commands.toc import format_toc_line, run_toc, run_toc_add

TEMPLATE = "templates/Default_Template.hwpx"

_HAS_COM = importlib.util.find_spec("pyhwpx") is not None


def _anchor_text():
    ad = HwpxEngineAdapter.open(TEMPLATE)
    return next(e["text"] for e in ad.outline()
                if len((e["text"] or "").strip()) >= 4)


def _section_xml(path):
    return zipfile.ZipFile(path).read("Contents/section0.xml").decode("utf-8")


# ── 서식 (순수) ───────────────────────────────────────────────


def test_format_toc_line_pads_dots_to_width():
    line = format_toc_line("Ⅰ. 추진배경", 3, width=40)
    assert line.startswith("Ⅰ. 추진배경ㅤ".replace("ㅤ", " ")) or line.startswith("Ⅰ. 추진배경 ")
    assert line.endswith(" 3")
    assert "···" in line


def test_format_toc_line_without_page():
    assert format_toc_line("Ⅰ. 추진배경", None) == "Ⅰ. 추진배경"


def test_format_toc_line_min_dots_when_long_title():
    line = format_toc_line("아주" * 40, 12, width=40)
    assert "···" in line  # 최소 점 3개는 보장
    assert line.endswith(" 12")


# ── 후보 탐지 ─────────────────────────────────────────────────


def test_toc_entries_detects_chapter_tables():
    result = run_toc(TEMPLATE)
    displays = [e["display"] for e in result["entries"]]
    assert any("추진배경 및 목적" in d for d in displays)
    # 장 번호가 접두로 붙는다
    assert any(d.startswith("1.") or d.startswith("1 ") for d in displays
               if "추진배경" in d)
    # 검색 키는 제목 원문 (셀에 번호와 제목이 분리돼 있으므로)
    searches = [e["search"] for e in result["entries"]]
    assert "추진배경 및 목적" in searches


# ── 삽입 ─────────────────────────────────────────────────────


def test_toc_add_inserts_title_and_entries(tmp_path):
    out = str(tmp_path / "toc.hwpx")
    result = run_toc_add(TEMPLATE, at_text=_anchor_text(), out_path=out,
                         title="목 차", pages="none", width=64)
    assert result["entry_count"] >= 1
    xml = _section_xml(out)
    assert "목 차" in xml
    assert "추진배경 및 목적" in xml


def test_toc_add_none_pages_has_no_dots(tmp_path):
    out = str(tmp_path / "toc2.hwpx")
    run_toc_add(TEMPLATE, at_text=_anchor_text(), out_path=out,
                title="목 차", pages="none", width=64)
    ad = HwpxEngineAdapter.open(out)
    toc_paras = [p for p in ad._iter_all_paragraphs()
                 if "추진배경 및 목적" in (p.text or "") and "···" in (p.text or "")]
    assert toc_paras == []  # 쪽번호 없으면 점선도 없음


# ── 한글 COM 쪽번호 (느림) ────────────────────────────────────


@pytest.mark.skipif(not _HAS_COM, reason="pyhwpx/한글 COM 없는 환경")
def test_toc_add_com_pages_and_opens(tmp_path):
    from hwpx_kit.commands.open_check import run_open_check

    out = str(tmp_path / "toc-com.hwpx")
    result = run_toc_add(TEMPLATE, at_text=_anchor_text(), out_path=out,
                         title="목 차", pages="com", width=64)
    assert result["pages_resolved"] >= 1
    xml = _section_xml(out)
    assert "···" in xml  # 쪽번호가 채워졌으면 점선 존재
    assert run_open_check(out)["opens"] is True
