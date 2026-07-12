"""결정론 변환기 — LLM이 미세하게 틀리는 계산을 순수함수로 못박는다.

정답지 출처:
- 금액 한글 읽기: 행정 효율과 협업 촉진에 관한 규정 시행규칙 예시
  (금113,560원(금일십일만삼천오백육십원)) — '일십일만'처럼 一을 생략하지 않는
  위변조 방지 표기.
- 날짜/만나이: 범정부오피스 가이드북 예시.
"""
import json

import pytest

from hwpx_kit.cli import main
from hwpx_kit.format import amount_to_korean, format_amount, gongmun_date, korean_age


# ---- 금액 한글 읽기 (숫자 → 한글) ----

@pytest.mark.parametrize(
    "n, expected",
    [
        (0, "영"),
        (1, "일"),
        (10, "일십"),          # 위변조 방지: 십 앞 일 생략 금지
        (100, "일백"),
        (1000, "일천"),
        (10000, "일만"),
        (12340, "일만이천삼백사십"),          # 범피스 가이드북 예시
        (113560, "일십일만삼천오백육십"),      # 시행규칙 예시
        (100000000, "일억"),
        (100010000, "일억일만"),
        (1000000000000, "일조"),
        (1234567890123, "일조이천삼백사십오억육천칠백팔십구만일백이십삼"),
        (500, "오백"),
        (20260710, "이천이십육만칠백일십"),
    ],
)
def test_amount_to_korean(n, expected):
    assert amount_to_korean(n) == expected


def test_amount_negative_rejected():
    with pytest.raises(ValueError):
        amount_to_korean(-1)


# ---- 금액 표기 스타일 ----

def test_format_amount_gongmun():
    """법정 공문 형식 (기본값) — 범피스와 동일."""
    assert format_amount(12340) == "금12,340원(금일만이천삼백사십원)"
    assert format_amount(113560, style="gongmun") == "금113,560원(금일십일만삼천오백육십원)"


def test_format_amount_ilgeum():
    """민간 관습 형식 — 영수증·차용증·계약서."""
    assert format_amount(12340, style="ilgeum") == "일금 12,340원정(일금 일만이천삼백사십원정)"


def test_format_amount_unknown_style():
    with pytest.raises(ValueError):
        format_amount(12340, style="foo")


# ---- 공문 날짜 (요일) ----

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("20260101", "2026.1.1.(목)"),   # 범피스 가이드북 예시
        ("20260710", "2026.7.10.(금)"),
        ("20251225", "2025.12.25.(목)"),
        ("2026-01-01", "2026.1.1.(목)"),  # 구분자 있는 입력도 허용
    ],
)
def test_gongmun_date(raw, expected):
    assert gongmun_date(raw) == expected


def test_gongmun_date_invalid():
    with pytest.raises(ValueError):
        gongmun_date("20261301")  # 13월


# ---- 만나이 ----

def test_korean_age_before_birthday():
    """가이드북 예시: 930705 → (31), 2025년 생일 전 기준."""
    assert korean_age("930705", base="20250704") == "930705(31)"


def test_korean_age_on_birthday():
    assert korean_age("930705", base="20250705") == "930705(32)"


def test_korean_age_invalid():
    with pytest.raises(ValueError):
        korean_age("931302", base="20250101")  # 13월


# ---- CLI 왕복 ----

def _last_json(capsys):
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def test_cli_fmt_amount(capsys):
    code = main(["fmt", "--amount", "12340", "--json"])
    env = _last_json(capsys)
    assert code == 0
    assert env["ok"] is True
    assert env["data"]["result"] == "금12,340원(금일만이천삼백사십원)"


def test_cli_fmt_amount_ilgeum(capsys):
    code = main(["fmt", "--amount", "12340", "--style", "ilgeum", "--json"])
    env = _last_json(capsys)
    assert code == 0
    assert env["data"]["result"] == "일금 12,340원정(일금 일만이천삼백사십원정)"


def test_cli_fmt_date(capsys):
    code = main(["fmt", "--date", "20260101", "--json"])
    env = _last_json(capsys)
    assert code == 0
    assert env["data"]["result"] == "2026.1.1.(목)"


def test_cli_fmt_age_with_base(capsys):
    code = main(["fmt", "--age", "930705", "--base", "20250704", "--json"])
    env = _last_json(capsys)
    assert code == 0
    assert env["data"]["result"] == "930705(31)"


def test_cli_fmt_requires_exactly_one(capsys):
    """변환 대상 플래그 0개 또는 2개면 오류 봉투 + 종료 1."""
    code = main(["fmt", "--json"])
    env = _last_json(capsys)
    assert code == 1
    assert env["ok"] is False

    code = main(["fmt", "--amount", "1", "--date", "20260101", "--json"])
    env = _last_json(capsys)
    assert code == 1
    assert env["ok"] is False


# ── 표 단위 변환 (천원/백만원) ────────────────────────────────

def test_scale_amount_to_cheonwon():
    from hwpx_kit.format import scale_amount

    # 관습: 반올림, 세 자리 콤마
    assert scale_amount(1234567, "천원") == "1,235"
    assert scale_amount(1000, "천원") == "1"
    assert scale_amount(37000000, "천원") == "37,000"


def test_scale_amount_to_baekmanwon():
    from hwpx_kit.format import scale_amount

    assert scale_amount(37000000, "백만원") == "37"
    assert scale_amount(1234567890, "백만원") == "1,235"
    assert scale_amount(500000, "백만원") == "1"   # 반올림 올라감


def test_scale_amount_rejects_unknown_unit():
    import pytest as _pytest

    from hwpx_kit.format import scale_amount

    with _pytest.raises(ValueError):
        scale_amount(1000, "억원")


def test_cli_fmt_scale(capsys):
    import json as _json

    from hwpx_kit.cli import main

    code = main(["fmt", "--scale", "1,234,567", "--unit", "천원", "--json"])
    env = _json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0
    assert env["data"]["result"] == "1,235"
