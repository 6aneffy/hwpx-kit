"""inspect 명령 — 제출 전 기계 검수.

문서 본문(표 셀 포함)을 뽑아 inspect_rules의 순수 검사를 돌린다.
위반이 있으면 CLI가 exit 2 (부분 성공)로 알린다 — 게이트로 쓸 수 있게.
"""
from __future__ import annotations

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
from hwpx_kit.inspect_rules import CHECKS


def run_inspect(path: str, checks: list[str] | None = None) -> dict:
    selected = checks or list(CHECKS)
    bad = [c for c in selected if c not in CHECKS]
    if bad:
        raise ValueError(f"알 수 없는 검사: {bad} (가능: {', '.join(CHECKS)})")

    ad = HwpxEngineAdapter.open(path)
    text = ad.export_text()

    issues: list[dict] = []
    for name in selected:
        issues.extend(CHECKS[name](text))

    return {
        "file": path,
        "checks": selected,
        "issues": issues,
        "clean": not issues,
    }
