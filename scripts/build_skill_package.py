"""플러그인 배포 번들 빌드 — 오프라인 zip 생성.

레포가 비공개라 외부 사용자는 git 설치가 불가 — wheel과 Claude Code 플러그인
(스킬 모음), 자체 설치 스크립트를 하나의 zip으로 묶어 전달한다.

사용: uv run python scripts/build_skill_package.py [--out dist]
산출: <out>/hwpx-kit-plugin-<버전>.zip
  ├── hwpx-kit-plugin/           ← 플러그인 겸 자기-마켓플레이스 (통째 복사)
  │   ├── .claude-plugin/{plugin.json, marketplace.json}
  │   └── skills/*/SKILL.md
  ├── hwpx_kit-<버전>-*.whl      ← CLI 런타임
  ├── install.ps1 / install.sh   ← wheel 설치 + 플러그인 등록
  └── README.md
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

INSTALL_PS1 = """\
# hwpx-kit 플러그인 번들 설치 (Windows) — 번들 폴더에서 실행
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "Python 3.10+ 가 필요합니다. https://www.python.org/downloads/ 에서 설치 후 다시 실행하세요."
    exit 1
}
$ver = & python -c "import sys; print(sys.version_info >= (3, 10))"
if ($ver.Trim() -ne "True") {
    Write-Host "Python 3.10 이상이 필요합니다. 현재: $(& python --version)"
    exit 1
}

$wheel = Get-ChildItem "$here\\hwpx_kit-*.whl" | Select-Object -First 1
if (-not $wheel) { Write-Host "번들에 wheel이 없습니다."; exit 1 }

Write-Host "hwpx-kit CLI 설치 중..."
& python -m pip install --user --upgrade $wheel.FullName
if ($LASTEXITCODE -ne 0) { Write-Host "설치 실패"; exit 1 }

# .hwp 변환/워드 내보내기용 (선택 — 실패해도 convert/export만 비활성)
& python -m pip install --user --upgrade pyhwpx *> $null
if ($LASTEXITCODE -ne 0) { Write-Host "참고: pyhwpx 설치 실패 — convert(.hwp 변환)/export(워드) 사용 불가" }

# kordoc — 조건부 옵션 (한글 없는 환경의 구형 .hwp 읽기·문서 생성 전용).
# npm이 이미 있으면 조용히 설치 시도, 없으면 아무 것도 요구하지 않는다 —
# PDF/DOCX/XLSX 읽기는 내장(파이썬)이라 kordoc 불필요.
$npm = Get-Command npm -ErrorAction SilentlyContinue
if ($npm) {
    & npm install -g "kordoc@3.18.0" *> $null
    if ($LASTEXITCODE -eq 0) { Write-Host "kordoc 3.18.0 설치됨 (구형 .hwp 직접 읽기 활성)" }
}

& python -m hwpx_kit.cli --version
if ($LASTEXITCODE -ne 0) { Write-Host "설치 확인 실패"; exit 1 }

# Claude Code 플러그인 등록 (마켓플레이스가 이 경로를 참조하므로 안정 위치에 복사)
$pluginDir = "$env:USERPROFILE\\.hwpx-kit\\plugin"
New-Item -ItemType Directory -Force (Split-Path $pluginDir) | Out-Null
if (Test-Path $pluginDir) { Remove-Item -Recurse -Force $pluginDir }
Copy-Item -Recurse "$here\\hwpx-kit-plugin" $pluginDir

# 구 단일 스킬 잔재 제거 (플러그인과 이중 트리거 방지)
$legacy = "$env:USERPROFILE\\.claude\\skills\\hwpx-kit"
if (Test-Path $legacy) { Remove-Item -Recurse -Force $legacy; Write-Host "구버전 단일 스킬 제거됨" }

$claude = Get-Command claude -ErrorAction SilentlyContinue
if ($claude) {
    & claude plugin marketplace add $pluginDir 2>$null
    & claude plugin install "hwpx-kit@hwpx-kit-market" 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Host "Claude Code 플러그인 설치됨 (hwpx-kit@hwpx-kit-market)" }
    else { Write-Host "플러그인 자동 등록 실패 — Claude Code에서 직접: /plugin marketplace add $pluginDir 후 /plugin install hwpx-kit@hwpx-kit-market" }
} else {
    Write-Host "Claude Code CLI가 없어 자동 등록을 건너뜁니다."
    Write-Host "Claude Code에서 직접 실행: /plugin marketplace add $pluginDir"
    Write-Host "                         /plugin install hwpx-kit@hwpx-kit-market"
}

Write-Host "완료. 새 터미널에서 'hwpx-kit --version', Claude Code 새 세션에서 hwpx 작업을 요청하세요."
"""

INSTALL_SH = """\
#!/usr/bin/env bash
# hwpx-kit 플러그인 번들 설치 (macOS/Linux) — 번들 폴더에서 실행
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 >/dev/null; then
    echo "Python 3.10+ 가 필요합니다."; exit 1
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \\
    || { echo "Python 3.10 이상 필요. 현재: $(python3 --version)"; exit 1; }

WHEEL="$(ls "$HERE"/hwpx_kit-*.whl | head -n 1)"
echo "hwpx-kit CLI 설치 중..."
python3 -m pip install --user --upgrade "$WHEEL"

# kordoc — 조건부 옵션 (한글 없는 환경의 구형 .hwp 전용). npm 있으면 조용히 시도
if command -v npm >/dev/null; then
    npm install -g kordoc@3.18.0 >/dev/null 2>&1 \\
        && echo "kordoc 3.18.0 설치됨 (구형 .hwp 직접 읽기 활성)" || true
fi

python3 -m hwpx_kit.cli --version

PLUGIN_DIR="$HOME/.hwpx-kit/plugin"
mkdir -p "$(dirname "$PLUGIN_DIR")"
rm -rf "$PLUGIN_DIR"
cp -R "$HERE/hwpx-kit-plugin" "$PLUGIN_DIR"

# 구 단일 스킬 잔재 제거 (플러그인과 이중 트리거 방지)
rm -rf "$HOME/.claude/skills/hwpx-kit"

if command -v claude >/dev/null; then
    claude plugin marketplace add "$PLUGIN_DIR" 2>/dev/null || true
    claude plugin install "hwpx-kit@hwpx-kit-market" \\
        && echo "Claude Code 플러그인 설치됨 (hwpx-kit@hwpx-kit-market)" \\
        || echo "자동 등록 실패 — Claude Code에서: /plugin marketplace add $PLUGIN_DIR"
else
    echo "Claude Code에서 직접 실행: /plugin marketplace add $PLUGIN_DIR"
    echo "                         /plugin install hwpx-kit@hwpx-kit-market"
fi
echo "완료."
"""

README = """\
# hwpx-kit — Claude Code 플러그인 배포 번들

한글(HWPX/HWP) 문서 자동화 스킬 모음. Claude Code에 플러그인으로 설치하면
"이 양식에 채워줘" 한마디로 서식 무손상 hwpx가 나온다.

포함 스킬:
- hwpx-form       양식 분석·채우기·검증·읽기·워드(docx) 출력 (코어 워크플로)
- doc-create      양식 없이 백지에서 문서 만들기 (양식 유무 라우팅)
- format-convert  금액 한글 병기·날짜 요일·만나이 — 결정론 계산 (안 틀림)
- gongmun-format  행안부 공문 작성 규약 (글머리 위계, 표기, 텍스트 정리)
- table-calc      보고서 표 증감·비율·합계 계산과 관습 표기
- office-export   hwpx → 워드/파워포인트/엑셀

## 설치

- Windows: PowerShell에서 `.\\install.ps1`
- macOS/Linux: `bash install.sh`

**필수는 Python 3.10+ 하나뿐이다.** PDF·워드·엑셀 읽기는 내장.
.hwp 변환과 워드 출력은 한글(한컴오피스)이 설치된 Windows에서 활성화된다.

## 확인

새 터미널: `hwpx-kit --version`
Claude Code 새 세션: hwpx 파일을 주며 "이 양식에 채워줘"

## 문의

6aneffy · tkdgus990809@gmail.com · github.com/6aneffy/hwpx-kit
"""


def build(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    version = subprocess.run(
        ["uv", "version", "--short"], capture_output=True, text=True, cwd=str(REPO), check=True
    ).stdout.strip()

    with tempfile.TemporaryDirectory() as td:
        subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", td], cwd=str(REPO), check=True,
            capture_output=True,
        )
        wheel = next(Path(td).glob("hwpx_kit-*.whl"))

        bundle = out_dir / f"hwpx-kit-plugin-{version}.zip"
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
            # 플러그인(자기-마켓플레이스) 통째
            for src_dir, arc_prefix in (
                (REPO / ".claude-plugin", "hwpx-kit-plugin/.claude-plugin"),
                (REPO / "skills", "hwpx-kit-plugin/skills"),
                (REPO / "templates", "hwpx-kit-plugin/templates"),
            ):
                for f in sorted(src_dir.rglob("*")):
                    if f.is_file():
                        zf.write(f, f"{arc_prefix}/{f.relative_to(src_dir).as_posix()}")
            zf.write(wheel, wheel.name)
            zf.writestr("install.ps1", INSTALL_PS1)
            zf.writestr("install.sh", INSTALL_SH)
            zf.writestr("README.md", README)
    return bundle


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(REPO / "dist"), help="출력 디렉터리 (기본 dist/)")
    args = ap.parse_args()
    bundle = build(Path(args.out))
    print(bundle)
    return 0


if __name__ == "__main__":
    sys.exit(main())
