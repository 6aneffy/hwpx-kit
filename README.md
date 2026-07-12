<div align="center">

# hwpx-kit

**한글(HWPX) 문서 자동화 — Claude Code 플러그인 & CLI**

*"이 양식에 채워줘" 한마디로, 서식 무손상 한글 문서가 나옵니다.*

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/hwpx-kit-cli.svg)](https://pypi.org/project/hwpx-kit-cli/)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-d97757.svg)](https://claude.com/claude-code)
[![Tests](https://img.shields.io/badge/tests-193%20passing-brightgreen.svg)](tests/)

</div>

---

## 무엇이 되나

한글(HWP/HWPX)은 한국 공공·기업 문서의 표준이지만, AI가 다룰 수 있는 도구가 사실상 없었습니다.
hwpx-kit은 **AI 에이전트가 한글 문서를 읽고, 채우고, 고치고, 새로 만들 수 있게** 하는 도구 모음입니다.

```
👤 "이 양식에 채워줘"                    → 서식(폰트·표·조판) 무손상으로 값만 채운 사본
👤 "이 기획서를 ○○사업용으로 바꿔줘"      → 기존 문서를 양식 삼아 내용 전면 교체
👤 "한글로 새 기획서 만들어줘"            → 내장 템플릿으로 표지·장·표 갖춘 문서 생성
👤 "예산 앞에 장 하나 추가하고 표 넣어줘"   → 장 헤더 복제·새 표 생성·쪽나눔까지
👤 "금액 한글로 병기해줘"                → 금12,340원(금일만이천삼백사십원) — 계산 착오 0
👤 "이거 워드로도 줘" / "PPT로 만들어줘"   → docx 변환 / 발표자료 재구성
👤 "이 명단으로 위촉장 30부 만들어줘"      → 엑셀 명단 × 양식 일괄 생성 (메일머지)
👤 "제출 전에 검토해줘"                  → 빈칸·표기 위반·개인정보 잔존 기계 검수
👤 "여기 도장 찍어줘"                    → 직인·증명사진 삽입 (이미지는 사용자 제공)
```

모든 채우기는 **원본을 절대 수정하지 않고** 사본에만 씁니다. 실제 공공기관 서식
(보도자료·신청서·계획서·회의록·공고문)으로 왕복 검증했습니다.

| | hwpx-kit 없이 | hwpx-kit으로 |
|---|---|---|
| 양식 채우기 | 한글 열고 칸마다 복붙, 서식 깨지면 수작업 복구 | 파일 주고 한마디 — 서식 무손상 사본 |
| 새 기획서 | 백지에서 표지·표·조판 직접 | 내장 템플릿에 내용만 — 몇 분 완주 |
| 금액 병기 | 손으로 한글 표기 (오타 위험) | 결정론 계산 — `금12,340원(금일만이천삼백사십원)` |
| AI에게 한글 파일 | 못 읽음 · PDF 변환 우회 | hwpx·hwp 직접 읽기/쓰기 |

**이런 분들을 위해 만들었습니다**: 공공기관·학교의 서식 담당자, 사업계획서를 반복 작성하는
창업자·연구자, 한글 문서를 AI 워크플로에 넣고 싶은 개발자.

## 데모 — 한마디로 기획서 한 부

> "hwpx로 새로운 사업기획서 작성해줘. 서울광역시에서 진행하는 Claude Code 해커톤"

**① 시작점 — 내장 템플릿** (양식 파일이 없을 때 기준. 갖고 있는 양식이 있으면 그 양식을 그대로 씁니다)

![내장 템플릿](docs/images/Before.png)

**② 작업 과정** — 필수 정보(일시·대상·주최·예산)를 먼저 묻고, 답을 받아 진행합니다

![작업 과정](docs/images/Tasking.png)

**③ 결과물** — 표지·5개 장·일정표·예산표까지 채워진 완성본. 서식은 템플릿 그대로

![완성본](docs/images/After.png)

이 데모에서 실제로 일어난 일들:

- **아는 것만 쓰고, 모르는 건 묻습니다** — 장소가 미정이라고 하자 "서울 시내 행사장(추후 확정)"으로 표기하고 확정되면 수정하겠다고 알림. 말하지 않은 정원·시상금을 지어내지 않음
- **내용을 주면 그대로, 안 주면 Claude가 초안** — 시상금 구성은 사용자가 준 숫자 그대로, 추진배경·목적은 "필요하다고 생각하는 것들 다 써줘"라는 요청에 Claude가 작성. **상세하게 말할수록 상세하게 반영됩니다**
- **표 계산은 결정론** — 예산표 합계 7,000 + 30,000 = 총계 37,000천원, 수기 계산 착오 없음
- **구조도 바꿉니다** — 장 추가/복제, 표 행 추가·삭제(서식 승계), 쪽나눔까지. "5장 뒤에 강사진 장 추가해줘"가 통합니다
- **기존 양식 재활용** — 작성 완료된 옛 기획서를 주고 "○○사업용으로 바꿔줘"라고 하면 그 문서를 양식 삼아 내용만 전면 교체 (서식 무손상)

## 30초 설치

Claude Code에서:

```
/plugin marketplace add 6aneffy/hwpx-kit
/plugin install hwpx-kit@hwpx-kit-market
```

이게 전부입니다. CLI 런타임은 첫 사용 때 스킬이 알아서 설치를 진행합니다
(PC에 Python 3.10+만 있으면 됩니다).

<details>
<summary>수동 설치</summary>

```bash
pip install hwpx-kit-cli
```

```powershell
# Windows 일괄 (CLI + 플러그인 등록)
irm https://raw.githubusercontent.com/6aneffy/hwpx-kit/main/install.ps1 | iex
```
</details>

## 스킬 (Claude Code 플러그인)

| 스킬 | 트리거 | 역할 |
|------|--------|------|
| **hwpx-form** | "이 양식에 채워줘" | 분석→채우기→검증 코어 워크플로. 일괄 생성(메일머지)·표 조작·이미지·secure 채우기 포함 |
| **doc-create** | "기획서 만들어줘" (파일 없이) | 백지 생성 라우터 — 내장 템플릿(표지·장 헤더·표 골격) 기반 |
| **format-convert** | "금액 한글로", "요일 붙여줘" | 금액 병기·날짜 요일·만나이 — 결정론 계산 (LLM 암산 금지) |
| **gongmun-format** | "공문 형식으로", "검토해줘" | 행안부 공문 규약 — 글머리 위계(□○-※\*), 표기, 제출 전 기계 검수 |
| **table-calc** | "증감 채워줘" | 보고서 표 증감(△·%p)·비율·합계 계산과 관습 표기 |
| **office-export** | "워드로", "PPT로" | docx 변환(한글 COM) / pptx·xlsx 재구성 |

스킬은 사용자에게 **필수 정보를 먼저 묻고**(선택지 UI), 초안을 확정받은 뒤 작업합니다.
말하지 않은 값을 지어내지 않습니다.

## CLI

모든 명령은 `--json`으로 한 줄 JSON 봉투(`ok`/`data`/`warnings`/`error`)를 반환합니다.
종료 코드: `0` 성공 · `1` 오류 · `2` 부분 성공.

```bash
# 읽기·분석
hwpx-kit analyze 양식.hwpx --json            # 채울 수 있는 필드 탐지 (fill_key 반환)
hwpx-kit read 문서 --format md               # 본문 추출 — hwpx·PDF·DOCX·XLSX 내장 지원
hwpx-kit outline 문서.hwpx --json            # 문단·표 배치 지도 (삽입 앵커 탐색)
hwpx-kit table-map 문서.hwpx --table 3 --json # 표 셀 좌표·병합 상태
hwpx-kit validate 문서.hwpx --json           # 구조 검증

# 채우기·편집 (원본 불변 — 항상 --out 사본)
hwpx-kit fill 양식.hwpx --data 값.json --out 결과.hwpx
hwpx-kit fill-batch 양식.hwpx --rows 명단.xlsx --template 값틀.json --out-dir 결과/ --name "{성명}_위촉장.hwpx"  # 메일머지
hwpx-kit inspect 결과.hwpx --json            # 제출 전 검수 — 잔여 마커·공문 표기·개인정보
hwpx-kit table-set 문서.hwpx --table 3 --data 셀.json --out 결과.hwpx   # 좌표 셀 쓰기
hwpx-kit table-clear 문서.hwpx --table 3 --rows 1-20 --out 결과.hwpx    # 셀 내용 비우기
hwpx-kit table-copy 문서.hwpx --table 1 --after-table 4 --out 결과.hwpx # 표 통째 복제 (서식·병합 유지)
hwpx-kit table-new 문서.hwpx --rows 6 --cols 4 --like-table 3 --after-text "앵커" --out 결과.hwpx
hwpx-kit row-add 문서.hwpx --table 3 --like 2 --count 3 --out 결과.hwpx      # 행 추가 (기준 행 서식 승계)
hwpx-kit row-del 문서.hwpx --table 3 --rows 5-7 --out 결과.hwpx              # 행 삭제
hwpx-kit row-height 문서.hwpx --table 3 --like 1 --rows 2-5 --out 결과.hwpx  # 행 높이 정돈
hwpx-kit page-break 문서.hwpx --table 5 --out 결과.hwpx                 # 쪽나눔 (새 장 시작)
hwpx-kit image-add 문서.hwpx --image 도장.png --at-text "(인)" --width-mm 20 --out 결과.hwpx  # 직인·사진
hwpx-kit header-footer 문서.hwpx --footer "대외비" --page-number center --out 결과.hwpx

# 변환·생성
hwpx-kit fmt --amount 12340 --json           # 금12,340원(금일만이천삼백사십원)
hwpx-kit fmt --date 20260101 --json          # 2026.1.1.(목)
hwpx-kit convert 문서.hwp --json             # .hwp → .hwpx (Windows + 한글)
hwpx-kit export 문서.hwpx --to docx --json   # 워드로 내보내기 (Windows + 한글)
hwpx-kit generate 초안.md --out 새문서.hwpx   # Markdown → 공문서 (kordoc)
hwpx-kit render 문서.hwpx --out p.svg        # SVG 미리보기 (kordoc)
```

## fill_key 계약

`analyze`가 주는 키를 그대로 데이터 JSON의 키로 씁니다.

| 키 | 대상 | 예시 |
|----|------|------|
| `clickhere:<이름>` | 누름틀 필드 | `"clickhere:신청자": "김철수"` |
| `marker:<키>` | `{{키}}` 마커 | `"marker:출장기간": "7/14~7/16"` |
| `table:<라벨>` | 라벨 오른쪽 셀 | `"table:성명": "김철수"` |
| `table:<라벨>#N` | 같은 라벨 N번째 | `"table:담당 부서#2": "운영과"` |
| `table:<라벨> > <방향>` | 방향 체인 | `"table:과 장 > right > right": "010-…"` |
| `text:<원문>` | 문장 교체 (서식 보존) | `"text:○○○ 사업": "청년 AI교육 사업"` |
| `delete:<문단원문>` | 안내문 삭제 | `"delete:(예시입니다)": ""` |
| `bold:` / `underline:<원문>` | 굵게·밑줄 | `"bold:핵심 성과": ""` |

## 요구 사항

| 기능 | 필요한 것 |
|------|-----------|
| 분석·채우기·검증·표 조작·표기 변환·PDF/DOCX/XLSX 읽기 | **Python 3.10+ 만** (순수 파이썬) |
| `.hwp` 변환, 워드(docx) 내보내기 | Windows + 한글(한컴오피스) |
| 한글 없는 환경(Mac 등)의 구형 `.hwp` 읽기, MD→HWPX, SVG | [kordoc](https://github.com/chrisryugj/kordoc) (Node 18+, 선택) |

## 아키텍처

```
Claude Code 스킬 6종 ──→  hwpx-kit CLI (23 명령, JSON 봉투)
                              └─ adapter/  ← 엔진 격리 계층
                                  ├─ python-hwpx    hwpx 분석·채우기·표 조작
                                  ├─ pypdf·python-docx·openpyxl   타 포맷 읽기
                                  ├─ pyhwpx(COM)    .hwp 변환·docx 내보내기
                                  └─ kordoc         구형 .hwp·생성·렌더 (선택)
templates/ 기본 계획서 템플릿 (표지·장 헤더·표 골격, 마커 내장)
```

설계 불변 원칙: **① 원본 절대 수정 금지 ② `--json` stdout은 봉투 한 줄만
③ 서식은 항상 보존** (셀을 비워도 글자모양이 유지되어 재기입 시 원래 서식을 물려받음).

## 민감정보 처리 (secure 모드)

주민번호·계좌 같은 값은 **AI 모델을 거치지 않고** 채울 수 있습니다:
사용자가 값 파일을 직접 작성 → 스킬은 경로만 전달 → `fill --secure`가 CLI에서만 읽어 채움.
`--secure`는 하나라도 못 채우면 산출물 없이 실패하고(부분 채움 방지), 출력에 값을 노출하지 않습니다.
제출 전 `inspect`로 개인정보 잔존(주민번호·전화·이메일 패턴)도 기계 검사할 수 있습니다.

> 🚧 같은 코어를 MCP 서버로 노출하는 버전도 제작 중입니다 (Claude Desktop 등 MCP 클라이언트용).

## 검증

- 자동 테스트 193개 (pytest)
- 실서식 수렴 테스트: 보도자료·신청서·계획서·회의록·공고문 5계열,
  실제 공공기관 문서 30여 종으로 analyze→fill→validate 왕복
- 실사용 시나리오 테스트 3회 (백지 생성 12분 완주, 장·표 동적 추가, 보도자료 변환)

## 라이선스

[Apache-2.0](LICENSE) · © 2026 [6aneffy](https://github.com/6aneffy)

이슈·PR 환영합니다. 특히 실제 기관 양식에서의 analyze/fill 실패 사례 제보가 가장 값집니다
(단, **기관 내부 문서를 이슈에 첨부하지 마세요** — 재현 가능한 합성 예시로 부탁드립니다).
