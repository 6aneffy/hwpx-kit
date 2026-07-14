"""미리보기(PrvText) 잔여물 — 편집 후 저장본의 미리보기 최신화 + 검사."""
import zipfile

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
from hwpx_kit.commands.fill import run_fill
from hwpx_kit.inspect_structure import check_preview

FIXTURE = "tests/fixtures/real/seoul-report-brief.hwpx"


def _first_long_paragraph_text(ad):
    for p in ad._iter_all_paragraphs():
        t = (p.text or "").strip()
        if len(t) >= 6:
            return t
    raise AssertionError("픽스처에 6자 이상 문단 필요")


def test_save_copy_refreshes_prvtext(tmp_path):
    ad = HwpxEngineAdapter.open(FIXTURE)
    target = _first_long_paragraph_text(ad)
    out = str(tmp_path / "edited.hwpx")
    run_fill(FIXTURE, {f"text:{target}": "완전히새로운문구팔이구공"}, out)

    prv = zipfile.ZipFile(out).read("Preview/PrvText.txt")
    decoded = prv.decode("utf-16")  # BOM 포함 UTF-16LE로 재생성됨
    assert "완전히새로운문구팔이구공" in decoded
    assert target not in decoded


def test_check_preview_tolerates_unreadable_encoding():
    # 원본 픽스처의 PrvText는 인코딩 불명 — 판독 불가면 침묵(오탐 방지)
    ad = HwpxEngineAdapter.open(FIXTURE)
    assert isinstance(check_preview(ad), list)


def test_check_preview_clean_after_refresh(tmp_path):
    ad = HwpxEngineAdapter.open(FIXTURE)
    out = str(tmp_path / "copy.hwpx")
    ad.save_copy(out)
    ad2 = HwpxEngineAdapter.open(out)
    assert check_preview(ad2) == []


def test_check_preview_detects_mismatch(tmp_path):
    ad = HwpxEngineAdapter.open(FIXTURE)
    out = str(tmp_path / "copy.hwpx")
    ad.save_copy(out)
    ad2 = HwpxEngineAdapter.open(out)
    payload = "﻿" + "본문에 없는 지워진 주민번호 구간 완전히 다른 텍스트"
    ad2._doc.package.set_part("Preview/PrvText.txt", payload.encode("utf-16-le"))
    issues = check_preview(ad2)
    assert any(i["code"] == "preview_stale" for i in issues)
