# 사진·직인·머리말·쪽번호

## 사진·직인 넣기 — "여기 도장 찍어줘", "사진 붙여줘"

`hwpx-kit image-add <문서.hwpx> --image <파일.png> ... --out <결과.hwpx>`
- **직인/서명**: 대상 문단 원문으로 — `--at-text "서명: (인)" --width-mm 20`
  (원문은 read 출력에서 복사. 이미지 파일은 사용자에게 받는다 — 도장을 그려주지 않는다)
- **사진 첨부 칸**(표 안): `--table N --cell R,C --width-mm 35 --height-mm 45`
  (증명사진 규격 예시. 좌표는 table-map으로 확인)
- 글자처럼취급으로 들어가므로 셀 크기가 이미지에 맞을수록 깔끔 — 크게 넣으면
  행이 부푼다. 삽입 후 validate + 한글 육안 확인 안내
- 사용자 제공 사진·도장 이미지도 문서와 동일한 기밀 취급


## 머리말·꼬리말·쪽번호 — "쪽번호 넣어줘"

`hwpx-kit header-footer <문서.hwpx> [--header "텍스트"] [--footer "텍스트"] [--page-number center] --out <결과.hwpx>`
— 쪽번호 위치는 left/center/right. 문서관리번호·대외비 표기 등에 사용.

