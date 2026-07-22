from __future__ import annotations

import argparse
import json
import os
import sys

from hwpx_kit.commands.analyze import run_analyze
from hwpx_kit.commands.convert import run_convert
from hwpx_kit.commands.export import run_export
from hwpx_kit.commands.fill import run_fill
from hwpx_kit.commands.fmt import run_fmt
from hwpx_kit.commands.generate import run_generate
from hwpx_kit.commands.outline import run_outline
from hwpx_kit.commands.page_break import run_page_break
from hwpx_kit.commands.read import run_read
from hwpx_kit.commands.render import run_render
from hwpx_kit.commands.row_height import parse_rows_spec, run_row_height
from hwpx_kit.commands.table_clear import run_table_clear
from hwpx_kit.commands.table_copy import run_table_copy
from hwpx_kit.commands.table_map_cmd import run_table_map
from hwpx_kit.commands.table_new import run_table_new
from hwpx_kit.commands.table_set import parse_assignments, run_table_set
from hwpx_kit.commands.validate import run_validate
from hwpx_kit.output import envelope, print_result


def _dist_version() -> str:
    # PyPI 배포명은 hwpx-kit-cli (hwpx-kit은 유사명 차단) — 구명 설치본 폴백 유지
    from importlib.metadata import PackageNotFoundError, version

    for name in ("hwpx-kit-cli", "hwpx-kit"):
        try:
            return version(name)
        except PackageNotFoundError:
            continue
    return "unknown"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hwpx-kit", description="HWPX 양식 자동화 CLI")
    p.add_argument("--version", action="version", version=f"hwpx-kit {_dist_version()}")
    sub = p.add_subparsers(dest="command", required=True)

    pa = sub.add_parser("analyze", help="양식에서 채울 수 있는 필드 탐지")
    pa.add_argument("file")
    pa.add_argument("--json", action="store_true")

    pf = sub.add_parser("fill", help="필드에 값 채워 사본 저장 (원본 불변)")
    pf.add_argument("file")
    pf.add_argument("--data", required=True, help="fill_key: 값 매핑 JSON 파일")
    pf.add_argument("--out", required=True, help="출력 hwpx 경로")
    pf.add_argument("--secure", action="store_true",
                    help="엄격 모드(민감정보용) — 하나라도 못 채우면 산출물 없이 실패, 출력에 값 비노출")
    pf.add_argument("--json", action="store_true")

    pr = sub.add_parser("read", help="본문을 Markdown/텍스트로 추출")
    pr.add_argument("file")
    pr.add_argument("--format", default="md", choices=["md", "text"])
    pr.add_argument("--json", action="store_true")

    pv = sub.add_parser("validate", help="hwpx 구조 검증")
    pv.add_argument("file")
    pv.add_argument("--json", action="store_true")

    pc = sub.add_parser("convert", help=".hwp를 .hwpx로 변환 (Windows + 한글 필요)")
    pc.add_argument("file")
    pc.add_argument("--out", help="출력 hwpx 경로 (기본: 같은 이름 .hwpx)")
    pc.add_argument("--json", action="store_true")

    px = sub.add_parser("export", help=".hwpx를 다른 형식으로 내보내기 — 워드(docx) (Windows + 한글 필요)")
    px.add_argument("file")
    px.add_argument("--to", default="docx", choices=["docx"], help="출력 형식 (기본 docx)")
    px.add_argument("--out", help="출력 경로 (기본: 같은 이름에 형식 확장자)")
    px.add_argument("--json", action="store_true")

    pn = sub.add_parser("render", help="레이아웃 보존 미리보기 — com: 한글 실물 PDF(정확) / kordoc: SVG(근사)")
    pn.add_argument("file")
    pn.add_argument("--out", help="출력 경로 (com→.pdf, kordoc→.svg, 기본: 같은 이름)")
    pn.add_argument("--engine", default="auto", choices=["auto", "com", "kordoc"],
                    help="auto=한글 있으면 com PDF(기본) / com=한글 실물 PDF / kordoc=SVG 근사")
    pn.add_argument("--json", action="store_true")

    pg = sub.add_parser("generate", help="Markdown → 공문서 HWPX 생성 (kordoc 필요)")
    pg.add_argument("file", help="입력 Markdown 파일")
    pg.add_argument("--out", required=True, help="출력 hwpx 경로")
    pg.add_argument("--preset", help="kordoc 공문서 프리셋 (예: 보고서)")
    pg.add_argument("--json", action="store_true")

    ph = sub.add_parser("row-height", help="표 기준 행 높이를 지정 행들에 복사 (행 추가 후 높이 정돈)")
    ph.add_argument("file")
    ph.add_argument("--table", type=int, required=True, help="표 인덱스 (analyze의 table_index, 0-기준)")
    ph.add_argument("--like", type=int, required=True, help="기준 행 (0-기준)")
    ph.add_argument("--rows", required=True, help="대상 행: '3-7' 범위 / '3,5' 나열 / 혼합")
    ph.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    ph.add_argument("--json", action="store_true")

    pfb = sub.add_parser("fill-batch", help="명단 × 양식 일괄 생성 (메일머지) — 위촉장·수료증·통지서 N부")
    pfb.add_argument("file", help="양식 hwpx")
    pfb.add_argument("--rows", required=True, help="명단 파일 (xlsx: 1행 헤더 / csv / json 객체 배열)")
    pfb.add_argument("--template", required=True, help="fill 데이터 JSON — 값 속 {열이름}이 행마다 치환됨")
    pfb.add_argument("--out-dir", required=True, help="출력 폴더 (없으면 생성)")
    pfb.add_argument("--name", required=True, help='파일명 패턴, 예: "{성명}_위촉장.hwpx" (충돌 시 _2 접미)')
    pfb.add_argument("--json", action="store_true")

    pin = sub.add_parser("inspect", help="제출 전 기계 검수 — 잔여물·공문 표기·개인정보·구조(유령 셀 등)·미리보기 잔존. 위반 시 종료코드 2")
    pin.add_argument("file")
    pin.add_argument("--checks", help="쉼표 구분: residue,gongmun,pii,structure,preview,layout (생략 시 layout 제외 전부)")
    pin.add_argument("--json", action="store_true")

    pim = sub.add_parser("image-add", help="이미지(사진·직인) 삽입 — 문단 앵커 또는 표 셀에 글자처럼취급")
    pim.add_argument("file")
    pim.add_argument("--image", required=True, help="이미지 파일 (png/jpg/bmp/gif)")
    pim.add_argument("--at-text", help="이 원문 문단에 삽입 (공백 정규화 전체 일치)")
    pim.add_argument("--table", type=int, help="표 인덱스 (--cell과 함께)")
    pim.add_argument("--cell", help="셀 좌표 'R,C' (0-기준)")
    pim.add_argument("--width-mm", type=float, default=20.0, help="가로 크기 mm (기본 20)")
    pim.add_argument("--height-mm", type=float, help="세로 크기 mm (생략 시 가로와 동일)")
    pim.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pim.add_argument("--json", action="store_true")

    phf = sub.add_parser("header-footer", help="머리말/꼬리말 텍스트·쪽번호 설정")
    phf.add_argument("file")
    phf.add_argument("--header", help="머리말 텍스트")
    phf.add_argument("--footer", help="꼬리말 텍스트")
    phf.add_argument("--page-number", help="쪽번호 위치: left/center/right")
    phf.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    phf.add_argument("--json", action="store_true")

    ptb = sub.add_parser("table-build", help="선언형 원샷 표 생성 — 스펙 JSON(크기·열폭·병합·헤더·내용·정렬) 하나로 완성 표")
    ptb.add_argument("file")
    ptb.add_argument("--spec", required=True, help="표 스펙 JSON 파일")
    ptb.add_argument("--at-text", help="이 원문 문단에 삽입")
    ptb.add_argument("--after-table", type=int, help="이 표 뒤에 삽입 (0-기준)")
    ptb.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    ptb.add_argument("--json", action="store_true")

    pca = sub.add_parser("cell-align", help="셀 텍스트 정렬 — 범위 일괄 (left/center/right/justify)")
    pca.add_argument("file")
    pca.add_argument("--table", type=int, required=True)
    pca.add_argument("--range", dest="cell_range", required=True, help="'R1,C1:R2,C2'")
    pca.add_argument("--align", required=True, choices=["left", "center", "right", "justify"])
    pca.add_argument("--out", required=True)
    pca.add_argument("--json", action="store_true")

    pcm = sub.add_parser("cell-merge", help="표 셀 병합 — 범위 'R1,C1:R2,C2'")
    pcm.add_argument("file")
    pcm.add_argument("--table", type=int, required=True, help="표 인덱스 (0-기준)")
    pcm.add_argument("--range", dest="cell_range", required=True, help="병합 범위 'R1,C1:R2,C2'")
    pcm.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pcm.add_argument("--json", action="store_true")

    pcs = sub.add_parser("cell-split", help="병합 셀 해제 — anchor 좌표 지정")
    pcs.add_argument("file")
    pcs.add_argument("--table", type=int, required=True)
    pcs.add_argument("--cell", required=True, help="병합 anchor 'R,C'")
    pcs.add_argument("--out", required=True)
    pcs.add_argument("--json", action="store_true")

    pcc = sub.add_parser("cell-color", help="셀 배경색 — 범위 일괄 (헤더 행 강조 등)")
    pcc.add_argument("file")
    pcc.add_argument("--table", type=int, required=True)
    pcc.add_argument("--range", dest="cell_range", required=True, help="'R1,C1:R2,C2' (단일 셀은 같은 좌표 반복)")
    pcc.add_argument("--color", required=True, help="6자리 hex, 예: #FFE9A9")
    pcc.add_argument("--out", required=True)
    pcc.add_argument("--json", action="store_true")

    pcw = sub.add_parser("col-width", help="열 너비 비율 조정 — 셀 줄바꿈 잘림 해결")
    pcw.add_argument("file")
    pcw.add_argument("--table", type=int, required=True)
    pcw.add_argument("--widths", required=True, help="열별 비율 쉼표 구분, 예: '2,3,5' (열 수와 일치)")
    pcw.add_argument("--out", required=True)
    pcw.add_argument("--json", action="store_true")

    pra = sub.add_parser("row-add", help="표 행 추가 — 기준 행 서식·높이 승계, 내용은 비움 (세로 병합 걸리면 거부)")
    pra.add_argument("file")
    pra.add_argument("--table", type=int, required=True, help="표 인덱스 (0-기준)")
    pra.add_argument("--like", type=int, required=True, help="복제할 기준 행 (0-기준, 병합 없는 행)")
    pra.add_argument("--count", type=int, default=1, help="추가할 행 수 (기본 1)")
    pra.add_argument("--at", type=int, help="새 행 시작 위치 (0-기준, 생략 시 기준 행 바로 다음)")
    pra.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pra.add_argument("--json", action="store_true")

    prd = sub.add_parser("row-del", help="표 행 삭제 — 세로 병합은 구간 전체를 함께 지정해야 허용")
    prd.add_argument("file")
    prd.add_argument("--table", type=int, required=True, help="표 인덱스 (0-기준)")
    prd.add_argument("--rows", required=True, help="삭제할 행: '3-7' 범위 / '3,5' 나열 / 혼합")
    prd.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    prd.add_argument("--json", action="store_true")

    pca = sub.add_parser("col-add", help="표 열 추가 — 기준 열 서식·폭 승계, 내용은 비움 (병합 표는 제약)")
    pca.add_argument("file")
    pca.add_argument("--table", type=int, required=True, help="표 인덱스 (0-기준)")
    pca.add_argument("--like", type=int, required=True, help="복제할 기준 열 (0-기준, 병합 없는 열)")
    pca.add_argument("--count", type=int, default=1, help="추가할 열 수 (기본 1)")
    pca.add_argument("--at", type=int, help="새 열 시작 위치 (0-기준, 생략 시 기준 열 바로 다음)")
    pca.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pca.add_argument("--json", action="store_true")

    pcd = sub.add_parser("col-del", help="표 열 삭제 — 가로 병합은 구간 전체를 함께 지정해야 허용")
    pcd.add_argument("file")
    pcd.add_argument("--table", type=int, required=True, help="표 인덱스 (0-기준)")
    pcd.add_argument("--cols", required=True, help="삭제할 열: '3-7' 범위 / '3,5' 나열 / 혼합")
    pcd.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pcd.add_argument("--json", action="store_true")

    pcl = sub.add_parser("table-clear", help="표의 지정 행 셀 내용 비우기 (구조는 유지 — 잔존 내용 정리용)")
    pcl.add_argument("file")
    pcl.add_argument("--table", type=int, required=True, help="표 인덱스 (0-기준)")
    pcl.add_argument("--rows", help="대상 행 '1-20'/'1,3' (생략 시 표 전체)")
    pcl.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pcl.add_argument("--json", action="store_true")

    pb = sub.add_parser("page-break", help="문단(또는 표) 앞 쪽나눔 — 끼워넣은 장을 새 쪽에서 시작시킴")
    pb.add_argument("file")
    pb.add_argument("--at-text", help="대상 문단 원문 (공백 정규화 전체 일치)")
    pb.add_argument("--table", type=int, help="이 표가 든 문단에 적용 (0-기준)")
    pb.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pb.add_argument("--json", action="store_true")

    pm = sub.add_parser("table-map", help="표 셀 상태 덤프 — 좌표·텍스트·병합 anchor (검사용)")
    pm.add_argument("file")
    pm.add_argument("--table", type=int, help="특정 표만 (0-기준, 생략 시 전체)")
    pm.add_argument("--json", action="store_true")

    pnw = sub.add_parser("table-new", help="임의 R×C 새 표 생성 (--like-table로 기존 표 서식 차용)")
    pnw.add_argument("file")
    pnw.add_argument("--rows", type=int, required=True)
    pnw.add_argument("--cols", type=int, required=True)
    pnw.add_argument("--after-text", help="삽입 위치 문단 원문")
    pnw.add_argument("--after-table", type=int, help="이 표 뒤(같은 문단)에 삽입")
    pnw.add_argument("--like-table", type=int, help="테두리 서식을 빌릴 기존 표 인덱스")
    pnw.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pnw.add_argument("--json", action="store_true")

    po = sub.add_parser("outline", help="문단·표 배치 지도 (앵커 탐색용, 읽기 전용)")
    po.add_argument("file")
    po.add_argument("--json", action="store_true")

    pcp = sub.add_parser("table-copy", help="표 통째 복제를 지정 문단에 삽입 (장 헤더 박스 늘리기 등)")
    pcp.add_argument("file")
    pcp.add_argument("--table", type=int, required=True, help="복제할 표 인덱스 (0-기준)")
    pcp.add_argument("--after-text", help="삽입 위치 문단의 원문 (read 출력에서 복사)")
    pcp.add_argument("--after-table", type=int, help="이 표 뒤(같은 문단)에 삽입 — 표 사이에 문단이 없을 때")
    pcp.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pcp.add_argument("--json", action="store_true")

    pts = sub.add_parser("table-set", help="표 셀 좌표 지정 쓰기 (table-clear로 비운 셀에 새 항목 기입)")
    pts.add_argument("file")
    pts.add_argument("--table", type=int, required=True, help="표 인덱스 (0-기준)")
    pts.add_argument("--set", action="append", metavar="R,C=값",
                     help="셀 기입 (반복 지정 가능, 0-기준 좌표) — 5개 이하 소량용")
    pts.add_argument("--data", help='셀 기입 JSON 파일 {"R,C": "값"} — 대량 기입은 이쪽 (명령 길이 한계 회피)')
    pts.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pts.add_argument("--json", action="store_true")

    pna = sub.add_parser("note-add", help="각주/미주 추가 — 앵커 문단 원문 지정")
    pna.add_argument("file")
    pna.add_argument("--at-text", required=True, help="각주를 달 문단 원문 (공백 정규화 전체 일치)")
    pna.add_argument("--text", required=True, help="각주/미주 내용")
    pna.add_argument("--type", default="footnote", choices=["footnote", "endnote"])
    pna.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pna.add_argument("--json", action="store_true")

    pla = sub.add_parser("link-add", help="하이퍼링크 추가 — 앵커 문단 끝에 표시문구+URL")
    pla.add_argument("file")
    pla.add_argument("--at-text", required=True, help="링크를 붙일 문단 원문")
    pla.add_argument("--url", required=True)
    pla.add_argument("--display", required=True, help="표시 문구")
    pla.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pla.add_argument("--json", action="store_true")

    pbm = sub.add_parser("bookmark-add", help="책갈피 추가 — 앵커 문단에 이름 표식")
    pbm.add_argument("file")
    pbm.add_argument("--at-text", required=True, help="책갈피를 둘 문단 원문")
    pbm.add_argument("--name", required=True, help="책갈피 이름")
    pbm.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pbm.add_argument("--json", action="store_true")

    pps = sub.add_parser("page-setup", help="용지·방향·여백·다단 설정 (다단은 한글 육안 확인 권장)")
    pps.add_argument("file")
    pps.add_argument("--paper", choices=["A4", "A3", "B4", "B5", "LETTER"], help="용지 규격")
    pps.add_argument("--orientation", choices=["portrait", "landscape"], help="용지 방향")
    pps.add_argument("--margins", help="여백 mm 'left,right,top,bottom' 4값")
    pps.add_argument("--columns", type=int, help="다단 수 (섹션 전체)")
    pps.add_argument("--column-gap-mm", type=float, help="단 간격 mm (기본 8)")
    pps.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pps.add_argument("--json", action="store_true")

    psl = sub.add_parser("seal", help="도장·서명 겹침 배치 — 발신명의 위 날인 (floating, 한글 육안 확인 필수)")
    psl.add_argument("file")
    psl.add_argument("--image", required=True, help="도장 이미지 (png/jpg/bmp/gif)")
    psl.add_argument("--at-text", required=True, help="기준 문단 원문 (발신명의 줄)")
    psl.add_argument("--size-mm", type=float, default=15.0, help="도장 크기 mm (기본 15)")
    psl.add_argument("--dx-mm", type=float, default=0.0, help="문단 기준 가로 오프셋 mm")
    psl.add_argument("--dy-mm", type=float, default=0.0, help="문단 기준 세로 오프셋 mm")
    psl.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    psl.add_argument("--json", action="store_true")

    psh = sub.add_parser("shape-add", help="도형 삽입 — 구분선(line)·사각형(rect)·타원(ellipse)")
    psh.add_argument("file")
    psh.add_argument("--type", required=True, choices=["line", "rect", "ellipse"])
    psh.add_argument("--at-text", required=True, help="삽입 위치 문단 원문")
    psh.add_argument("--width-mm", type=float, required=True)
    psh.add_argument("--height-mm", type=float, default=0.0)
    psh.add_argument("--fill", help="채움색 6자리 hex (rect/ellipse)")
    psh.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    psh.add_argument("--json", action="store_true")

    pil = sub.add_parser("image-list", help="본문 이미지 목록 — 인덱스·크기 (편집 대상 확인)")
    pil.add_argument("file")
    pil.add_argument("--json", action="store_true")

    pir = sub.add_parser("image-resize", help="이미지 크기 변경 — 위치·배치 유지")
    pir.add_argument("file")
    pir.add_argument("--index", type=int, required=True, help="image-list의 picture_index")
    pir.add_argument("--width-mm", type=float)
    pir.add_argument("--height-mm", type=float)
    pir.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pir.add_argument("--json", action="store_true")

    pip_ = sub.add_parser("image-replace", help="이미지 교체 — 크기·위치·배치 그대로, 그림만 갈아끼움")
    pip_.add_argument("file")
    pip_.add_argument("--index", type=int, required=True, help="image-list의 picture_index")
    pip_.add_argument("--image", required=True, help="새 이미지 파일")
    pip_.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pip_.add_argument("--json", action="store_true")

    pid = sub.add_parser("image-del", help="이미지 삭제 — 본문 배치와 내장 바이너리까지 정리")
    pid.add_argument("file")
    pid.add_argument("--index", type=int, required=True, help="image-list의 picture_index")
    pid.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pid.add_argument("--json", action="store_true")

    ptc = sub.add_parser("toc", help="목차 후보 나열 (읽기 전용) — 장 헤더 표·장 패턴 문단 탐지")
    ptc.add_argument("file")
    ptc.add_argument("--json", action="store_true")

    pta = sub.add_parser("toc-add", help="목차 블록 삽입 — 쪽번호는 한글 COM으로 실측 (Windows + 한글이면 자동)")
    pta.add_argument("file")
    pta.add_argument("--at-text", required=True, help="목차가 들어갈 위치의 문단 원문 (그 뒤에 삽입)")
    pta.add_argument("--title", default="목 차", help='목차 제목 (기본 "목 차")')
    pta.add_argument("--pages", default="auto", choices=["auto", "com", "none"],
                     help="쪽번호: auto=한글 있으면 실측(기본) / com=필수 / none=제목만")
    pta.add_argument("--width", type=int, default=64, help="줄 표시 폭(반각 단위, 기본 64) — 점선 길이 계산용")
    pta.add_argument("--own-page", action="store_true",
                     help="목차를 새 쪽에서 시작 (제목에 쪽나눔) — 표지 뒤 삽입 시 권장")
    pta.add_argument("--out", required=True, help="출력 hwpx 경로 (원본 불변)")
    pta.add_argument("--json", action="store_true")

    poc = sub.add_parser("open-check", help="한글 실열림 확인 — 정적 검사가 못 잡는 스키마 거부 탐지 (Windows + 한글 필요, 실패 시 종료코드 2)")
    poc.add_argument("file")
    poc.add_argument("--json", action="store_true")

    pt = sub.add_parser("fmt", help="공문 표기 변환 — 금액 한글화·날짜(요일)·만나이 (파일 불필요)")
    pt.add_argument("--amount", help="금액 (정수, 콤마 허용)")
    pt.add_argument("--style", default="gongmun", choices=["gongmun", "ilgeum"],
                    help="금액 표기: gongmun=법정 공문(기본) / ilgeum=민간 관습(일금…원정)")
    pt.add_argument("--date", help="날짜 YYYYMMDD → YYYY.M.D.(요일)")
    pt.add_argument("--age", help="생년월일 YYMMDD → YYMMDD(만나이)")
    pt.add_argument("--base", help="만나이 기준일 YYYYMMDD (기본 오늘)")
    pt.add_argument("--scale", help="원 단위 금액 → --unit 단위로 환산 (반올림·콤마)")
    pt.add_argument("--unit", default="천원", choices=["천원", "백만원"], help="--scale 대상 단위 (기본 천원)")
    pt.add_argument("--json", action="store_true")

    return p


def main(argv: list[str] | None = None) -> int:
    # 파이프/리다이렉트 시 Windows 기본이 cp949 — JSON 소비자를 위해 UTF-8 고정.
    # stderr(엔진 한글 경고)도 동일 — 로그 리다이렉트 시 깨짐 방지
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args(argv)
    as_json = args.json

    # fmt는 파일 입력이 없다 — 파일 가드는 파일 위치인수가 있는 명령에만
    if args.command != "fmt" and not os.path.exists(args.file):
        env = envelope(
            args.command, ok=False,
            error={"code": "FILE_NOT_FOUND", "message": f"파일이 없습니다: {args.file}"},
        )
        print_result(env, as_json)
        return 1

    try:
        exit_code = 0
        if args.command == "analyze":
            data = run_analyze(args.file)
        elif args.command == "fill":
            with open(args.data, encoding="utf-8") as fh:
                mapping = json.load(fh)
            if args.secure:
                from hwpx_kit.commands.fill import run_fill_secure

                data = run_fill_secure(args.file, mapping, args.out)
                if not data["ok"]:
                    exit_code = 1
            else:
                data = run_fill(args.file, mapping, args.out)
                if data["unmatched"]:
                    exit_code = 2
        elif args.command == "read":
            data = run_read(args.file, fmt=args.format)
        elif args.command == "convert":
            data = run_convert(args.file, out_path=args.out)
        elif args.command == "export":
            data = run_export(args.file, to=args.to, out_path=args.out)
        elif args.command == "fmt":
            data = run_fmt(
                amount=args.amount, date=args.date, age=args.age,
                base=args.base, style=args.style,
                scale=args.scale, unit=args.unit,
            )
        elif args.command == "row-height":
            data = run_row_height(
                args.file, table=args.table, like=args.like,
                rows=parse_rows_spec(args.rows), out_path=args.out,
            )
        elif args.command == "fill-batch":
            from hwpx_kit.commands.fill_batch import run_fill_batch

            data = run_fill_batch(
                args.file, rows_path=args.rows, template_path=args.template,
                out_dir=args.out_dir, name_pattern=args.name,
            )
            if not data["all_ok"]:
                exit_code = 2
        elif args.command == "inspect":
            from hwpx_kit.commands.inspect_doc import run_inspect

            data = run_inspect(
                args.file,
                checks=[c.strip() for c in args.checks.split(",")] if args.checks else None,
            )
            if not data["clean"]:
                exit_code = 2
        elif args.command == "image-add":
            from hwpx_kit.commands.image_add import run_image_add

            data = run_image_add(
                args.file, image_path=args.image, at_text=args.at_text,
                table=args.table, cell=args.cell,
                width_mm=args.width_mm, height_mm=args.height_mm,
                out_path=args.out,
            )
        elif args.command == "header-footer":
            from hwpx_kit.commands.header_footer import run_header_footer

            data = run_header_footer(
                args.file, header=args.header, footer=args.footer,
                page_number=args.page_number, out_path=args.out,
            )
        elif args.command == "table-build":
            from hwpx_kit.commands.table_build import run_table_build

            data = run_table_build(args.file, spec_path=args.spec,
                                   at_text=args.at_text, out_path=args.out,
                                   after_table=args.after_table)
        elif args.command == "cell-align":
            from hwpx_kit.commands.table_build import run_cell_align

            data = run_cell_align(args.file, table=args.table,
                                  cell_range=args.cell_range,
                                  align=args.align, out_path=args.out)
        elif args.command == "cell-merge":
            from hwpx_kit.commands.table_style import run_cell_merge

            data = run_cell_merge(args.file, table=args.table,
                                  cell_range=args.cell_range, out_path=args.out)
        elif args.command == "cell-split":
            from hwpx_kit.commands.table_style import run_cell_split

            data = run_cell_split(args.file, table=args.table,
                                  cell=args.cell, out_path=args.out)
        elif args.command == "cell-color":
            from hwpx_kit.commands.table_style import run_cell_color

            data = run_cell_color(args.file, table=args.table,
                                  cell_range=args.cell_range,
                                  color=args.color, out_path=args.out)
        elif args.command == "col-width":
            from hwpx_kit.commands.table_style import run_col_width

            data = run_col_width(
                args.file, table=args.table,
                widths=[float(w) for w in args.widths.split(",")],
                out_path=args.out,
            )
        elif args.command == "row-add":
            from hwpx_kit.commands.table_rows import run_row_add

            data = run_row_add(
                args.file, table=args.table, like=args.like,
                count=args.count, at=args.at, out_path=args.out,
            )
        elif args.command == "row-del":
            from hwpx_kit.commands.table_rows import run_row_del

            data = run_row_del(
                args.file, table=args.table,
                rows=parse_rows_spec(args.rows), out_path=args.out,
            )
        elif args.command == "col-add":
            from hwpx_kit.commands.table_rows import run_col_add

            data = run_col_add(
                args.file, table=args.table, like=args.like,
                count=args.count, at=args.at, out_path=args.out,
            )
        elif args.command == "col-del":
            from hwpx_kit.commands.table_rows import run_col_del

            data = run_col_del(
                args.file, table=args.table,
                cols=parse_rows_spec(args.cols), out_path=args.out,
            )
        elif args.command == "table-clear":
            data = run_table_clear(
                args.file, table=args.table,
                rows=parse_rows_spec(args.rows) if args.rows else None,
                out_path=args.out,
            )
        elif args.command == "table-set":
            assignments = []
            if args.set:
                assignments += parse_assignments(args.set)
            if args.data:
                from hwpx_kit.commands.table_set import load_assignments_file

                assignments += load_assignments_file(args.data)
            if not assignments:
                raise ValueError("--set 또는 --data 중 하나는 지정해야 합니다.")
            data = run_table_set(
                args.file, table=args.table,
                assignments=assignments, out_path=args.out,
            )
        elif args.command == "table-copy":
            data = run_table_copy(
                args.file, table=args.table,
                after_text=args.after_text, out_path=args.out,
                after_table=args.after_table,
            )
        elif args.command == "outline":
            data = run_outline(args.file)
        elif args.command == "page-break":
            data = run_page_break(
                args.file, at_text=args.at_text, table=args.table, out_path=args.out,
            )
        elif args.command == "table-map":
            data = run_table_map(args.file, table=args.table)
        elif args.command == "table-new":
            data = run_table_new(
                args.file, rows=args.rows, cols=args.cols,
                after_text=args.after_text, like_table=args.like_table,
                out_path=args.out, after_table=args.after_table,
            )
        elif args.command == "toc":
            from hwpx_kit.commands.toc import run_toc

            data = run_toc(args.file)
        elif args.command == "toc-add":
            from hwpx_kit.commands.toc import run_toc_add

            data = run_toc_add(args.file, at_text=args.at_text, out_path=args.out,
                               title=args.title, pages=args.pages,
                               width=args.width, own_page=args.own_page)
        elif args.command == "open-check":
            from hwpx_kit.commands.open_check import run_open_check

            data = run_open_check(args.file)
            if not data["opens"]:
                exit_code = 2
        elif args.command == "note-add":
            from hwpx_kit.commands.doc_objects import run_note_add

            data = run_note_add(args.file, at_text=args.at_text, text=args.text,
                                kind=args.type, out_path=args.out)
        elif args.command == "link-add":
            from hwpx_kit.commands.doc_objects import run_link_add

            data = run_link_add(args.file, at_text=args.at_text, url=args.url,
                                display=args.display, out_path=args.out)
        elif args.command == "bookmark-add":
            from hwpx_kit.commands.doc_objects import run_bookmark_add

            data = run_bookmark_add(args.file, at_text=args.at_text,
                                    name=args.name, out_path=args.out)
        elif args.command == "page-setup":
            from hwpx_kit.commands.doc_objects import run_page_setup

            margins = None
            if args.margins:
                vals = [float(v) for v in args.margins.split(",")]
                if len(vals) != 4:
                    raise ValueError("--margins는 'left,right,top,bottom' mm 4값")
                margins = dict(zip(("left", "right", "top", "bottom"), vals))
            data = run_page_setup(args.file, paper=args.paper,
                                  orientation=args.orientation, margins=margins,
                                  columns=args.columns,
                                  column_gap_mm=args.column_gap_mm,
                                  out_path=args.out)
        elif args.command == "seal":
            from hwpx_kit.commands.doc_objects import run_seal

            data = run_seal(args.file, at_text=args.at_text, image_path=args.image,
                            size_mm=args.size_mm, dx_mm=args.dx_mm,
                            dy_mm=args.dy_mm, out_path=args.out)
        elif args.command == "shape-add":
            from hwpx_kit.commands.doc_objects import run_shape_add

            data = run_shape_add(args.file, at_text=args.at_text, shape=args.type,
                                 width_mm=args.width_mm, height_mm=args.height_mm,
                                 fill_color=args.fill, out_path=args.out)
        elif args.command == "image-list":
            from hwpx_kit.commands.image_edit import run_image_list

            data = run_image_list(args.file)
        elif args.command == "image-resize":
            from hwpx_kit.commands.image_edit import run_image_resize

            data = run_image_resize(args.file, index=args.index,
                                    width_mm=args.width_mm,
                                    height_mm=args.height_mm, out_path=args.out)
        elif args.command == "image-replace":
            from hwpx_kit.commands.image_edit import run_image_replace

            data = run_image_replace(args.file, index=args.index,
                                     image_path=args.image, out_path=args.out)
        elif args.command == "image-del":
            from hwpx_kit.commands.image_edit import run_image_del

            data = run_image_del(args.file, index=args.index, out_path=args.out)
        elif args.command == "render":
            data = run_render(args.file, out_path=args.out, engine=args.engine)
        elif args.command == "generate":
            data = run_generate(args.file, args.out, preset=args.preset)
        else:
            data = run_validate(args.file)
            if not data["valid"]:
                exit_code = 2
    except Exception as exc:
        env = envelope(
            args.command, ok=False,
            error={"code": "COMMAND_FAILED", "message": str(exc)},
        )
        print_result(env, as_json)
        return 1

    env = envelope(args.command, ok=True, data=data)
    if as_json:
        print_result(env, as_json=True)
    else:
        if args.command == "read":
            print(data["content"])
        else:
            print_result(env, as_json=False)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
