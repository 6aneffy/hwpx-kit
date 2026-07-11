from hwpx_kit.adapter.base import MARKER_RE, FormField, Marker
from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter


def test_marker_re_matches_korean_keys():
    keys = MARKER_RE.findall("가 {{성명}} 나 {{출장기간}} 다 {{name_en}}")
    assert keys == ["성명", "출장기간", "name_en"]


def test_open_and_markers(marker_doc):
    ad = HwpxEngineAdapter.open(marker_doc)
    found = ad.markers()
    assert {m.key for m in found} == {"성명", "출장기간"}
    seong = next(m for m in found if m.key == "성명")
    assert "신청자" in seong.context
    assert isinstance(seong, Marker)


def test_replace_marker_and_save_copy(marker_doc, tmp_path):
    ad = HwpxEngineAdapter.open(marker_doc)
    count = ad.replace_marker("성명", "김철수")
    assert count == 1
    out = str(tmp_path / "out.hwpx")
    saved = ad.save_copy(out)
    reopened = HwpxEngineAdapter.open(saved)
    assert "김철수" in reopened.export_text()
    assert "{{성명}}" not in reopened.export_text()


def test_fill_by_label_roundtrip(label_table_doc, tmp_path):
    ad = HwpxEngineAdapter.open(label_table_doc)
    result = ad.fill_by_label("성명 > right", "김철수")
    assert result["applied_count"] == 1
    saved = ad.save_copy(str(tmp_path / "out.hwpx"))
    reopened = HwpxEngineAdapter.open(saved)
    assert "김철수" in reopened.export_text()


def test_table_map_shape(label_table_doc):
    ad = HwpxEngineAdapter.open(label_table_doc)
    tm = ad.table_map()
    assert tm["tables"][0]["rows"] == 2
    assert tm["tables"][0]["cells"][0]["text"] == "성명"


def test_form_fields_empty_when_none(marker_doc):
    ad = HwpxEngineAdapter.open(marker_doc)
    assert ad.form_fields() == []


def test_validate_returns_issues_list(marker_doc):
    ad = HwpxEngineAdapter.open(marker_doc)
    report = ad.validate()
    assert "issues" in report
