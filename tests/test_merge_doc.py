"""merge — 같은 서식 문서 합본 (붙임 합치기).

MVP: header refList가 동일할 때만 append. 다르면 거부(서식 깨짐 방지).
"""
import json

import pytest

from hwpx_kit.cli import main
from hwpx_kit.commands.merge_doc import run_merge


def _make(tmp_path, name, paras, with_table=False):
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
        if with_table:
            doc.add_table(2, 2)  # 표 추가 → borderFill 등 refList 분기
        path = str(tmp_path / name)
        doc.save_to_path(path)
    return path


def _paragraphs(path):
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        d = HwpxDocument.open(path)
        return [(p.text or "").strip() for p in d.paragraphs if (p.text or "").strip()]


def test_merge_same_template(tmp_path):
    a = _make(tmp_path, "a.hwpx", ["붙임1 개요", "가. 목적"])
    b = _make(tmp_path, "b.hwpx", ["붙임2 예산", "가. 총액"])
    out = str(tmp_path / "m.hwpx")
    res = run_merge(a, b, out_path=out)
    assert res["appended_paragraphs"] == 2
    paras = _paragraphs(out)
    assert "붙임1 개요" in paras and "붙임2 예산" in paras
    assert paras.index("붙임1 개요") < paras.index("붙임2 예산")  # 순서 유지


def test_merge_page_break(tmp_path):
    a = _make(tmp_path, "a.hwpx", ["앞문서"])
    b = _make(tmp_path, "b.hwpx", ["뒷문서"])
    out = str(tmp_path / "m.hwpx")
    run_merge(a, b, out_path=out, page_break=True)
    # 뒷문서 첫 문단에 pageBreak=1
    from hwpx.document import HwpxDocument

    from hwpx_kit.output import quiet_engine

    with quiet_engine():
        d = HwpxDocument.open(out)
        brk = [p for p in d.paragraphs if p.element.get("pageBreak") == "1"]
    assert brk, "합본 경계에 쪽나눔이 있어야 함"


def test_merge_rejects_different_format(tmp_path):
    a = _make(tmp_path, "a.hwpx", ["평문 문서"])
    b = _make(tmp_path, "b.hwpx", ["표 문서"], with_table=True)
    with pytest.raises(ValueError, match="서식"):
        run_merge(a, b, out_path=str(tmp_path / "m.hwpx"))


def test_merge_original_unchanged(tmp_path):
    a = _make(tmp_path, "a.hwpx", ["원본A"])
    b = _make(tmp_path, "b.hwpx", ["원본B"])
    run_merge(a, b, out_path=str(tmp_path / "m.hwpx"))
    assert _paragraphs(a) == ["원본A"]  # base 불변


def test_cli_merge(tmp_path, capsys):
    a = _make(tmp_path, "a.hwpx", ["붙임1"])
    b = _make(tmp_path, "b.hwpx", ["붙임2"])
    out = str(tmp_path / "m.hwpx")
    code = main(["merge", a, b, "--out", out, "--json"])
    env = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and env["ok"] is True
    assert "붙임2" in _paragraphs(out)
