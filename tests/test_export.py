"""hwpx → 타 형식(docx) 내보내기 — 한글 COM SaveAs 경유.

카이스트 실의뢰(2026-07-10)로 확인된 요구: 같은 내용을 한글과 워드 둘 다로.
한글 COM은 format="OOXML"로 docx를 저장한다 ("DOCX"/"MSWORD" 문자열은 거부 — 실탐침 결과).
"""
import importlib.util

import pytest

from hwpx_kit.commands.export import run_export


def test_export_rejects_non_hwpx(tmp_path):
    f = tmp_path / "doc.hwp"
    f.write_bytes(b"x")
    with pytest.raises(ValueError):
        run_export(str(f))


def test_export_rejects_unknown_format(tmp_path):
    f = tmp_path / "doc.hwpx"
    f.write_bytes(b"x")
    with pytest.raises(ValueError, match="docx"):
        run_export(str(f), to="hwp")


def test_export_uses_ooxml_format_and_auto_answers_dialogs(monkeypatch, tmp_path, capsys):
    """save_as는 OOXML 문자열로 호출돼야 하고(DOCX는 조용히 실패), 저장 경고
    팝업 무한대기 방지를 위해 메시지박스 자동응답을 켜야 한다. stdout은 침묵."""
    import hwpx_kit.commands.convert as conv

    calls = {}

    class FakeHwp:
        def __init__(self, visible=False):
            print("RegisterModule noise")

        def set_message_box_mode(self, mode):
            calls["msgbox"] = mode
            return 0

        def open(self, path):
            return True

        def save_as(self, out, format=""):
            calls["format"] = format
            with open(out, "wb") as fh:
                fh.write(b"x")
            return True

        def quit(self):
            pass

    monkeypatch.setattr(conv, "_load_hwp_com", lambda: FakeHwp)
    f = tmp_path / "doc.hwpx"
    f.write_bytes(b"x")
    result = run_export(str(f))
    assert calls["format"] == "OOXML"
    assert calls.get("msgbox") is not None
    assert result["out"].endswith(".docx")
    assert capsys.readouterr().out == ""


_HAS_COM = importlib.util.find_spec("pyhwpx") is not None


@pytest.mark.skipif(not _HAS_COM, reason="pyhwpx/한글 COM 없는 환경")
def test_export_real_docx_roundtrip(tmp_path, marker_doc):
    """실제 한글 COM으로 docx 저장 후 read로 내용 보존 확인. 느림(한글 구동)."""
    from hwpx_kit.adapter.kordoc_engine import kordoc_available
    from hwpx_kit.commands.read import run_read

    out = str(tmp_path / "exported.docx")
    result = run_export(marker_doc, out_path=out)
    assert result["out"] == out

    if not kordoc_available():
        pytest.skip("kordoc 없음 — docx 내용 검증 생략")
    content = run_read(out, fmt="text")["content"]
    assert "출장 신청서" in content
