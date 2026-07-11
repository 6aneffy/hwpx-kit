from __future__ import annotations

import os

from hwpx_kit.adapter.kordoc_engine import KordocAdapter


def run_render(path: str, out_path: str | None = None) -> dict:
    out = out_path or os.path.splitext(path)[0] + ".svg"
    saved = KordocAdapter.render_svg(path, out)
    return {"file": os.path.abspath(path), "out": saved}
