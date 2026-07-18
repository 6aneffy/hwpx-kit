"""image-add / header-footer — 이미지 삽입·머리말/꼬리말/쪽번호.

이미지는 엔진 add_image(바이너리 등록)+add_picture(문단 배치) 2단계 —
저장 왕복 생존과 원본 불변이 계약. mm 크기는 hwpx 단위로 환산된다.
"""
import json

import pytest

# 1x1 투명 PNG
PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63f8ffff3f0300050001ff5cccd90000000049454e44ae426082"
)

from hwpx_kit.cli import main
from hwpx_kit.commands.header_footer import run_header_footer
from hwpx_kit.commands.image_add import run_image_add


@pytest.fixture()
def doc_with_anchor(tmp_path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        doc.add_paragraph("신청서")
        doc.add_paragraph("서명: (인)")
        t = doc.add_table(2, 2)
        t.set_cell_text(0, 0, "사진")
        path = str(tmp_path / "form.hwpx")
        doc.save_to_path(path)
    return path


@pytest.fixture()
def png_file(tmp_path):
    p = tmp_path / "stamp.png"
    p.write_bytes(PNG_1PX)
    return str(p)


def _image_count(path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        return len(HwpxDocument.open(path).list_images())


def test_image_add_at_text(doc_with_anchor, png_file, tmp_path):
    out = str(tmp_path / "o.hwpx")
    result = run_image_add(doc_with_anchor, image_path=png_file,
                           at_text="서명: (인)", table=None, cell=None,
                           width_mm=20, height_mm=None, out_path=out)
    assert result["inserted"] is True
    assert _image_count(out) == 1
    assert _image_count(doc_with_anchor) == 0  # 원본 불변


def test_image_add_into_table_cell(doc_with_anchor, png_file, tmp_path):
    out = str(tmp_path / "o.hwpx")
    result = run_image_add(doc_with_anchor, image_path=png_file,
                           at_text=None, table=0, cell="1,0",
                           width_mm=25, height_mm=30, out_path=out)
    assert result["inserted"] is True
    assert _image_count(out) == 1


def test_image_add_validates_roundtrip(doc_with_anchor, png_file, tmp_path):
    from hwpx_kit.commands.validate import run_validate

    out = str(tmp_path / "o.hwpx")
    run_image_add(doc_with_anchor, image_path=png_file,
                  at_text="서명: (인)", table=None, cell=None,
                  width_mm=20, height_mm=None, out_path=out)
    assert run_validate(out)["valid"] is True


def test_image_add_rejects_missing_anchor(doc_with_anchor, png_file, tmp_path):
    with pytest.raises(ValueError, match="문단"):
        run_image_add(doc_with_anchor, image_path=png_file,
                      at_text="없는 문장", table=None, cell=None,
                      width_mm=20, height_mm=None, out_path=str(tmp_path / "o.hwpx"))


def test_image_add_rejects_bad_format(doc_with_anchor, tmp_path):
    bad = tmp_path / "note.txt"
    bad.write_text("텍스트", encoding="utf-8")
    with pytest.raises(ValueError, match="형식"):
        run_image_add(doc_with_anchor, image_path=str(bad),
                      at_text="서명: (인)", table=None, cell=None,
                      width_mm=20, height_mm=None, out_path=str(tmp_path / "o.hwpx"))


def test_cli_image_add(doc_with_anchor, png_file, tmp_path, capsys):
    out = str(tmp_path / "o.hwpx")
    code = main(["image-add", doc_with_anchor, "--image", png_file,
                 "--at-text", "서명: (인)", "--width-mm", "20",
                 "--out", out, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and env["ok"] is True
    assert _image_count(out) == 1


# ── header-footer ─────────────────────────────────────────────

def _headers_footers(path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        d = HwpxDocument.open(path)
        return d.headers


def test_header_footer_set(doc_with_anchor, tmp_path):
    out = str(tmp_path / "o.hwpx")
    result = run_header_footer(doc_with_anchor, header="문서관리번호 2026-01",
                               footer=None, page_number=None, out_path=out)
    assert "header" in result["applied"]
    # 재열기 후에도 구조 유효 + 헤더 존재 (증발 회귀 감지)
    from hwpx_kit.commands.validate import run_validate

    assert run_validate(out)["valid"] is True
    assert len(_headers_footers(out)) >= 1


def test_page_number_set(doc_with_anchor, tmp_path):
    out = str(tmp_path / "o.hwpx")
    result = run_header_footer(doc_with_anchor, header=None, footer=None,
                               page_number="center", out_path=out)
    assert "page_number" in result["applied"]


def test_header_footer_requires_one(doc_with_anchor, tmp_path):
    with pytest.raises(ValueError):
        run_header_footer(doc_with_anchor, header=None, footer=None,
                          page_number=None, out_path=str(tmp_path / "o.hwpx"))


def test_cli_header_footer(doc_with_anchor, tmp_path, capsys):
    out = str(tmp_path / "o.hwpx")
    code = main(["header-footer", doc_with_anchor, "--footer", "대외비",
                 "--page-number", "center", "--out", out, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and env["ok"] is True
    assert set(env["data"]["applied"]) == {"footer", "page_number"}


def test_footer_and_page_number_coexist(doc_with_anchor, tmp_path):
    """꼬리말 텍스트 + 쪽번호를 동시 지정하면 둘 다 살아야 —
    엔진 set_page_number가 footer를 통째 교체해 텍스트가 증발했다 (렌더 검증 실증)."""
    import zipfile

    out = str(tmp_path / "both.hwpx")
    run_header_footer(doc_with_anchor, header=None, footer="대외비",
                      page_number="center", out_path=out)
    sec = zipfile.ZipFile(out).read("Contents/section0.xml").decode("utf-8")
    assert "대외비" in sec, "꼬리말 텍스트 증발"
    # 쪽번호 필드도 존재 (autoNum/pageNum 계열)
    assert "PAGE" in sec.upper() or "autoNum" in sec, "쪽번호 필드 없음"
