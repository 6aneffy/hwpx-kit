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
