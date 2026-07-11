from hwpx_kit.commands.analyze import find_label_candidates, run_analyze


def _cell(row, col, text):
    return {"row": row, "col": col, "text": text}


def test_label_candidates_from_table_map():
    tm = {
        "tables": [
            {
                "table_index": 0,
                "rows": 2,
                "cols": 2,
                "cells": [
                    _cell(0, 0, "성명"), _cell(0, 1, ""),
                    _cell(1, 0, "부서"), _cell(1, 1, ""),
                ],
            }
        ]
    }
    cands = find_label_candidates(tm)
    assert [c["label"] for c in cands] == ["성명", "부서"]
    assert cands[0]["fill_key"] == "table:성명"
    assert cands[0]["ambiguous"] is False


def test_label_candidates_prefilled_and_duplicates():
    """값이 이미 찬 오른쪽 셀도 후보 — prefilled 표시 (실서식 수신/제목 케이스)."""
    tm = {
        "tables": [
            {
                "table_index": 0,
                "rows": 3,
                "cols": 2,
                "cells": [
                    _cell(0, 0, "수신"), _cell(0, 1, "수신자참조"),
                    _cell(1, 0, "비고"), _cell(1, 1, ""),
                    _cell(2, 0, "비고"), _cell(2, 1, ""),
                ],
            }
        ]
    }
    cands = find_label_candidates(tm)
    susin = next(c for c in cands if c["label"] == "수신")
    assert susin["prefilled"] is True
    assert susin["current"] == "수신자참조"
    bigo = [c for c in cands if c["label"] == "비고"]
    assert all(c["prefilled"] is False for c in bigo)
    assert all(c["ambiguous"] for c in bigo)  # 중복 라벨은 ambiguous


def test_label_candidates_skip_merged_cell_artifacts():
    """병합 셀은 같은 텍스트가 격자 전체에 복제됨 — 라벨==오른쪽값이면 후보 아님."""
    tm = {
        "tables": [
            {
                "table_index": 0,
                "rows": 1,
                "cols": 3,
                "cells": [
                    _cell(0, 0, "공지배너"), _cell(0, 1, "공지배너"), _cell(0, 2, "공지배너"),
                ],
            }
        ]
    }
    assert find_label_candidates(tm) == []


def test_label_candidates_reject_noise():
    """잡음 패턴 거부: 구두점 단독, 과도한 길이.

    개행 포함 셀은 과거엔 일괄 거부했으나 실서식(관계부처합동 보도자료)의
    '담당 부서\n<총괄>' 라벨이 그 필터에 걸려 블록 전체가 누락됨 —
    지금은 엔진과 같은 공백 정규화로 라벨화한다 (재현율 우선, fill은 안전).
    """
    tm = {
        "tables": [
            {
                "table_index": 0,
                "rows": 4,
                "cols": 2,
                "cells": [
                    _cell(0, 0, "("), _cell(0, 1, ""),
                    _cell(1, 0, "04/05\n이행용"), _cell(1, 1, ""),
                    _cell(2, 0, "이 라벨은 스무 글자를 훌쩍 넘겨서 본문 문장으로 보입니다"), _cell(2, 1, ""),
                    _cell(3, 0, "접수"), _cell(3, 1, ""),
                ],
            }
        ]
    }
    cands = find_label_candidates(tm)
    assert [c["label"] for c in cands] == ["04/05 이행용", "접수"]


def test_label_candidates_normalize_multiline_label():
    """개행 든 라벨 셀은 엔진과 같은 규칙(공백 정규화)으로 라벨화.

    관계부처합동 보도자료의 '담당 부서\n<총괄>' 병합 라벨 패턴 — 정규화된
    fill_key는 엔진 매칭도 통과한다.
    """
    tm = {
        "tables": [
            {
                "table_index": 0,
                "rows": 2,
                "cols": 2,
                "cells": [
                    _cell(0, 0, "담당 부서\n<총괄>"), _cell(0, 1, "기획실"),
                    _cell(1, 0, "담당 부서\n<총괄>"), _cell(1, 1, "운영과"),
                ],
            }
        ]
    }
    cands = find_label_candidates(tm)
    assert [c["label"] for c in cands] == ["담당 부서 <총괄>", "담당 부서 <총괄>"]
    assert all(c["ambiguous"] for c in cands)


def test_run_analyze_on_marker_doc(marker_doc):
    data = run_analyze(marker_doc)
    keys = {f["fill_key"] for f in data["fields"]}
    assert "marker:성명" in keys
    assert "marker:출장기간" in keys
    assert data["structure"]["paragraphs"] >= 3


def test_run_analyze_duplicate_labels_get_nth_keys(dup_label_doc):
    """중복 라벨은 fill이 바로 쓸 수 있게 table:라벨#N 키로 출력 (문서 순서 1-기준)."""
    data = run_analyze(dup_label_doc)
    dept = [f for f in data["fields"] if f.get("label") == "부서"]
    assert [f["fill_key"] for f in dept] == ["table:부서#1", "table:부서#2"]
    assert all(f["ambiguous"] for f in dept)
    contact = next(f for f in data["fields"] if f.get("label") == "연락")
    assert contact["fill_key"] == "table:연락"  # 유일 라벨은 접미사 없음


def test_run_analyze_merged_label_no_ghost_candidates(merged_dup_label_doc):
    """병합 라벨의 격자 복제 행은 후보에서 제외 — 논리 셀당 필드 1개."""
    data = run_analyze(merged_dup_label_doc)
    pos = [f for f in data["fields"] if f.get("label") == "직위"]
    assert [f["fill_key"] for f in pos] == ["table:직위#1", "table:직위#2"]
    assert [(f["row"], f["col"]) for f in pos] == [(0, 0), (2, 0)]


def test_analyze_key_fillable_when_duplicate_lacks_neighbor(tmp_path):
    """라벨이 두 곳인데 한 곳만 오른쪽 칸이 있는 경우 — analyze 후보는 1개지만
    fill 열거는 2개라 평키가 ambiguous로 거부됨 (고용부 공고문 실증).
    analyze는 fill 열거 기준으로 #N을 붙여 '키 그대로 fill' 계약을 지켜야 함."""
    from hwpx.document import HwpxDocument

    from hwpx_kit.commands.fill import run_fill
    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        table = doc.add_table(2, 2)
        table.set_cell_text(0, 0, "조건")
        table.set_cell_text(1, 1, "조건")  # 마지막 열 — 오른쪽 칸 없음
        src = str(tmp_path / "dupnn.hwpx")
        doc.save_to_path(src)

    fields = [f for f in run_analyze(src)["fields"] if f.get("label") == "조건"]
    assert len(fields) == 1
    assert fields[0]["fill_key"] == "table:조건#1"
    assert fields[0]["ambiguous"] is True

    result = run_fill(src, {fields[0]["fill_key"]: "값X"}, str(tmp_path / "o.hwpx"))
    assert result["unmatched"] == []


def test_run_analyze_on_label_table_doc(label_table_doc):
    data = run_analyze(label_table_doc)
    keys = {f["fill_key"] for f in data["fields"]}
    assert "table:성명" in keys
    assert "table:부서" in keys
    assert data["tables"]["count"] == 1
