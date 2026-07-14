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
