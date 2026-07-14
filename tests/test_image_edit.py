"""이미지 편집 — 목록·크기변경·교체·삭제 (본문 문서 순서 인덱스)."""
import pytest

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
from hwpx_kit.commands.image_edit import (
    run_image_del, run_image_list, run_image_replace, run_image_resize,
)

FIXTURE = "tests/fixtures/real/seoul-report-brief.hwpx"

_DOT_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c62600100000005000157bfabd40000000049454e44ae426082")


@pytest.fixture()
def doc_with_image(tmp_path):
    png = tmp_path / "dot.png"
    png.write_bytes(_DOT_PNG)
    ad = HwpxEngineAdapter.open(FIXTURE)
    anchor = next(e["text"] for e in ad.outline()
                  if len((e["text"] or "").strip()) >= 6)
    ad.insert_image(str(png), at_text=anchor, width_mm=20.0)
    src = str(tmp_path / "with-image.hwpx")
    ad.save_copy(src)
    return src, str(png)


def test_image_list(doc_with_image):
    src, _ = doc_with_image
    result = run_image_list(src)
    assert result["count"] >= 1
    assert {"picture_index", "width_mm", "height_mm"} <= set(result["pictures"][0])


def test_image_resize(doc_with_image, tmp_path):
    src, _ = doc_with_image
    out = str(tmp_path / "resized.hwpx")
    run_image_resize(src, index=0, width_mm=40.0, height_mm=25.0, out_path=out)
    listed = run_image_list(out)["pictures"][0]
    assert abs(listed["width_mm"] - 40.0) < 0.5
    assert abs(listed["height_mm"] - 25.0) < 0.5


def test_image_replace(doc_with_image, tmp_path):
    src, png = doc_with_image
    out = str(tmp_path / "replaced.hwpx")
    before = run_image_list(src)["pictures"][0]
    run_image_replace(src, index=0, image_path=png, out_path=out)
    after = run_image_list(out)["pictures"][0]
    assert abs(after["width_mm"] - before["width_mm"]) < 0.5  # 기하 보존


def test_image_del(doc_with_image, tmp_path):
    src, _ = doc_with_image
    out = str(tmp_path / "deleted.hwpx")
    before = run_image_list(src)["count"]
    run_image_del(src, index=0, out_path=out)
    assert run_image_list(out)["count"] == before - 1
