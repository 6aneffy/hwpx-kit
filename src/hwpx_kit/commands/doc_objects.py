"""문서 개체 명령 진입점 — 각주·링크·책갈피·페이지 설정·도장·도형.

전부 어댑터 경유 (엔진 직접 import 금지 원칙 유지).
"""
from __future__ import annotations

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter


def run_note_add(path: str, *, at_text: str, text: str, kind: str,
                 out_path: str) -> dict:
    ad = HwpxEngineAdapter.open(path)
    ad.add_note(at_text, text, kind)
    saved = ad.save_copy(out_path)
    return {"out": saved, "kind": kind}


def run_link_add(path: str, *, at_text: str, url: str, display: str,
                 out_path: str) -> dict:
    ad = HwpxEngineAdapter.open(path)
    ad.add_hyperlink(at_text, url, display)
    saved = ad.save_copy(out_path)
    return {"out": saved, "url": url}


def run_bookmark_add(path: str, *, at_text: str, name: str, out_path: str) -> dict:
    ad = HwpxEngineAdapter.open(path)
    ad.add_bookmark(at_text, name)
    saved = ad.save_copy(out_path)
    return {"out": saved, "name": name}


def run_page_setup(path: str, *, paper: str | None, orientation: str | None,
                   margins: dict[str, float] | None, columns: int | None,
                   column_gap_mm: float | None, out_path: str) -> dict:
    if not any([paper, orientation, margins, columns]):
        raise ValueError("--paper/--orientation/--margins/--columns 중 하나는 지정하세요.")
    ad = HwpxEngineAdapter.open(path)
    result = ad.page_setup(paper=paper, orientation=orientation, margins=margins,
                           columns=columns, column_gap_mm=column_gap_mm)
    saved = ad.save_copy(out_path)
    return {"out": saved, "applied": result}
