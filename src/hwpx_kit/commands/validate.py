from __future__ import annotations

import os

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter


def run_validate(path: str) -> dict:
    ad = HwpxEngineAdapter.open(path)
    report = ad.validate()
    issues = list(report.get("issues", []))
    return {"file": os.path.abspath(path), "valid": not issues, "issues": issues}
