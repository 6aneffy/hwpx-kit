from __future__ import annotations

import os
import re
from collections import Counter

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter

# 라벨은 단어 문자(한글/영숫자)를 포함해야 함 — 구두점 단독 셀 배제
_WORD_RE = re.compile(r"\w", re.UNICODE)
_WS_RE = re.compile(r"\s+")
_MAX_LABEL_LEN = 20


def _normalize_label(text: str) -> str:
    """엔진(fill_by_path)과 같은 공백 정규화 — 개행 든 라벨('담당 부서\\n<총괄>')도
    한 줄 라벨로 취급해 fill_key가 엔진 매칭을 그대로 통과하게 한다."""
    return _WS_RE.sub(" ", text).strip()


def _is_label_text(text: str) -> bool:
    if not text:
        return False
    if len(text) > _MAX_LABEL_LEN:
        return False
    return bool(_WORD_RE.search(text))


def find_label_candidates(table_map: dict) -> list[dict]:
    """라벨 후보: 텍스트가 있고 바로 오른쪽 셀이 비어 있는 셀."""
    candidates = []
    for table in table_map.get("tables", []):
        cells = {(c["row"], c["col"]): c for c in table.get("cells", [])}
        for (row, col), cell in cells.items():
            if cell.get("is_anchor") is False:
                # 병합 셀의 격자 복제 — 논리 셀은 anchor 좌표 하나뿐
                continue
            text = _normalize_label(cell.get("text") or "")
            if not _is_label_text(text):
                continue
            right = cells.get((row, col + 1))
            if right is None:
                continue
            right_text = (right.get("text") or "").strip()
            if _normalize_label(right_text) == text:
                # 병합 셀은 같은 텍스트가 격자 전체에 복제되어 나타남
                continue
            candidates.append(
                {
                    "table_index": table.get("table_index", 0),
                    "label": text,
                    "row": row,
                    "col": col,
                    "fill_key": f"table:{text}",
                    "prefilled": bool(right_text),
                    "current": right_text,
                    "ambiguous": False,
                }
            )
    counts = Counter(c["label"] for c in candidates)
    for c in candidates:
        c["ambiguous"] = counts[c["label"]] > 1
    return candidates


def _assign_nth_keys(ad: HwpxEngineAdapter, candidates: list[dict]) -> None:
    """중복 라벨 후보의 fill_key에 #N 접미사 부여.

    중복 판정·번호 모두 fill과 같은 열거(label_positions_map, anchor 셀
    전체) 기준 — analyze 후보로는 유일해 보여도(두 번째 출현에 오른쪽 칸이
    없는 경우 등) fill이 ambiguous로 거부할 수 있어, fill 관점의 출현 수로
    판정해야 'analyze 키 그대로 fill' 계약이 지켜진다.
    """
    if not candidates:
        return
    posmap = ad.label_positions_map()
    for c in candidates:
        matches = posmap.get(ad.normalize_label(c["label"]), [])
        if len(matches) < 2:
            continue
        c["ambiguous"] = True
        for i, m in enumerate(matches):
            if (m["table_index"], m["row"], m["col"]) == (c["table_index"], c["row"], c["col"]):
                c["fill_key"] = f"table:{c['label']}#{i + 1}"
                break


def run_analyze(path: str) -> dict:
    ad = HwpxEngineAdapter.open(path)
    fields: list[dict] = []

    for ff in ad.form_fields():
        fields.append(
            {
                "type": "clickhere",
                "fill_key": f"clickhere:{ff.name or ff.index}",
                "name": ff.name,
                "index": ff.index,
                "current": ff.current,
            }
        )

    for m in ad.markers():
        fields.append(
            {
                "type": "marker",
                "fill_key": f"marker:{m.key}",
                "key": m.key,
                "paragraph_index": m.paragraph_index,
                "context": m.context,
            }
        )

    table_map = ad.table_map()
    candidates = find_label_candidates(table_map)
    _assign_nth_keys(ad, candidates)
    for cand in candidates:
        fields.append({"type": "table_label", **cand})

    paragraph_count = len(ad.export_text().splitlines())
    return {
        "file": os.path.abspath(path),
        "fields": fields,
        "tables": {"count": len(table_map.get("tables", []))},
        "structure": {"paragraphs": paragraph_count},
    }
