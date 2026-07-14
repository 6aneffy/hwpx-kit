"""문서 개체 명령 — 각주·하이퍼링크·책갈피·페이지 설정·도장·도형."""
import zipfile

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
from hwpx_kit.commands.doc_objects import run_note_add

FIXTURE = "tests/fixtures/real/seoul-report-brief.hwpx"


def _anchor_text():
    # 앵커는 본문 문단만 유효 (표 셀 문단은 _find_anchor_paragraph 검색 밖)
    ad = HwpxEngineAdapter.open(FIXTURE)
    return next(e["text"] for e in ad.outline()
                if len((e["text"] or "").strip()) >= 6)


def _section_xml(path):
    return zipfile.ZipFile(path).read("Contents/section0.xml").decode("utf-8")


def test_note_add_footnote_roundtrip(tmp_path):
    out = str(tmp_path / "note.hwpx")
    result = run_note_add(FIXTURE, at_text=_anchor_text(),
                          text="각주 내용입니다", kind="footnote", out_path=out)
    assert result["kind"] == "footnote"
    xml = _section_xml(out)
    assert "footNote" in xml
    assert "각주 내용입니다" in xml


def test_note_add_endnote_roundtrip(tmp_path):
    out = str(tmp_path / "note2.hwpx")
    run_note_add(FIXTURE, at_text=_anchor_text(),
                 text="미주 내용", kind="endnote", out_path=out)
    xml = _section_xml(out)
    assert "endNote" in xml


# ── 하이퍼링크·책갈피 ─────────────────────────────────────────

from hwpx_kit.commands.doc_objects import run_bookmark_add, run_link_add


def test_link_add_roundtrip(tmp_path):
    out = str(tmp_path / "link.hwpx")
    run_link_add(FIXTURE, at_text=_anchor_text(), url="https://www.korea.kr",
                 display="정책브리핑", out_path=out)
    xml = _section_xml(out)
    assert "korea.kr" in xml
    assert "정책브리핑" in xml


def test_bookmark_add_roundtrip(tmp_path):
    out = str(tmp_path / "bm.hwpx")
    run_bookmark_add(FIXTURE, at_text=_anchor_text(), name="결재란", out_path=out)
    assert "결재란" in _section_xml(out)


# ── 페이지 설정 ───────────────────────────────────────────────

from hwpx_kit.commands.doc_objects import run_page_setup


def test_page_setup_landscape(tmp_path):
    out = str(tmp_path / "land.hwpx")
    run_page_setup(FIXTURE, paper="A4", orientation="landscape",
                   margins=None, columns=None, column_gap_mm=None, out_path=out)
    xml = _section_xml(out)
    assert 'landscape="WIDELY"' in xml


def test_page_setup_margins(tmp_path):
    out = str(tmp_path / "margin.hwpx")
    run_page_setup(FIXTURE, paper=None, orientation=None,
                   margins={"left": 30.0, "right": 30.0, "top": 20.0, "bottom": 15.0},
                   columns=None, column_gap_mm=None, out_path=out)
    ad = HwpxEngineAdapter.open(out)
    sec = ad.section_elements()[0]
    margin = next(el for el in sec.iter() if el.tag.endswith("}margin"))
    assert margin.get("left") == str(round(30.0 * 7200 / 25.4))  # 엔진은 반올림


def test_page_setup_columns_lands_in_first_paragraph(tmp_path):
    out = str(tmp_path / "cols.hwpx")
    run_page_setup(FIXTURE, paper=None, orientation=None, margins=None,
                   columns=2, column_gap_mm=8.0, out_path=out)
    ad = HwpxEngineAdapter.open(out)
    sec = ad.section_elements()[0]
    first_p = next(el for el in sec.iter() if el.tag.endswith("}p"))
    assert any(el.tag.endswith("}colPr") for el in first_p.iter()), \
        "섹션 전체 다단은 첫 문단에 colPr이 있어야 함"
