import importlib.util

import pytest

from hwpx_kit.commands.convert import run_convert


def test_convert_rejects_non_hwp(tmp_path):
    f = tmp_path / "doc.hwpx"
    f.write_bytes(b"x")
    with pytest.raises(ValueError):
        run_convert(str(f))


def test_convert_error_without_pyhwpx(monkeypatch, tmp_path):
    """pyhwpx 부재 환경에서는 설치 안내가 담긴 RuntimeError."""
    import hwpx_kit.commands.convert as conv

    def boom():
        raise RuntimeError("hwp 변환에는 Windows + 한글(한컴오피스) + pyhwpx가 필요합니다.")

    monkeypatch.setattr(conv, "_load_hwp_com", boom)
    f = tmp_path / "doc.hwp"
    f.write_bytes(b"x")
    with pytest.raises(RuntimeError, match="한글"):
        run_convert(str(f))


def test_convert_stdout_silent_even_if_engine_prints(monkeypatch, tmp_path, capsys):
    """pyhwpx는 RegisterModule 실패 등을 print()로 stdout에 쓴다 —
    --json 봉투 앞에 붙어 파서를 깨뜨리므로 convert도 quiet_engine 필수."""
    import hwpx_kit.commands.convert as conv

    class FakeHwp:
        def __init__(self, visible=False):
            print("RegisterModule 액션을 실행할 수 없음 (흉내)")

        def open(self, path):
            print("open noise")
            return True

        def save_as(self, out, format=""):
            with open(out, "wb") as fh:
                fh.write(b"x")
            return True

        def quit(self):
            print("quit noise")

    monkeypatch.setattr(conv, "_load_hwp_com", lambda: FakeHwp)
    f = tmp_path / "doc.hwp"
    f.write_bytes(b"x")
    run_convert(str(f))
    assert capsys.readouterr().out == ""


_HAS_COM = importlib.util.find_spec("pyhwpx") is not None


@pytest.mark.skipif(not _HAS_COM, reason="pyhwpx/한글 COM 없는 환경")
def test_convert_real_roundtrip(tmp_path, marker_doc):
    """한글 COM으로 hwpx→hwp 저장 후 convert로 되돌려 내용 보존 확인. 느림(한글 구동)."""
    from pyhwpx import Hwp

    from hwpx_kit.commands.read import run_read

    hwp_file = str(tmp_path / "legacy.hwp")
    hwp = Hwp(visible=False)
    try:
        assert hwp.open(marker_doc)
        assert hwp.save_as(hwp_file, format="HWP")
    finally:
        hwp.quit()

    result = run_convert(hwp_file)
    assert result["out"].endswith(".hwpx")
    content = run_read(result["out"], fmt="text")["content"]
    assert "출장 신청서" in content


def test_ensure_security_module_creates_registry_key():
    """보안모듈 미등록 환경에서 레지스트리 키를 생성해 팝업을 억제한다.
    pyhwpx register_regedit는 키 부재 시 OpenKey로 실패 — 우리는 CreateKey로 견고.
    (Windows 전용, pyhwpx 있을 때만)"""
    import importlib.util
    import pytest as _pytest

    if importlib.util.find_spec("pyhwpx") is None:
        _pytest.skip("pyhwpx 없는 환경")

    from hwpx_kit.commands.convert import _ensure_security_module
    from pyhwpx.core import check_registry_key

    ok = _ensure_security_module()
    assert ok is True
    assert check_registry_key() is True
    # 멱등 — 두 번째 호출도 안전
    assert _ensure_security_module() is True
