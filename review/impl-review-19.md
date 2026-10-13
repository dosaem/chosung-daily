# 티켓 19 최종 리뷰 — 라운드 1

- 기준: 로컬 `main` = `285c804aa8f6c25afc155eaa51d2bdfddc48d41f`, 구현 HEAD = `b1171302bd4a84aaf4b75de5385b8d352a3bee3b`.
- `git diff main...HEAD`, `git log main..HEAD`의 3개 커밋(49a4a91, 57d590c, b117130)을 검토했다. origin/main은 사용하지 않았다.
- 티켓 원문, 스펙 C.26·D3·미정 8/16, `review/impl-evidence-19.md`를 읽었다. UI 변경은 없으며 티켓이 지칭한 루트 `CONTEXT.md`는 존재하지 않는다.

## 티켓 체크박스별 확인

| 체크박스 | 상태 | 직접 확인한 근거와 한계 |
|---|---|---|
| compose 고정 이름 제거, APP_PORT/env 파일 파라미터화, 프로젝트별 볼륨, 두 예시 파일 | 충족 | YAML과 실제 `docker compose config --format json` 확인. 고정 이름 없음, prod/develop 프로젝트명·8089/8090·두 볼륨 접두사 분리. app/worker/beat 모두 ENV_FILE 사용. 실제 env 파일의 커밋 변경 없음. 임시 복사본 사용 절차에는 D-19-1이 있음. |
| `.dockerignore` 신설 | 충족 | mobile/.scratch/review/.venv/tests 및 `.env`, `.env.*` 제외를 직접 확인. Dockerfile의 COPY와 모순 없음. 이미지 빌드는 이번 리뷰에서 재실행하지 않음. |
| 로컬 검증 ① 기존 볼륨·기록·토큰 보존 및 절차/결과 기록 | 증거 부족 | 변경 전후 볼륨 키가 동일하고 config의 실제 이름도 기존 이름과 일치. RELEASE와 구현 증거에 실행 결과는 있으나 이번 리뷰에서 실제 컨테이너 전환·토큰 보존을 재실행하지 않았음. 기록된 재현 절차에는 D-19-1/2가 있음. |
| 로컬 검증 ② 동시 기동·이름/포트/DB 및 쓰기 격리 | 증거 부족 | config에서 프로젝트·포트·볼륨·기본 네트워크 분리를 확인. 구현 증거의 10개 컨테이너 기동 및 교차 토큰 401 주장은 이번 리뷰에서 재실행하지 않아 독립 확인으로 취급하지 않음. |
| RELEASE 첫 배포 체크, NAS 실제 프로젝트/볼륨 확인, develop 경로, named volume | 충족 | RELEASE:12, 29, 35에서 요구 내용 확인. 다만 공유 파일 번호 규칙은 D-19-3 참조. |
| README 설계 판단에 prod 프로젝트명 유지 이유 | 충족 | README:274의 `### 19.`에 기존 볼륨 연결 유지와 빈 볼륨 생성 위험 설명을 추가함. |

## 직접 실행한 검증

- `uv run ruff check .` → `All checks passed!`, 종료 코드 0.
- `TEST_DATABASE_URL`을 로컬 MySQL의 전용 `chosung_daily_test_r19`로, `TEST_REDIS_URL`을 로컬 Redis DB 15로 지정한 `uv run pytest -q` → **85 passed in 27.81s**, 종료 코드 0. 접속 문자열·비밀번호는 문서에 기록하지 않는다.
- 최초 DB 준비는 일반 DB 사용자의 시스템 DB 접근 권한 부족(1044)으로 실패했다. 로컬 Docker MySQL에서 전용 DB만 생성·권한 부여한 뒤 위 전체 테스트를 실행했다. 공유 테스트 DB나 다른 Redis DB는 사용하지 않았다.
- `uv run flask db heads` → `9ec267465b4e (head)` 한 줄. 이 티켓에 마이그레이션 변경은 없다.
- `git diff main...HEAD --check` → 종료 코드 0.
- 예시 파일을 시스템 임시 디렉터리로 복사하여 `docker compose -f docker-compose.prod.yml --env-file <복사본> config --format json` 실행: prod/develop 모두 종료 코드 1, 각각 저장소의 `.env`/`.env.develop`가 없다는 오류. `ENV_FILE=<복사본 절대경로>`를 추가하면 양쪽 종료 코드 0, 프로젝트명·포트·볼륨명 정상.
- `git show HEAD:docker-compose.prod.yml` 결과는 현재 compose와 같고 변경 전 main 버전과 다름을 비교 확인.
- 추가 계약 테스트 8개는 실제 파일을 읽고 assertion을 수행하며 mock/항상 통과하는 테스트는 아니다. 다만 Docker 기동·데이터 보존까지 검증하는 테스트는 아니므로 85개 통과를 그 증명으로 확대하지 않는다.

## 결함 목록

### D-19-1 — 임시 env 복사본 검증 명령에 ENV_FILE 경로 지정 누락

- 심각도: **MINOR**
- 위치: `docs/RELEASE.md:76`, `docs/RELEASE.md:85` (관련 `.env.prod.example:14`, `.env.develop.example:17`).
- 재현: 실제 `.env`가 없는 체크아웃에서 예시를 임시 디렉터리로 복사하고 문서의 `--env-file <임시 복사본>` 인자로 `docker compose -f docker-compose.prod.yml ... config` 실행.
- 기대: 임시 파일만으로 설정 해석 및 이후 로컬 기동이 가능.
- 실제: Compose 서비스의 env_file은 복사본 내부 ENV_FILE 값인 `.env` 또는 `.env.develop`로 해석되어 해당 파일 부재로 종료 코드 1. `--env-file`은 서비스 env_file 경로를 자동으로 바꾸지 않음.
- 영향/수정 방향: 운영용 지정 경로에 env를 두는 정상 배포는 가능하지만, 티켓이 요구한 임시 파일만 사용하는 재검증 절차가 실패한다. 절차에 `ENV_FILE=<임시 복사본 절대경로>` 지정 또는 복사본의 해당 항목 변경을 명시해야 한다.

### D-19-2 — 변경 전 compose 추출 명령이 현재 HEAD를 가리킴

- 심각도: **MINOR**
- 위치: `docs/RELEASE.md:70`.
- 재현: 리뷰 HEAD에서 `git show HEAD:docker-compose.prod.yml` 실행 후 현재 파일 및 `git show 285c804:docker-compose.prod.yml` 결과와 비교.
- 기대: 고정 name/container_name이 있는 전환 전 compose 추출.
- 실제: 고정 이름이 이미 제거된 현재 compose 추출. 문서대로 재실행하면 구버전→신버전 볼륨 보존 검증이 되지 않는다.
- 영향/수정 방향: 기록 당시 작업 중 HEAD였을 수는 있으나 현재 독자가 재현할 수 없다. 변경 전 고정 커밋으로 명령을 기록해야 한다.

### D-19-3 — RELEASE의 공통 본문을 자기 번호 소제목 밖에 작성

- 심각도: **MINOR**
- 위치: `docs/RELEASE.md:3` (7·33·50행의 공통 절 포함).
- 재현: `git diff main...HEAD -- docs/RELEASE.md`에서 첫 `### 19.`의 위치와 추가된 본문 범위를 확인.
- 기대: 티켓 공통 규칙대로 새 파일이라도 자기 번호 소제목/행 아래에 내용을 추가하여 병렬 티켓의 공유 파일 편집을 분리.
- 실제: 인스턴스 구성과 두 배포 체크리스트 전체가 번호 없는 공통 절에 추가되고, 62행부터 로컬 검증만 `### 19.` 아래에 있다.
- 영향/수정 방향: 병렬 티켓의 RELEASE 추가 시 공유 절 소유 경계가 깨진다. 해당 내용을 19번 소제목 아래로 배치할 필요가 있다. 런타임 영향은 없어 MINOR로 분류한다.

## 보안·범위·참고

- 변경 diff에서 실제 키·토큰·비밀번호 값의 추가를 발견하지 않았다. 예시의 시크릿 값은 비어 있고 증거 문서의 인증 값은 변수/마스킹으로 표현된다.
- 앱 포트의 loopback 바인딩은 유지되고 DB/Redis 호스트 포트는 노출하지 않는다. 인증·CSRF·입력 검증 애플리케이션 코드는 변경되지 않았다.
- 볼륨 키 변경, 외부 공유 볼륨 지정, bind mount 추가는 없다. PyYAML과 lock 변경은 계약 테스트용이며 별도 기능 추가는 아니다.
- NAS 접속·배포·외부 제공자 호출은 하지 않았다. 스펙 미정 8과 D3의 NAS 실측은 사람 작업으로 남아 있다.
- 스타일/취향 제안은 결함으로 올리지 않았다. 실제 컨테이너 전환·쓰기 격리 재실행의 미확인은 위 표의 검증 한계이며, 구현 결함이 확인된 것으로 간주하지 않는다.

결함 수: BLOCKER 0, MAJOR 0, MINOR 3. 확인된 결함은 문서 재현성과 공유 파일 규칙에 한정된다.

판정: PASS
