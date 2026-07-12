"""header-footer 명령 — 머리말/꼬리말 텍스트·쪽번호 설정."""
from __future__ import annotations

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter


def run_header_footer(path: str, header: str | None, footer: str | None,
                      page_number: str | None, out_path: str) -> dict:
    ad = HwpxEngineAdapter.open(path)
    applied = ad.set_header_footer(header=header, footer=footer,
                                   page_number=page_number)
    out = ad.save_copy(out_path)
    return {"file": path, "out": out, "applied": applied}
