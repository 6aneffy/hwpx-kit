from __future__ import annotations

import os

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
from hwpx_kit.adapter.kordoc_engine import KordocAdapter, kordoc_available
from hwpx_kit.adapter.office_readers import read_docx, read_pdf, read_xlsx

# 순수 파이썬 리더 (kordoc 흡수, 2026-07-10) — Node 불필요
_PY_READERS = {
    ".pdf": read_pdf,
    ".docx": read_docx,
    ".xlsx": read_xlsx,
}

# 구형 한글 포맷 — kordoc(있으면)만 가능. 없으면 convert 안내
_LEGACY_HWP_EXTS = {".hwp", ".hwpml"}


def run_read(path: str, fmt: str = "md") -> dict:
    if fmt not in ("md", "text"):
        raise ValueError(f"지원하지 않는 형식: {fmt} (md 또는 text)")

    ext = os.path.splitext(path)[1].lower()

    if ext in _PY_READERS:
        content = _PY_READERS[ext](path)
        return {"file": os.path.abspath(path), "format": "md", "content": content}

    if ext in _LEGACY_HWP_EXTS or ext == ".xls":
        if kordoc_available():
            content = KordocAdapter.convert_to_markdown(path)
            return {"file": os.path.abspath(path), "format": "md", "content": content}
        raise RuntimeError(
            "구형 포맷은 두 가지 방법으로 읽을 수 있습니다: "
            "① Windows+한글 환경이면 'hwpx-kit convert'로 hwpx 변환 후 read "
            "② 한글이 없는 환경(Mac 등)이면 kordoc 설치 (Node.js 18+ 필요: npm install -g kordoc)"
        )

    ad = HwpxEngineAdapter.open(path)
    content = ad.export_markdown() if fmt == "md" else ad.export_text()
    return {"file": os.path.abspath(path), "format": fmt, "content": content}
