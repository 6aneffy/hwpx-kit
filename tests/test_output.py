import json

from hwpx_kit.output import envelope, print_result, quiet_engine


def test_envelope_success_shape():
    env = envelope("analyze", ok=True, data={"fields": []}, warnings=["w1"])
    assert env == {
        "ok": True,
        "command": "analyze",
        "data": {"fields": []},
        "warnings": ["w1"],
    }


def test_envelope_error_shape():
    env = envelope("fill", ok=False, error={"code": "FILE_NOT_FOUND", "message": "없음"})
    assert env["ok"] is False
    assert env["error"]["code"] == "FILE_NOT_FOUND"
    assert "data" not in env


def test_quiet_engine_captures_stdout(capsys):
    with quiet_engine() as noise:
        print("manifest에서 masterPage를 찾지 못해 fallback")
    assert capsys.readouterr().out == ""
    assert noise == ["manifest에서 masterPage를 찾지 못해 fallback"]


def test_print_result_json_is_single_clean_line(capsys):
    env = envelope("read", ok=True, data={"text": "가나다"})
    print_result(env, as_json=True)
    out = capsys.readouterr().out
    assert json.loads(out) == env
    assert out.count("\n") == 1
