"""inspect structure 검사 — 유령 셀·표 일관성·댕글링 참조·secPr."""
import copy

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
from hwpx_kit.inspect_structure import check_structure

FIXTURE = "tests/fixtures/real/seoul-report-brief.hwpx"


def _codes(issues):
    return {i["code"] for i in issues}


def test_clean_fixture_has_no_structure_issues():
    ad = HwpxEngineAdapter.open(FIXTURE)
    assert check_structure(ad) == []


def test_ghost_cell_detected():
    ad = HwpxEngineAdapter.open(FIXTURE)
    sec = ad.section_elements()[0]
    tcs = [el for el in sec.iter() if el.tag.endswith("}tc")]
    assert tcs, "픽스처에 표 셀이 있어야 함"
    ghost = copy.deepcopy(tcs[0])
    for ch in ghost:
        if ch.tag.endswith("}cellSz"):
            ch.set("width", "0")
            ch.set("height", "0")
    tcs[0].getparent().append(ghost)
    issues = check_structure(ad)
    assert "ghost_cell" in _codes(issues)


def test_rowcnt_mismatch_detected():
    ad = HwpxEngineAdapter.open(FIXTURE)
    sec = ad.section_elements()[0]
    tbl = next(el for el in sec.iter() if el.tag.endswith("}tbl"))
    tbl.set("rowCnt", "999")
    assert "table_rowcnt_mismatch" in _codes(check_structure(ad))


def test_dangling_charpr_ref_detected():
    ad = HwpxEngineAdapter.open(FIXTURE)
    sec = ad.section_elements()[0]
    run = next(el for el in sec.iter() if el.tag.endswith("}run"))
    run.set("charPrIDRef", "99999")
    assert "dangling_ref" in _codes(check_structure(ad))


def test_missing_secpr_detected():
    ad = HwpxEngineAdapter.open(FIXTURE)
    sec = ad.section_elements()[0]
    first_p = next(el for el in sec.iter() if el.tag.endswith("}p"))
    for el in list(first_p.iter()):
        if el.tag.endswith("}secPr"):
            el.getparent().remove(el)
    assert "missing_secpr" in _codes(check_structure(ad))


# ── layout: 넘침 추정 ─────────────────────────────────────────

from hwpx_kit.inspect_structure import check_layout


def test_layout_clean_on_fixtures():
    for name in ("seoul-report-brief", "seoul-body", "seoul-attachment",
                 "seoul-report-cover"):
        ad = HwpxEngineAdapter.open(f"tests/fixtures/real/{name}.hwpx")
        overflow = [i for i in check_layout(ad) if i["code"] == "cell_overflow_risk"]
        assert overflow == [], f"{name} 오탐: {overflow[:2]}"


def test_layout_flags_overflowing_cell():
    ad = HwpxEngineAdapter.open(FIXTURE)
    sec = ad.section_elements()[0]
    tc = next(el for el in sec.iter() if el.tag.endswith("}tc"))
    sz = next(ch for ch in tc if ch.tag.endswith("}cellSz"))
    sz.set("width", "3000")   # ≈10mm — 좁은 칸
    sz.set("height", "1000")  # 한 줄도 빠듯
    t = next((el for el in tc.iter() if el.tag.endswith("}t")), None)
    assert t is not None
    t.text = "이 칸에는 도저히 들어갈 수 없는 매우 긴 내용이 들어간다 " * 5
    issues = check_layout(ad)
    assert any(i["code"] == "cell_overflow_risk" for i in issues)
