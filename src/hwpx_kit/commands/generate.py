from __future__ import annotations

import os

from hwpx_kit.adapter.kordoc_engine import KordocAdapter


def run_generate(markdown_path: str, out_path: str, preset: str | None = None) -> dict:
    if not markdown_path.lower().endswith((".md", ".markdown")):
        raise ValueError("generate 입력은 Markdown 파일이어야 합니다.")
    saved = KordocAdapter.generate_hwpx(markdown_path, out_path, preset=preset)
    return {"file": os.path.abspath(markdown_path), "out": saved, "preset": preset}
