"""inspect — 제출 전 기계 검수 (잔여물·공문 표기·PII).

fmt와 같은 원칙: LLM 판단이 아니라 정규식 순수함수. 위반이 있으면 exit 2.
"""
import json

import pytest

from hwpx_kit.cli import main
from hwpx_kit.commands.inspect_doc import run_inspect
from hwpx_kit.inspect_rules import (
    check_gongmun_text,
    check_pii_text,
    check_residue_text,
)


# ── 순수함수 단위 ──────────────────────────────────────────────

def test_residue_detects_leftover_marker():
    issues = check_residue_text("성명: {{성명}}")
    assert any(i["code"] == "leftover_marker" for i in issues)


def test_residue_detects_placeholder_chars():
    assert check_residue_text("주최: ○○○")
    assert check_residue_text("(예시입니다)")
    assert check_residue_text("←해당시 기재")
    assert not check_residue_text("정상 문장입니다.")


def test_gongmun_date_style():
    # 공문 날짜는 '2026. 7. 10.' — 하이픈/슬래시 표기는 위반
    issues = check_gongmun_text("개최일: 2026-07-10")
    assert any(i["code"] == "date_style" for i in issues)
    issues = check_gongmun_text("개최일: 2026/07/10")
    assert any(i["code"] == "date_style" for i in issues)
    assert not any(i["code"] == "date_style"
                   for i in check_gongmun_text("개최일: 2026. 7. 10.(금)"))


def test_gongmun_time_style():
    # 24시각제 — '오후 3시'는 위반, '15:00'은 통과
    issues = check_gongmun_text("행사 시작 오후 3시")
    assert any(i["code"] == "time_style" for i in issues)
    assert not any(i["code"] == "time_style"
                   for i in check_gongmun_text("행사 시작 15:00"))


def test_pii_patterns():
    issues = check_pii_text("주민등록번호 900101-1234567")
    assert any(i["code"] == "rrn" for i in issues)
    issues = check_pii_text("연락처 010-1234-5678")
    assert any(i["code"] == "phone" for i in issues)
    assert not check_pii_text("사업번호 2026-001, 예산 1,234천원")


# ── 문서 단위 ─────────────────────────────────────────────────

@pytest.fixture()
def dirty_doc(tmp_path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        doc.add_paragraph("행사 계획")
        doc.add_paragraph("대상: {{대상}}")            # 잔여 마커
        doc.add_paragraph("일시: 2026-07-10 오후 3시")  # 공문 표기 위반 2건
        doc.add_paragraph("담당 010-1234-5678")        # PII
        path = str(tmp_path / "dirty.hwpx")
        doc.save_to_path(path)
    return path


@pytest.fixture()
def clean_doc(tmp_path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        doc.add_paragraph("행사 계획")
        doc.add_paragraph("일시: 2026. 7. 10.(금) 15:00")
        path = str(tmp_path / "clean.hwpx")
        doc.save_to_path(path)
    return path


def test_run_inspect_finds_all_categories(dirty_doc):
    data = run_inspect(dirty_doc, checks=["residue", "gongmun", "pii"])
    codes = {i["code"] for i in data["issues"]}
    assert "leftover_marker" in codes
    assert "date_style" in codes and "time_style" in codes
    assert "phone" in codes
    assert data["clean"] is False


def test_run_inspect_clean_doc(clean_doc):
    data = run_inspect(clean_doc, checks=["residue", "gongmun", "pii"])
    assert data["clean"] is True and data["issues"] == []


def test_run_inspect_check_filter(dirty_doc):
    data = run_inspect(dirty_doc, checks=["pii"])
    assert all(i["check"] == "pii" for i in data["issues"])


def test_cli_inspect_exit_codes(dirty_doc, clean_doc, capsys):
    code = main(["inspect", dirty_doc, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 2                       # 위반 있음 = 부분 성공
    assert env["ok"] is True and env["data"]["clean"] is False

    code = main(["inspect", clean_doc, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and env["data"]["clean"] is True


# ── gongmun 확장 규칙 (0.8.0) ────────────────────────────────

from hwpx_kit.inspect_rules import check_gongmun_text


def _codes(issues):
    return {i["code"] for i in issues}


def test_gongmun_zero_padded_date():
    assert "date_zero_pad" in _codes(check_gongmun_text("시행일: 2026. 07. 01."))


def test_gongmun_missing_trailing_dot():
    assert "date_no_trailing_dot" in _codes(check_gongmun_text("기한: 2026. 7. 14 까지"))


def test_gongmun_hour_minute_style():
    assert "time_hour_minute" in _codes(check_gongmun_text("회의는 14시 30분에 시작"))
    assert "time_hour_minute" not in _codes(check_gongmun_text("소요 3시간 30분"))


def test_gongmun_tilde_kkaji_duplicate():
    assert "period_kkaji" in _codes(check_gongmun_text("2026. 1. 1. ~ 12. 31.까지"))


def test_gongmun_geum_spacing():
    assert "amount_geum_spacing" in _codes(check_gongmun_text("계약금액: 금 13,000,000원"))
    assert "amount_geum_spacing" not in _codes(check_gongmun_text("금13,000,000원"))


def test_gongmun_clean_text_passes():
    ok = "일시: 2026. 7. 14.(화) 15:00 / 금액: 금1,000원 / 기간: 1. 1. ~ 12. 31."
    assert check_gongmun_text(ok) == []
