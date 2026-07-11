"""수동 수용 확인용 샘플 생성: sample-form.hwpx / sample-filled.hwpx"""
import json
import subprocess
import sys

from hwpx.document import HwpxDocument

from hwpx_kit.output import quiet_engine

with quiet_engine():
    doc = HwpxDocument.new()
    doc.add_paragraph("출 장 신 청 서")
    doc.add_paragraph("문서번호: {{문서번호}}")
    table = doc.add_table(4, 2)
    table.set_cell_text(0, 0, "성명")
    table.set_cell_text(1, 0, "소속")
    table.set_cell_text(2, 0, "출장기간")
    table.set_cell_text(3, 0, "출장목적")
    doc.save_to_path("sample-form.hwpx")

values = {
    "marker:문서번호": "혁신-2026-041",
    "table:성명": "김철수",
    "table:소속": "혁신기획팀",
    "table:출장기간": "2026-07-14 ~ 2026-07-16",
    "table:출장목적": "AI 활용 문서자동화 교육 출강",
}
with open("sample-values.json", "w", encoding="utf-8") as fh:
    json.dump(values, fh, ensure_ascii=False)

sys.exit(subprocess.run([
    sys.executable, "-m", "hwpx_kit.cli",
    "fill", "sample-form.hwpx",
    "--data", "sample-values.json",
    "--out", "sample-filled.hwpx", "--json",
]).returncode)
