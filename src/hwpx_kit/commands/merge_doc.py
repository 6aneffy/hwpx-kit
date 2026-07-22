"""merge 명령 — 두 hwpx를 하나로 합본 (붙임 문서 합치기).

MVP: 두 문서의 서식 정의(header refList: 글꼴·글자·문단·스타일·테두리)가
동일할 때만 지원 — 같은 기관 서식/템플릿에서 나온 붙임 문서 합치기가 대상.
서식이 다르면 id 재매핑이 필요해 자동 합본을 거부한다(조용한 서식 깨짐 방지).
완전 재매핑(다른 서식 문서 합본)은 후속 백로그.
"""
from __future__ import annotations

import copy

from lxml import etree

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
from hwpx_kit.output import quiet_engine


def _reflist_signature(ad: HwpxEngineAdapter) -> bytes:
    """header.xml의 <refList> 직렬화 — 서식 정의 동일성 비교용."""
    header = ad.header_element()
    ref = next((c for c in header if c.tag.endswith("}refList")), None)
    if ref is None:
        return b""
    return etree.tostring(ref)


def run_merge(base_path: str, add_path: str, out_path: str,
              page_break: bool = True) -> dict:
    """base 뒤에 add 문서의 본문을 이어붙여 out_path 사본에 저장.

    서식 정의(refList)가 다르면 거부. 같으면 add의 최상위 문단(표 포함)을
    base 마지막 섹션에 append하고 경계에 쪽나눔을 준다.
    """
    base = HwpxEngineAdapter.open(base_path)
    add = HwpxEngineAdapter.open(add_path)

    if _reflist_signature(base) != _reflist_signature(add):
        raise ValueError(
            "두 문서의 서식 정의(글꼴·스타일·테두리 등)가 달라 자동 합본을 할 수 "
            "없습니다 — 같은 서식(템플릿)에서 만든 문서만 지원합니다. 서식이 다른 "
            "문서는 한글에서 합치세요.")

    with quiet_engine():
        sections = base.section_elements()
        if not sections:
            raise ValueError("base 문서에 섹션이 없습니다.")
        target_sec = sections[-1]

        add_paras = [p.element for p in add._doc.paragraphs]
        appended = 0
        first = True
        for pel in add_paras:
            new_el = copy.deepcopy(pel)
            # add 문단의 섹션 정의(secPr)는 제거 — base 섹션에 흡수시켜
            # 중복 섹션 정의로 인한 손상을 막는다 (같은 서식이라 base secPr로 충분)
            for sec_pr in new_el.findall(".//{*}secPr"):
                parent = sec_pr.getparent()
                if parent is not None:
                    parent.remove(sec_pr)
            if first and page_break:
                new_el.set("pageBreak", "1")
            target_sec.append(new_el)
            appended += 1
            first = False

        base._mark_sections_dirty()
    out = base.save_copy(out_path)
    return {"base": base_path, "add": add_path, "out": out,
            "appended_paragraphs": appended}
