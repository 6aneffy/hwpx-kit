"""hwpx → 타 형식 내보내기 (현재 docx).

Windows + 한글(한컴오피스) COM 경유 — convert와 같은 제약.
한글 SaveAs의 워드 형식 문자열은 "OOXML"이다 ("DOCX"/"MSWORD"는 조용히
실패 — 2026-07-10 실탐침). 다른 형식 저장 시 경고 팝업이 뜰 수 있는데
visible=False라 보이지 않아 무한대기가 됨 — 메시지박스 자동응답 필수.
"""
from __future__ import annotations

import os

from hwpx_kit.commands import convert as _convert
from hwpx_kit.commands.convert import AUTO_ANSWER_MODE
from hwpx_kit.output import quiet_engine

# to → (한글 SaveAs format 문자열, 확장자)
_FORMATS = {"docx": ("OOXML", ".docx")}


def run_export(path: str, to: str = "docx", out_path: str | None = None) -> dict:
    if not path.lower().endswith(".hwpx"):
        raise ValueError("export 입력은 .hwpx 파일이어야 합니다 (.hwp는 먼저 convert)")
    if to not in _FORMATS:
        raise ValueError(f"지원 형식: {', '.join(_FORMATS)} (요청: {to})")
    save_format, ext = _FORMATS[to]

    src = os.path.abspath(path)
    out = os.path.abspath(out_path) if out_path else src[: -len(".hwpx")] + ext
    if out == src:
        raise ValueError("출력 경로가 원본과 같습니다.")

    with quiet_engine():
        hwp_cls = _convert._load_hwp_com()
        hwp = hwp_cls(visible=False)
        try:
            if hasattr(hwp, "set_message_box_mode"):
                hwp.set_message_box_mode(AUTO_ANSWER_MODE)
            if not hwp.open(src):
                raise RuntimeError(f"한글이 파일을 열지 못했습니다: {src}")
            if not hwp.save_as(out, format=save_format):
                raise RuntimeError(f"{to} 저장에 실패했습니다: {out}")
        finally:
            hwp.quit()
    return {"file": src, "out": out, "format": to}
