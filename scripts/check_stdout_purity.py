"""서브프로세스에서 --json stdout이 순수 JSON(UTF-8)인지 바이트 레벨 검증."""
import json
import subprocess
import sys

p = subprocess.run(
    [sys.executable, "-m", "hwpx_kit.cli", "analyze", "sample-form.hwpx", "--json"],
    capture_output=True,
)
stdout_lines = p.stdout.strip().splitlines()
print("stdout line count:", len(stdout_lines))
print("stderr byte count:", len(p.stderr))
env = json.loads(p.stdout.decode("utf-8"))
assert env["ok"] is True
print("STDOUT_IS_PURE_UTF8_JSON: True")
