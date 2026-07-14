"""open-check — 한글 실열림 게이트."""
import importlib.util

import pytest

from hwpx_kit.commands.open_check import run_open_check

_HAS_COM = importlib.util.find_spec("pyhwpx") is not None


def test_open_check_error_without_com(monkeypatch, tmp_path):
    import hwpx_kit.commands.open_check as oc

    def boom():
        raise RuntimeError("hwp 변환에는 Windows + 한글(한컴오피스) + pyhwpx가 필요합니다.")

    monkeypatch.setattr(oc, "_load_hwp_com", boom)
    f = tmp_path / "x.hwpx"
    f.write_bytes(b"x")
    with pytest.raises(RuntimeError, match="한글"):
        run_open_check(str(f))


@pytest.mark.skipif(not _HAS_COM, reason="pyhwpx/한글 COM 없는 환경")
def test_open_check_real_fixture_opens():
    """정상 픽스처는 열린다. 느림(한글 구동)."""
    result = run_open_check("tests/fixtures/real/seoul-report-brief.hwpx")
    assert result["opens"] is True


@pytest.mark.skipif(not _HAS_COM, reason="pyhwpx/한글 COM 없는 환경")
def test_open_check_rejects_broken_shape(tmp_path):
    """hp: 네임스페이스 기하점(한글 거부 실증 패턴)을 열림 실패로 판정."""
    from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter

    ad = HwpxEngineAdapter.open("tests/fixtures/real/seoul-report-brief.hwpx")
    anchor = next(e["text"] for e in ad.outline()
                  if len((e["text"] or "").strip()) >= 6)
    ad.add_shape(at_text=anchor, shape="line", width_mm=100.0, height_mm=0.0)
    # 고의 파손: 수정된 기하점을 hp:로 되돌림 (0.9.0 버그 재현)
    sec = ad.section_elements()[0]
    hp = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
    line = [el for el in sec.iter() if el.tag.endswith("}line")][-1]
    for ch in line:
        local = ch.tag.rsplit("}", 1)[-1]
        if local in ("startPt", "endPt"):
            ch.tag = hp + local
    ad._mark_sections_dirty()
    broken = str(tmp_path / "broken.hwpx")
    ad.save_copy(broken)

    result = run_open_check(broken)
    assert result["opens"] is False
