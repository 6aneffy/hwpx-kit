"""inspect 명령 — 제출 전 기계 검수.

텍스트 검사(inspect_rules: 정규식)와 문서 검사(inspect_structure 등: XML 계층)
두 계열을 하나의 게이트로 묶는다. 위반이 있으면 CLI가 exit 2.
layout(넘침 추정)은 휴리스틱이라 기본 세트에서 제외 — 명시 지정 시만.
"""
from __future__ import annotations

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
from hwpx_kit.inspect_rules import CHECKS as TEXT_CHECKS
from hwpx_kit.inspect_structure import check_structure

DOC_CHECKS = {
    "structure": check_structure,
}

DEFAULT_CHECKS = ["residue", "gongmun", "pii", "structure"]


def all_check_names() -> list[str]:
    return list(TEXT_CHECKS) + list(DOC_CHECKS)


def run_inspect(path: str, checks: list[str] | None = None) -> dict:
    selected = checks or DEFAULT_CHECKS
    bad = [c for c in selected if c not in TEXT_CHECKS and c not in DOC_CHECKS]
    if bad:
        raise ValueError(f"알 수 없는 검사: {bad} (가능: {', '.join(all_check_names())})")

    ad = HwpxEngineAdapter.open(path)
    text = ad.export_text()

    issues: list[dict] = []
    for name in selected:
        if name in TEXT_CHECKS:
            issues.extend(TEXT_CHECKS[name](text))
        else:
            issues.extend(DOC_CHECKS[name](ad))

    return {
        "file": path,
        "checks": selected,
        "issues": issues,
        "clean": not issues,
    }
