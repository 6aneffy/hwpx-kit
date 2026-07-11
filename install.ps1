# hwpx-kit installer (Windows)
$ErrorActionPreference = "Stop"

$source = $env:HWPX_KIT_SOURCE
if (-not $source) {
    $source = "git+https://github.com/6aneffy/hwpx-kit.git"
}

# 1. Python 확인
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

# 2. 패키지 설치 (사용자 영역 — 관리자 권한 불필요)
Write-Host "hwpx-kit 설치 중..."
& python -m pip install --user --upgrade $source
if ($LASTEXITCODE -ne 0) { Write-Host "설치 실패"; exit 1 }

# 2-1. .hwp 변환용 (실패해도 치명적 아님 — convert만 비활성)
& python -m pip install --user --upgrade pyhwpx *> $null
if ($LASTEXITCODE -ne 0) { Write-Host "참고: pyhwpx 설치 실패 — 'hwpx-kit convert'(.hwp 변환)만 사용 불가" }

# 2-2. kordoc — 조건부 옵션 (한글 없는 환경의 구형 .hwp 전용). npm 있으면 조용히 시도.
# PDF/DOCX/XLSX 읽기는 내장(파이썬)이라 kordoc 불필요
$npm = Get-Command npm -ErrorAction SilentlyContinue
if ($npm) {
    & npm install -g "kordoc@3.18.0" *> $null
    if ($LASTEXITCODE -eq 0) { Write-Host "kordoc 3.18.0 설치됨 (구형 .hwp 직접 읽기 활성)" }
}

# 3. 동작 확인
& python -m hwpx_kit.cli --help *> $null
if ($LASTEXITCODE -ne 0) { Write-Host "설치 확인 실패"; exit 1 }

# 4. Claude Code 플러그인 등록 (레포 루트 = 자기-마켓플레이스)
# 구 단일 스킬 잔재가 있으면 제거 (플러그인과 이중 트리거 방지)
$legacy = "$env:USERPROFILE\.claude\skills\hwpx-kit"
if (Test-Path $legacy) { Remove-Item -Recurse -Force $legacy; Write-Host "구버전 단일 스킬 제거됨" }

$claude = Get-Command claude -ErrorAction SilentlyContinue
if ($claude -and $env:HWPX_KIT_SOURCE -and (Test-Path "$env:HWPX_KIT_SOURCE\.claude-plugin\marketplace.json")) {
    & claude plugin marketplace add $env:HWPX_KIT_SOURCE 2>$null
    & claude plugin install "hwpx-kit@hwpx-kit-market" 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Host "Claude Code 플러그인 설치됨 (hwpx-kit@hwpx-kit-market)" }
    else { Write-Host "플러그인 등록 실패 — Claude Code에서 직접: /plugin marketplace add $env:HWPX_KIT_SOURCE" }
} else {
    Write-Host "플러그인 등록: 레포 클론 경로에서 /plugin marketplace add <레포경로> 후 /plugin install hwpx-kit@hwpx-kit-market"
}

Write-Host "완료. 새 터미널에서 'hwpx-kit --help' 또는 Claude에게 hwpx 작업을 요청하세요."

