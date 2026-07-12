"""inspect 순수 검사함수 — 잔여물·공문 표기·PII 정규식.

format.py와 같은 원칙: 엔진 임포트 금지, LLM 판단이 아닌 결정론 검사.
각 함수는 텍스트 한 덩이를 받아 issues 목록을 반환한다:
  {"check": ..., "code": ..., "message": ..., "context": <위반 주변 원문>}
"""
from __future__ import annotations

import re

_CONTEXT_SPAN = 30


def _issue(check: str, code: str, message: str, text: str, match: re.Match) -> dict:
    start = max(0, match.start() - _CONTEXT_SPAN)
    end = min(len(text), match.end() + _CONTEXT_SPAN)
    return {"check": check, "code": code, "message": message,
            "context": text[start:end].strip()}


# ── residue: 채움 잔여물 ──────────────────────────────────────

_RESIDUE_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    ("leftover_marker", "채우지 않은 {{마커}}가 남아 있음",
     re.compile(r"\{\{[^{}]{1,40}\}\}")),
    ("placeholder_chars", "자리표시 문자(○○○·△△△·×××)가 남아 있음",
     re.compile(r"[○◯]{3,}|[△▲]{3,}|[×✕]{3,}")),
    ("example_note", "양식 안내문(예시·해당시)이 남아 있음",
     re.compile(r"\(예시[^)]{0,20}\)|←\s*해당\s*시")),
]


def check_residue_text(text: str) -> list[dict]:
    issues = []
    for code, message, pattern in _RESIDUE_PATTERNS:
        for m in pattern.finditer(text):
            issues.append(_issue("residue", code, message, text, m))
    return issues


# ── gongmun: 공문 표기 규약 ───────────────────────────────────

# 날짜: 공문은 '2026. 7. 10.' — 하이픈/슬래시 연월일은 위반
_DATE_BAD = re.compile(r"\b(19|20)\d{2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{1,2}\b")
# 시각: 공문은 24시각제 '15:00' — '오전/오후 N시(N분)'는 위반
_TIME_BAD = re.compile(r"(오전|오후)\s*\d{1,2}\s*시(\s*\d{1,2}\s*분)?")


def check_gongmun_text(text: str) -> list[dict]:
    issues = []
    for m in _DATE_BAD.finditer(text):
        issues.append(_issue("gongmun", "date_style",
                             "공문 날짜 표기는 '2026. 7. 10.' 형식 — 하이픈/슬래시 표기 위반",
                             text, m))
    for m in _TIME_BAD.finditer(text):
        issues.append(_issue("gongmun", "time_style",
                             "공문 시각은 24시각제 '15:00' — 오전/오후 표기 위반",
                             text, m))
    return issues


# ── pii: 개인정보 잔존 ────────────────────────────────────────

_RRN = re.compile(r"\b\d{6}\s*-\s*[1-4]\d{6}\b")           # 주민등록번호
_PHONE = re.compile(r"\b01[016789]\s*-\s*\d{3,4}\s*-\s*\d{4}\b")  # 휴대전화
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")


def check_pii_text(text: str) -> list[dict]:
    issues = []
    for m in _RRN.finditer(text):
        issues.append(_issue("pii", "rrn", "주민등록번호 패턴 발견 — 제출 전 확인", text, m))
    for m in _PHONE.finditer(text):
        issues.append(_issue("pii", "phone", "휴대전화 번호 발견 — 공개 배포 시 확인", text, m))
    for m in _EMAIL.finditer(text):
        issues.append(_issue("pii", "email", "이메일 주소 발견 — 공개 배포 시 확인", text, m))
    return issues


CHECKS = {
    "residue": check_residue_text,
    "gongmun": check_gongmun_text,
    "pii": check_pii_text,
}
