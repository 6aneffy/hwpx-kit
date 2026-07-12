"""image-add 명령 — 이미지(사진·직인)를 문단 앵커 또는 표 셀에 삽입."""
from __future__ import annotations

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter


def run_image_add(path: str, image_path: str, at_text: str | None,
                  table: int | None, cell: str | None,
                  width_mm: float, height_mm: float | None, out_path: str) -> dict:
    if (at_text is None) == (cell is None):
        raise ValueError("--at-text 또는 (--table + --cell) 중 정확히 하나를 지정하세요.")
    cell_rc = None
    if cell is not None:
        try:
            r, c = cell.split(",")
            cell_rc = (int(r), int(c))
        except ValueError:
            raise ValueError(f"--cell 형식은 'R,C': {cell!r}") from None

    ad = HwpxEngineAdapter.open(path)
    info = ad.insert_image(image_path, at_text=at_text, table_index=table,
                           cell=cell_rc, width_mm=width_mm, height_mm=height_mm)
    out = ad.save_copy(out_path)
    return {"file": path, "out": out, "image": image_path,
            "inserted": True, **info}
