"""open-check — 한글이 실제로 파일을 여는지 확인 (최종 게이트).

validate(구조)·inspect(정적)를 통과해도 한글이 스키마 수준에서 거부하는
파일이 있다 (실증: 도형 네임스페이스·다단 중복). 한글을 COM으로 백그라운드
구동해 실열림을 확인한다 — Windows + 한글(한컴오피스) 필요.
열리지 않으면 CLI가 exit 2 (게이트로 쓸 수 있게).
"""
from __future__ import annotations

import os

from hwpx_kit.commands.convert import AUTO_ANSWER_MODE, _load_hwp_com
from hwpx_kit.output import quiet_engine


def run_open_check(path: str) -> dict:
    src = os.path.abspath(path)
    with quiet_engine():
        hwp_cls = _load_hwp_com()
        hwp = hwp_cls(visible=False)
        try:
            if hasattr(hwp, "set_message_box_mode"):
                hwp.set_message_box_mode(AUTO_ANSWER_MODE)
            try:
                opens = bool(hwp.open(src))
            except Exception:
                opens = False
        finally:
            hwp.quit()
    return {
        "file": src,
        "opens": opens,
        "note": None if opens else
        "한글이 파일을 열지 못했습니다 — 구조가 스키마를 벗어났을 가능성. "
        "validate/inspect 통과와 별개의 최종 게이트입니다.",
    }
