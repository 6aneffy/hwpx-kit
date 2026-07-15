"""toc — 목차 후보 탐지·목차 블록 삽입.

목차의 생명은 쪽번호다 — 조판 없이는 못 구하므로 한글 COM(Windows + 한글)이
있으면 실제 쪽번호를 조회해 채우고, 없으면 제목만 넣고 경고한다.
점선 채움은 관공서 관례인 '·' 리터럴(표시 폭 근사) — 폰트가 비례라 자리
맞춤은 근사치이며 정밀 정렬은 한글에서 탭으로 다듬는 것을 안내.
"""
from __future__ import annotations

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter

_MIN_DOTS = 3


def format_toc_line(text: str, page: int | None, *, width: int = 64) -> str:
    """'제목 ····· 쪽' 한 줄 — width는 표시 폭(반각 단위) 목표."""
    if page is None:
        return text
    w = HwpxEngineAdapter._display_width
    pg = str(page)
    dots = max(_MIN_DOTS, width - w(text) - w(pg) - 2)
    return f"{text} {'·' * dots} {pg}"


def run_toc(path: str) -> dict:
    """목차 후보 나열 (읽기 전용) — display(표시문구)/search(쪽번호 조회 키)."""
    ad = HwpxEngineAdapter.open(path)
    entries = ad.toc_entries()
    return {"file": path, "count": len(entries), "entries": entries}


def _lookup_pages_com(path: str, searches: list[str]) -> dict[str, int | None]:
    """한글 COM으로 각 문구의 실제 쪽번호 조회 (문서 순서 전방 탐색)."""
    import os

    from hwpx_kit.commands.convert import AUTO_ANSWER_MODE, _load_hwp_com
    from hwpx_kit.output import quiet_engine

    pages: dict[str, int | None] = {}
    with quiet_engine():
        hwp_cls = _load_hwp_com()
        hwp = hwp_cls(visible=False)
        try:
            if hasattr(hwp, "set_message_box_mode"):
                hwp.set_message_box_mode(AUTO_ANSWER_MODE)
            if not hwp.open(os.path.abspath(path)):
                raise RuntimeError(f"한글이 파일을 열지 못했습니다: {path}")
            for text in searches:
                try:
                    # Forward는 헤드리스에서 탐색 실패 (실증) — AllDoc만 동작.
                    # 장 제목은 문서 순서대로 조회하므로 커서가 자연히 전진한다
                    found = hwp.find(text, direction="AllDoc")
                    pages[text] = int(hwp.current_page) if found else None
                except Exception:
                    pages[text] = None
        finally:
            hwp.quit()
    return pages


def run_toc_add(path: str, *, at_text: str, out_path: str,
                title: str = "목 차", pages: str = "auto",
                width: int = 64, own_page: bool = False) -> dict:
    if pages not in ("auto", "com", "none"):
        raise ValueError(f"--pages는 auto/com/none 중 하나: {pages}")

    ad = HwpxEngineAdapter.open(path)
    entries = ad.toc_entries()
    if not entries:
        raise ValueError("목차 후보를 찾지 못했습니다 — 장 헤더 표(1행 번호+제목)나 "
                         "'Ⅰ.'/'제N장' 문단이 있어야 합니다.")

    warnings: list[str] = []
    page_map: dict[str, int | None] = {}
    if pages in ("auto", "com"):
        try:
            page_map = _lookup_pages_com(path, [e["search"] for e in entries])
        except RuntimeError as exc:
            if pages == "com":
                raise
            warnings.append(f"쪽번호 생략 — 한글 COM 불가 환경: {exc}")

    lines = [format_toc_line(e["display"], page_map.get(e["search"]), width=width)
             for e in entries]
    ad.insert_toc(at_text, lines, title=title, own_page=own_page)
    saved = ad.save_copy(out_path)

    resolved = sum(1 for v in page_map.values() if v is not None)
    result = {
        "out": saved,
        "entry_count": len(entries),
        "pages_resolved": resolved,
        "note": "점선 자리 맞춤은 근사치 — 정밀 정렬이 필요하면 한글에서 탭으로 다듬으세요",
    }
    if page_map and resolved < len(entries):
        warnings.append(f"쪽번호 미확인 항목 {len(entries) - resolved}개 — 제목만 표기")
    if warnings:
        result["warnings"] = warnings
    return result
