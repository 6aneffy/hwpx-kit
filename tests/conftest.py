import pytest
from hwpx.document import HwpxDocument

from hwpx_kit.output import quiet_engine


@pytest.fixture
def marker_doc(tmp_path):
    """마커 2개({{성명}}, {{출장기간}})가 든 hwpx를 만들어 경로 반환."""
    with quiet_engine():
        doc = HwpxDocument.new()
        doc.add_paragraph("출장 신청서")
        doc.add_paragraph("신청자: {{성명}}")
        doc.add_paragraph("기간: {{출장기간}}")
        path = tmp_path / "marker.hwpx"
        doc.save_to_path(str(path))
    return str(path)


@pytest.fixture
def label_table_doc(tmp_path):
    """라벨 셀(성명/부서)과 빈 입력 셀이 있는 2x2 표 hwpx 경로 반환."""
    with quiet_engine():
        doc = HwpxDocument.new()
        table = doc.add_table(2, 2)
        table.set_cell_text(0, 0, "성명")
        table.set_cell_text(1, 0, "부서")
        path = tmp_path / "table.hwpx"
        doc.save_to_path(str(path))
    return str(path)


@pytest.fixture
def merged_dup_label_doc(tmp_path):
    """세로 병합 라벨('직위'가 0-1행 병합) + 같은 라벨 단독 행 — 실보도자료
    담당부서 블록에서 병합 복제가 #N 번호를 오염시키던 패턴."""
    with quiet_engine():
        doc = HwpxDocument.new()
        table = doc.add_table(3, 2)
        table.set_cell_text(0, 0, "직위")
        table.set_cell_text(2, 0, "직위")
        doc.merge_table_cells(table, "A1:A2")
        path = tmp_path / "merged.hwpx"
        doc.save_to_path(str(path))
    return str(path)


@pytest.fixture
def dup_label_doc(tmp_path):
    """같은 라벨(부서/담당)이 두 번씩 나오는 표 — 보도자료 담당부서 2개 블록 패턴."""
    with quiet_engine():
        doc = HwpxDocument.new()
        table = doc.add_table(5, 2)
        table.set_cell_text(0, 0, "부서")
        table.set_cell_text(1, 0, "담당")
        table.set_cell_text(2, 0, "부서")
        table.set_cell_text(3, 0, "담당")
        table.set_cell_text(4, 0, "연락")
        path = tmp_path / "dup.hwpx"
        doc.save_to_path(str(path))
    return str(path)
