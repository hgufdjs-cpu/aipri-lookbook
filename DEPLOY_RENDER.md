# Render를 통한 아이프리 코디 검색 사이트 공개

## 현재 범위
배포 설정(render.yaml)은 준비되어 있지만 **실제 서비스 공개는 아직 되지 않았습니다**. 사용자의 GitHub 및 Render 계정 연동이 필요합니다.

## 공개 방법
1. 이 ZIP을 압축 해제하고 `aipri-search` 폴더 안 파일들을 GitHub의 **새 저장소 최상위**에 업로드합니다. `.env`나 비밀키는 절대 업로드하지 않습니다.
2. https://dashboard.render.com/ 에 로그인하고 **New > Blueprint**를 선택합니다.
3. GitHub 저장소를 연결하고 `render.yaml`을 이용해 배포합니다. Papago 설정을 요구하면 네이버 클라우드에서 발급한 값을 넣습니다. 아직 키가 없으면 서비스 생성 후 환경변수에서 설정할 수 있습니다.
4. 배포가 완료되면 Render의 `https://...onrender.com` 주소에서 `/health`가 `{"ok":true}`를 반환하는지 확인합니다.
5. 서버 콘솔에서 `ADMIN_TOKEN` 환경변수 값을 확인한 뒤 관리자 API로 코디 수집, 파파고 번역을 순서대로 실행합니다. URL은 실제 Render URL로 바꿉니다.

```bash
curl -X POST -H 'X-Admin-Token: YOUR_ADMIN_TOKEN' https://YOUR_SITE.onrender.com/api/refresh
curl https://YOUR_SITE.onrender.com/api/status
curl -X POST -H 'X-Admin-Token: YOUR_ADMIN_TOKEN' https://YOUR_SITE.onrender.com/api/translate
```

## 운영상 주의
- **Render 무료 웹서비스는 로컬 DB 저장이 영구적이지 않습니다.** 앱을 다시 배포하거나 재시작하면 수집·번역 데이터가 사라질 수 있습니다. 실사용 목적이면 유료 영구 디스크 또는 PostgreSQL 영구 DB로 바꿔야 합니다. Render 무료 PostgreSQL도 30일 제한이 있습니다.
- 최초 코디명 일부만 제공됩니다. 한국어는 실제 Papago API 번역을 완료한 뒤 검색할 수 있습니다.
- 공식 사이트 이미지 재게시·원격 이미지 표시와 자동 수집은 권리자 정책을 먼저 확인하세요.
- 관리자 API는 공개 페이지 UI가 제공되지 않습니다. 비밀키는 웹페이지 소스나 GitHub에 넣지 마세요.
- 비공식 팬 사이트이며 공식 사이트와 무관하다는 고지를 유지하세요.

## 향후 개선
영구 DB 이전, 공식 페이지의 HTML 파서 검증, 이미지 이용 조건 확인, 관리자 화면, 자동 갱신 주기 제한.
