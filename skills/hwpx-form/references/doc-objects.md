# 문서 개체 — 목차·각주·링크·책갈피·페이지 설정·도장·도형·이미지 편집

모든 명령은 `--out` 사본 저장(원본 불변), `--json` 봉투. 앵커(`--at-text`)는
**본문 문단 원문 전체 일치**(공백 정규화) — 표 셀 안 문단은 앵커가 못 된다.
앵커 후보는 `outline --json`에서 고를 것.

## 목차 — "목차 만들어줘"

```bash
hwpx-kit toc 문서.hwpx --json                                          # 후보 확인 (장 헤더 표·Ⅰ./제N장 문단)
hwpx-kit toc-add 문서.hwpx --at-text "<목차 넣을 위치 문단>" --out 결과.hwpx
```
- **쪽번호는 한글 COM으로 실측** (Windows + 한글이면 `--pages auto` 기본값이
  알아서) — 한글이 백그라운드로 잠깐 뜬다고 사용자에게 미리 알릴 것.
  한글 없는 환경은 제목만 들어가고 warnings로 알려줌
- 순서: ① `toc --json`으로 후보를 사용자에게 보여주고 빠진 장·잡음 확인
  ② 승인 후 toc-add ③ 결과의 warnings(쪽번호 미확인 항목) 전달
- 점선(·) 자리 맞춤은 표시 폭 근사 — 비례 폰트라 완벽 정렬은 아님.
  정밀 정렬 요구 시 한글에서 탭으로 다듬으라고 안내
- 목차는 보통 표지 다음, 본문 첫 장 앞 — 앵커는 outline으로 고르고,
  삽입 후 `page-break --at-text <본문 첫 문단>`으로 목차를 단독 쪽으로

## 각주/미주 — "여기에 각주 달아줘"

```bash
hwpx-kit note-add 문서.hwpx --at-text "<문단 원문>" --text "각주 내용" --out 결과.hwpx
hwpx-kit note-add 문서.hwpx --at-text "<문단 원문>" --text "미주 내용" --type endnote --out 결과.hwpx
```
붙임·출처·용어 설명에 사용. 각주 번호는 한글이 자동 부여.

## 하이퍼링크·책갈피

```bash
hwpx-kit link-add 문서.hwpx --at-text "<문단 원문>" --url "https://..." --display "표시 문구" --out 결과.hwpx
hwpx-kit bookmark-add 문서.hwpx --at-text "<문단 원문>" --name "책갈피이름" --out 결과.hwpx
```
링크는 앵커 문단 **끝에** 표시 문구가 덧붙는다 (문단 중간 삽입 아님).

## 페이지 설정 — "가로로 바꿔줘", "여백 줄여줘", "2단으로"

```bash
hwpx-kit page-setup 문서.hwpx --orientation landscape --out 결과.hwpx
hwpx-kit page-setup 문서.hwpx --paper A4 --margins "20,20,15,15" --out 결과.hwpx   # left,right,top,bottom mm
hwpx-kit page-setup 문서.hwpx --columns 2 --column-gap-mm 8 --out 결과.hwpx
```
- 가로 전환 시 기존 표 폭은 자동으로 안 늘어난다 — col-width로 재조정 필요할 수 있음
- 🔴 **다단은 텍스트 위주 문서 전용** — 표가 든 문서에 걸면 표 폭 > 단 폭이라
  겹침으로 무너진다 (실캡처 실증). 명령이 단 폭보다 넓은 표를 감지하면
  warnings로 알려주는데, 그 경고가 나오면 사용자에게 보여주고 진행 여부 확인.
  한글 육안 확인 필수 (validate 통과 ≠ 렌더 정상)

## 도장·서명 날인 — "도장 찍어줘" (겹침 배치)

image-add(글자처럼취급 — 칸 안에 들어감)와 다르다: **seal은 floating으로
글자 위에 겹쳐** 찍는다 — 발신명의 위 날인용.

```bash
hwpx-kit seal 문서.hwpx --image 도장.png --at-text "행정안전부장관" --size-mm 15 --dx-mm 25 --out 결과.hwpx
```
- `--dx-mm`/`--dy-mm`: 앵커 문단 왼쪽 위 기준 오른쪽/아래 오프셋 (0 이상만).
  발신명의 텍스트 길이를 보고 겹칠 위치를 추정해 지정 — 한글 글자 하나 ≈ 글자크기(pt)×0.35mm
- 도장 이미지는 사용자에게 받는다 (그려주지 않는다). 투명 배경 PNG 권장
- 🔴 **floating 배치는 한글 육안 확인 필수** — 위치가 어긋나면 dx/dy 조정 재시도

## 도형 — 구분선·사각형·타원

```bash
hwpx-kit shape-add 문서.hwpx --type line --at-text "<문단 원문>" --width-mm 150 --out 결과.hwpx      # 공문 결문 구분선
hwpx-kit shape-add 문서.hwpx --type rect --at-text "<문단 원문>" --width-mm 50 --height-mm 20 --fill "#FFE9A9" --out 결과.hwpx
```
글자처럼취급으로 앵커 문단에 **인라인**으로 들어간다 — 그래서 앵커는
**내용 없는 빈 줄용 문단**이어야 자연스럽다 (제목·본문 문단에 넣으면 글자
옆에 붙어 이상해 보임, 실캡처 실증). 빈 문단이 없으면 임시 앵커 패턴
(`text:`로 고유 문구 심기 → 도형 삽입 → 되돌리기)을 쓸 것.
색 상자 안 텍스트가 필요하면 도형 대신 1x1 표(cell-color)가 더 다루기 쉽다.
rect/ellipse는 실무 수요가 확인되기 전까지 굳이 권하지 말 것 — 구분선(line)이
주 용도다.

## 기존 이미지 편집 — "로고 바꿔줘", "사진 키워줘", "이미지 지워줘"

```bash
hwpx-kit image-list 문서.hwpx --json                                        # 인덱스·크기 확인 (편집 대상 특정)
hwpx-kit image-resize 문서.hwpx --index 0 --width-mm 40 --height-mm 25 --out 결과.hwpx
hwpx-kit image-replace 문서.hwpx --index 0 --image 새로고.png --out 결과.hwpx  # 크기·위치 유지, 그림만 교체
hwpx-kit image-del 문서.hwpx --index 0 --out 결과.hwpx                       # 배치+내장 바이너리 정리
```
- 인덱스는 image-list의 `picture_index` (본문 문서 순서). 편집 후 인덱스가
  변할 수 있으니 연속 편집은 매번 image-list로 재확인
- resize는 표시 크기만 바꾼다 (원본 픽셀 훼손 없음) — 비율 유지하려면
  기존 width:height 비로 계산해서 둘 다 지정
- 기관 로고 교체(image-replace)는 기하 보존이라 표지 레이아웃이 안 흔들린다

## 검증 공통

편집 후 `validate` → `inspect` (구조·미리보기 잔존 포함) →
**Windows + 한글 환경이면 `open-check`** (한글 실구동 열림 확인 — 개체 조작
후 필수 권장, exit 2면 산출물 폐기하고 원인 보고). floating 개체(seal)·
다단·각주의 **위치/모양**은 최종적으로 한글 육안 확인을 안내할 것 —
open-check는 열림만 보증하고 배치 품질은 못 본다.
