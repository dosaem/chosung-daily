# 티켓 20 최종 리뷰 — 라운드 1

- 검토일: 2026-10-14
- 기준: 로컬 `main` (`491418f`) ... `HEAD` (`9ff5509`). `origin/main` 미사용.
- 검토 커밋: `2fa6a75`, `36d94c5`, `9ff5509`.
- 읽은 자료: 티켓 20, 스펙 §C.27 및 US 64·65, 전체 변경 diff, 구현 증거 문서, 관련 compose·CI·테스트.
- UI·마이그레이션 변경 없음. NAS 접속·배포·외부 서비스 호출·push 없음.

## 티켓 체크박스별 판정

| 체크박스 | 충족 여부 | 직접 확인한 근거 |
|---|---|---|
| 대상별 설정 선택, pull/build/upgrade/재기동 확인/health 200, 두 인자 로컬 검증 및 RELEASE 절차 | 미충족 | `deploy/deploy.sh`의 대상별 분기와 compose 명령 순서, 서비스 목록 비교, 실제 발행 포트 조회는 구현됨. 두 인자 dry-run 및 가짜 NAS 실행 테스트 통과. 그러나 실제 HTTP 302에서도 성공 종료하여 200 검사 요구 위반(D-20-2). RELEASE의 로컬 절차는 존재하나 실제 Docker 재기동은 이번 리뷰에서 실행하지 않음. |
| main/develop push, CI 성공 선행, Tailscale → SSH, ci.yml 변경 제한 | 미충족 | workflow_run의 CI 성공 조건, 브랜치 매핑, Tailscale 후 SSH 순서 확인. ci.yml diff는 develop 추가 한 줄뿐. 그러나 성공한 CI의 head_sha는 러너의 스크립트 선택에만 적용되고 NAS 빌드 소스는 최신 브랜치이므로 미검증 커밋 배포 가능(D-20-1). 실제 Actions/Tailscale 연결은 범위상 검증하지 않음. |
| secrets 목록 표, NAS 사람 작업 D3 분리, push 금지 | 충족 | RELEASE에 사용한 secret 이름 4개와 D3 체크리스트 존재. 변경 파일에서 실제 운영 키·토큰·비밀번호 값은 발견하지 않음. 리뷰 중 push하지 않았으며, 구현자의 과거 push 여부는 로컬 diff/log만으로 독립 증명할 수 없음. |

공통 공유 파일 규칙은 미충족(D-20-3). README는 설계 판단 끝의 `### 20.` 추가로 규칙을 지켰지만 RELEASE는 일부만 번호 절에 추가했다.

## 직접 실행한 검증

- `uv run ruff check .` → `All checks passed!` (exit 0).
- `TEST_REDIS_URL=redis://127.0.0.1:6379/15 uv run pytest -q` → **135 passed in 36.43s** (exit 0). `TEST_DATABASE_URL` 환경변수 미설정임을 확인했고 레포 기본 `chosung_daily_test`를 그대로 사용했다. 새 DB 생성 없음. 간헐 실패·재실행 없음.
- `bash -n deploy/deploy.sh` → exit 0.
- 마이그레이션 추가/변경이 없으므로 `flask db heads` 추가 실행 대상 아님.
- `git diff --check main...HEAD` → 구현 증거 문서 164행의 trailing whitespace로 exit 2. 기능 결함으로 집계하지 않음.
- 아래 두 동작은 임시 로컬 Git 저장소, 레포의 fake docker/sleep, 실제 curl 및 루프백 HTTP 서버로 재현했다. 가짜 git/curl을 사용하지 않았고 실제 Docker 배포·원격 Git 호출도 하지 않았다.

## 결함 목록

### D-20-1 — CI 통과 커밋과 실제 NAS 빌드 커밋이 연결되지 않음

- 심각도: **MAJOR**
- 위치: `deploy/deploy.sh:82`, `.github/workflows/deploy.yml:27`, `.github/workflows/deploy.yml:51`
- 재현: 임시 로컬 origin의 main에 A를 커밋하고 가짜 NAS 디렉터리 `chosung-daily`에 clone한다. A의 CI 성공 이벤트가 배포를 시작한 상황에서 origin main에 B를 추가한다. `DEPLOY_BASE_DIR`를 임시 NAS에 지정하고, PATH에는 레포의 fake docker/sleep만 추가해 `bash deploy/deploy.sh prod`를 실행한다. 실제 git은 B를 pull하며 이후 compose build는 B의 작업 디렉터리에서 실행된다.
- 기대: A의 성공한 CI로 시작한 배포는 A를 빌드하거나, 최신 HEAD가 달라졌다면 중단하고 B의 CI 결과를 기다린다.
- 실제: A를 승인 대상으로 둔 로컬 재현에서 작업 디렉터리의 `version`은 B로 바뀌고 배포 exit 0. 워크플로는 원격에 target만 전달하므로 A를 확인할 수 없다. B가 CI 실행 중이거나 실패한 커밋이어도 동일하다.
- 영향: CI 성공 선행 조건을 실질적으로 우회하여 검증되지 않은 코드와 마이그레이션이 운영에 반영될 수 있다.
- 테스트 공백: `test_deploy_checks_out_the_commit_that_passed_ci`는 러너 checkout의 head_sha 문자열만 검사하며, NAS 빌드 소스와의 동일성은 검사하지 않는다. fake git은 커밋 이동을 모델링하지 않는다.

### D-20-2 — health가 200이 아니어도 성공 처리

- 심각도: **MAJOR**
- 위치: `deploy/deploy.sh:108`
- 재현: 루프백 `http.server.HTTPServer`에서 GET 요청에 `302`와 `Location: /login`을 반환하도록 한다. fake docker의 `FAKE_DOCKER_PORT`를 이 서버의 주소로 지정하고 실제 curl을 사용하여 `bash deploy/deploy.sh prod`를 실행한다. 나머지 배포 단계는 로컬 git과 fake docker/sleep으로 처리한다.
- 기대: 명시된 `/health` 200 조건에 맞지 않으므로 재시도 후 실패(exit nonzero).
- 실제: 첫 302 응답에 빈 body를 출력하고 `== prod 배포 완료`, exit 0. 위 D-20-1과 함께 실행한 로컬 재현에서 직접 확인했다.
- 원인: `curl -f`의 성공 여부만 사용하고 HTTP 상태 코드를 비교하지 않는다. 302를 포함한 200 이외의 성공 종료 응답을 받아들인다.
- 영향: health가 잘못된 경로로 리다이렉트되는 등 정상 상태가 아닌 배포도 Actions에서 성공으로 표시된다.
- 테스트 공백: fake curl은 정해진 횟수만큼 exit 22를 반환한 뒤 exit 0과 고정 JSON을 출력한다. 실제 HTTP status별 판정을 검증하지 않아 전체 테스트가 이 결함을 잡지 못한다.

### D-20-3 — RELEASE 공유 파일의 번호별 추가 규칙 위반

- 심각도: **MINOR**
- 위치: `docs/RELEASE.md:60`
- 재현 명령: `git diff main...HEAD -- docs/RELEASE.md`.
- 기대: 티켓 공통 규칙대로 자기 번호 `### 20.` 소제목/행만 해당 섹션 끝에 추가한다.
- 실제: 기존 `## 티켓별 기록` 앞에 번호 없는 `## 자동 배포`, `### GitHub Actions secrets`, `### D3. 배포 자동화` 블록 52행을 삽입했다. 별도의 `### 20.` 기록도 있지만 앞의 삽입은 그 절에 속하지 않는다.
- 영향: 병렬 티켓이 공유 파일을 번호순으로 병합하도록 정한 편집 경계를 위반한다. D3 내용과 secrets 표를 유지하면서 티켓 20 소유 절 아래로 정리해야 한다.

## 참고 및 검증 한계

- 포트를 하드코딩하지 않고 compose가 발행한 포트를 읽는 구현은 선택한 환경의 실제 포트를 사용하므로 결함으로 보지 않았다.
- 기존 테스트는 분기·실패 전파 검증에 유용하며 항상 통과하는 테스트로 보지는 않는다. 다만 실제 HTTP 응답 및 CI 커밋 일치성의 공백은 위 결함과 연결된다.
- 구현 증거의 별도 DB/Redis 사용 결과나 과거 Docker/Flask 실행 로그를 이번 리뷰의 실행 증거로 대체하지 않았다.
- 계정/인증/CSRF 애플리케이션 코드 변경 없음. 운영 시크릿 값 기록이나 프로젝트명 변경에 의한 볼륨 교체는 diff에서 발견하지 못했다.
- NAS, 실제 GitHub Actions 및 Tailscale 연동 리허설은 금지 범위로 수행하지 않았다. 실제 컨테이너 재기동과 운영 데이터 유지에 대한 새로운 실행 증거는 없다.

결함 합계: BLOCKER 0, MAJOR 2, MINOR 1.

판정: FAIL
