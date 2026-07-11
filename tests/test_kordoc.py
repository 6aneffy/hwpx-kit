"""kordoc 엔진 래핑 테스트 — kordoc 미설치 환경에서는 전부 skip."""
from pathlib import Path

import pytest

from hwpx_kit.adapter.kordoc_engine import kordoc_available
from hwpx_kit.commands.generate import run_generate
from hwpx_kit.commands.read import run_read
from hwpx_kit.commands.render import run_render
from hwpx_kit.commands.validate import run_validate

REAL = Path(__file__).parent / "fixtures" / "real"

pytestmark = pytest.mark.skipif(not kordoc_available(), reason="kordoc 미설치")


def test_read_legacy_hwp_without_hancom():
    """레거시 .hwp를 한글 프로그램 없이 읽는다 (kordoc 라우팅)."""
    data = run_read(str(REAL / "legacy-sample.hwp"))
    assert data["format"] == "md"
    assert "레거시 테스트 문서" in data["content"]
    assert "kordoc가 한글 없이 읽어야 하는 내용" in data["content"]


def test_read_hwpx_still_uses_python_hwpx(marker_doc):
    """hwpx는 여전히 python-hwpx 경로 — text 형식 지원이 그 증거."""
    data = run_read(marker_doc, fmt="text")
    assert data["format"] == "text"
    assert "출장 신청서" in data["content"]


def test_render_svg(tmp_path):
    out = str(tmp_path / "preview.svg")
    result = run_render(str(REAL / "seoul-body.hwpx"), out_path=out)
    svg = Path(result["out"]).read_text(encoding="utf-8", errors="replace")
    assert svg.lstrip().startswith("<")
    assert "<svg" in svg[:2000]


def test_render_reflow_fallback_for_non_hancom_files(marker_doc, tmp_path):
    """python-hwpx로 만든 파일은 조판 캐시가 없다 — reflow 폴백으로 렌더돼야 함."""
    out = str(tmp_path / "preview.svg")
    result = run_render(marker_doc, out_path=out)
    assert Path(result["out"]).stat().st_size > 0


def test_generate_hwpx_from_markdown(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text(
        "# 교육 결과 보고\n\n## 개요\n\nAI 문서자동화 교육을 완료하였다.\n",
        encoding="utf-8",
    )
    out = str(tmp_path / "doc.hwpx")
    result = run_generate(str(md), out)
    assert Path(result["out"]).exists()
    assert run_validate(result["out"])["valid"] is True
    content = run_read(result["out"], fmt="text")["content"]
    assert "교육 결과 보고" in content


def test_generate_rejects_non_markdown(tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        run_generate(str(f), str(tmp_path / "o.hwpx"))
