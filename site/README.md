# AI 객체 탐지 랜딩페이지

`latest_version.json`의 릴리스 정보를 빌드 시 읽는 Astro 사이트입니다. 공개 페이지는
정적으로 생성하고, 관리자 로그인·공지 저장·최신 공지 조회만 Vercel Functions로
처리합니다. 페이지에 버전·날짜·변경사항·다운로드 주소를 별도로 작성하지 않습니다.

## 로컬 실행

```bash
cd site
npm ci
npm run dev
```

정적 빌드와 결과 검증은 다음과 같이 실행합니다.

```bash
npm test
```

이 명령은 관리자 인증·공지 스키마·GitHub 저장 API 단위 테스트도 함께 실행합니다.

## 기존 공개페이지 사진

기존 Gamma 페이지에서 사용하던 실제 프로그램 화면과 현장 시연 사진은
`public/images/field/`에 보존합니다. 사진별 원본 이름과 사용 목적은
[`ASSET_SOURCES.md`](ASSET_SOURCES.md)에 기록합니다. 구형 프로그램 화면은 현재
버전처럼 보이지 않도록 이전 버전 기록으로 표시하며, 사진 속 탐지 수치는 성능 보증으로
사용하지 않습니다.

## 온라인 공지 관리자

`/admin`에서 작성한 일반 공지는 GitHub `content` 브랜치의 `site_updates.json`에만
자동 기록됩니다. 랜딩페이지와 데스크톱 GUI가 같은 공지를 읽으므로 글을 작성할 때마다
코드의 `main` 브랜치를 직접 커밋하거나 다시 배포할 필요가 없습니다.

`site/vercel.json`은 `content` 브랜치의 자동 배포를 끕니다. 공지를 저장할 때 GitHub
커밋은 남지만 Vercel 미리보기 배포는 새로 만들지 않습니다.

관리자 화면에서는 제목·요약·본문·표시 위치·관련 버전 표기만 관리합니다. 실제 프로그램
버전, Google Drive 주소, 배포 파일명·크기·SHA-256은 수정할 수 없으며 기존 릴리스
검증 절차만 사용합니다.

게시 내용과 수정 이력은 공개 GitHub 브랜치에 저장됩니다. 비밀번호, 내부 연락망,
개인정보, 위치정보, 사건정보 등 비공개 정보는 입력하지 않습니다.

### 1. 공지 브랜치 생성

최초 배포 전에 GitHub에 `content` 브랜치를 한 번 생성합니다. 브랜치가 이미 있으면
다시 실행하지 않습니다.

```bash
git push github main:content
```

### 2. 관리자 비밀값 준비

관리자 비밀번호는 평문이 아니라 scrypt 해시로 설정합니다. 프로젝트 루트에서 다음
명령을 실행하면 비밀번호를 화면에 표시하지 않고 해시를 생성합니다.

```bash
node site/scripts/hash-admin-password.mjs
```

세션 서명용 무작위 값은 별도로 생성합니다.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

GitHub에서는 `MuyeongKim/AI-page` 한 저장소만 선택한 fine-grained token을 만들고
`Contents: Read and write` 권한만 부여합니다. 토큰과 위 비밀값은 저장소나 브라우저
코드에 넣지 않습니다.

### 3. Vercel 환경변수

Vercel Production 환경에 다음 값을 Sensitive로 등록합니다.

- `ADMIN_PASSWORD_HASH`: 해시 생성 명령의 출력값
- `ADMIN_SESSION_SECRET`: 32바이트 이상의 무작위 값
- `GITHUB_CONTENT_TOKEN`: 한 저장소로 제한한 GitHub token

아래 값은 기본값과 다를 때만 설정합니다.

- `GITHUB_CONTENT_OWNER=MuyeongKim`
- `GITHUB_CONTENT_REPO=AI-page`
- `GITHUB_CONTENT_BRANCH=content`

설정 후 다시 배포하고 `https://운영주소/admin`에서 로그인·초안 작성·게시·게시 중단을
확인합니다. 비밀값이 없거나 `content` 브랜치가 없으면 관리자 API는 저장하지 않고
설정 오류를 반환합니다.

### 4. 로그인 요청 제한

공개 전 [Vercel WAF Rate Limiting](https://vercel.com/docs/vercel-firewall/vercel-waf/rate-limiting)을
참고해 Dashboard의 Firewall에서 다음 고정창 Rate Limit 규칙을 적용합니다.
서버 함수 내부 메모리는 인스턴스마다 달라 로그인 시도 제한 저장소로 사용하지 않습니다.

- 조건: Request Path가 `/api/admin/login`이고 Method가 `POST`
- 동작: IP 기준 10분에 10회, 초과 시 `429`

비밀번호를 바꾸면 새 해시로 `ADMIN_PASSWORD_HASH`를 교체한 뒤 다시 배포합니다. GitHub
token이 만료되거나 노출된 경우에는 즉시 폐기하고 새 token으로 교체합니다.

관리자 세션은 서버 저장소를 두지 않는 서명 쿠키 방식이며 2시간 후 만료됩니다. 로그아웃은
현재 브라우저 쿠키를 삭제하지만 이미 복사된 세션을 서버에서 개별 폐기할 수는 없습니다.
세션 노출이 의심되면 `ADMIN_SESSION_SECRET`을 교체하고 다시 배포해 모든 기존 세션을
무효화합니다.

## Windows 배포본 공개

새 버전으로 올리면 `python scripts/export_release.py`가 이전 배포 링크를 자동으로
폐기하고 `preparing` 상태로 초기화합니다. 검증된 EXE 배포본을 Google Drive에
올린 뒤 프로젝트 루트에서 실제 로컬 배포 파일과 공유 주소를 함께 지정합니다. 파일명,
크기와 SHA-256은 스크립트가 직접 계산하므로 `latest_version.json`에 수동으로 입력하지
않습니다.

```bash
python scripts/export_release.py \
  --download-file /path/to/AI-object-detection.exe \
  --download-url https://drive.google.com/file/d/FILE_ID/view

python scripts/export_release.py --check
```

두 다운로드 옵션을 함께 제공하지 않거나, 파일이 없거나 비어 있거나, 주소가 허용된
Google Drive HTTPS 주소가 아니면 `ready` 상태로 전환하지 않습니다.

스크립트는 로컬 파일의 무결성을 계산하지만 Google Drive의 대용량 파일을 다시
다운로드하지는 않습니다. 공개 전에는 로그아웃 또는 비공개 브라우저에서 공유 주소로
실제 다운로드가 가능한지 확인하고, 내려받은 파일의 SHA-256이 원본과 같은지 확인하세요.

```bash
# macOS / Linux
shasum -a 256 /path/to/downloaded-file

# Windows PowerShell
Get-FileHash C:\path\to\downloaded-file -Algorithm SHA256
```

## Vercel 설정

1. GitHub의 `MuyeongKim/AI-page` 저장소를 Vercel 프로젝트로 가져옵니다.
2. Production Branch는 `main`, Root Directory는 `site`로 지정합니다.
3. Root Directory 설정에서 빌드 시 상위 소스 파일 포함 옵션을 활성화합니다.
4. Framework Preset은 Astro, Install Command는 `npm ci`를 사용합니다.
5. Vercel이 배정한 운영 URL 또는 충돌 없는 사용자 도메인을 Production 범위의
   `SITE_URL` 환경변수로 지정한 뒤 다시 배포합니다. Preview에는 이 값을 설정하지
   않습니다. 값이 없으면 HTML과 robots.txt에서 검색엔진 색인을 차단하고 canonical
   URL과 소셜 이미지 절대 주소를 내보내지 않습니다.

현재 `stayup-ai.com`은 다른 서비스가 사용 중이므로 새 랜딩페이지의 도메인으로
가정하지 않습니다. 실제 운영 주소가 확정되기 전 기존 도메인의 DNS를 변경하지 마세요.

공개 페이지는 정적 출력이고 관리자 API만 서버 함수로 실행됩니다. 비밀 환경변수는
Vercel 서버에서만 사용되며 클라이언트 번들에 포함하지 않습니다. 현재 루트
`index.html`의 Gamma 이동은 Vercel 검증과 도메인 전환을 마친 뒤 제거합니다.
