"""render — 레이아웃 보존 미리보기.

두 엔진:
- kordoc: SVG (한컴 프리, 우리 생성 파일엔 reflow 근사 — 대략 확인용)
- com: 한글 COM으로 PDF (진짜 조판, Windows+한글 필요) — 자가 검증의 근거.
  에이전트가 이 PDF를 Read로 열어 페이지별 육안 검사한다.
"""
from __future__ import annotations

import os

from hwpx_kit.adapter.kordoc_engine import KordocAdapter
# COM 로더·자동응답 모드는 convert 계층 재사용 (중복 COM 코드 금지)
from hwpx_kit.commands.convert import AUTO_ANSWER_MODE, _load_hwp_com
from hwpx_kit.output import quiet_engine

_ENGINES = ("auto", "com", "kordoc")


def _com_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("pyhwpx") is not None


def _render_com_pdf(src: str, out: str) -> str:
    """한글 COM으로 PDF 렌더 — 원본 hwpx는 열기만, 저장은 out(PDF)뿐."""
    src_abs = os.path.abspath(src)
    out_abs = os.path.abspath(out)
    with quiet_engine():
        hwp_cls = _load_hwp_com()
        hwp = hwp_cls(visible=False)
        try:
            if hasattr(hwp, "set_message_box_mode"):
                hwp.set_message_box_mode(AUTO_ANSWER_MODE)
            if not hwp.open(src_abs):
                raise RuntimeError(f"한글이 파일을 열지 못했습니다: {src_abs}")
            if not hwp.save_as(out_abs, format="PDF"):
                raise RuntimeError(f"PDF 렌더에 실패했습니다: {out_abs}")
        finally:
            hwp.quit()
    return out_abs


def run_render(path: str, out_path: str | None = None,
               engine: str = "auto") -> dict:
    if engine not in _ENGINES:
        raise ValueError(f"engine은 {'/'.join(_ENGINES)} 중 하나: {engine}")

    resolved = engine
    if resolved == "auto":
        # 출력 확장자가 의도를 결정 — .svg는 kordoc, .pdf는 com.
        # 확장자 없으면 한글 있을 때 com PDF(정확) 우선, 없으면 kordoc SVG.
        if out_path and out_path.lower().endswith(".svg"):
            resolved = "kordoc"
        elif out_path and out_path.lower().endswith(".pdf"):
            resolved = "com"
        else:
            resolved = "com" if _com_available() else "kordoc"

    if resolved == "com":
        out = out_path or os.path.splitext(path)[0] + ".pdf"
        if not out.lower().endswith(".pdf"):
            raise ValueError("com 엔진은 .pdf 출력만 지원합니다 (한글이 PDF로 렌더).")
        saved = _render_com_pdf(path, out)
        return {"file": os.path.abspath(path), "out": saved, "engine": "com"}

    out = out_path or os.path.splitext(path)[0] + ".svg"
    saved = KordocAdapter.render_svg(path, out)
    return {"file": os.path.abspath(path), "out": saved, "engine": "kordoc"}
