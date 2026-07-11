"""플러그인 배포 번들 빌드 검증.

레포가 비공개라 git 설치가 외부인에게 불가 — 배포는 오프라인 zip
(wheel + Claude Code 플러그인 + 자체 설치 스크립트)이어야 한다.
"""
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_build_plugin_bundle(tmp_path):
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "build_skill_package.py"), "--out", str(tmp_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO),
    )
    assert result.returncode == 0, result.stderr

    zips = list(tmp_path.glob("hwpx-kit-plugin-*.zip"))
    assert len(zips) == 1
    with zipfile.ZipFile(zips[0]) as zf:
        names = set(zf.namelist())
        assert "install.ps1" in names
        assert "install.sh" in names
        assert "README.md" in names
        assert "hwpx-kit-plugin/.claude-plugin/plugin.json" in names
        assert "hwpx-kit-plugin/.claude-plugin/marketplace.json" in names
        wheels = [n for n in names if n.endswith(".whl")]
        assert len(wheels) == 1

        # 레포의 스킬 전부가 번들에 그대로 — 누락·구버전 배포 방지
        repo_skills = {p.parent.name for p in (REPO / "skills").glob("*/SKILL.md")}
        bundle_skills = {
            n.split("/")[2]
            for n in names
            if n.startswith("hwpx-kit-plugin/skills/") and n.endswith("SKILL.md")
        }
        assert bundle_skills == repo_skills
        for skill in repo_skills:
            assert zf.read(f"hwpx-kit-plugin/skills/{skill}/SKILL.md") == (
                REPO / "skills" / skill / "SKILL.md"
            ).read_bytes()
