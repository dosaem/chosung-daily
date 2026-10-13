# 가짜 NAS 명령

`deploy/deploy.sh` 를 로컬에서 실제로 끝까지 돌려보기 위한 `git`/`docker`/`curl`/`sleep`
대역. PATH 앞에 두면 스크립트는 분기·순서·실패 처리를 전부 실제로 지나가고,
호출된 명령은 `$FAKE_LOG` 에 한 줄씩 쌓인다. 동작은 환경변수로 조절한다.

| 환경변수 | 쓰는 곳 | 뜻 |
|---|---|---|
| `FAKE_LOG` | 전부 | 호출 기록을 쌓을 파일 (필수) |
| `FAKE_GIT_BRANCH` | git | `rev-parse --abbrev-ref HEAD` 가 출력할 브랜치 |
| `FAKE_GIT_FAIL` | git | 인자에 이 문자열이 있으면 exit 1 |
| `FAKE_DOCKER_SERVICES` | docker | `compose config --services` 출력 (공백 구분) |
| `FAKE_DOCKER_RUNNING` | docker | `compose ps --filter status=running` 출력 (공백 구분) |
| `FAKE_DOCKER_PORT` | docker | `compose port app 5000` 출력 |
| `FAKE_DOCKER_FAIL` | docker | 인자에 이 문자열이 있으면 exit 1 |
| `FAKE_CURL_FAILS` | curl | 처음 N 번은 연결 실패(`000`)하고 그 뒤로 응답 (기본 0) |
| `FAKE_CURL_STATUS` | curl | 연결된 뒤 돌려줄 HTTP 상태 코드 (기본 200) |
| `FAKE_CURL_COUNTER` | curl | 호출 횟수를 기록할 파일 (필수) |
