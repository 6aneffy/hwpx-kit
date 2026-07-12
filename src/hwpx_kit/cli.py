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

    pn = sub.add_parser("render", help="레이아웃 보존 SVG 렌더 — 브라우저로 결과 확인 (kordoc 필요)")
    pn.add_argument("file")
    pn.add_argument("--out", help="출력 SVG 경로 (기본: 같은 이름 .svg)")
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

    pin = sub.add_parser("inspect", help="제출 전 기계 검수 — 잔여물({{마커}}·○○○)·공문 표기(날짜·시각)·개인정보. 위반 시 종료코드 2")
    pin.add_argument("file")
    pin.add_argument("--checks", help="쉼표 구분: residue,gongmun,pii (생략 시 전부)")
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

    pt = sub.add_parser("fmt", help="공문 표기 변환 — 금액 한글화·날짜(요일)·만나이 (파일 불필요)")
    pt.add_argument("--amount", help="금액 (정수, 콤마 허용)")
    pt.add_argument("--style", default="gongmun", choices=["gongmun", "ilgeum"],
                    help="금액 표기: gongmun=법정 공문(기본) / ilgeum=민간 관습(일금…원정)")
    pt.add_argument("--date", help="날짜 YYYYMMDD → YYYY.M.D.(요일)")
    pt.add_argument("--age", help="생년월일 YYMMDD → YYMMDD(만나이)")
    pt.add_argument("--base", help="만나이 기준일 YYYYMMDD (기본 오늘)")
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
        elif args.command == "render":
            data = run_render(args.file, out_path=args.out)
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
