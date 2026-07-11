---
name: office-export
description: 한글(hwpx) 문서를 오피스 형식으로 — 워드(docx) 변환, 파워포인트(pptx) 발표자료 재구성, 엑셀(xlsx) 표 추출. "이거 PPT로 만들어줘", "워드로 줘", "워드로도 뽑아줘", "엑셀로 정리해줘" 요청 시 사용. Triggers: convert hwpx to Word/docx, make a PowerPoint from this Hangul document.
---

# office-export: hwpx → 워드/파워포인트/엑셀

포맷마다 경로가 다르다 — 이 구분이 이 스킬의 핵심:

| 대상 | 경로 | 성격 |
|---|---|---|
| DOCX | `hwpx-kit export` (한글 COM) + officecli 후처리 | **변환** — 내용·서식 이어받음 |
| PPTX | `hwpx-kit read` → 슬라이드 설계 → officecli 생성 | **재구성** — 요약·재배치 (변환기는 세상에 없음) |
| XLSX | `hwpx-kit read` → 표 데이터 추출 → officecli 생성 | **재구성** — 표만 발췌 |

전제: `officecli` CLI (선택 의존성, 무료·오피스 설치 불필요).
`officecli --version`으로 확인하고, 없으면 **사용자에게 물어보고 네가 직접 설치**:

> "PPTX/XLSX 생성에는 officecli(무료 오픈 배포 CLI)가 필요합니다. 설치할까요? (명령 한 줄, 인터넷 필요)"

승낙하면 실행 — Windows PowerShell: `irm https://d.officecli.ai/install.ps1 | iex` /
macOS·Linux: `curl -fsSL https://d.officecli.ai/install.sh | bash`.
설치 후 `officecli --version` 재확인 (안 잡히면 새 터미널 필요할 수 있음 —
전체 경로나 PATH 갱신 후 재시도). 사용자에게 설치를 떠넘기지 말 것 —
질문 한 번, 설치는 네가.
officecli가 없어도(설치 거절 시) DOCX는 `hwpx-kit export`만으로 가능(후처리 생략),
PPTX/XLSX는 불가 — 이 한계를 그대로 안내.

## DOCX

hwpx-form 스킬의 "워드(docx)로도 달라는 경우" 절차를 그대로 따른다
(export → 페이지 밀림 후처리 3종 → "사람 최종 손질" 안내).

## PPTX (발표자료 재구성)

1. `hwpx-kit read <문서> --format md`로 내용 파악 — 장 구조·핵심 수치·표
2. **슬라이드 구성안을 먼저 사용자에게 보여주고 확정** — 재구성은 요약이라
   무엇을 넣고 뺄지는 사용자 결정 (임의 누락 금지). 기본 설계:
   - 장(章)당 슬라이드 1장, 표지 + 목차/개요 포함
   - 슬라이드당 핵심 3~5개 항목만 (문서 문장을 그대로 붓지 말 것)
   - 큰 표는 핵심 행·열만 발췌하거나 요점 문장으로
3. **생성 전에 반드시 `officecli load_skill pptx` 실행하고 그 규칙대로** —
   이거 건너뛰고 텍스트만 부으면 "워드 문서를 슬라이드에 붙인 것" 같은 결과가
   나온다 (실증된 실패). 최소 준수: 팔레트 1개(공공·대학은 Midnight Executive
   계열이 무난)·한글은 맑은 고딕 명시, 제목 ≥36pt 볼드·본문 ≥18pt, 슬라이드마다
   비텍스트 시각 요소(번호 원, 단계 카드, 통계 큰 숫자, 스타일된 표), 표지에
   제목+부제+기관+날짜, 발표자 노트. 수치·금액은 원문 그대로 — 금액 병기는
   format-convert 스킬(`hwpx-kit fmt`)
4. QA 두 단계: `officecli view <결과> issues` (0건까지) →
   `officecli view <결과> screenshot -o <png>` 렌더를 **직접 눈으로 확인** —
   셀 줄바꿈 잘림("스튜디/오"), 단어 중간 절단 같은 건 issues가 못 잡는다.
   표 셀이 좁으면 `colWidths`로 열 폭 조정

## XLSX (표 추출)

1. read 출력에서 대상 표를 찾고, 어느 표를 원하는지 애매하면 사용자에게 확인
2. officecli로 시트 생성 — 헤더 굵게, 숫자는 숫자 타입으로 (콤마 문자열 금지,
   서식은 셀 서식으로). 합계 행은 수식(`=SUM(...)`)으로 넣어 검산 가능하게
3. `officecli validate` 후 경로 안내

## 공통 규칙

- 원본 hwpx는 절대 수정하지 않는다 — 산출물은 별도 파일
- 사용자(기관) 제공 문서의 산출물(pptx/xlsx/docx)도 원본과 동일한 기밀 —
  `incoming/`/`private/` 규칙 그대로, 커밋·외부 업로드 금지
- officecli 사용법이 불확실하면 추측하지 말고 `officecli help <format> <element>` 조회
