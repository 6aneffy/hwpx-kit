import json

from hwpx_kit.cli import main


def _last_json(capsys):
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def test_analyze_json_clean_stdout(marker_doc, capsys):
    code = main(["analyze", marker_doc, "--json"])
    out = capsys.readouterr().out
    env = json.loads(out)  # 한 줄 전체가 JSON이어야 함 — 엔진 노이즈 섞이면 여기서 실패
    assert code == 0
    assert env["ok"] is True
    assert any(f["fill_key"] == "marker:성명" for f in env["data"]["fields"])


def test_fill_exit_2_on_unmatched(marker_doc, tmp_path, capsys):
    data_file = tmp_path / "d.json"
    data_file.write_text(
        json.dumps({"marker:성명": "김철수", "marker:없는키": "x"}, ensure_ascii=False),
        encoding="utf-8",
    )
    code = main([
        "fill", marker_doc,
        "--data", str(data_file),
        "--out", str(tmp_path / "o.hwpx"),
        "--json",
    ])
    env = _last_json(capsys)
    assert code == 2
    assert env["ok"] is True
    assert env["data"]["unmatched"][0]["key"] == "marker:없는키"


def test_missing_file_exit_1(capsys):
    code = main(["analyze", "없는파일.hwpx", "--json"])
    env = _last_json(capsys)
    assert code == 1
    assert env["ok"] is False
    assert env["error"]["code"] == "FILE_NOT_FOUND"


def test_read_human_output(marker_doc, capsys):
    code = main(["read", marker_doc, "--format", "text"])
    out = capsys.readouterr().out
    assert code == 0
    assert "출장 신청서" in out


def test_version_flag(capsys):
    """--version은 패키지 메타데이터 버전을 출력 — 배포본 지원 문의 때 식별용."""
    import re

    import pytest

    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert re.search(r"hwpx-kit \d+\.\d+\.\d+", out)
