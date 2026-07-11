#!/usr/bin/env bash
set -euo pipefail

SOURCE="${HWPX_KIT_SOURCE:-git+https://github.com/6aneffy/hwpx-kit.git}"

if ! command -v python3 >/dev/null; then
    echo "Python 3.10+ 가 필요합니다."; exit 1
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
    || { echo "Python 3.10 이상 필요. 현재: $(python3 --version)"; exit 1; }

echo "hwpx-kit 설치 중..."
python3 -m pip install --user --upgrade "$SOURCE"
python3 -m hwpx_kit.cli --help >/dev/null

# Claude Code 플러그인 등록 (레포 루트 = 자기-마켓플레이스)
rm -rf "$HOME/.claude/skills/hwpx-kit"   # 구 단일 스킬 잔재 — 이중 트리거 방지

if command -v claude >/dev/null && [ -n "${HWPX_KIT_SOURCE:-}" ] \
    && [ -f "$HWPX_KIT_SOURCE/.claude-plugin/marketplace.json" ]; then
    claude plugin marketplace add "$HWPX_KIT_SOURCE" 2>/dev/null || true
    claude plugin install "hwpx-kit@hwpx-kit-market" \
        && echo "Claude Code 플러그인 설치됨 (hwpx-kit@hwpx-kit-market)" \
        || echo "등록 실패 — Claude Code에서: /plugin marketplace add $HWPX_KIT_SOURCE"
else
    echo "플러그인 등록: 레포 클론 경로에서 /plugin marketplace add <레포경로> 후 /plugin install hwpx-kit@hwpx-kit-market"
fi
echo "완료."

