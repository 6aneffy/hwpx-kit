"""inspect 구조 검사 — 한글 열림·조판 위험의 XML 계층 정적 탐지.

inspect_rules(텍스트 정규식)와 병렬 — 이쪽은 문서 XML을 본다.
validate(스키마 well-formed)가 통과해도 한글이 조판을 깨뜨리는 패턴들:
유령 셀, 표 좌표 불일치, 댕글링 스타일 참조, secPr 소실.
issue 형식은 inspect_rules와 동일: {"check","code","message","context"}.
"""
from __future__ import annotations


def _issue(code: str, message: str, context: str = "") -> dict:
    return {"check": "structure", "code": code, "message": message, "context": context}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(el, suffix: str):
    return next((ch for ch in el if ch.tag.endswith("}" + suffix)), None)


def _check_ghost_cells(sections) -> list[dict]:
    issues = []
    for si, sec in enumerate(sections):
        for tc in sec.iter():
            if not tc.tag.endswith("}tc"):
                continue
            sz = _child(tc, "cellSz")
            if sz is not None and sz.get("width") == "0" and sz.get("height") == "0":
                addr = _child(tc, "cellAddr")
                pos = (f"({addr.get('rowAddr')},{addr.get('colAddr')})"
                       if addr is not None else "?")
                issues.append(_issue(
                    "ghost_cell",
                    "크기 0 유령 셀 — 한글 조판이 최소 폭을 부여해 뒤 셀이 표 밖으로 밀림",
                    f"section {si} 셀 {pos}"))
    return issues


def _check_tables(sections) -> list[dict]:
    issues = []
    for si, sec in enumerate(sections):
        for ti, tbl in enumerate(el for el in sec.iter() if el.tag.endswith("}tbl")):
            trs = [c for c in tbl if c.tag.endswith("}tr")]
            declared = tbl.get("rowCnt")
            if declared is not None and declared != str(len(trs)):
                issues.append(_issue(
                    "table_rowcnt_mismatch",
                    f"표 rowCnt={declared} vs 실제 행 {len(trs)}개 — 행 조작 잔재, 한글이 표를 오해석",
                    f"section {si} 표 {ti}"))
            seen: set[tuple[str, str]] = set()
            for tr in trs:
                for tc in tr:
                    if not tc.tag.endswith("}tc"):
                        continue
                    addr = _child(tc, "cellAddr")
                    if addr is None:
                        continue
                    key = (addr.get("rowAddr", "?"), addr.get("colAddr", "?"))
                    if key in seen:
                        issues.append(_issue(
                            "table_dup_celladdr",
                            f"셀 좌표 중복 {key} — 같은 자리에 셀 2개, 조판 붕괴 위험",
                            f"section {si} 표 {ti}"))
                    seen.add(key)
    return issues


_REF_ATTRS = {
    "charPrIDRef": "charPr",
    "paraPrIDRef": "paraPr",
    "borderFillIDRef": "borderFill",
}


def _check_dangling_refs(sections, header) -> list[dict]:
    ids: dict[str, set[str]] = {suffix: set() for suffix in _REF_ATTRS.values()}
    for el in header.iter():
        suffix = _local(el.tag)
        if suffix in ids:
            el_id = el.get("id")
            if el_id is not None:
                ids[suffix].add(el_id)
    issues = []
    reported: set[tuple[str, str]] = set()
    for si, sec in enumerate(sections):
        for el in sec.iter():
            for attr, suffix in _REF_ATTRS.items():
                ref = el.get(attr)
                if ref is None or ref in ids[suffix] or (attr, ref) in reported:
                    continue
                reported.add((attr, ref))
                issues.append(_issue(
                    "dangling_ref",
                    f"{attr}={ref}가 header에 없음 — 한글이 기본 서식으로 대체하거나 열기 거부",
                    f"section {si} <{_local(el.tag)}>"))
    return issues


def _check_secpr(sections) -> list[dict]:
    issues = []
    for si, sec in enumerate(sections):
        first_p = next((el for el in sec.iter() if el.tag.endswith("}p")), None)
        if first_p is None:
            continue
        if not any(el.tag.endswith("}secPr") for el in first_p.iter()):
            issues.append(_issue(
                "missing_secpr",
                "섹션 첫 문단에 secPr 없음 — 용지/여백 정보 소실, 한글 열림 실패 위험",
                f"section {si}"))
    return issues


def check_structure(ad) -> list[dict]:
    """어댑터를 받아 구조 이슈 목록 반환. 전부 결정론 검사."""
    sections = ad.section_elements()
    header = ad.header_element()
    issues: list[dict] = []
    issues += _check_ghost_cells(sections)
    issues += _check_tables(sections)
    issues += _check_dangling_refs(sections, header)
    issues += _check_secpr(sections)
    return issues


import re as _re


def _norm_ws(s: str) -> str:
    return _re.sub(r"\s+", " ", s).strip()


def check_preview(ad) -> list[dict]:
    """미리보기 텍스트가 본문과 다르면 잔여물로 판정.

    편집·삭제 이전 내용이 PrvText에 살아남는 패턴 — 판독 불가(인코딩 불명)는
    오탐 방지를 위해 침묵한다.
    """
    prv = ad.preview_text()
    if not prv:
        return []
    head = _norm_ws(prv.lstrip("﻿"))[:120]
    if len(head) < 10:
        return []
    body = _norm_ws(ad.export_text())
    if head in body:
        return []
    return [{
        "check": "preview",
        "code": "preview_stale",
        "message": "미리보기(PrvText)가 본문과 다름 — 편집 전 내용 잔존 (탐색기 미리보기로 노출될 수 있음)",
        "context": head[:60],
    }]


import unicodedata as _ud

# 넘침 추정 상수 — 10pt 기준 근사 (1pt=100 hwpunit): 전각 폭 ≈1000, 줄높이 ≈1700
_CHAR_UNIT = 1000
_LINE_UNIT = 1700
_CELL_PAD = 1100      # 좌우 여백 합 근사
# cellSz height는 최소 높이(한글이 자동 확장)라 비율 하나로는 과탐 —
# 실측(공개 서식 4종): 정상 최악 (8줄, 비율0.5)·(2줄, 비율3.4). 둘 다 넘어야 경고
_OVERFLOW_MIN_LINES = 4
_OVERFLOW_RATIO = 3.0
_MIN_ROW_UNIT = 900   # 이보다 낮은 행높이에 내용이 있으면 잘림 위험


def _text_units(s: str) -> int:
    return sum(_CHAR_UNIT if _ud.east_asian_width(ch) in ("W", "F")
               else _CHAR_UNIT // 2 for ch in s)


def check_layout(ad) -> list[dict]:
    """셀 넘침·과소 행높이 추정 — 휴리스틱이라 기본 게이트엔 미포함.

    표 품질 저하 1순위 원인(내용 잘림)을 제출 전에 잡기 위한 경고.
    중첩 표가 든 셀은 추정 불가로 건너뛴다.
    """
    issues: list[dict] = []
    for si, sec in enumerate(ad.section_elements()):
        for ti, tbl in enumerate(el for el in sec.iter() if el.tag.endswith("}tbl")):
            for tc in tbl.iter():
                if not tc.tag.endswith("}tc"):
                    continue
                if any(el.tag.endswith("}tbl") for el in tc.iter() if el is not tc):
                    continue
                sz = _child(tc, "cellSz")
                if sz is None:
                    continue
                w = int(sz.get("width", "0") or 0)
                h = int(sz.get("height", "0") or 0)
                if w <= _CELL_PAD or h <= 0:
                    continue
                text = "".join(el.text or "" for el in tc.iter()
                               if el.tag.endswith("}t"))
                if not text.strip():
                    continue
                addr = _child(tc, "cellAddr")
                pos = (f"({addr.get('rowAddr')},{addr.get('colAddr')})"
                       if addr is not None else "?")
                chars_per_line = max(1, (w - _CELL_PAD) // _CHAR_UNIT)
                est_lines = -(-_text_units(text) // (_CHAR_UNIT * chars_per_line))
                if (est_lines >= _OVERFLOW_MIN_LINES
                        and est_lines * _LINE_UNIT > h * _OVERFLOW_RATIO):
                    issues.append(_issue(
                        "cell_overflow_risk",
                        f"셀 내용이 칸보다 큼 (추정 {est_lines}줄) — 내용 압축 또는 col-width/row-height 조정",
                        f"section {si} 표 {ti} 셀 {pos}: {text[:20]}…"))
                elif h < _MIN_ROW_UNIT:
                    issues.append(_issue(
                        "row_height_too_small",
                        "행높이가 글자보다 낮음 — 내용 잘림 위험",
                        f"section {si} 표 {ti} 셀 {pos}"))
    for i in issues:
        i["check"] = "layout"
    return issues
