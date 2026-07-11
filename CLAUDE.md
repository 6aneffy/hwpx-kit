# hwpx-kit — 개발 컨텍스트

한글(HWPX/HWP) 문서 자동화 — Claude Code 플러그인(스킬 모음) + CLI.
"이 양식에 채워줘" 한마디로 서식 무손상 hwpx가 나오는 것이 목표.

> 내부 작업 노트(전략·검증 이력·백로그)는 `private/PROJECT-NOTES.md` (gitignore 구역).
> 세션 시작 시 그 파일을 먼저 읽을 것.

## 🔴 보안 — 최우선 규칙

**사용자(기관)가 제공한 문서 파일은 .env급 비밀이다.**

- `incoming/`, `private/` = 기밀 구역 (gitignore 됨). 이 안의 파일과 **모든 파생물**(render SVG, fill 결과, read 추출 텍스트)은 절대 git 커밋·외부 업로드 금지
- 코드·테스트에 사용자 문서 속 문장 하드코딩 금지 — 파일에서 동적 추출할 것 (`tests/test_real_forms.py` 참고)
- 레포 픽스처(`tests/fixtures/real/`)에는 **공개 출처 서식만** (현재: 서울시 정보소통광장 공개 서식 + 합성 legacy-sample.hwp)

## 아키텍처

```
skills/*/SKILL.md → Claude Code 플러그인 스킬들 (.claude-plugin/plugin.json이 컨테이너)
 ├─ hwpx-form        → 양식 채우기 코어 워크플로
 ├─ doc-create       → 백지 시작 라우터 (양식 유무 확인)
 ├─ format-convert   → 금액한글화·날짜요일·만나이 (CLI fmt 호출 — 암산 금지 원칙)
 ├─ gongmun-format   → 행안부 공문 규약 (지식 스킬)
 ├─ table-calc       → 표 증감·비율·합계 (지식 + fill 착지)
 └─ office-export    → hwpx→docx(변환)·pptx/xlsx(재구성, officecli 선택 의존)

CLI (cli.py) — JSON 봉투, 종료코드 0/1/2
 └─ commands/ (analyze·fill·read·validate·convert·export·render·generate·fmt·row-height·table-clear·table-set·table-copy·table-map·table-new·page-break·outline)
     ├─ format.py ← 순수함수 (금액한글화·요일·만나이) — 엔진 임포트 금지, fmt는 파일 인수 없음(FILE_NOT_FOUND 가드 우회)
     └─ adapter/ ← 명령 계층은 어댑터 인터페이스만 사용 (엔진 직접 import 금지)
         ├─ hwpx_engine.py   → python-hwpx (hwpx 분석·채우기·검증·표 조작, 순수 Python)
         ├─ office_readers.py → PDF·DOCX·XLSX 읽기 (pypdf/python-docx/openpyxl, Node 불필요)
         ├─ kordoc_engine.py → kordoc 3.18.0 고정 — 조건부 옵션: 한글 없는 환경의 구형 .hwp 읽기 + render + generate (Node 필요)
         └─ (convert.py·export.py) → pyhwpx/한글 COM (.hwp→.hwpx / .hwpx→docx, Windows+한글 필요)
```

- 배포: 레포 루트가 자기-마켓플레이스 (`.claude-plugin/marketplace.json`). 로컬 개발 반영은 `claude plugin update hwpx-kit@hwpx-kit-market`. 오프라인 zip은 `scripts/build_skill_package.py`
- MCP 서버(`mcp/`)는 공개 레포에서 제외(gitignore) — 로컬에만 유지, GUI 단계 대비. 환경변수: `HWPX_KIT_CLI` / `HWPX_KIT_CLI_ARGS` / `HWPX_KIT_CWD`. 테스트: `cd mcp && npm test`
- kordoc는 MIT, 보험 포크: github.com/6aneffy/kordoc (업스트림 소멸 대비)
- python-hwpx는 어댑터로 격리 — 문제 시 엔진 교체 가능하게 유지

## fill_key 계약 (analyze가 주고 fill이 소비)

| 키 | 대상 | 비고 |
|---|---|---|
| `clickhere:<이름>` | 누름틀 | 실서식으로 검증됨 |
| `marker:<키>` | `{{키}}` 마커 | 자체 정규식(한글 키 지원) — 엔진 것은 ASCII 전용이라 쓰면 안 됨 |
| `table:<라벨>` | 라벨 오른쪽 셀 | `#N`으로 중복 라벨 N번째 출현 지정, `> right > right` 방향 체인 가능. prefilled(기본값 찬 칸)도 덮어씀. 라벨은 공백 정규화(개행 든 병합 라벨 OK) |
| `text:<원문>` | 예시 텍스트 교체 | 런 단위 → 실패 시 문단 전체 일치 폴백. 서식 보존 |
| `delete:<문단원문>` | 양식 지시블록 삭제 | "(예시)", "←해당시" 류. blank-first 후 remove |
| `bold:<원문>` / `underline:<원문>` | 글자 서식 적용 (값 "") | 런 단위 — 원문을 품은 런 전체에 적용. 부분 강조는 원문이 런 경계와 일치해야 정밀 |

## 절대 규칙 (설계 불변)

1. **fill은 원본 절대 수정 금지** — `--out` 사본만. 원본 경로로 저장 시 ValueError
2. **`--json` 모드 stdout = JSON 한 줄만** — python-hwpx가 stdout에 print하므로 모든 엔진 호출은 `quiet_engine()`으로 감쌀 것. CLI는 stdout/stderr를 UTF-8로 강제(Windows cp949 문제)
3. **lxml 요소 프록시에 `id()` 쓰지 말 것** — GC 후 id 재사용으로 비결정 버그 남 (`test_press_form_title_text_replacement_roundtrip`이 재발 감지)
4. `skills/*/SKILL.md`(또는 templates/) 수정하면 **커밋·push 후 `claude plugin update hwpx-kit@hwpx-kit-market`** — 마켓플레이스가 GitHub(6aneffy/hwpx-kit) 기준이라 push가 곧 배포다. git 추적 파일만 설치되므로 기밀 유출 불가. 🔴 레포 루트를 **로컬 경로**로 마켓플레이스 등록 금지 — 로컬 경로 설치는 gitignore 무시 통째 복사라 기밀까지 캐시에 복제된다 (실사고 1회). 구 단일 스킬 폴더(`~/.claude/skills/hwpx-kit/`)가 다시 생기면 이중 트리거되니 지울 것

## 엔진 특성 (알아두면 삽질 안 함)

- 표 채우기는 어댑터 자체 구현(`fill_at_label`) — 엔진 `fill_by_path`는 라벨 속 `>`(예: `<총괄>`)를 경로 구분자로 오파싱해서 안 씀. 엔진 내부 열거(`_find_label_candidates`)를 직접 사용하니 엔진 교체 시 재구현 지점
- 표 셀 문단의 `p.remove()`는 예외 없이 무효될 수 있음 → 삭제는 blank-first
- kordoc render는 한컴 저장본(조판 캐시)만 정밀 — 우리가 만든 파일은 `--reflow` 합성 렌더로 자동 폴백되는데 **겹침 등 부정확. 대략 확인용일 뿐, 정확한 검증은 한글로 여는 것**
- 한글 COM(convert/export) 함정 3가지: ① SaveAs의 워드 형식 문자열은 `"OOXML"` — "DOCX"/"MSWORD"는 False 반환하며 조용히 실패 ② visible=False에서 경고 팝업 뜨면 무한대기 — `set_message_box_mode(AUTO_ANSWER_MODE)` 필수 (convert.py 상수) ③ **좀비 Hwp 프로세스가 남아 있으면 다음 COM 세션이 그냥 멈춤** — hang 시 `Stop-Process -Name Hwp -Force` 먼저
- python-hwpx에는 표 행 추가/삭제 API 없음 (`add_table`/`merge_table_cells`뿐) — 행 개수 변경은 사용자가 한글에서, 높이 정돈은 `row-height`, 내용 비우기는 `table-clear`, 좌표 기입은 `table-set`
- **셀 비우기는 서식을 잃지 않는다** (실험 확인): `set_cell_text('')`가 텍스트만 지우고 빈 런의 글자모양(charPr) 참조는 유지 → 재기입 시 원래 서식 물려받음. table-clear가 안전한 근거
- 병합 셀은 엔진 표 맵에서 같은 텍스트가 격자 전체에 복제되어 보임 — 어댑터 table_map()이 셀별 `is_anchor`를 덧붙이고, 라벨 후보·#N 열거는 anchor만 센다 (복제를 세면 #N 오염 + 같은 논리 셀 이중 기입으로 값 유실)
- analyze의 마커 탐지는 본문 문단만 훑음 — 표 셀 안 {{마커}}는 못 잡음 (fill은 됨) ← 개선 후보

## 개발 환경

- Python 3.11 venv (`.venv`), `uv sync` / `uv run pytest`
- 실행: `uv run hwpx-kit <명령>` 또는 전역 `hwpx-kit`
- 작업 방식: feature 브랜치 → 테스트 통과 → main 머지. TDD
- 커밋 게이트로 쓰는 테스트 명령은 파이프로 자르지 말 것 (종료코드 삼킴). 한글 COM 왕복 테스트는 간헐 플레이크 — 실패 시 한 번 재실행으로 판별
