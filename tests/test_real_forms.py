"""실제 공개 서식(서울시 정보소통광장, opengov.seoul.go.kr/sanction/11678326) 회귀 테스트.

tests/fixtures/real/ 의 4개 hwpx는 위 공개 페이지에서 받은 결재/보고서 표준 서식이다.
"""
from pathlib import Path

import pytest

from hwpx_kit.commands.analyze import run_analyze
from hwpx_kit.commands.fill import run_fill
from hwpx_kit.commands.read import run_read
from hwpx_kit.commands.validate import run_validate

REAL = Path(__file__).parent / "fixtures" / "real"
ALL_FORMS = sorted(REAL.glob("*.hwpx"))


@pytest.mark.parametrize("form", ALL_FORMS, ids=lambda p: p.name)
def test_real_form_validates(form):
    assert run_validate(str(form))["valid"] is True


@pytest.mark.parametrize("form", ALL_FORMS, ids=lambda p: p.name)
def test_real_form_analyze_and_read_do_not_crash(form):
    data = run_analyze(str(form))
    assert isinstance(data["fields"], list)
    assert run_read(str(form), fmt="text")["content"] is not None


def test_seoul_body_has_clickhere_field():
    data = run_analyze(str(REAL / "seoul-body.hwpx"))
    keys = {f["fill_key"] for f in data["fields"]}
    assert "clickhere:본문" in keys


def test_seoul_body_label_noise_filtered():
    """구두점 단독('(')과 개행 포함('04/05\\n이행용') 라벨은 후보에서 제외."""
    data = run_analyze(str(REAL / "seoul-body.hwpx"))
    labels = [f["label"] for f in data["fields"] if f["type"] == "table_label"]
    assert "(" not in labels
    assert not any("\n" in label for label in labels)


def test_seoul_body_prefilled_header_fields_detected():
    """수신/제목처럼 템플릿 기본값이 든 칸도 prefilled 후보로 잡혀야 한다."""
    data = run_analyze(str(REAL / "seoul-body.hwpx"))
    by_key = {f["fill_key"]: f for f in data["fields"] if f["type"] == "table_label"}
    assert by_key["table:수신"]["prefilled"] is True
    assert by_key["table:수신"]["current"] == "수신자참조"
    assert by_key["table:제목"]["prefilled"] is True


# 부처 제공 기밀 양식 — 레포에 포함하지 않음 (private/ 는 gitignore).
# 존재할 때만 로컬 검증 실행. 양식 내용(제목 문자열 등)도 코드에 하드코딩 금지.
PRIVATE = Path(__file__).parent.parent / "private"
_PRESS = PRIVATE / "press-joint.hwpx"

pytestmark_press = pytest.mark.skipif(not _PRESS.exists(), reason="비공개 양식 없음")


def _press_title(form: str) -> str:
    """제목 표(2x1)의 첫 셀 텍스트를 파일에서 직접 추출 — 원문 하드코딩 회피."""
    from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter

    tm = HwpxEngineAdapter.open(form).table_map()
    for t in tm["tables"]:
        if t["rows"] == 2 and t["cols"] == 1:
            return t["cells"][0]["text"].strip()
    raise AssertionError("제목 표(2x1)를 찾지 못함")


@pytestmark_press
def test_press_form_header_fields_detected():
    """보도자료 양식(부처 제공): 보도시점/배포가 prefilled 후보로 잡혀야 한다."""
    data = run_analyze(str(_PRESS))
    by_key = {f["fill_key"]: f for f in data["fields"] if f["type"] == "table_label"}
    assert by_key["table:보도시점"]["prefilled"] is True


@pytestmark_press
def test_press_form_title_text_replacement_roundtrip(tmp_path):
    """제목 표 셀의 예시 텍스트 교체 — 런 분할 폴백 경로의 실서식 회귀.

    과거 회귀: lxml 프록시 id() 재사용으로 문단 순회가 비결정적으로 문단을
    건너뛰어 같은 입력에서 매칭이 됐다 안 됐다 했다. 반복 실행으로 재발 감지.
    """
    form = str(_PRESS)
    title = _press_title(form)
    for attempt in range(3):
        out = str(tmp_path / f"filled{attempt}.hwpx")
        result = run_fill(
            form,
            {
                "table:보도시점": "2026. 7. 9.(목) 10:00",
                f"text:{title}": "공공부문 문서작성에 AI 도입, 행정 효율 높인다",
            },
            out,
        )
        assert result["unmatched"] == [], f"attempt {attempt}: {result['unmatched']}"
        content = run_read(out, fmt="text")["content"]
        assert "행정 효율 높인다" in content
        assert title not in content


def test_seoul_body_full_document_fill_roundtrip(tmp_path):
    """실서식 공문 작성 시나리오: 수신·경유·제목(덮어쓰기) + 본문(누름틀) 동시 채움."""
    form = str(REAL / "seoul-body.hwpx")
    out = str(tmp_path / "filled.hwpx")
    values = {
        "table:수신": "서울특별시장(문서과)",
        "table:(경유)": "행정국장",
        "table:제목": "AI 문서자동화 교육 결과 보고",
        "clickhere:본문": "붙임과 같이 AI 문서자동화 교육 결과를 보고드립니다.",
    }

    result = run_fill(form, values, out)
    assert set(result["applied"]) == set(values)
    assert result["unmatched"] == []
    assert run_validate(out)["valid"] is True
    content = run_read(out, fmt="text")["content"]
    for value in values.values():
        assert value in content
    assert "수신자참조" not in content  # 기본값이 실제로 덮어써졌는지
