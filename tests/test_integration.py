"""출장신청서 유사 양식으로 analyze → fill → validate → read 전체 왕복."""
import json

import pytest
from hwpx.document import HwpxDocument

from hwpx_kit.cli import main
from hwpx_kit.output import quiet_engine


@pytest.fixture
def realistic_form(tmp_path):
    """공공 양식 근사 픽스처: 제목 + 마커 문단 + 라벨 표 혼합."""
    with quiet_engine():
        doc = HwpxDocument.new()
        doc.add_paragraph("출 장 신 청 서")
        doc.add_paragraph("문서번호: {{문서번호}}")
        table = doc.add_table(4, 2)
        table.set_cell_text(0, 0, "성명")
        table.set_cell_text(1, 0, "소속")
        table.set_cell_text(2, 0, "출장기간")
        table.set_cell_text(3, 0, "출장목적")
        path = tmp_path / "form.hwpx"
        doc.save_to_path(str(path))
    return str(path)


def test_full_roundtrip(realistic_form, tmp_path, capsys):
    # 1. analyze
    assert main(["analyze", realistic_form, "--json"]) == 0
    env = json.loads(capsys.readouterr().out)
    keys = {f["fill_key"] for f in env["data"]["fields"]}
    assert {"marker:문서번호", "table:성명", "table:소속", "table:출장기간", "table:출장목적"} <= keys

    # 2. fill — analyze가 준 fill_key를 그대로 사용
    values = {
        "marker:문서번호": "혁신-2026-041",
        "table:성명": "김철수",
        "table:소속": "혁신기획팀",
        "table:출장기간": "2026-07-14 ~ 2026-07-16",
        "table:출장목적": "AI 활용 문서자동화 교육 출강",
    }
    data_file = tmp_path / "values.json"
    data_file.write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")
    out_file = tmp_path / "filled.hwpx"
    assert main(["fill", realistic_form, "--data", str(data_file),
                 "--out", str(out_file), "--json"]) == 0
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert env["data"]["unmatched"] == []

    # 3. validate
    assert main(["validate", str(out_file), "--json"]) == 0
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert env["data"]["valid"] is True

    # 4. read — 채운 값 전부 재확인
    assert main(["read", str(out_file), "--format", "text", "--json"]) == 0
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    for value in values.values():
        assert value in env["data"]["content"]
