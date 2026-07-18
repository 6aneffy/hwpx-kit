"""render COM PDF 엔진 — 한글 실물 렌더 (자가 검증용)."""
import importlib.util

import pytest

from hwpx_kit.commands.render import run_render

_HAS_COM = importlib.util.find_spec("pyhwpx") is not None
FIXTURE = "tests/fixtures/real/seoul-report-brief.hwpx"


def test_engine_com_requires_pdf_extension(tmp_path):
    """engine=com은 .pdf 출력만 — COM 없이도 가드가 먼저 걸린다."""
    with pytest.raises(ValueError, match="pdf"):
        run_render(FIXTURE, out_path=str(tmp_path / "x.svg"), engine="com")


def test_unknown_engine_rejected(tmp_path):
    with pytest.raises(ValueError, match="engine"):
        run_render(FIXTURE, out_path=str(tmp_path / "x.pdf"), engine="nope")


def test_engine_com_without_pyhwpx_errors(tmp_path, monkeypatch):
    """한글 COM 불가 환경에서 engine=com은 설치 안내 오류."""
    import hwpx_kit.commands.render as r

    def boom():
        raise RuntimeError("hwp 변환에는 Windows + 한글(한컴오피스) + pyhwpx가 필요합니다.")

    monkeypatch.setattr(r, "_load_hwp_com", boom)
    with pytest.raises(RuntimeError, match="한글"):
        run_render(FIXTURE, out_path=str(tmp_path / "x.pdf"), engine="com")


@pytest.mark.skipif(not _HAS_COM, reason="pyhwpx/한글 COM 없는 환경")
def test_engine_com_renders_real_pdf(tmp_path):
    """실제 한글 COM으로 PDF 렌더 — 파일 생성·PDF 매직바이트·크기>0. 느림."""
    out = str(tmp_path / "render.pdf")
    result = run_render(FIXTURE, out_path=out, engine="com")
    assert result["engine"] == "com"
    import os

    assert os.path.exists(out)
    with open(out, "rb") as f:
        assert f.read(5) == b"%PDF-"
    assert os.path.getsize(out) > 1000
