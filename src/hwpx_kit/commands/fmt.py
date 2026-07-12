"""fmt 명령 — 결정론 표기 변환 (파일 입력 없음).

정확히 하나의 변환 대상(amount/date/age)을 받아 envelope로 반환.
"""
from __future__ import annotations

from hwpx_kit.format import format_amount, gongmun_date, korean_age, scale_amount


def run_fmt(
    amount: str | None = None,
    date: str | None = None,
    age: str | None = None,
    base: str | None = None,
    style: str = "gongmun",
    scale: str | None = None,
    unit: str = "천원",
) -> dict:
    targets = [k for k, v in (("amount", amount), ("date", date), ("age", age),
                              ("scale", scale)) if v is not None]
    if len(targets) != 1:
        raise ValueError("--amount / --date / --age / --scale 중 정확히 하나를 지정하세요.")

    if scale is not None:
        cleaned = scale.replace(",", "").strip()
        if not cleaned.isdigit():
            raise ValueError(f"금액은 정수여야 합니다: {scale}")
        return {"kind": "scale", "input": scale, "unit": unit,
                "result": scale_amount(int(cleaned), unit)}

    if amount is not None:
        cleaned = amount.replace(",", "").strip()
        if not cleaned.isdigit():
            raise ValueError(f"금액은 정수여야 합니다: {amount}")
        result = format_amount(int(cleaned), style=style)
        return {"kind": "amount", "input": amount, "style": style, "result": result}
    if date is not None:
        return {"kind": "date", "input": date, "result": gongmun_date(date)}
    return {"kind": "age", "input": age, "base": base, "result": korean_age(age, base=base)}
