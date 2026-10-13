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

## 라운드 2

- 검토일: 2026-10-14. 기준: 로컬 `main` (`4f9f179`) ... `HEAD` (`d82ffd5`), `origin/main` 미사용.
- 검토 커밋: `b162115`, `751dcea`, `3a60f09`, `141bf83`, `d82ffd5` (`git log main..HEAD`). 티켓 20, 스펙 §C.27·US 64/65, CONTEXT, 전체 변경 파일, 이전 리뷰와 구현 증거를 대조했다.
- 애플리케이션·테스트·설정·scratch 수정 없음. UI 변경 없음. NAS 접속·배포·외부 서비스 호출·push 없음. 아래 Docker 검증은 이미 실행 중인 로컬 개발 Redis 컨테이너에서 `sleep 0.2`만 실행하며 데이터·서비스 구성을 바꾸지 않는다.

### 티켓 체크박스별 판정

| 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 대상별 브랜치·디렉터리·포트·env·프로젝트 선택, Git 갱신/build/upgrade/재기동 확인/health 200, 양쪽 로컬 검증 | 미충족 | 두 대상의 dry-run·실행 테스트, 실제 Git 커밋 검사·실제 HTTP 302/200 테스트 통과. fetch + ff-only merge는 기존 pull의 갱신 역할을 수행한다. 그러나 실제 워크플로와 같은 표준입력 실행에서는 compose exec가 뒤의 서비스·health 검사를 소비하고 성공 종료한다(D-20-4). |
| main/develop CI 성공 선행 → Tailscale → SSH, ci.yml은 develop 추가만 | 미충족 | 성공 조건·브랜치 매핑·SHA 전달·Tailscale 뒤 SSH 순서를 확인했고 ci.yml diff는 지정된 한 줄뿐이다. 다만 SSH가 쓰는 `bash -s` 경로에서 검사를 건너뛰어 장애 시 워크플로가 실패해야 한다는 동작을 충족하지 못한다(D-20-4). 실제 Actions·tailnet 연동은 금지 범위라 실행하지 않았다. |
| secrets 표, NAS 사람 작업 D3 분리, push 금지 | 충족 | RELEASE의 티켓 20 절에 사용하는 secret 이름 4개와 D3 체크리스트가 있다. 리뷰 중 push하지 않았다. 구현자의 과거 push 여부는 로컬 기록만으로 독립 증명할 수 없다. |

공유 파일 규칙: RELEASE는 충족(D-20-3 FIXED). 현재 main 기준 README 추가 위치는 설계 판단 절 끝이 아니어서 미충족(D-20-5).

### 이전 결함 재판정

| ID | 이전 심각도 | 판정 | 직접 확인한 근거 |
|---|---|---|---|
| D-20-1 | MAJOR | FIXED | `.github/workflows/deploy.yml:25,58`에서 승인 SHA를 NAS에 전달하고 `deploy/deploy.sh:109,120`에서 원격 끝·병합 후 HEAD를 비교한다. 실제 로컬 Git을 사용하는 네 회귀 테스트가 통과하며, A 승인 후 origin B 상황에서 Docker 호출 전에 중단한다. 이전 재현 조건의 결함은 해소됐다. |
| D-20-2 | MAJOR | FIXED | `deploy/deploy.sh:156,159`에서 실제 HTTP 상태를 200과 비교한다. 실제 curl·루프백 HTTP 서버를 쓰는 302 실패/200 성공 회귀 테스트와 상태별 실패 테스트가 통과했다. 이 비교 자체는 수정됐으며, 비교에 도달하지 않는 별도 실행 경로는 D-20-4로 분리한다. |
| D-20-3 | MINOR | FIXED | `git diff main...HEAD -- docs/RELEASE.md`에서 모든 추가가 파일 끝 `### 20.` 아래에 있고 secrets·D3는 그 하위 `####`이다. 이전 번호 없는 상위 블록 삽입은 없다. |

### 직접 실행한 검증

- `TEST_DATABASE_URL`은 구현 증거의 로컬 접속 형식으로 기존 `chosung_daily_test_t20`을 지정하고 `TEST_REDIS_URL=redis://127.0.0.1:6379/8`로 `uv run pytest -q` 실행 → **187 passed in 62.06s**, exit 0. 접속 정보 값은 이 문서에 기록하지 않는다. 기본 DB fallback·새 DB 생성·간헐 실패·재실행 없음. 마이그레이션 테스트도 기존 티켓 전용 파생 DB를 사용했다.
- `uv run ruff check .` → **All checks passed!**, exit 0.
- `bash -n deploy/deploy.sh` → exit 0.
- `uv run flask db heads` → `4e72a4045fbc (head)` 한 줄. 티켓 diff에 마이그레이션 변경은 없다.
- `git diff --check main...HEAD` → 출력 없음, exit 0.
- 배포 테스트는 항상 통과하는 테스트가 아니며 실패 분기와 실제 Git/HTTP 회귀 검증이 유효하다. 다만 `FakeNas.deploy()`는 파일 인자로 Bash를 실행하고 fake Docker는 stdin을 소비하지 않아서 아래 실제 실행 방식의 결함을 놓친다.

### 신규 결함

#### D-20-4 — compose exec가 SSH로 전달한 스크립트 뒷부분을 소비하여 검증을 생략함

- 심각도: **MAJOR**
- 위치: `deploy/deploy.sh:129`, `.github/workflows/deploy.yml:58`; 테스트 공백: `tests/test_deploy_script.py:80`.
- 원인: 워크플로는 `bash -s -- ...`로 스크립트를 표준입력에서 읽는데, `docker compose exec -T`도 같은 표준입력을 컨테이너로 전달한다. `-T`는 TTY만 끄며 stdin 전달을 차단하지 않는다. Bash가 아직 읽지 않은 서비스 조회·health 루프가 exec의 입력으로 소비된다.
- 재현: 아래 명령은 레포 루트에서 실행한다. 실제 Docker의 stdin 처리를 그대로 사용하되 마이그레이션 대신 이미 실행 중인 로컬 개발 Redis 컨테이너의 무해한 `sleep 0.2`를 실행한다. 나머지 단계는 기존 fake NAS 명령을 사용하므로 실제 배포나 DB 변경은 없다.

```bash
uv run python - <<'PY'
import importlib.util
import pathlib
import shutil
import subprocess
import tempfile

spec = importlib.util.spec_from_file_location('dt', 'tests/test_deploy_script.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as directory:
    p = pathlib.Path(directory)
    nas = m.FakeNas(p, 'chosung-daily', fakes=('git', 'curl', 'sleep'))
    wrapper = p / 'bin/docker'
    compose = pathlib.Path('docker-compose.yml').resolve()
    wrapper.write_text(
        '#!/bin/sh\ncase "$*" in\n *"exec -T app"*) exec '
        + shutil.which('docker') + ' compose -f ' + str(compose)
        + ' -p chosung-daily exec -T redis sh -c "sleep 0.2" ;;\n'
        + ' *) exec ' + str(m.FAKE_BIN / 'docker') + ' "$@" ;;\nesac\n'
    )
    wrapper.chmod(0o755)
    for mode in ('file', 'stdin'):
        cmd = (['bash', str(m.DEPLOY_SH), 'prod'] if mode == 'file'
               else ['bash', '-s', '--', 'prod'])
        result = subprocess.run(
            cmd, input=m.DEPLOY_SH.read_text() if mode == 'stdin' else None,
            env=nas.env, capture_output=True, text=True, timeout=20,
        )
        print(mode, 'exit', result.returncode,
              'health called', '/health' in result.stdout,
              'completed', '배포 완료' in result.stdout)
PY
```

- 기대: 두 실행 방식 모두 서비스 상태와 health를 검사하고 같은 결과를 낸다. 검사되지 않은 배포가 성공으로 종료하면 안 된다.
- 실제 직접 실행 출력:

```text
file exit 0 health called True completed True
stdin exit 0 health called False completed False
```

- stdin 모드의 마지막 출력은 `... exec -T app uv run flask db upgrade`이며 이후 config/ps/port/curl 호출이 전부 없다. 마이그레이션 프로세스 자체가 stdin을 읽지 않는 경우도 Docker CLI가 이를 전달하면서 소비하는 문제임을 실제 Docker와 `sleep`으로 확인했다.
- 영향: worker 미기동이나 health 실패가 있어도 자동 배포 잡이 성공으로 표시될 수 있다. 표준입력으로 실행하는 실제 진입 경로와 stdin을 처리하는 하위 프로세스를 포함한 검증이 필요하다.

#### D-20-5 — README 공유 절의 끝에 추가해야 하는 규칙 위반

- 심각도: **MINOR**
- 위치: `README.md:386`.
- 재현: `git diff main...HEAD -- README.md` 및 `rg -n '^##|^###' README.md`.
- 기대: 티켓의 공통 규칙대로 자기 번호 `### 20.`을 현재 `설계 판단` 섹션 끝에 덧붙인다.
- 실제: `### 20.`이 기존 `### 02. 퍼즐 언어 모델`과 `### 02. 가림(mask)`보다 앞에 삽입돼 있다. 현재 절 끝은 이 두 02 절 뒤, `## 부하 테스트 요약` 앞이다.
- 영향: 병렬 티켓의 공유 파일 추가 경계를 위반한다. 이전 리뷰에서는 README가 절 끝이었지만 현재 로컬 main에 티켓 02가 포함된 diff에서는 중간 삽입이다. 내용이나 소제목 번호 자체의 취향 문제가 아니라 명시된 추가 위치 규칙 위반이다.

### 참고 및 검증 한계

- 인증·CSRF 애플리케이션 코드 변경 없음. 프로젝트명·env 선택은 prod/develop을 분리하며 볼륨 삭제 명령은 없다. 새 변경에서 운영 키·토큰·비밀번호 실값은 발견하지 않았다. 증거 문서에는 기존 개발용 DB 접속 문자열이 있으므로 운영 시크릿 부재와 모든 자격 증명 문자열 부재는 구별했다.
- 컨테이너 build/up·실제 NAS 마이그레이션·GitHub Actions/Tailscale 전체 연결은 실행하지 않았다. 구현 증거의 과거 실행 로그를 이번 검증 결과로 대체하지 않았다.
- 파일 인자 실행과 stdin 실행을 비교한 재현은 로컬 Docker의 실제 입력 처리를 검증한다. 운영 NAS에서 직접 재현했다는 뜻은 아니다.

현재 열린 결함 합계: **BLOCKER 0, MAJOR 1, MINOR 1**. 이전 결함 3건 FIXED, REPEAT 0건.

판정: FAIL

## 라운드 3

- 검토일: 2026-10-14. 기준: 로컬 `main` (`72a2a3c`) ... `HEAD` (`47b37fb`). `origin/main` 미사용.
- `git log main..HEAD`의 8개 커밋과 `git diff main...HEAD`, 티켓 20, 스펙 §C.27·US 64/65, CONTEXT, 구현 증거 및 이전 리뷰를 직접 대조했다.
- 하위 에이전트 없이 검토했다. 애플리케이션·테스트·설정·scratch 수정, NAS 접속, 배포, 외부 서비스 호출, push 없음. UI·마이그레이션 변경 없음.

### 티켓 체크박스별 판정

| 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 대상별 설정, Git 갱신/build/upgrade/재기동 확인/health 200, 양쪽 인자 로컬 검증 및 RELEASE 절차 | 충족 | 두 대상의 dry-run/실행 테스트, 실제 임시 Git 저장소의 승인 SHA 검사, 루프백 HTTP 302 실패/200 성공 테스트 통과. fetch + ff-only merge가 pull의 갱신 역할을 한다. 서비스 목록은 compose에서 조회하므로 추가된 backup도 실제 실행 시 검사 대상이다. stdin 진입 경로도 실제 로컬 Docker로 재검증했다. |
| main/develop push에 CI 성공 선행 → Tailscale → SSH, ci.yml 변경 제한 | 미충족 | CI 성공·브랜치 매핑·SHA 전달·연결 순서는 구현됐고 ci.yml 변경은 develop 추가 한 줄뿐이다. 그러나 PR CI도 배포 권한을 얻는 이벤트 검증 누락이 있다(D-20-6). |
| secrets 목록 표, NAS 사람 작업 D3 분리, push 금지 | 충족 | RELEASE 티켓 20 절의 secret 이름 4개와 SSH/Tailscale D3 체크리스트 확인. 이번 리뷰는 push하지 않았다. 구현자의 과거 push 여부는 로컬 diff/log로 독립 증명할 수 없다. |

공유 파일 규칙은 충족: README는 설계 판단 마지막의 `### 20.`, RELEASE는 파일 끝의 `### 20.` 아래에만 추가된다. 범위 밖 애플리케이션 변경은 없다.

### 이전 결함 재판정

| ID | 이전 심각도 | 판정 | 직접 확인한 근거 |
|---|---|---|---|
| D-20-1 | MAJOR | FIXED | workflow 25/62행의 SHA 전달과 deploy.sh 120~139행의 원격 tip/HEAD 비교 유지. 실제 로컬 Git 회귀 테스트 통과. 기존 A 승인 후 origin B 재현 조건에서 빌드를 차단한다. |
| D-20-2 | MAJOR | FIXED | deploy.sh 172~175행의 HTTP 상태 200 비교 유지. 실제 curl/루프백 서버의 302 거부·200 수용 테스트 통과. |
| D-20-3 | MINOR | FIXED | RELEASE diff의 추가 85행 전체가 201행 `### 20.` 이하이며 다른 티켓 절 변경 없음. |
| D-20-4 | MAJOR | FIXED | deploy.sh 51행부터 본문이 main 함수이고 190행에서 `main "$@" < /dev/null` 실행. stdin을 소비하는 fake Docker와 실제 로컬 Docker 양쪽에서 후속 검사를 수행한다. |
| D-20-5 | MINOR | FIXED | README 505행 `### 20.`이 두 티켓 02 절 이후, `## 부하 테스트 요약` 바로 앞에 추가된다. 기존 다른 티켓 내용 삭제/이동 없음. |

### 직접 실행한 검증

- 기존 `chosung_daily_test_t20`에 `TEST_DATABASE_URL`, Redis DB 8에 `TEST_REDIS_URL`을 지정하여 `uv run pytest -q` → **231 passed in 70.96s**, exit 0. 접속 문자열의 인증 값은 문서에 기록하지 않는다. 기본 DB fallback·새 DB 생성·간헐 실패·재실행 없음. 마이그레이션 테스트도 기존 전용 파생 DB를 사용했다.
- `uv run ruff check .` → **All checks passed!**, exit 0.
- `bash -n deploy/deploy.sh` → exit 0.
- `uv run flask db heads` → `4e72a4045fbc (head)` 한 줄.
- `git diff --check main...HEAD` → 출력 없음, exit 0.
- 라운드 2 D-20-4에 실린 Python 재현 명령을 현재 스크립트로 다시 실행했다. 이미 실행 중인 로컬 개발 Redis 컨테이너에서 `sleep 0.2`만 실행하고 나머지는 가짜 NAS 명령을 사용했다. 서비스 구성·데이터는 변경하지 않았다.

```text
file exit 0 health called True completed True
stdin exit 0 health called True completed True
```

- 새 stdin 회귀 테스트 4개는 정상 완료뿐 아니라 health 500 및 서비스 누락 시 실패도 검사한다. 실제 Git/HTTP 테스트도 존재하므로 전체 테스트가 항상 통과하거나 과한 mock만으로 구성됐다고 보지는 않는다. 워크플로 테스트에는 아래 이벤트 출처 검증 공백이 남아 있다.

### 신규 결함

#### D-20-6 — PR CI 성공도 배포 잡을 열어 PR 스크립트를 NAS에서 실행할 수 있음

- 심각도: **MAJOR**
- 위치: `.github/workflows/deploy.yml:18` (출처 조건 누락), `.github/workflows/deploy.yml:30` (이벤트 SHA checkout), `.github/workflows/deploy.yml:62` (그 스크립트를 NAS로 전송). 관련 입력: `.github/workflows/ci.yml:6`의 `pull_request` 트리거.
- 원인: workflow_run의 브랜치 이름 필터와 conclusion만 검사한다. 선행 CI가 `push`였는지, 그 head repository가 이 저장소인지 확인하지 않는다. `main`/`develop`이라는 이름은 PR의 소스 브랜치에도 사용할 수 있다. PR CI가 성공하면 배포 잡이 이벤트 SHA를 checkout하고 배포 secrets로 연결한 NAS에 해당 커밋의 스크립트를 보낸다.
- 재현 입력: CI 성공 `workflow_run`에 `event=pull_request`, `head_branch=main`(또는 develop), PR의 `head_sha`를 넣는다. fork PR을 허용하고 그 CI가 실행/승인되는 저장소에서는 head repository가 fork인 경우도 동일하다. PR의 `deploy/deploy.sh` 앞에 무해한 출력 명령을 추가한 경우조차 이 코드는 신뢰 검증 전에 NAS에서 실행되는 구조다. 기존 스크립트 내부의 SHA 검사는 PR이 바꿀 수 있는 코드라 신뢰 경계를 대신하지 못한다.
- 기대: 이 저장소 main/develop **push**의 성공한 CI만 배포 잡에 들어가고, PR 성공은 checkout·secret 사용·NAS 연결 전에 차단된다.
- 실제: 현재 YAML의 조건은 PR/fork를 구별하지 않아 모두 허용한다. 외부 호출 없이 아래 명령으로 실제 설정을 읽고 조건을 대조했다(실제 GitHub Actions/NAS 공격 실행을 했다는 뜻은 아니다).

```bash
uv run python - <<'PY'
from pathlib import Path
import yaml
w = yaml.safe_load(Path('.github/workflows/deploy.yml').read_text())
job = w['jobs']['deploy']
assert job['if'] == "github.event.workflow_run.conclusion == 'success'"
for event, repo in [('push', 'base'), ('pull_request', 'base'),
                    ('pull_request', 'fork')]:
    payload = dict(event=event, head_repository=repo,
                   head_branch='main', conclusion='success')
    allowed = (payload['head_branch'] in w[True]['workflow_run']['branches']
               and payload['conclusion'] == 'success')
    print(event, repo, allowed)
print(job['steps'][0]['with']['ref'])
PY
```

```text
push base True
pull_request base True
pull_request fork True
${{ github.event.workflow_run.head_sha }}
```

- 영향: 요청된 push 자동 배포를 넘어 PR에도 배포 권한이 전달된다. 특히 외부 PR CI를 허용하는 경우 검토·병합 전 코드가 NAS 배포 계정 권한으로 실행될 수 있다.
- 테스트 공백: `tests/test_deploy_workflow.py:71`의 성공 조건 테스트는 conclusion/success 문자열만 확인하고 PR 및 다른 head repository를 거부하는지 검사하지 않는다. push 성공/실패, PR 성공, fork의 동일 이름 브랜치를 구별하는 검증이 필요하다.

### 참고 및 검증 한계

- 실제 GitHub Actions/Tailscale/NAS 전체 리허설, 컨테이너 build/up 및 운영 데이터 유지 검증은 수행하지 않았다. D3 사람 체크리스트로 남아 있으며 구현 증거의 과거 실행 기록을 이번 실행 결과로 대체하지 않았다.
- 인증·CSRF 애플리케이션 코드는 변경되지 않았다. prod 프로젝트명 유지와 볼륨 삭제 명령 부재를 확인했다. diff에서 운영 시크릿 실값은 발견하지 않았다. 구현 증거 초기 절에는 기존 개발 DB의 접속 문자열이 있으므로 "모든 자격 증명 문자열이 없다"는 주장은 성립하지 않지만 이를 운영 시크릿 누출로 집계하지 않았다.
- 이번 결함은 코드의 신뢰 경계 문제이며, 권한 설정이 없는 실제 저장소에 공격이 성공했다고 주장하지 않는다. 외부 서비스 접근 없이 YAML의 허용 조건과 스크립트 실행 경로를 확인했다.

현재 열린 결함 합계: **BLOCKER 0, MAJOR 1, MINOR 0**. 이전 결함 5건 FIXED, REPEAT 0건. 신규 D-20-6 1건.

판정: FAIL
