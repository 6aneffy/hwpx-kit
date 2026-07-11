import pytest

from hwpx_kit.commands.read import run_read
from hwpx_kit.commands.validate import run_validate


def test_read_text(marker_doc):
    data = run_read(marker_doc, fmt="text")
    assert data["format"] == "text"
    assert "출장 신청서" in data["content"]


def test_read_markdown_default(marker_doc):
    data = run_read(marker_doc)
    assert data["format"] == "md"
    assert "출장 신청서" in data["content"]


def test_read_rejects_unknown_format(marker_doc):
    with pytest.raises(ValueError):
        run_read(marker_doc, fmt="pdf")


def test_validate_clean_doc(marker_doc):
    data = run_validate(marker_doc)
    assert data["valid"] is True
    assert data["issues"] == []
