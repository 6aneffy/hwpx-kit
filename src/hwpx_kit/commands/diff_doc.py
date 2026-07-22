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


def run_diff(old_path: str, new_path: str, out_path: str | None = None,
             changes_only: bool = True, header_color: str = "D9E2F3",
             title: str = "신구대조표") -> dict:
    """두 문서를 비교. out_path 있으면 신구대조표 hwpx 생성, 없으면 JSON
    리포트만 반환. 비교는 본문 최상위 문단 단위(difflib)."""
    old_paras = _body_paragraphs(old_path)
    new_paras = _body_paragraphs(new_path)
    blocks = diff_paragraphs(old_paras, new_paras)
    summary = diff_summary(blocks)
    src = [b for b in blocks if b["tag"] != "equal"] if changes_only else blocks

    if not out_path:
        return {"old": old_path, "new": new_path, "summary": summary,
                "changes_only": changes_only,
                "blocks": [{"tag": b["tag"], "old": b["old"], "new": b["new"]}
                           for b in src]}

    # 신구대조표 행: 헤더(현행|개정) + 변경(또는 전체) 블록
    rows_data = [["현행", "개정"]]
    for b in src:
        left = "\n".join(b["old"])
        right = "\n".join(b["new"])
        rows_data.append([left, right])
    if len(rows_data) == 1:  # 변경 없음
        rows_data.append(["(변경 없음)", "(변경 없음)"])

    n_rows = len(rows_data)
    cells = {}
    for r, row in enumerate(rows_data):
        for c, val in enumerate(row):
            cells[f"{r},{c}"] = val
    spec = {"rows": n_rows, "cols": 2, "header_rows": 1,
            "header_color": header_color, "cells": cells}

    import os
    import tempfile

    from hwpx.document import HwpxDocument

    # 빈 문서를 임시 경로에 만들고 → 어댑터로 열어 표 생성 → out_path 사본 저장.
    # (어댑터 save_copy는 원본 경로 덮어쓰기를 막으므로 임시 경로를 원본으로 둔다.)
    fd, tmp = tempfile.mkstemp(suffix=".hwpx")
    os.close(fd)
    try:
        with quiet_engine():
            doc = HwpxDocument.new()
            paras = list(doc.paragraphs)
            if paras:
                paras[0].text = title
                try:
                    doc.set_paragraph_format(paragraph_index=0, alignment="center")
                except Exception:
                    pass  # 정렬 실패해도 표 생성은 진행 (제목은 배분정렬로 남음)
            doc.save_to_path(tmp)
        ad = HwpxEngineAdapter.open(tmp)
        ad.build_table(spec, anchor_text=title)
        out = ad.save_copy(out_path)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    return {"old": old_path, "new": new_path, "out": out, "summary": summary,
            "changes_only": changes_only, "rows": n_rows}
