"""구형 .hwp → .hwpx 변환.

Windows + 한글(한컴오피스) 설치 환경에서만 동작 — 한글을 COM으로 백그라운드
구동해 다른 형식으로 저장한다. 서버/타 OS에서는 명확한 에러를 낸다.
"""
from __future__ import annotations

import os

from hwpx_kit.output import quiet_engine

# visible=False 팝업 무한대기 방지 — 자동응답: 확인(0x1) / 확인·취소→확인(0x10)
# / 종료·재시도·무시→무시(0x400) / 예·아니오·취소→예(0x1000) / 예·아니오→예(0x10000)
# / 재시도·취소→취소(0x200000)
AUTO_ANSWER_MODE = 0x1 | 0x10 | 0x400 | 0x1000 | 0x10000 | 0x200000


def _ensure_security_module() -> bool:
    """한글 보안모듈(FilePathCheckerModule)을 레지스트리에 등록해 접근 경고
    팝업을 억제한다.

    외부 프로그램이 한글 COM으로 파일을 열면 한글이 "손상/유출 위험" 승인
    팝업을 띄운다. pyhwpx가 자동 등록을 시도하나, register_regedit가
    레지스트리 키를 OpenKey(KEY_WRITE)로 여는 탓에 **키가 처음부터 없는
    환경(신규 PC 다수)에서는 실패**한다. 여기서는 CreateKeyEx로 키를 만들어
    번들 DLL 경로를 확실히 등록한다 — 실사용자 팝업 방지의 핵심.
    이미 등록됐으면 아무것도 안 함. 성공/이미등록이면 True.
    """
    try:
        from pyhwpx.core import check_registry_key
    except ImportError:
        return False
    if check_registry_key():
        return True
    try:
        import os
        from importlib.resources import files
        from winreg import (
            HKEY_CURRENT_USER, KEY_WRITE, REG_SZ, CloseKey, ConnectRegistry,
            CreateKeyEx, SetValueEx,
        )

        dll = str(files("pyhwpx").joinpath("FilePathCheckerModule.dll"))
        if not os.path.exists(dll):
            return False
        reg = ConnectRegistry(None, HKEY_CURRENT_USER)
        # OpenKey와 달리 CreateKeyEx는 중간 키까지 없으면 생성한다
        key = CreateKeyEx(reg, r"Software\HNC\HwpAutomation\Modules", 0, KEY_WRITE)
        SetValueEx(key, "FilePathCheckerModule", 0, REG_SZ, dll)
        CloseKey(key)
        return check_registry_key()
    except Exception:
        return False


def _load_hwp_com():
    """pyhwpx.Hwp 클래스를 반환. 불가 환경이면 RuntimeError.

    반환 전에 보안모듈 등록을 보장해 COM 접근 경고 팝업을 억제한다.
    """
    try:
        from pyhwpx import Hwp
    except ImportError as exc:
        raise RuntimeError(
            "hwp 변환에는 Windows + 한글(한컴오피스) + pyhwpx가 필요합니다. "
            "설치: pip install pyhwpx"
        ) from exc
    _ensure_security_module()
    return Hwp


def run_convert(path: str, out_path: str | None = None) -> dict:
    if not path.lower().endswith(".hwp"):
        raise ValueError("convert 입력은 .hwp 파일이어야 합니다 (.hwpx는 변환 불필요)")
    src = os.path.abspath(path)
    out = os.path.abspath(out_path) if out_path else src[: -len(".hwp")] + ".hwpx"
    if out == src:
        raise ValueError("출력 경로가 원본과 같습니다.")

    # pyhwpx는 RegisterModule 실패 등을 print()로 stdout에 씀 —
    # --json 봉투 오염 방지 (절대 규칙: JSON 모드 stdout은 봉투 한 줄만)
    with quiet_engine():
        hwp_cls = _load_hwp_com()
        hwp = hwp_cls(visible=False)
        try:
            if hasattr(hwp, "set_message_box_mode"):
                hwp.set_message_box_mode(AUTO_ANSWER_MODE)
            if not hwp.open(src):
                raise RuntimeError(f"한글이 파일을 열지 못했습니다: {src}")
            if not hwp.save_as(out, format="HWPX"):
                raise RuntimeError(f"HWPX 저장에 실패했습니다: {out}")
        finally:
            hwp.quit()
    return {"file": src, "out": out}
