"""결정론 표기 변환 — 순수함수만. 엔진(python-hwpx/kordoc) 임포트 금지.

LLM이 미세하게 틀리는 계산(큰 금액 한글 읽기, 요일, 만나이)을 못박는
정확성 보험. 스킬은 이 값들을 손으로 계산하지 말고 CLI `fmt`로 얻는다.
"""
from __future__ import annotations

import datetime
import re

_DIGITS = "영일이삼사오육칠팔구"
_SMALL_UNITS = ((1000, "천"), (100, "백"), (10, "십"), (1, ""))
_BIG_UNITS = ((10**16, "경"), (10**12, "조"), (10**8, "억"), (10**4, "만"), (1, ""))
_WEEKDAYS = "월화수목금토일"

_AMOUNT_STYLES = ("gongmun", "ilgeum")


def _group_to_korean(n: int) -> str:
    """0~9999를 한글로. 위변조 방지 표기 — 십/백/천 앞 '일'을 생략하지 않는다
    (시행규칙 예시 '일십일만삼천오백육십')."""
    parts = []
    for value, unit in _SMALL_UNITS:
        digit, n = divmod(n, value)
        if digit:
            parts.append(_DIGITS[digit] + unit)
    return "".join(parts)


def amount_to_korean(n: int) -> str:
    """정수 금액의 한글 읽기. 예: 113560 → 일십일만삼천오백육십."""
    if n < 0:
        raise ValueError("금액은 음수가 될 수 없습니다.")
    if n == 0:
        return "영"
    parts = []
    for value, unit in _BIG_UNITS:
        group, n = divmod(n, value)
        if group:
            parts.append(_group_to_korean(group) + unit)
    return "".join(parts)


def format_amount(n: int, style: str = "gongmun") -> str:
    """금액 표기.

    - gongmun(기본): 법정 공문 형식 — 행정 효율과 협업 촉진에 관한 규정
      시행규칙. 예: 금113,560원(금일십일만삼천오백육십원)
    - ilgeum: 민간 관습 형식(영수증·차용증·계약서). '정(整)'은 금액 뒤에
      숫자를 못 붙이게 하는 위변조 방지 관습.
      예: 일금 12,340원정(일금 일만이천삼백사십원정)
    """
    if style not in _AMOUNT_STYLES:
        raise ValueError(f"style은 {'/'.join(_AMOUNT_STYLES)} 중 하나여야 합니다: {style}")
    reading = amount_to_korean(n)
    if style == "gongmun":
        return f"금{n:,}원(금{reading}원)"
    return f"일금 {n:,}원정(일금 {reading}원정)"


def _parse_date(raw: str) -> datetime.date:
    digits = re.sub(r"\D", "", raw)
    if len(digits) != 8:
        raise ValueError(f"날짜는 YYYYMMDD 8자리여야 합니다: {raw}")
    try:
        return datetime.date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
    except ValueError as exc:
        raise ValueError(f"달력에 없는 날짜입니다: {raw}") from exc


def gongmun_date(raw: str) -> str:
    """공문 날짜 표기. 예: 20260101 → 2026.1.1.(목).
    월·일 앞 0 없음, 일 뒤 마침표, 요일 괄호 — 행안부 공문 관습."""
    d = _parse_date(raw)
    return f"{d.year}.{d.month}.{d.day}.({_WEEKDAYS[d.weekday()]})"


def korean_age(yymmdd: str, base: str | None = None) -> str:
    """주민번호 앞 6자리 → 'YYMMDD(만나이)'. YY는 19YY로 해석(주민번호 관습).
    base: 기준일 YYYYMMDD (기본 오늘)."""
    digits = re.sub(r"\D", "", yymmdd)
    if len(digits) != 6:
        raise ValueError(f"생년월일은 YYMMDD 6자리여야 합니다: {yymmdd}")
    try:
        birth = datetime.date(1900 + int(digits[:2]), int(digits[2:4]), int(digits[4:6]))
    except ValueError as exc:
        raise ValueError(f"달력에 없는 생년월일입니다: {yymmdd}") from exc
    base_date = _parse_date(base) if base else datetime.date.today()
    age = base_date.year - birth.year - (
        (base_date.month, base_date.day) < (birth.month, birth.day)
    )
    if age < 0:
        raise ValueError("기준일이 생년월일보다 앞섭니다.")
    return f"{digits}({age})"
