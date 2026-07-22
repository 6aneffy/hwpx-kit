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
