"""fill-batch 명령 — 명단 × 양식 메일머지.

명단(xlsx/csv/json)의 행마다 fill 템플릿의 {열이름}을 치환해 run_fill을
반복하고, 파일명 패턴으로 사본 N부를 만든다. 원본 불변은 fill과 동일.
"""
from __future__ import annotations

import csv
import json
import os
import re

from hwpx_kit.commands.fill import run_fill

_FORBIDDEN_FILENAME = re.compile(r'[\\/:*?"<>|]')


def load_rows(rows_path: str) -> list[dict[str, str]]:
    """명단 파일 → 행 dict 목록. xlsx는 1행을 헤더로 본다."""
    ext = os.path.splitext(rows_path)[1].lower()
    if ext == ".json":
        with open(rows_path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("명단 JSON은 객체 배열이어야 합니다: [{\"성명\": ...}, ...]")
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in data]
    if ext == ".csv":
        with open(rows_path, encoding="utf-8-sig", newline="") as f:
            return [dict(row) for row in csv.DictReader(f)]
    if ext == ".xlsx":
        import openpyxl

        ws = openpyxl.load_workbook(rows_path, data_only=True).active
        rows_iter = ws.iter_rows(values_only=True)
        header = [str(h) if h is not None else "" for h in next(rows_iter, [])]
        rows = []
        for values in rows_iter:
            if values is None or all(v is None for v in values):
                continue
            rows.append({
                header[i]: "" if v is None else str(v)
                for i, v in enumerate(values) if i < len(header) and header[i]
            })
        return rows
    raise ValueError(f"지원하지 않는 명단 형식: {ext} (xlsx/csv/json)")


def _substitute(template: str, row: dict[str, str]) -> str:
    out = template
    for key, value in row.items():
        out = out.replace("{" + key + "}", value)
    return out


def _unique_path(out_dir: str, name: str) -> str:
    base, ext = os.path.splitext(name)
    candidate = os.path.join(out_dir, name)
    n = 2
    while os.path.exists(candidate):
        candidate = os.path.join(out_dir, f"{base}_{n}{ext}")
        n += 1
    return candidate


def run_fill_batch(path: str, rows_path: str, template_path: str,
                   out_dir: str, name_pattern: str) -> dict:
    with open(template_path, encoding="utf-8") as f:
        template: dict[str, str] = json.load(f)

    rows = load_rows(rows_path)
    if not rows:
        raise ValueError("명단이 비어 있습니다.")
    os.makedirs(out_dir, exist_ok=True)

    results = []
    succeeded = 0
    for i, row in enumerate(rows):
        data = {k: _substitute(str(v), row) for k, v in template.items()}
        name = _FORBIDDEN_FILENAME.sub("_", _substitute(name_pattern, row))
        out_path = _unique_path(out_dir, name)
        try:
            fill_result = run_fill(path, data, out_path)
            ok = not fill_result["unmatched"]
            if ok:
                succeeded += 1
            results.append({
                "row": i, "out": fill_result["out"], "ok": ok,
                "applied": fill_result["applied"],
                "unmatched": fill_result["unmatched"],
            })
        except Exception as exc:
            results.append({"row": i, "out": None, "ok": False,
                            "applied": [], "unmatched": [],
                            "error": str(exc)})

    return {
        "file": path,
        "out_dir": os.path.abspath(out_dir),
        "total": len(rows),
        "succeeded": succeeded,
        "all_ok": succeeded == len(rows),
        "rows": results,
    }
