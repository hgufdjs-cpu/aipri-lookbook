# 아이프리 코디 도감 — 공개 팬사이트 (배포 준비 버전)

공식 일본어 코디명 검색 + NAVER Cloud Papago로 번역해 **저장한 한국어명** 검색. 모바일/PC 반응형, 시리즈 필터, 브라우저 즐겨찾기(기기별), 이름순 정렬, 상세정보 모달, 더 보기, 공식 출처 링크 지원.

> **비공식 팬 사이트이며 공식 사이트와 무관합니다.** 공개 서버는 아직 만들거나 배포한 것이 아닙니다. 배포자의 호스팅 계정과 도메인이 필요합니다.

## 데이터 상태

- `app.py`에 2026-11-11 공식 코디 페이지에서 확인된 **일부 일본어 코디명**이 초기 데이터로 포함되어 있어 빈 화면 없이 시작합니다. 이미지는 초기 데이터에 포함되지 않습니다.
- 관리자가 `/api/refresh`를 호출하면 공식 코디 목록 페이지(오네가이 1~4, 링 1~6, 기존 1~6, 스페셜)를 읽고 이미지의 일본어 alt 이름/이미지 URL을 수집하려고 시도합니다. **공식 사이트 실제 HTML 크롤링 실행 결과는 검증되지 않았습니다**. 페이지에 따라 실패하거나 코디가 누락될 수 있습니다.
- 한국어 이름은 임의 번역을 하지 않습니다. 파파고 API 연결 후 `/api/translate`로 저장한 이름만 표시/검색됩니다. 키가 없으면 일본어 검색은 가능하지만 한국어 번역 검색은 제한됩니다.
- 이미지 외부 연결(핫링크)·수집·공개 이용 가능 여부를 권리자 정책과 약관으로 확인하고 사용하세요. 확인 전에는 이미지 없이 운영하거나 공식 링크만 제공하는 방법을 권장합니다.

## 로컬 설치

Python 3.10+ 설치 후 프로젝트 폴더에서:

```bash
python -m pip install -r requirements.txt
cp .env.example .env  # Windows: copy .env.example .env
python app.py
```

접속: http://127.0.0.1:5000

`.env`에서 `ADMIN_TOKEN`은 임의의 긴 값으로 바꾸고 외부에 노출하지 마세요. 파파고는 NAVER Cloud 콘솔에서 Papago Translation 앱과 인증키를 설정해야 합니다. 예전 NAVER Developers 파파고 API는 종료되었으므로 혼동하지 마세요.

## 관리자 전용 데이터 갱신

```bash
curl -X POST -H 'X-Admin-Token: YOUR_SECRET' http://127.0.0.1:5000/api/refresh
curl http://127.0.0.1:5000/api/status
curl -X POST -H 'X-Admin-Token: YOUR_SECRET' http://127.0.0.1:5000/api/translate
```

번역은 아직 한국어명이 없는 항목만 처리합니다. 실제 API 호출은 과금 및 요금 제한이 적용될 수 있습니다. 토큰이 없으면 두 관리자 명령은 403입니다. 방문자의 일반 검색으로 파파고 유료 API가 호출되지는 않습니다.

## 공개 서버 배포

Docker 기반 호스팅(Railway, VPS 등)에 업로드하세요. `Dockerfile`로 이미지가 빌드되고 웹서버는 호스팅의 `PORT`에 바인딩됩니다.

- 서버 비밀 환경변수: `ADMIN_TOKEN`, `PAPAGO_CLIENT_ID`, `PAPAGO_CLIENT_SECRET`, `DB_PATH=/data/aipri.db`
- **`/data` 영구 디스크**를 반드시 연결하세요. 그렇지 않으면 재배포 때 번역·수집 자료가 사라집니다.
- HTTPS 및 도메인 연결 후 `/health` 확인 → 관리자 갱신 → 데이터와 이미지/출처 검수 → 일반 공개 순서로 진행하세요.
- 개인 VPS의 Docker Compose 사용 시 `.env` 작성 후 `docker compose up -d --build`, `http://서버주소:8000` 확인. 공개 도메인은 HTTPS 역방향 프록시(예: Caddy/Nginx) 설정이 추가로 필요합니다.
- 정기 갱신을 원하면 서버의 scheduler에서 관리자 API를 제한된 주기로 호출하세요. 공식 서버에 잦은 접근은 하지 마세요.

## API

- `GET /api/outfits?q=...&series=...`: 코디 목록. 현재 웹 UI는 한 번 불러와 클라이언트에서 필터합니다.
- `GET /api/status`: 갱신 상태
- `GET /health`: 서비스 상태 확인
- `POST /api/refresh`: 관리자 인증 요구 (`X-Admin-Token`)
- `POST /api/translate`: 관리자 인증 + NAVER Cloud 인증 요구

## 운영 전 체크리스트

1. 공식 사이트 robots.txt/이용약관/이미지 사용 허용 범위 확인 및 요청 속도 제한
2. 전체 페이지별 코디명 추출 정확도·중복·레이아웃 이미지 제외 여부 검수
3. 파파고 한국어 번역 결과의 고유명사 교정, 번역 비용/쿼터 확인
4. 영구 DB 백업, HTTPS 도메인, 비밀키 관리
5. 모바일 브라우저에서 이미지 핫링크 작동 여부 확인

출처: https://aipri.jp/verse/item/oa4.html · https://aipri.jp/verse/item/oa3.html · NAVER Cloud Papago Translation 설명서 https://guide.ncloud-docs.com/docs/en/papagotranslation-use-apis

## Render 빠른 공개 안내

`render.yaml` (무료 테스트 환경용)을 추가했습니다. **반드시 `DEPLOY_RENDER.md`를 먼저 읽어 주세요.** 무료 플랜에는 DB 영구 보존이 없으므로 장기 공개 서비스에는 별도 데이터베이스가 필요합니다.
