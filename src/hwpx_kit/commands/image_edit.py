"""이미지 편집 명령 진입점 — 목록·크기변경·교체·삭제."""
from __future__ import annotations

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter


def run_image_list(path: str) -> dict:
    ad = HwpxEngineAdapter.open(path)
    pictures = ad.list_pictures()
    return {"count": len(pictures), "pictures": pictures}


def run_image_resize(path: str, *, index: int, width_mm: float | None,
                     height_mm: float | None, out_path: str) -> dict:
    ad = HwpxEngineAdapter.open(path)
    applied = ad.resize_picture(index, width_mm=width_mm, height_mm=height_mm)
    saved = ad.save_copy(out_path)
    return {"out": saved, **applied}


def run_image_replace(path: str, *, index: int, image_path: str,
                      out_path: str) -> dict:
    ad = HwpxEngineAdapter.open(path)
    result = ad.replace_picture_at(index, image_path)
    saved = ad.save_copy(out_path)
    return {"out": saved, "replaced": result}


def run_image_del(path: str, *, index: int, out_path: str) -> dict:
    ad = HwpxEngineAdapter.open(path)
    result = ad.delete_picture(index)
    saved = ad.save_copy(out_path)
    return {"out": saved, **result}
