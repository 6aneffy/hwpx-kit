"""outline 명령 — 문단·표 배치 지도 (읽기 전용).

앵커 후보를 찾을 때 원시 XML을 뒤지지 말고 이걸 쓴다: 문단 인덱스,
텍스트, 표 위치(문서 순서 table_index)가 한 번에 나온다.
"""
from __future__ import annotations

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter


def run_outline(path: str) -> dict:
    ad = HwpxEngineAdapter.open(path)
    return {"file": path, "paragraphs": ad.outline()}
