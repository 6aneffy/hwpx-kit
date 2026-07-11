"""kordoc(MIT, chrisryugj/kordoc) 래퍼 — 레거시/타 포맷 읽기·렌더·생성 엔진.

python-hwpx가 못 하는 것을 맡는다:
- .hwp(HWP3/5)·PDF·DOCX·XLSX → Markdown (한글 프로그램 불필요)
- HWPX → SVG 렌더 (눈 검증용)
- Markdown → 공문서 HWPX 생성

공급망 보험: github.com/6aneffy/kordoc 포크 유지, 검증 버전 KNOWN_GOOD_VERSION.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

KNOWN_GOOD_VERSION = "3.18.0"

# kordoc가 읽을 수 있는 확장자 (hwpx는 python-hwpx가 담당)
KORDOC_READ_EXTS = {".hwp", ".hwpml", ".pdf", ".docx", ".xlsx", ".xls"}

_INSTALL_HINT = (
    "kordoc가 필요합니다 (Node.js 18+ 필요). 설치: npm install -g kordoc"
)


def kordoc_available() -> bool:
    return shutil.which("kordoc") is not None


def _run(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    exe = shutil.which("kordoc")
    if exe is None:
        raise RuntimeError(_INSTALL_HINT)
    proc = subprocess.run(
        [exe, *args], capture_output=True, timeout=timeout,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()[:300]
        raise RuntimeError(f"kordoc 실행 실패: {detail or '알 수 없는 오류'}")
    return proc


class KordocAdapter:
    """서브프로세스 기반이라 상태 없음 — 전부 정적 메서드."""

    @staticmethod
    def convert_to_markdown(path: str) -> str:
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out.md")
            _run([os.path.abspath(path), "-o", out, "--silent"])
            with open(out, encoding="utf-8") as fh:
                return fh.read()

    @staticmethod
    def render_svg(path: str, out_path: str) -> str:
        """조판 캐시가 있으면 원본 조판 렌더, 없으면(비한컴 저장본) reflow 합성 렌더."""
        out_abs = os.path.abspath(out_path)
        src = os.path.abspath(path)
        try:
            _run(["render", src, "-o", out_abs, "--silent"])
        except RuntimeError as exc:
            if "linesegarray" not in str(exc) and "조판 캐시" not in str(exc):
                raise
            _run(["render", src, "--reflow", "-o", out_abs, "--silent"])
        if not os.path.exists(out_abs):
            raise RuntimeError("kordoc render가 SVG를 생성하지 못했습니다.")
        return out_abs

    @staticmethod
    def generate_hwpx(markdown_path: str, out_path: str, preset: str | None = None) -> str:
        out_abs = os.path.abspath(out_path)
        args = ["generate", os.path.abspath(markdown_path), "-o", out_abs, "--silent"]
        if preset:
            args += ["--preset", preset]
        _run(args)
        if not os.path.exists(out_abs):
            raise RuntimeError("kordoc generate가 파일을 생성하지 못했습니다.")
        return out_abs
