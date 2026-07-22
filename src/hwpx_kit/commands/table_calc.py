"""table-sum 명령 — 표 셀 수치 합계·평균을 결정론으로 계산해 대상 셀에 기입.

지식 스킬 table-calc(읽기→계산→fill)를 원샷 CLI로. 암산 금지 원칙 —
계산은 Decimal로 하고 사사오입(ROUND_HALF_UP)·세 자리 콤마를 도구가 보장.
셀 읽기는 table_map, 착지는 set_table_cells 재사용.
"""
from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter


def parse_number(text: str) -> Decimal | None:
    """셀 텍스트 → 수치. 콤마·공백·단위글자 제거. 선두 △/▽/-는 음수
    (행정 관습: △=감소). 숫자가 없으면 None (합계에서 건너뜀)."""
    s = (text or "").strip()
    if not s:
        return None
    neg = s[0] in "△▽-"
    digits = re.findall(r"\d[\d,]*(?:\.\d+)?", s)
    if not digits:
        return None
    try:
        val = Decimal(digits[0].replace(",", ""))
    except Exception:
        return None
    return -val if neg else val


def compute(values: list[Decimal], op: str) -> Decimal:
    """sum/avg. 빈 목록이면 거부 (계산 대상 없음)."""
    if not values:
        raise ValueError("계산할 숫자 셀이 없습니다 (모두 비었거나 숫자 아님).")
    total = sum(values, Decimal(0))
    if op == "sum":
        return total
    if op == "avg":
        return total / Decimal(len(values))
    raise ValueError(f"op는 sum/avg 중 하나: {op}")


def format_result(value: Decimal, decimals: int = 0) -> str:
    """세 자리 콤마 + 지정 소수 자릿수 (사사오입)."""
    if decimals < 0:
        raise ValueError(f"decimals는 0 이상: {decimals}")
    q = Decimal(1).scaleb(-decimals) if decimals else Decimal(1)
    return f"{value.quantize(q, rounding=ROUND_HALF_UP):,}"


def parse_cells_spec(spec: str) -> list[tuple[int, int]]:
    """'R,C;R,C;...' → [(r,c), ...]."""
    out = []
    for token in spec.split(";"):
        token = token.strip()
        if not token:
            continue
        parts = token.split(",")
        if len(parts) != 2:
            raise ValueError(f"셀 형식은 'R,C': {token!r}")
        try:
            out.append((int(parts[0]), int(parts[1])))
        except ValueError as exc:
            raise ValueError(f"좌표는 정수여야 합니다: {token!r}") from exc
    if not out:
        raise ValueError("셀을 하나 이상 지정하세요.")
    return out


def _read_grid(ad: HwpxEngineAdapter, table_index: int) -> dict[tuple[int, int], str]:
    tmap = ad.table_map()
    tables = tmap.get("tables", [])
    if not 0 <= table_index < len(tables):
        raise ValueError(f"표 인덱스 범위 밖: {table_index} (표 {len(tables)}개)")
    grid = {}
    for cell in tables[table_index].get("cells", []):
        grid[(cell["row"], cell["col"])] = cell.get("text", "")
    return grid


def run_table_sum(path: str, table: int, cells: list[tuple[int, int]],
                  into: tuple[int, int], out_path: str, op: str = "sum",
                  decimals: int = 0) -> dict:
    """cells의 수치를 op로 계산해 into 셀에 콤마 형식으로 기입."""
    ad = HwpxEngineAdapter.open(path)
    grid = _read_grid(ad, table)
    nums, skipped = [], []
    for (r, c) in cells:
        n = parse_number(grid.get((r, c), ""))
        if n is None:
            skipped.append([r, c])
        else:
            nums.append(n)
    result = compute(nums, op)
    text = format_result(result, decimals)
    ad.set_table_cells(table_index=table, assignments=[(into[0], into[1], text)])
    out = ad.save_copy(out_path)
    return {"file": path, "out": out, "table": table, "op": op,
            "into": [into[0], into[1]], "result": text,
            "counted": len(nums), "skipped": skipped}
