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
| `FAKE_DOCKER_PORT` | docker | `compose port proxy 80` 출력 |
| `FAKE_DOCKER_APP_PORT` | docker | `compose port app 5000` 출력 — proxy 전환 전 컨테이너 흉내. 비면 exit 1(포트 없음) |
| `FAKE_DOCKER_OLD_APP` | docker | 롤링 교체 전 `ps --status running -q app` 이 낼 옛 app 컨테이너 id (공백 구분, 기본 `app-old`, 빈 문자열이면 없음) |
| `FAKE_DOCKER_NEW_APP` | docker | `--scale` 뒤에 추가로 보일 새 app 컨테이너 id (기본 `app-new`) |
| `FAKE_DOCKER_NEW_HEALTH` | docker | `inspect -f '{{.State.Health.Status}}'` 출력 (기본 `healthy`) |
| `FAKE_DOCKER_FAIL` | docker | 인자에 이 문자열이 있으면 exit 1 |
| `FAKE_CURL_FAILS` | curl | 처음 N 번은 연결 실패(`000`)하고 그 뒤로 응답 (기본 0) |
| `FAKE_CURL_STATUS` | curl | 연결된 뒤 돌려줄 HTTP 상태 코드 (기본 200) |
| `FAKE_CURL_COUNTER` | curl | 호출 횟수를 기록할 파일 (필수) |

가짜 `docker` 는 `exec -T`·`run --rm` 에서 진짜처럼 표준입력을 끝까지 읽는다 — 부를 때 stdin 을
닫거나(`subprocess.DEVNULL`) 넘겨야 한다. 터미널에 붙은 채로 부르면 멈춘다.
