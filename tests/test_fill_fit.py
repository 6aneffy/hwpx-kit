"""fill 신뢰성 확장 — 런 경계 교체 + fit(자리 폭 보존) 채우기."""
import copy

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
from hwpx_kit.commands.fill import run_fill

FIXTURE = "tests/fixtures/real/seoul-report-brief.hwpx"


def _split_first_text_run(ad):
    """첫 유효 런을 lxml 복제로 두 런으로 쪼개 '런 분할 문구'를 재현.

    반환: (원래 문구, 앞조각, 뒷조각)
    """
    for para in ad._iter_all_paragraphs():
        runs = list(para.runs)
        for run in runs:
            t = run.text or ""
            if len(t.strip()) >= 6:
                el = run.element
                clone = copy.deepcopy(el)
                el.addnext(clone)
                mid = len(t) // 2
                for node in el.iter():
                    if node.tag.endswith("}t"):
                        node.text = t[:mid]
                        break
                for node in clone.iter():
                    if node.tag.endswith("}t"):
                        node.text = t[mid:]
                        break
                return t, t[:mid], t[mid:]
    raise AssertionError("6자 이상 런이 있는 픽스처 필요")


def test_replace_across_runs_spanning_boundary():
    ad = HwpxEngineAdapter.open(FIXTURE)
    original, front, back = _split_first_text_run(ad)
    # 경계에 걸치는 부분 문구: 앞조각 끝 2자 + 뒷조각 앞 2자
    span = front[-2:] + back[:2]
    assert ad.replace_text(span, "먹") == 0, "엔진 런 교체는 경계를 못 넘어야 전제 성립"
    n = ad.replace_text_across_runs(span, "새문구")
    assert n == 1
    joined = original.replace(span, "새문구")
    assert any(joined in (p.text or "") for p in ad._iter_all_paragraphs())


def test_fill_text_key_uses_across_runs_fallback(tmp_path):
    ad = HwpxEngineAdapter.open(FIXTURE)
    original, front, back = _split_first_text_run(ad)
    tmp_split = str(tmp_path / "split.hwpx")
    ad.save_copy(tmp_split)

    out = str(tmp_path / "filled.hwpx")
    span = front[-2:] + back[:2]
    result = run_fill(tmp_split, {f"text:{span}": "치환됨"}, out)
    assert result["unmatched"] == []


# ── fit: 자리 폭 보존 ─────────────────────────────────────────


def test_fit_preserves_display_width(tmp_path):
    ad = HwpxEngineAdapter.open(FIXTURE)
    target = None
    for p in ad._iter_all_paragraphs():
        t = (p.text or "").strip()
        if len(t) >= 8:
            target = t
            break
    src = str(tmp_path / "src.hwpx")
    ad.save_copy(src)

    out = str(tmp_path / "fit.hwpx")
    result = run_fill(src, {f"fit:{target}": "홍길동"}, out)
    assert result["unmatched"] == []

    width = HwpxEngineAdapter._display_width
    ad2 = HwpxEngineAdapter.open(out)
    filled = next((p.text or "") for p in ad2._iter_all_paragraphs()
                  if "홍길동" in (p.text or ""))
    # 표시 폭 보존: 교체된 구간(값+패딩)의 폭 == 자리 원문의 폭
    ad_before = HwpxEngineAdapter.open(src)
    before = next((p.text or "") for p in ad_before._iter_all_paragraphs()
                  if target in (p.text or ""))
    assert width(filled) == width(before)


def test_fit_rejects_value_wider_than_slot(tmp_path):
    out = str(tmp_path / "reject.hwpx")
    result = run_fill(FIXTURE, {"fit:가나": "이값은자리보다훨씬넓다"}, out)
    assert len(result["unmatched"]) == 1
    reason = result["unmatched"][0]["reason"]
    assert "폭" in reason or "찾지 못함" in reason


def test_text_fill_matches_across_fwspace(tmp_path):
    """제목에 전각공백(fwSpace)이 껴 있으면 런 텍스트엔 공백이 없다 —
    사용자는 렌더에서 공백으로 보고 공백을 넣으므로, 공백 유연 매칭이 필요.
    (실양식 seoul-report-brief 제목이 이 패턴)"""
    out = str(tmp_path / "fw.hwpx")
    # 실제 텍스트는 '보고서 제목(HY헤드라인M+굵게28)'(공백0) — 사용자는 공백 넣음
    result = run_fill(FIXTURE,
                      {"text:보고서 제목 (HY헤드라인M+굵게28)": "새 제목입니다"},
                      out)
    assert result["unmatched"] == [], f"fwSpace 제목 매칭 실패: {result['unmatched']}"
    ad = HwpxEngineAdapter.open(out)
    assert any("새 제목입니다" in (p.text or "")
               for p in ad._iter_all_paragraphs())
