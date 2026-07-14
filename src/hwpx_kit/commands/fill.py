from __future__ import annotations

import re

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter

# 라벨 끝의 출현 인덱스: "부서#2" → ("부서", 2). 중복 라벨 구분용
_NTH_RE = re.compile(r"^(.+?)\s*#(\d+)$")

_DIRECTIONS = {"left", "right", "up", "down"}


def _parse_table_spec(spec: str) -> tuple[str, list[str], int | None]:
    """"라벨#N > 방향..." 분해. 방향 토큰은 끝에서부터 유효한 것만 소비 —
    라벨 자체에 '>'가 들어가도('담당 부서 <총괄>') 잘리지 않는다."""
    parts = spec.split(">")
    directions: list[str] = []
    while len(parts) > 1 and parts[-1].strip().casefold() in _DIRECTIONS:
        directions.insert(0, parts.pop().strip().casefold())
    label = ">".join(parts).strip()
    if not directions:
        directions = ["right"]
    nth = None
    nth_match = _NTH_RE.match(label)
    if nth_match:
        label, nth = nth_match.group(1), int(nth_match.group(2))
    return label, directions, nth


def _apply_one(ad: HwpxEngineAdapter, fill_key: str, value: str) -> str | None:
    """성공 시 None, 실패 시 사유 문자열 반환."""
    if fill_key.startswith("clickhere:"):
        name = fill_key[len("clickhere:"):]
        try:
            ad.fill_form_field(name, value)
            return None
        except Exception as exc:  # 엔진이 없는 필드에 던지는 예외를 사유로 변환
            return f"누름틀 채우기 실패: {exc}"

    if fill_key.startswith("marker:"):
        key = fill_key[len("marker:"):]
        count = ad.replace_marker(key, value)
        if count == 0:
            # 마커가 런 경계로 쪼개진 경우 ({{와 키가 다른 런)
            count = ad.replace_text_across_runs("{{" + key + "}}", value)
        return None if count > 0 else "문서에서 마커를 찾지 못함"

    if fill_key.startswith("text:"):
        search = fill_key[len("text:"):]
        count = ad.replace_text(search, value)
        if count == 0:
            # 런 경계에 걸친 문구 — 매치 밖 서식은 보존
            count = ad.replace_text_across_runs(search, value)
        if count == 0:
            # 최후 폴백: 문단 전체 일치 (문단이 첫 런 서식으로 합쳐짐)
            count = ad.replace_paragraph_text(search, value)
        return None if count > 0 else "문서에서 해당 문구를 찾지 못함"

    if fill_key.startswith("fit:"):
        count, reason = ad.replace_text_fit(fill_key[len("fit:"):], value)
        return None if count > 0 else reason

    if fill_key.startswith("delete:"):
        search = fill_key[len("delete:"):]
        count = ad.delete_paragraph_text(search)
        return None if count > 0 else "문서에서 해당 문단을 찾지 못함"

    if fill_key.startswith("bold:"):
        count = ad.apply_run_format(fill_key[len("bold:"):], bold=True)
        return None if count > 0 else "문서에서 해당 문구를 찾지 못함"

    if fill_key.startswith("underline:"):
        count = ad.apply_run_format(fill_key[len("underline:"):], underline=True)
        return None if count > 0 else "문서에서 해당 문구를 찾지 못함"

    if fill_key.startswith("table:"):
        label, directions, nth = _parse_table_spec(fill_key[len("table:"):])
        result = ad.fill_at_label(label, directions, value, nth=nth)
        if result.get("applied_count", 0) > 0:
            return None
        failed = result.get("failed") or [{}]
        reason = failed[0].get("reason", "라벨 없음")
        if "ambiguous" in str(reason):
            reason = f"{reason} — 같은 라벨이 여러 곳. analyze의 table:라벨#N 키로 지정"
        return f"표 채우기 실패: {reason}"

    return "알 수 없는 fill_key 형식 (clickhere:/marker:/table:/text:/fit:/delete:/bold:/underline: 중 하나여야 함)"


def run_fill_secure(path: str, data: dict[str, str], out_path: str) -> dict:
    """엄격 모드 — 민감정보(PII) 채우기용.

    ① 하나라도 못 채우면 산출물을 남기지 않는다 (반쯤 채워진 개인정보 문서 방지)
    ② 결과에 값을 절대 노출하지 않는다 — 키 목록·개수만.
    값 파일은 CLI만 읽는 것이 전제 (스킬 규약: Claude는 경로만 전달).
    """
    import os as _os

    result = run_fill(path, data, out_path)
    if result["unmatched"]:
        try:
            _os.remove(result["out"])
        except OSError:
            pass
        return {
            "ok": False,
            "out": None,
            "applied_count": len(result["applied"]),
            "unmatched_keys": [u["key"] for u in result["unmatched"]],
            "reason": "일부 키를 채우지 못해 산출물을 만들지 않았습니다 (--secure 엄격 모드)",
        }
    return {"ok": True, "out": result["out"], "applied_count": len(result["applied"])}


def run_fill(path: str, data: dict[str, str], out_path: str) -> dict:
    ad = HwpxEngineAdapter.open(path)
    applied: list[str] = []
    unmatched: list[dict] = []
    for fill_key, value in data.items():
        reason = _apply_one(ad, fill_key, str(value))
        if reason is None:
            applied.append(fill_key)
        else:
            unmatched.append({"key": fill_key, "reason": reason})
    saved = ad.save_copy(out_path)
    return {"out": saved, "applied": applied, "unmatched": unmatched}
