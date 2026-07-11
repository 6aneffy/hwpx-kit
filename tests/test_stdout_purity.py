"""서브프로세스 기준 --json stdout 순수성: UTF-8 JSON 한 줄, 노이즈는 stderr로만."""
import json
import subprocess
import sys


def test_json_stdout_is_pure_utf8_single_line(marker_doc):
    p = subprocess.run(
        [sys.executable, "-m", "hwpx_kit.cli", "analyze", marker_doc, "--json"],
        capture_output=True,
    )
    assert p.returncode == 0
    lines = p.stdout.strip().splitlines()
    assert len(lines) == 1
    env = json.loads(lines[0].decode("utf-8"))
    assert env["ok"] is True


def test_stderr_is_utf8(marker_doc):
    """stderr(엔진 한글 경고)도 UTF-8 — 콘솔 코드페이지(cp949)로 나가면
    리다이렉트한 로그가 깨진다 (수렴 테스트 중 실제로 겪음)."""
    p = subprocess.run(
        [sys.executable, "-m", "hwpx_kit.cli", "analyze", marker_doc, "--json"],
        capture_output=True,
    )
    assert p.stderr, "엔진 경고가 stderr로 나와야 유효한 테스트"
    p.stderr.decode("utf-8")  # cp949로 인코딩됐으면 여기서 UnicodeDecodeError
