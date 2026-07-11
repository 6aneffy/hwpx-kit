from __future__ import annotations

import os

from hwpx.document import HwpxDocument

from hwpx_kit.adapter.base import MARKER_RE, FormField, Marker
from hwpx_kit.output import quiet_engine


class HwpxEngineAdapter:
    def __init__(self, doc: HwpxDocument, source_path: str):
        self._doc = doc
        self._source_path = os.path.abspath(source_path)

    @classmethod
    def open(cls, path: str) -> "HwpxEngineAdapter":
        with quiet_engine():
            doc = HwpxDocument.open(path)
        return cls(doc, path)

    def form_fields(self) -> list[FormField]:
        with quiet_engine():
            raw = self._doc.list_form_fields()
        return [
            FormField(
                index=i,
                name=str(f.get("name", "") or ""),
                current=str(f.get("text", f.get("value", "")) or ""),
            )
            for i, f in enumerate(raw)
        ]

    def markers(self) -> list[Marker]:
        found: list[Marker] = []
        with quiet_engine():
            paragraphs = list(self._doc.paragraphs)
        for idx, para in enumerate(paragraphs):
            text = para.text or ""
            for key in MARKER_RE.findall(text):
                found.append(Marker(key=key, paragraph_index=idx, context=text))
        return found

    def table_map(self) -> dict:
        """엔진 표 맵에 셀별 is_anchor를 덧붙여 반환.

        병합 셀은 격자 전체에 복제되어 보이는데(엔진 특성), anchor가 아닌
        복제 좌표를 라벨 후보로 세면 #N 번호가 오염되고 같은 논리 셀에
        이중 기입된다 — 소비자(analyze)가 복제를 거를 수 있게 표식 제공.
        """
        with quiet_engine():
            result = self._doc.get_table_map()
            from hwpx.tools import table_navigation as tn

            tables = tn._collect_document_tables(self._doc)
            for entry in result.get("tables", []):
                table = tables[entry["table_index"]].table
                for cell in entry.get("cells", []):
                    cell["is_anchor"] = self._cell_is_anchor(table, cell["row"], cell["col"])
        return result

    @staticmethod
    def _cell_is_anchor(table, row: int, col: int) -> bool:
        try:
            return bool(table._grid_entry(row, col).is_anchor)
        except Exception:
            return True  # 판정 불가면 후보 유지 (누락보다 잡음이 안전)

    def fill_form_field(self, name: str, value: str) -> dict:
        with quiet_engine():
            return self._doc.fill_form_field(value, name=name)

    def replace_marker(self, key: str, value: str) -> int:
        with quiet_engine():
            return self._doc.replace_text_in_runs("{{" + key + "}}", value)

    def replace_text(self, search: str, value: str) -> int:
        with quiet_engine():
            return self._doc.replace_text_in_runs(search, value)

    def _iter_all_paragraphs(self):
        """본문 + 표 셀(중첩 포함) 문단 전부 순회."""

        def walk(paragraphs):
            for p in paragraphs:
                yield p
                for table in getattr(p, "tables", []) or []:
                    for r in range(table.row_count):
                        for c in range(table.column_count):
                            try:
                                cell = table.cell(r, c)
                            except Exception:
                                continue
                            yield from walk(cell.paragraphs)

        yield from walk(list(self._doc.paragraphs))

    def delete_paragraph_text(self, search: str) -> int:
        """문단 전체 텍스트가 search와 일치하면 문단을 제거.

        양식의 안내문(예: '←해당시' 지시 블록) 삭제용. 셀의 마지막 문단처럼
        제거가 불가능한 위치면 텍스트만 비운다.
        """
        count = 0
        with quiet_engine():
            targets = [
                p for p in self._iter_all_paragraphs()
                if (p.text or "").strip() == search.strip()
            ]
            for p in targets:
                # 비우기 먼저: remove()가 위치에 따라 예외 없이 무효될 수 있어
                # (표 셀 문단 등) 어느 경로든 내용이 사라지도록 보장
                p.text = ""
                try:
                    p.remove()
                except Exception:
                    pass
                count += 1
        return count

    def apply_run_format(self, search: str, *, bold: bool | None = None,
                         underline: bool | None = None) -> int:
        """search를 품은 런에 글자 서식 적용 (본문+표 셀). 적용 런 수 반환.

        런 단위 적용 — search가 런의 일부여도 그 런 전체에 서식이 걸린다.
        (부분 강조가 필요하면 원문이 런 경계와 일치해야 함 — 스킬에 명시)
        엔진이 run.bold=True 시 새 charPr을 만들어 연결한다 (실증 2026-07-10).
        """
        count = 0
        with quiet_engine():
            for para in self._iter_all_paragraphs():
                for run in list(para.runs):
                    if search and search in (run.text or ""):
                        if bold is not None:
                            run.bold = bold
                        if underline is not None:
                            run.underline = underline
                        count += 1
        return count

    def replace_paragraph_text(self, search: str, value: str) -> int:
        """문단 전체 텍스트가 search와 일치하면 통째로 교체.

        런이 쪼개져 replace_text가 못 잡는 긴 문장용 폴백. 문단은 첫 런
        서식으로 합쳐진다(제목/부제처럼 단일 서식 문단에 안전).
        """
        count = 0
        with quiet_engine():
            for p in self._iter_all_paragraphs():
                if (p.text or "").strip() == search.strip():
                    p.text = value
                    count += 1
        return count

    def fill_by_label(self, label_path: str, value: str) -> dict:
        with quiet_engine():
            return self._doc.fill_by_path({label_path: value})

    def _label_candidates(self, label: str) -> list:
        """엔진이 fill_by_path 내부에서 쓰는 것과 동일한 라벨 열거 (문서 순서, 공백 정규화).

        공개 API(find_cell_by_label)는 방향 유효성으로 후보를 걸러 번호가 방향에
        따라 달라지고, fill_by_path는 라벨 속 '>'를 경로 구분자로 오파싱한다 —
        그래서 내부 열거를 직접 쓴다 (엔진 교체 시 이 지점 재구현).
        """
        from hwpx.tools import table_navigation as tn

        tables = tn._collect_document_tables(self._doc)
        return [
            c
            for c in tn._find_label_candidates(tables, label)
            # 병합 셀의 격자 복제(비-anchor)는 같은 논리 셀 — 출현 수에서 제외
            if self._cell_is_anchor(c.table, c.row, c.col)
        ]

    def normalize_label(self, label: str) -> str:
        """엔진 라벨 매칭과 동일한 정규화 (공백 축약 + casefold + 끝 콜론 제거)."""
        from hwpx.tools import table_navigation as tn

        return tn._normalize_label_text(label)

    def label_positions_map(self) -> dict[str, list[dict]]:
        """정규화 라벨 텍스트 → anchor 셀 좌표 목록(문서 순서). 격자 한 번 스캔.

        fill_at_label의 후보 열거와 같은 기준이라, 여기서 매긴 #N은
        fill이 고르는 N번째와 항상 같은 셀이다. analyze가 모든 라벨의
        중복 여부를 fill 관점에서 판정할 때 쓴다.
        """
        from hwpx.tools import table_navigation as tn

        out: dict[str, list[dict]] = {}
        with quiet_engine():
            for tref in tn._collect_document_tables(self._doc):
                table = tref.table
                for row in range(table.row_count):
                    for col in range(table.column_count):
                        if not self._cell_is_anchor(table, row, col):
                            continue
                        text = tn._normalize_label_text(tn._cell_text(table, row, col))
                        if not text:
                            continue
                        out.setdefault(text, []).append(
                            {"table_index": tref.table_index, "row": row, "col": col}
                        )
        return out

    def find_label_matches(self, label: str) -> list[dict]:
        """라벨과 일치하는 셀 전부를 문서 순서로 반환 (중복 라벨 #N 번호 매기기용).

        fill_at_label과 같은 열거를 쓰므로 analyze가 붙인 #N과
        fill이 고르는 N번째가 항상 일치한다.
        """
        with quiet_engine():
            candidates = self._label_candidates(label)
        return [
            {"table_index": c.table_index, "row": c.row, "col": c.col}
            for c in candidates
        ]

    def fill_at_label(
        self, label: str, directions: list[str], value: str, nth: int | None = None
    ) -> dict:
        """라벨 셀에서 directions만큼 이동한 셀을 채운다.

        nth가 None이면 라벨이 유일할 때만 채움(중복이면 ambiguous 거부 —
        엔진 fill_by_path와 같은 안전 동작). nth(1-기준)가 있으면 문서 순서
        N번째 출현을 지정해 채운다.
        """
        from hwpx.tools import table_navigation as tn

        def _fail(reason: str) -> dict:
            return {"applied_count": 0, "failed": [{"reason": reason}]}

        for d in directions:
            if d not in ("left", "right", "up", "down"):
                return _fail(f"지원하지 않는 방향: {d}")

        with quiet_engine():
            try:
                candidates = self._label_candidates(label)
            except ValueError as exc:
                return _fail(str(exc))
            if not candidates:
                return _fail("label not found")
            if nth is None:
                if len(candidates) > 1:
                    return _fail("ambiguous label")
                candidate = candidates[0]
            elif not (1 <= nth <= len(candidates)):
                return _fail(f"라벨 출현 {len(candidates)}곳인데 #{nth} 지정 — 범위 밖")
            else:
                candidate = candidates[nth - 1]

            row, col = candidate.row, candidate.col
            for d in directions:
                moved = tn._move(candidate.table, row, col, d)
                if moved is None:
                    return _fail("navigation out of bounds")
                row, col = moved
            candidate.table.set_cell_text(row, col, str(value), logical=True)
        return {"applied_count": 1, "failed": []}

    def export_markdown(self) -> str:
        with quiet_engine():
            return self._doc.export_markdown()

    def export_text(self) -> str:
        with quiet_engine():
            return self._doc.export_text()

    def validate(self) -> dict:
        with quiet_engine():
            report = self._doc.validate()
        return report if isinstance(report, dict) else vars(report)

    def copy_row_height(self, table_index: int, like: int, rows: list[int]) -> int:
        """table_index번째 표에서 like 행의 높이를 rows 행들에 복사. 적용 높이 반환.

        사용자가 한글에서 행을 추가하면 기본 높이로 붙는 경우가 있어,
        구조(행 개수)는 사용자가 맞추고 높이 정돈은 도구가 맡는 분업용.
        기준 높이는 like 행 첫 셀 기준 — 세로 병합이 낀 행은 셀별 높이가
        다를 수 있으니 기준 행은 병합 없는 행으로 지정할 것.
        """
        with quiet_engine():
            from hwpx.tools import table_navigation as tn

            tables = tn._collect_document_tables(self._doc)
            if not 0 <= table_index < len(tables):
                raise ValueError(f"표 인덱스 범위 밖: {table_index} (표 {len(tables)}개)")
            table = tables[table_index].table
            all_rows = list(table.rows)
            if not 0 <= like < len(all_rows):
                raise ValueError(f"기준 행 범위 밖: {like} (행 {len(all_rows)}개)")
            bad = [r for r in rows if not 0 <= r < len(all_rows)]
            if bad:
                raise ValueError(f"대상 행 범위 밖: {bad} (행 {len(all_rows)}개)")
            height = list(all_rows[like].cells)[0].height
            for r in rows:
                for cell in all_rows[r].cells:
                    cell.set_size(height=height)
        return height

    def clear_table_rows(self, table_index: int, rows: list[int] | None) -> int:
        """table_index번째 표에서 지정 행들(None=전체)의 셀 내용을 비운다.

        병합 셀은 anchor 좌표만 비운다 (복제 좌표에 쓰면 이중 처리).
        비운 셀 수를 반환. 행 구조는 그대로 — 구조 변경은 사용자가 한글에서.
        """
        with quiet_engine():
            from hwpx.tools import table_navigation as tn

            tables = tn._collect_document_tables(self._doc)
            if not 0 <= table_index < len(tables):
                raise ValueError(f"표 인덱스 범위 밖: {table_index} (표 {len(tables)}개)")
            table = tables[table_index].table
            row_count = len(list(table.rows))
            col_count = max(len(list(r.cells)) for r in table.rows)
            targets = list(range(row_count)) if rows is None else rows
            bad = [r for r in targets if not 0 <= r < row_count]
            if bad:
                raise ValueError(f"행 범위 밖: {bad} (행 {row_count}개)")
            cleared = 0
            for r in targets:
                for c in range(col_count):
                    if not self._cell_is_anchor(table, r, c):
                        continue
                    try:
                        table.set_cell_text(r, c, "", logical=True)
                        cleared += 1
                    except Exception:
                        continue  # 격자 밖(짧은 행) 좌표는 건너뜀
        return cleared

    def set_table_cells(self, table_index: int, assignments: list[tuple[int, int, str]]) -> int:
        """table_index번째 표의 (row, col) 셀들에 값을 기입. 기입 수 반환."""
        with quiet_engine():
            from hwpx.tools import table_navigation as tn

            tables = tn._collect_document_tables(self._doc)
            if not 0 <= table_index < len(tables):
                raise ValueError(f"표 인덱스 범위 밖: {table_index} (표 {len(tables)}개)")
            table = tables[table_index].table
            row_count = len(list(table.rows))
            for r, c, _ in assignments:
                if not 0 <= r < row_count:
                    raise ValueError(f"행 범위 밖: {r} (행 {row_count}개)")
            for r, c, value in assignments:
                table.set_cell_text(r, c, value, logical=True)
        return len(assignments)


    def _find_anchor_paragraph(self, anchor_text: str | None = None,
                               after_table: int | None = None):
        """앵커 문단 찾기 — 문단 원문(공백 정규화 전체 일치) 또는 표 인덱스
        (그 표가 든 문단). 표끼리 붙어 있어 사이 문단이 없을 때는 after_table이
        유일한 길이다."""
        import re as _re

        norm = lambda s: _re.sub(r"\s+", " ", (s or "")).strip()  # noqa: E731
        if (anchor_text is None) == (after_table is None):
            raise ValueError("anchor_text 또는 after_table 중 정확히 하나를 지정하세요.")
        if after_table is not None:
            from hwpx.tools import table_navigation as tn

            tables = tn._collect_document_tables(self._doc)
            if not 0 <= after_table < len(tables):
                raise ValueError(f"표 인덱스 범위 밖: {after_table} (표 {len(tables)}개)")
            el = tables[after_table].table.element
            while el is not None and not el.tag.endswith("}p"):
                el = el.getparent()
            if el is None:
                raise ValueError("표의 문단을 찾지 못했습니다.")
            tree = el.getroottree()
            target_path = tree.getpath(el)
            for para in self._doc.paragraphs:
                if para.element.getroottree().getpath(para.element) == target_path:
                    return para
            raise ValueError("표의 문단 객체를 찾지 못했습니다.")
        for para in self._doc.paragraphs:
            if norm(para.text) == norm(anchor_text):
                return para
        raise ValueError(f"해당 원문의 문단을 찾지 못함: {anchor_text!r}")

    def outline(self) -> list[dict]:
        """본문 문단 지도 — 인덱스·텍스트·표 위치(문서 순서 표 인덱스).

        앵커 후보 탐색용: 원시 XML을 뒤지지 않고 문단/표 배치를 한 번에 본다.
        """
        out = []
        table_counter = 0
        with quiet_engine():
            for i, para in enumerate(self._doc.paragraphs):
                entry: dict = {"paragraph": i, "text": (para.text or "")}
                tables_here = []
                for t in para.tables:
                    tables_here.append({
                        "table_index": table_counter,
                        "rows": t.row_count,
                        "cols": t.column_count,
                    })
                    table_counter += 1
                if tables_here:
                    entry["tables"] = tables_here
                out.append(entry)
        return out

    def copy_table(self, table_index: int, anchor_text: str | None = None,
                   after_table: int | None = None) -> dict:
        """table_index번째 표를 통째 복제해 anchor_text 문단에 삽입.

        원시 XML 노드 삽입은 엔진 저장이 무시한다(실험 확인) — 엔진 등록
        경유(add_table)로 새 표를 만든 뒤 내용을 원본의 deepcopy로 바꿔치기.
        서식·병합·행 높이까지 그대로 복제되고 저장에 살아남는다.
        """
        import copy as _copy

        import re as _re

        norm = lambda s: _re.sub(r"\s+", " ", (s or "")).strip()  # noqa: E731
        with quiet_engine():
            from hwpx.tools import table_navigation as tn

            tables = tn._collect_document_tables(self._doc)
            if not 0 <= table_index < len(tables):
                raise ValueError(f"표 인덱스 범위 밖: {table_index} (표 {len(tables)}개)")
            src = tables[table_index].table
            rows = len(list(src.rows))
            cols = max(len(list(r.cells)) for r in src.rows)

            target = self._find_anchor_paragraph(anchor_text=anchor_text,
                                                  after_table=after_table)

            new_table = target.add_table(rows, cols)
            new_el, src_el = new_table.element, src.element
            for child in list(new_el):
                new_el.remove(child)
            for key, value in src_el.attrib.items():
                if key != "id":  # 표 id는 새로 발급된 것 유지 (중복 방지)
                    new_el.set(key, value)
            for child in src_el:
                new_el.append(_copy.deepcopy(child))
        return {"rows": rows, "cols": cols}

    def set_page_break(self, at_text: str | None = None,
                       table_index: int | None = None) -> int:
        """문단(원문 일치) 또는 표가 앵커된 문단에 pageBreak=1 설정. 적용 수 반환.

        hwpx 문단은 pageBreak 속성(기본 '0')을 원래 갖고 있음 — 실증 2026-07-10.
        """
        import re as _re

        norm = lambda s: _re.sub(r"\s+", " ", (s or "")).strip()  # noqa: E731

        def _apply(paragraph) -> None:
            # 원시 element.set은 파일에서 연 문서의 저장 시 증발(모델 재직렬화) —
            # 반드시 모델 경유 (to_model → page_break → apply_model)
            model = paragraph.to_model()
            model.page_break = True
            paragraph.apply_model(model)

        with quiet_engine():
            if table_index is not None:
                from hwpx.tools import table_navigation as tn

                tables = tn._collect_document_tables(self._doc)
                if not 0 <= table_index < len(tables):
                    raise ValueError(f"표 인덱스 범위 밖: {table_index} (표 {len(tables)}개)")
                tbl_el = tables[table_index].table.element
                p_el = tbl_el
                while p_el is not None and not p_el.tag.endswith("}p"):
                    p_el = p_el.getparent()
                if p_el is None:
                    raise ValueError("표의 문단을 찾지 못했습니다.")
                tree = p_el.getroottree()
                target_path = tree.getpath(p_el)
                for para in self._doc.paragraphs:
                    if para.element.getroottree().getpath(para.element) == target_path:
                        _apply(para)
                        return 1
                raise ValueError("표의 문단 객체를 찾지 못했습니다.")
            for para in self._doc.paragraphs:
                if norm(para.text) == norm(at_text):
                    _apply(para)
                    return 1
            raise ValueError(f"해당 원문의 문단을 찾지 못함: {at_text!r}")

    def new_table(self, rows: int, cols: int, anchor_text: str | None = None,
                  like_table: int | None = None,
                  after_table: int | None = None) -> None:
        """anchor_text 문단에 rows×cols 새 표 생성. like_table 지정 시 그 표의
        테두리 서식 참조(borderFillIDRef — tbl·셀 최빈값)를 빌려 입힌다."""
        import re as _re
        from collections import Counter

        norm = lambda s: _re.sub(r"\s+", " ", (s or "")).strip()  # noqa: E731
        with quiet_engine():
            from hwpx.tools import table_navigation as tn

            tbl_ref = header_ref = body_ref = None
            header_h = body_h = None
            if like_table is not None:
                tables = tn._collect_document_tables(self._doc)
                if not 0 <= like_table < len(tables):
                    raise ValueError(f"like_table 범위 밖: {like_table} (표 {len(tables)}개)")
                src = tables[like_table].table
                tbl_ref = src.element.get("borderFillIDRef")

                def _row_ref(row):
                    refs = [c.element.get("borderFillIDRef") for c in row.cells]
                    refs = [r for r in refs if r]
                    return Counter(refs).most_common(1)[0][0] if refs else None

                src_rows = list(src.rows)
                if src_rows:
                    header_ref = _row_ref(src_rows[0])
                    header_h = list(src_rows[0].cells)[0].height
                if len(src_rows) > 1:
                    body_ref = _row_ref(src_rows[1])
                    body_h = list(src_rows[1].cells)[0].height
                body_ref = body_ref or header_ref
                body_h = body_h or header_h

            target = self._find_anchor_paragraph(anchor_text=anchor_text,
                                                  after_table=after_table)

            new_t = target.add_table(rows, cols)
            if tbl_ref:
                new_t.element.set("borderFillIDRef", tbl_ref)
            # 행별 차용: 헤더 행(0)은 기준 표 헤더 서식+높이, 본문 행은 본문 것
            for r_i, row in enumerate(new_t.rows):
                ref = header_ref if r_i == 0 else body_ref
                height = header_h if r_i == 0 else body_h
                for cell in row.cells:
                    if ref:
                        cell.element.set("borderFillIDRef", ref)
                    if height:
                        cell.set_size(height=height)

    def save_copy(self, out_path: str) -> str:
        out_abs = os.path.abspath(out_path)
        if out_abs == self._source_path:
            raise ValueError("원본 파일에 덮어쓸 수 없습니다. 다른 출력 경로를 지정하세요.")
        with quiet_engine():
            self._doc.save_to_path(out_abs)
        return out_abs
