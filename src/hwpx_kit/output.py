"""JSON 봉투와 stdout 위생.

python-hwpx는 manifest fallback 등 경고를 print()로 stdout에 쓴다.
--json 모드에서 stdout은 JSON 봉투 한 줄만 허용되므로, 엔진 호출은
quiet_engine()으로 감싸 노이즈를 warnings로 회수한다.
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import contextmanager


def envelope(command, ok, data=None, warnings=None, error=None):
    env = {"ok": ok, "command": command}
    if data is not None:
        env["data"] = data
    env["warnings"] = warnings or []
    if error is not None:
        env["error"] = error
    return env


@contextmanager
def quiet_engine():
    captured: list[str] = []
    buf = io.StringIO()
    orig = sys.stdout
    sys.stdout = buf
    try:
        yield captured
    finally:
        sys.stdout = orig
        captured.extend(line for line in buf.getvalue().splitlines() if line.strip())


def print_result(env, as_json):
    if as_json:
        print(json.dumps(env, ensure_ascii=False))
        return
    status = "OK" if env["ok"] else "ERROR"
    print(f"[{status}] {env['command']}")
    for w in env["warnings"]:
        print(f"  warning: {w}")
    if not env["ok"]:
        err = env.get("error") or {}
        print(f"  {err.get('code', '?')}: {err.get('message', '')}")
