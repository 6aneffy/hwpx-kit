import pytest

from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
from hwpx_kit.commands.fill import run_fill


def test_fill_markers_and_labels(marker_doc, tmp_path):
    out = str(tmp_path / "out.hwpx")
    result = run_fill(
        marker_doc,
        {"marker:성명": "김철수", "marker:출장기간": "2026-07-14 ~ 07-16"},
        out,
    )
    assert result["out"].endswith("out.hwpx")
    assert set(result["applied"]) == {"marker:성명", "marker:출장기간"}
    text = HwpxEngineAdapter.open(result["out"]).export_text()
    assert "김철수" in text and "2026-07-14" in text


def test_fill_table_label(label_table_doc, tmp_path):
    result = run_fill(label_table_doc, {"table:성명": "김철수"}, str(tmp_path / "o.hwpx"))
    assert result["applied"] == ["table:성명"]
    assert "김철수" in HwpxEngineAdapter.open(result["out"]).export_text()


def test_fill_exact_text_replacement(marker_doc, tmp_path):
    """text:<원문> — 예시 텍스트 교체 (보도자료 제목/부제목 패턴). 서식은 런 단위 보존."""
    result = run_fill(
        marker_doc,
        {"text:출장 신청서": "출장 결과 보고서"},
        str(tmp_path / "o.hwpx"),
    )
    assert result["applied"] == ["text:출장 신청서"]
    text = HwpxEngineAdapter.open(result["out"]).export_text()
    assert "출장 결과 보고서" in text
    assert "출장 신청서" not in text


def test_fill_text_split_runs_falls_back_to_paragraph(tmp_path):
    """긴 문장은 런이 쪼개져 런 단위 매칭 실패 — 문단 전체 일치로 폴백 (보도자료 제목 패턴)."""
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        p = doc.add_paragraph("가상의 첫 구절, ")
        p.add_run("나뉜 두 번째 구절이 이어진다")
        table = doc.add_table(1, 1)
        table.set_cell_text(0, 0, "표 안의 제목 예시")
        src = str(tmp_path / "split.hwpx")
        doc.save_to_path(src)

    full = "가상의 첫 구절, 나뉜 두 번째 구절이 이어진다"
    result = run_fill(
        src,
        {f"text:{full}": "AI 도입으로 행정 효율을 높인다",
         "text:표 안의 제목 예시": "표 안의 새 제목"},
        str(tmp_path / "o.hwpx"),
    )
    assert result["unmatched"] == []
    text = HwpxEngineAdapter.open(result["out"]).export_text()
    assert "AI 도입으로 행정 효율을 높인다" in text
    assert "표 안의 새 제목" in text


def test_fill_delete_instruction_paragraphs(tmp_path):
    """delete:<원문> — 양식 안내문 삭제 (보도자료 '←해당시' 지시 블록 패턴)."""
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        doc.add_paragraph("본문 유지 문단")
        doc.add_paragraph("【관련 국정과제】 (예시) 1. 헌법 개정 ←해당시")
        table = doc.add_table(1, 1)
        table.set_cell_text(0, 0, "(국정과제 관련시) (예시) 지시문")
        src = str(tmp_path / "inst.hwpx")
        doc.save_to_path(src)

    result = run_fill(
        src,
        {
            "delete:【관련 국정과제】 (예시) 1. 헌법 개정 ←해당시": "",
            "delete:(국정과제 관련시) (예시) 지시문": "",
        },
        str(tmp_path / "o.hwpx"),
    )
    assert result["unmatched"] == []
    text = HwpxEngineAdapter.open(result["out"]).export_text()
    assert "본문 유지 문단" in text
    assert "국정과제" not in text
    assert "예시" not in text


def test_fill_duplicate_label_plain_key_reports_ambiguous(dup_label_doc, tmp_path):
    """중복 라벨에 인덱스 없는 키 — 엉뚱한 곳을 채우지 말고 ambiguous 사유로 거부."""
    result = run_fill(dup_label_doc, {"table:부서": "x"}, str(tmp_path / "o.hwpx"))
    assert result["applied"] == []
    assert "ambiguous" in result["unmatched"][0]["reason"]


def test_fill_duplicate_label_nth_targets_each_occurrence(dup_label_doc, tmp_path):
    """table:라벨#N — 문서 순서 N번째 출현만 채움 (담당부서 2개 블록 패턴)."""
    result = run_fill(
        dup_label_doc,
        {"table:부서#1": "기획팀", "table:부서#2 > right": "운영팀"},
        str(tmp_path / "o.hwpx"),
    )
    assert result["unmatched"] == []
    tm = HwpxEngineAdapter.open(result["out"]).table_map()
    cells = {(c["row"], c["col"]): (c.get("text") or "").strip()
             for c in tm["tables"][0]["cells"]}
    assert cells[(0, 1)] == "기획팀"
    assert cells[(2, 1)] == "운영팀"


def test_fill_multiline_label_roundtrip_from_analyze_key(tmp_path):
    """개행 라벨 셀 — analyze가 준 정규화 키 그대로 fill이 받아 채우는 왕복."""
    from hwpx.document import HwpxDocument

    from hwpx_kit.commands.analyze import run_analyze
    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        table = doc.add_table(2, 2)
        table.set_cell_text(0, 0, "담당 부서\n<총괄>")
        table.set_cell_text(1, 0, "연락")
        src = str(tmp_path / "ml.hwpx")
        doc.save_to_path(src)

    fields = run_analyze(src)["fields"]
    key = next(
        f["fill_key"] for f in fields
        if f.get("label", "").startswith("담당 부서")
    )
    result = run_fill(src, {key: "가상기획부"}, str(tmp_path / "o.hwpx"))
    assert result["unmatched"] == []
    tm = HwpxEngineAdapter.open(result["out"]).table_map()
    cells = {(c["row"], c["col"]): (c.get("text") or "").strip()
             for c in tm["tables"][0]["cells"]}
    assert cells[(0, 1)] == "가상기획부"


def test_fill_nth_counts_merged_label_once(merged_dup_label_doc, tmp_path):
    """병합 라벨의 격자 복제(비-anchor)는 출현 수에서 제외 — #2가 진짜
    두 번째 라벨을 가리켜야 함 (복제를 세면 같은 셀에 이중 기입돼 값 유실)."""
    result = run_fill(
        merged_dup_label_doc,
        {"table:직위#1": "가상A", "table:직위#2": "가상B"},
        str(tmp_path / "o.hwpx"),
    )
    assert result["unmatched"] == []
    tm = HwpxEngineAdapter.open(result["out"]).table_map()
    cells = {(c["row"], c["col"]): (c.get("text") or "").strip()
             for c in tm["tables"][0]["cells"]}
    assert cells[(0, 1)] == "가상A"
    assert cells[(2, 1)] == "가상B"  # 복제를 세면 (1,1)에 감


def test_fill_nth_out_of_range_reports_reason(dup_label_doc, tmp_path):
    result = run_fill(dup_label_doc, {"table:부서#3": "x"}, str(tmp_path / "o.hwpx"))
    assert result["applied"] == []
    assert "#3" in result["unmatched"][0]["reason"]


def test_fill_exact_text_not_found(marker_doc, tmp_path):
    result = run_fill(
        marker_doc,
        {"text:존재하지 않는 문구": "x"},
        str(tmp_path / "o.hwpx"),
    )
    assert result["applied"] == []
    assert result["unmatched"][0]["key"] == "text:존재하지 않는 문구"


def test_unmatched_keys_reported_not_fatal(marker_doc, tmp_path):
    result = run_fill(
        marker_doc,
        {"marker:성명": "김철수", "marker:없는키": "x", "이상한형식": "y"},
        str(tmp_path / "o.hwpx"),
    )
    assert result["applied"] == ["marker:성명"]
    unmatched_keys = {u["key"] for u in result["unmatched"]}
    assert unmatched_keys == {"marker:없는키", "이상한형식"}


def test_original_file_never_modified(marker_doc, tmp_path):
    before = open(marker_doc, "rb").read()
    run_fill(marker_doc, {"marker:성명": "김철수"}, str(tmp_path / "o.hwpx"))
    assert open(marker_doc, "rb").read() == before


def test_refuse_overwrite_source(marker_doc):
    with pytest.raises(ValueError):
        run_fill(marker_doc, {"marker:성명": "김철수"}, marker_doc)



def test_bold_key_sets_run_bold(marker_doc, tmp_path):
    """bold:<원문> — 원문을 품은 런에 볼드 적용 (범피스 강조 흡수).

    v1 의미론: 런 단위 적용 — 원문이 런의 일부면 그 런 전체가 굵어진다.
    """
    from hwpx.document import HwpxDocument

    from hwpx_kit.commands.fill import run_fill
    from hwpx_kit.output import quiet_engine

    out = str(tmp_path / "o.hwpx")
    result = run_fill(marker_doc, {"bold:출장 신청서": ""}, out)
    assert result["unmatched"] == []
    with quiet_engine():
        doc = HwpxDocument.open(out)
        runs = [r for p in doc.paragraphs for r in p.runs if "출장 신청서" in (r.text or "")]
    assert runs and all(r.bold for r in runs)


def test_underline_key(marker_doc, tmp_path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.commands.fill import run_fill
    from hwpx_kit.output import quiet_engine

    out = str(tmp_path / "o.hwpx")
    result = run_fill(marker_doc, {"underline:출장 신청서": ""}, out)
    assert result["unmatched"] == []
    with quiet_engine():
        doc = HwpxDocument.open(out)
        runs = [r for p in doc.paragraphs for r in p.runs if "출장 신청서" in (r.text or "")]
    assert runs and all(r.underline for r in runs)


def test_bold_key_unmatched_when_absent(marker_doc, tmp_path):
    from hwpx_kit.commands.fill import run_fill

    result = run_fill(marker_doc, {"bold:없는 문장": ""}, str(tmp_path / "o.hwpx"))
    assert result["unmatched"][0]["key"] == "bold:없는 문장"


def test_bold_key_works_in_table_cells(label_table_doc, tmp_path):
    """표 셀 안 텍스트도 강조 가능해야 함."""
    from hwpx_kit.commands.fill import run_fill

    result = run_fill(label_table_doc, {"bold:성명": ""}, str(tmp_path / "o.hwpx"))
    assert result["unmatched"] == []


# ── secure fill 카나리 — 값 비노출 보증 (0.8.0) ─────────────


def test_secure_fill_never_leaks_values_in_output(tmp_path, capsys):
    """--secure 산출 JSON·stdout 어디에도 채운 값이 나타나면 안 된다 (카나리)."""
    import json as _json

    from hwpx_kit.adapter.hwpx_engine import HwpxEngineAdapter
    from hwpx_kit.cli import main as _main

    canary = "카나리860107비밀값"
    ad = HwpxEngineAdapter.open("tests/fixtures/real/seoul-report-brief.hwpx")
    target = next((p.text or "").strip() for p in ad._iter_all_paragraphs()
                  if len((p.text or "").strip()) >= 6)
    data_file = tmp_path / "secure.json"
    data_file.write_text(_json.dumps({f"text:{target}": canary}), encoding="utf-8")

    out = tmp_path / "secure-out.hwpx"
    code = _main(["fill", "tests/fixtures/real/seoul-report-brief.hwpx",
                  "--data", str(data_file), "--out", str(out), "--secure", "--json"])
    stdout = capsys.readouterr().out
    assert code == 0
    assert canary not in stdout


def test_secure_fill_failure_leaves_no_output_and_no_values(tmp_path, capsys):
    import json as _json

    from hwpx_kit.cli import main as _main

    canary = "유출되면안되는값9화7"
    data_file = tmp_path / "secure.json"
    data_file.write_text(_json.dumps({"text:존재하지않는문구뷁뷁": canary}),
                         encoding="utf-8")
    out = tmp_path / "no-out.hwpx"
    code = _main(["fill", "tests/fixtures/real/seoul-report-brief.hwpx",
                  "--data", str(data_file), "--out", str(out), "--secure", "--json"])
    stdout = capsys.readouterr().out
    assert code == 1
    assert not out.exists()
    assert canary not in stdout
