"""diff — 신구대조표 / 문서 비교.

순수 diff_paragraphs(difflib)는 한글 불필요. run_diff는 build_table로
신구대조표(현행|개정)를 새 문서에 만든다.
"""
import json

import pytest

from hwpx_kit.cli import main
from hwpx_kit.commands.diff_doc import diff_paragraphs, diff_summary


def test_diff_paragraphs_replace():
    blocks = diff_paragraphs(["가", "나", "다"], ["가", "라", "다"])
    tags = [b["tag"] for b in blocks]
    assert tags == ["equal", "replace", "equal"]
    rep = blocks[1]
    assert rep["old"] == ["나"] and rep["new"] == ["라"]


def test_diff_paragraphs_insert_delete():
    blocks = diff_paragraphs(["가", "다"], ["가", "나", "다"])
    # 가(equal) → 나(insert) → 다(equal)
    assert [b["tag"] for b in blocks] == ["equal", "insert", "equal"]
    assert blocks[1]["new"] == ["나"] and blocks[1]["old"] == []


def test_diff_paragraphs_identical():
    blocks = diff_paragraphs(["가", "나"], ["가", "나"])
    assert [b["tag"] for b in blocks] == ["equal"]


def test_diff_summary():
    blocks = diff_paragraphs(["가", "나", "다"], ["가", "라"])
    s = diff_summary(blocks)
    assert s["equal"] >= 1 and (s["replace"] + s["delete"] + s["insert"]) >= 1


def _make(tmp_path, name, paras):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        doc = HwpxDocument.new()
        first = list(doc.paragraphs)
        for i, txt in enumerate(paras):
            if i == 0 and first:
                first[0].text = txt
            else:
                doc.add_paragraph(txt)
        path = str(tmp_path / name)
        doc.save_to_path(path)
    return path


@pytest.fixture()
def old_new(tmp_path):
    old = _make(tmp_path, "old.hwpx", ["제1조 목적", "제2조 정의", "제3조 적용"])
    new = _make(tmp_path, "new.hwpx", ["제1조 목적", "제2조 정의(개정)", "제3조 적용"])
    return old, new


def _table_grid(path):
    from hwpx.document import HwpxDocument
    from hwpx.tools import table_navigation as tn

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        t = tn._collect_document_tables(HwpxDocument.open(path))[0].table
        cells = {}
        for r in range(t.row_count):
            for c in range(t.column_count):
                try:
                    cells[(r, c)] = (tn._cell_text(t, r, c) or "").strip()
                except Exception:
                    pass
        return t.row_count, t.column_count, cells


def test_run_diff_json(old_new):
    from hwpx_kit.commands.diff_doc import run_diff

    old, new = old_new
    rep = run_diff(old, new)
    assert rep["summary"]["replace"] >= 1
    # 변경 블록에 정의 조항 수정이 잡힘
    joined = "".join("".join(b["old"]) + "".join(b["new"]) for b in rep["blocks"])
    assert "정의(개정)" in joined and "정의" in joined


def test_run_diff_builds_table(old_new, tmp_path):
    from hwpx_kit.commands.diff_doc import run_diff

    old, new = old_new
    out = str(tmp_path / "singu.hwpx")
    res = run_diff(old, new, out_path=out)
    rows, cols, cells = _table_grid(out)
    assert cols == 2
    assert cells[(0, 0)] == "현행" and cells[(0, 1)] == "개정"
    # 변경 행에 현행/개정 정의 조항
    allcells = " ".join(cells.values())
    assert "제2조 정의" in allcells and "제2조 정의(개정)" in allcells


def test_cli_diff(old_new, tmp_path, capsys):
    old, new = old_new
    out = str(tmp_path / "singu.hwpx")
    code = main(["diff", old, new, "--out", out, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and env["ok"] is True


def test_cli_diff_report_only(old_new, capsys):
    old, new = old_new
    code = main(["diff", old, new, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and env["ok"] is True
    assert env["data"]["summary"]["replace"] >= 1
