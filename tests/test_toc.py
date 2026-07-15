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


def test_toc_entries_left_aligned_not_inheriting_anchor(tmp_path):
    """항목은 왼쪽 정렬 강제 — 앵커가 가운데 정렬(표지)이면 계단이 됨 (실캡처)."""
    out = str(tmp_path / "toc-left.hwpx")
    run_toc_add(TEMPLATE, at_text=_anchor_text(), out_path=out,
                title="목 차", pages="none", width=64)
    ad = HwpxEngineAdapter.open(out)
    header = ad.header_element()
    import re
    xml = _section_xml(out)
    # 항목 문단의 paraPrIDRef가 LEFT 정렬 paraPr을 가리켜야 한다
    entry_p = re.search(r'<hp:p ([^>]*)>(?:(?!</hp:p>).)*추진배경 및 목적', xml)
    assert entry_p is not None
    para_ref = re.search(r'paraPrIDRef="(\d+)"', entry_p.group(1)).group(1)
    para_pr = re.search(
        rf'<hh:paraPr id="{para_ref}"[^>]*>.*?</hh:paraPr>',
        zipfile.ZipFile(out).read("Contents/header.xml").decode("utf-8"), re.S)
    assert para_pr is not None
    assert 'horizontal="LEFT"' in para_pr.group(0)


def test_toc_add_own_page_sets_page_break(tmp_path):
    out = str(tmp_path / "toc-ownpage.hwpx")
    run_toc_add(TEMPLATE, at_text=_anchor_text(), out_path=out,
                title="목 차", pages="none", width=64, own_page=True)
    import re
    xml = _section_xml(out)
    title_p = re.search(r'<hp:p ([^>]*)>(?:(?!</hp:p>).)*목 차', xml)
    assert title_p is not None
    assert 'pageBreak="1"' in title_p.group(1)


def test_toc_own_page_breaks_after_block_too(tmp_path):
    """own_page면 목차 뒤 원래 내용도 새 쪽에서 — 표지 잔여물이 목차 쪽으로
    흘러드는 것 방지 (실캡처: 주최주관이 목차 페이지에 박힘)."""
    import re

    # 템플릿 표지 끝("2026. 00.") 뒤 첫 내용 문단은 {{주최주관}} —
    # 사이 빈 여백 문단들은 건너뛰고 그 문단에 쪽나눔이 걸려야 한다
    out = str(tmp_path / "toc-break-after.hwpx")
    run_toc_add(TEMPLATE, at_text="2026. 00.", out_path=out,
                title="목 차", pages="none", width=64, own_page=True)
    xml = _section_xml(out)
    fp = re.search(r'<hp:p ([^>]*)>(?:(?!</hp:p>).)*\{\{주최주관\}\}', xml, re.S)
    assert fp is not None
    # 엔진 모델 직렬화는 "true"로 씀 (page-break 명령과 동일 경로)
    assert re.search(r'pageBreak="(1|true)"', fp.group(1)), \
        "목차 뒤 첫 내용 문단에 쪽나눔 없음"


def test_toc_entries_use_body_font_not_anchor_font(tmp_path):
    """항목 글자는 바탕글 서식 — 앵커(표지 제목 등)의 크고 굵은 글자를
    물려받으면 목차 같지 않다 (실캡처)."""
    import re

    out = str(tmp_path / "toc-font.hwpx")
    run_toc_add(TEMPLATE, at_text=_anchor_text(), out_path=out,
                title="목 차", pages="none", width=64)
    header_xml = zipfile.ZipFile(out).read("Contents/header.xml").decode("utf-8")
    style0 = re.search(r'<hh:style id="0"[^>]*charPrIDRef="(\d+)"', header_xml)
    assert style0 is not None
    body_char = style0.group(1)
    xml = _section_xml(out)
    entry_p = re.search(r'<hp:p [^>]*>((?:(?!</hp:p>).)*추진배경 및 목적(?:(?!</hp:p>).)*)</hp:p>', xml)
    assert entry_p is not None
    assert f'charPrIDRef="{body_char}"' in entry_p.group(1)
