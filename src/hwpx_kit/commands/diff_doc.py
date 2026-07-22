"""diff 명령 — 두 hwpx 본문을 비교해 신구대조표(현행|개정)로 만든다.

공문 개정(법령·규정·지침)에서 쓰는 신구대조표 산출물이 목표.
비교는 순수 파이썬(difflib) — 한글 불필요. 문단 단위(본문 최상위)로 정렬한다.
표 셀 내부 diff·어절 단위 밑줄은 후속 백로그.
"""
from __future__ import annotations

import difflib

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
from hwpx_kit.output import quiet_engine


def diff_paragraphs(old: list[str], new: list[str]) -> list[dict]:
    """difflib으로 문단 정렬 → 블록 리스트.

    각 블록: {"tag": "equal|insert|delete|replace", "old": [...], "new": [...]}
    tag 의미: equal=동일, delete=현행에만(삭제), insert=개정에만(신설), replace=수정.
    """
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    blocks = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        blocks.append({"tag": tag, "old": old[i1:i2], "new": new[j1:j2]})
    return blocks


def diff_summary(blocks: list[dict]) -> dict:
    """블록 태그별 개수."""
    summary = {"equal": 0, "insert": 0, "delete": 0, "replace": 0}
    for b in blocks:
        summary[b["tag"]] = summary.get(b["tag"], 0) + 1
    return summary


def _body_paragraphs(path: str) -> list[str]:
    """문서 본문 최상위 문단 텍스트 (빈 문단 제외)."""
    ad = HwpxEngineAdapter.open(path)
    with quiet_engine():
        out = []
        for p in ad._doc.paragraphs:
            t = (p.text or "").strip()
            if t:
                out.append(t)
    return out
