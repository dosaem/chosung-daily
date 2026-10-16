#!/usr/bin/env bash
# NAS 배포 — deploy.sh <prod|develop> [<CI 를 통과한 커밋 sha>] [--dry-run]
#
# 대상 인자 하나가 브랜치·체크아웃 디렉터리·compose 프로젝트명·env 파일을 전부
# 정한다. 하는 일: git fetch → (sha 를 받았으면) 그 커밋이 아직 브랜치 끝인지 확인
# → ff-only merge → 이미지 빌드(옛 컨테이너는 계속 서비스) → 새 이미지로 마이그레이션
# → app 롤링 교체(새 app 을 옆에 띄워 건강해지면 옛 app 을 내림, 티켓 50) →
# worker/beat 교체 → 6개 서비스 기동 확인 → /health 가 HTTP 200. 어느 단계에서든
# 실패하면 즉시 0 이 아닌 코드로 끝나서 GitHub Actions 가 빨갛게 멈춘다
# (.github/workflows/deploy.yml). 롤링 중 새 app 이 건강해지지 않으면 새것만 지우고
# 끝낸다 — 옛 app 이 그대로 서비스 중이라 실패한 배포가 사용자에게 보이지 않는다.
#
# 두 번째 인자(sha)는 "CI 를 통과한 커밋" 이다. 이 인자가 없으면 브랜치 끝을 그냥
# 올리므로(NAS 에서 사람이 손으로 돌릴 때) 자동 배포는 반드시 넘긴다.
#
# GitHub Actions 는 이 파일을 ssh 표준입력으로 흘려보낸다(`ssh nas 'bash -s -- prod
# <sha>' < deploy/deploy.sh`) — NAS 체크아웃의 스크립트를 실행하면 아래 git merge 가
# 실행 중인 자기 자신을 갈아치운다. 이유는 README "설계 판단" §20.
#
# 그래서 본문 전체를 main() 에 넣고 표준입력 없이 부른다(파일 맨 끝). bash 는 표준
# 입력에서 읽는 스크립트를 실행하면서 읽어 나가는데, 자식 프로세스는 그 표준입력을
# 그대로 물려받는다 — `docker compose exec -T` 는 `-T` 로 TTY 만 끄고 표준입력은
# 컨테이너로 흘려보내므로, 아직 안 읽힌 스크립트 뒷부분(서비스 조회·health 루프)을
# 먹어버린다. bash 는 읽을 게 없어진 자리에서 조용히 0 으로 끝나고, 검사되지 않은
# 배포가 초록색이 된다. main 을 `< /dev/null` 로 부르면 어떤 자식도 스크립트 본문을
# 물려받지 않는다.
#
# DEPLOY_BASE_DIR 로 체크아웃 상위 디렉터리를 바꿀 수 있다(기본 /volume1/docker).
# 테스트에서 가짜 NAS 를 가리키는 용도 — NAS 에서는 기본값을 쓴다.
set -euo pipefail

# Synology 의 비대화형 ssh 셸은 PATH 에 /usr/local/bin 이 없다 — docker 가 거기 있어서
# GitHub Actions 의 `ssh nas 'bash -s'` 가 `docker: command not found`(127) 로 죽었다
# (2026-10-16, main 머지는 끝났는데 컨테이너는 옛것인 채로 초록/빨강이 갈렸다).
# 앞이 아니라 **뒤에** 붙인다 — 테스트가 PATH 앞에 둔 가짜 docker 를 가리지 않게.
export PATH="$PATH:/usr/local/bin"

COMPOSE_FILE=docker-compose.prod.yml
HEALTH_RETRIES=10
HEALTH_RETRY_DELAY=3
# 새 app 컨테이너가 healthy 가 될 때까지 기다리는 횟수·간격(compose 의 healthcheck:
# start_period 20s + interval 5s 에 맞춰 넉넉히 2분).
APP_READY_RETRIES=40
APP_READY_DELAY=3
# docker stop 이 SIGKILL 전에 주는 시간 — compose 의 stop_grace_period 와 같다.
APP_STOP_TIMEOUT=20

usage() {
  echo "사용법: deploy.sh <prod|develop> [<CI 를 통과한 커밋 sha>] [--dry-run]" >&2
}

# 실행할 명령을 찍고 실행한다. dry-run 이면 찍고 넘어간다.
run() {
  echo "+ $*"
  if [[ "$dry_run" == 0 ]]; then
    "$@"
  fi
}

# 출력을 되읽어야 하는 조회 명령. dry-run 이면 빈 문자열을 돌려준다.
capture() {
  echo "+ $*" >&2
  if [[ "$dry_run" == 0 ]]; then
    "$@"
  fi
}

# app 을 끊김 없이 바꾼다: 새 이미지의 컨테이너를 옛것 옆에 하나 더 띄우고
# (`--scale app=N+1 --no-recreate`), healthy 가 되면 옛 컨테이너를 stop(진행 중 요청을
# 마칠 시간을 주고) → rm. 프록시(Caddy)는 도커 DNS 로 app 레플리카를 1초마다 다시
# 찾으니(deploy/Caddyfile) 그 사이 요청은 둘 중 살아 있는 쪽으로 간다.
# 새것이 끝내 건강해지지 않으면 새것만 지우고 1 로 끝낸다 — 옛것이 계속 서비스한다.
rolling_replace_app() {
  if [[ "$dry_run" == 1 ]]; then
    echo "+ <app 롤링 교체: ps -q app → up -d --no-build --no-recreate --scale app=N+1 app" \
      "→ 새 컨테이너 healthy 대기(최대 ${APP_READY_RETRIES}회) → 옛 컨테이너 stop -t ${APP_STOP_TIMEOUT}·rm>"
    return 0
  fi

  local old_ids old_count new_id
  old_ids="$(capture "${compose[@]}" ps --status running -q app)"
  old_count="$(printf '%s' "$old_ids" | grep -c . || true)"

  run "${compose[@]}" up -d --no-build --no-recreate --scale "app=$((old_count + 1))" app

  # 지금 도는 app 중 옛 목록에 없는 것이 새 컨테이너다.
  new_id="$(capture "${compose[@]}" ps --status running -q app \
    | grep -vxF -f <(printf '%s\n' "$old_ids") || true)"
  if [[ -z "$new_id" ]]; then
    echo "새 app 컨테이너가 생기지 않았다 — 중단" >&2
    exit 1
  fi

  local attempt health
  for attempt in $(seq 1 "$APP_READY_RETRIES"); do
    health="$(capture docker inspect -f '{{.State.Health.Status}}' "$new_id")"
    if [[ "$health" == "healthy" ]]; then
      echo "새 app $new_id → healthy (${attempt}회째)"
      break
    fi
    echo "($attempt/$APP_READY_RETRIES) 새 app $new_id → ${health:-unknown}"
    [[ "$attempt" == "$APP_READY_RETRIES" ]] || sleep "$APP_READY_DELAY"
  done
  if [[ "$health" != "healthy" ]]; then
    echo "새 app 이 ${APP_READY_RETRIES}회 뒤에도 healthy 가 아니다 — 새것을 지우고 옛것을 유지한다" >&2
    run docker logs --tail 50 "$new_id" || true
    run docker rm -f "$new_id"
    exit 1
  fi

  local id
  for id in $old_ids; do
    run docker stop -t "$APP_STOP_TIMEOUT" "$id"
    run docker rm "$id"
  done
}

main() {
  local target="${1:-}"
  local commit=""
  dry_run=0
  # 2·3번째 인자는 순서가 바뀌어도 받는다. sha 모양이 아닌 값은 오타로 보고 멈춘다.
  for arg in "${2:-}" "${3:-}"; do
    case "$arg" in
      "") ;;
      --dry-run) dry_run=1 ;;
      *)
        if [[ ! "$arg" =~ ^[0-9a-f]{7,40}$ ]]; then
          echo "알 수 없는 인자: $arg" >&2
          usage
          exit 2
        fi
        commit="$arg"
        ;;
    esac
  done

  local branch checkout_dir project env_file
  case "$target" in
    prod)
      branch=main
      checkout_dir="${DEPLOY_BASE_DIR:-/volume1/docker}/chosung-daily"
      project=chosung-daily-prod
      env_file=.env
      ;;
    develop)
      branch=develop
      checkout_dir="${DEPLOY_BASE_DIR:-/volume1/docker}/chosung-daily-develop"
      project=chosung-daily-develop
      env_file=.env.develop
      ;;
    *)
      usage
      exit 2
      ;;
  esac

  local compose=(docker compose -f "$COMPOSE_FILE" -p "$project" --env-file "$env_file")

  echo "== $target 배포: $branch → $checkout_dir ($project / $env_file)"

  if [[ "$dry_run" == 0 ]]; then
    if [[ ! -d "$checkout_dir" ]]; then
      echo "체크아웃 디렉터리가 없다: $checkout_dir" >&2
      exit 1
    fi
    cd "$checkout_dir"

    local current_branch
    current_branch="$(git rev-parse --abbrev-ref HEAD)"
    if [[ "$current_branch" != "$branch" ]]; then
      echo "$checkout_dir 가 $branch 가 아니라 $current_branch 에 있다 — 중단" >&2
      exit 1
    fi
  fi

  run git fetch --quiet origin "$branch"

  # CI 를 통과한 커밋과 NAS 가 실제로 빌드하는 커밋을 못박는다. 러너 checkout 만
  # head_sha 로 맞춰도 NAS 는 자기 git pull 로 "지금의 브랜치 끝" 을 가져오기 때문에,
  # A 의 CI 로 시작한 배포가 그 사이 올라온 B(아직 CI 중이거나 실패한 커밋)를 빌드할
  # 수 있다. 브랜치가 움직였으면 여기서 멈춘다 — B 는 자기 CI 가 통과하면 자기 배포가
  # 올린다. 옛 커밋을 그대로 빌드하면 B 가 이미 올라간 뒤에 A 로 되돌릴 수 있어서
  # 그렇게 하지 않는다. 이유는 README "설계 판단" §20.
  if [[ -n "$commit" && "$dry_run" == 0 ]]; then
    local remote_head
    remote_head="$(git rev-parse "origin/$branch")"
    if [[ "$remote_head" != "$commit" ]]; then
      echo "origin/$branch 가 이미 $remote_head 로 움직였다 — CI 를 통과한 $commit 의" >&2
      echo "배포를 중단한다. $remote_head 는 자기 CI 가 통과하면 배포된다." >&2
      exit 1
    fi
  fi

  run git merge --ff-only "origin/$branch"

  if [[ -n "$commit" && "$dry_run" == 0 ]]; then
    local head
    head="$(git rev-parse HEAD)"
    if [[ "$head" != "$commit" ]]; then
      echo "체크아웃이 $head 인데 CI 를 통과한 커밋은 $commit 이다 — 중단" >&2
      exit 1
    fi
  fi

  # 1) 빌드만 한다 — 옛 컨테이너는 그동안 계속 서비스한다.
  run "${compose[@]}" build

  # 2) 마이그레이션을 **교체 전에** 새 이미지로 돌린다. 옛 코드가 돌고 있는 채로
  #    스키마가 먼저 바뀌므로 마이그레이션은 확장(expand)만 허용한다 — 열·테이블
  #    삭제나 이름 변경은 두 배포로 나눈다(README "설계 판단" §02). 예전처럼 새 코드
  #    기동 뒤에 돌리면 "새 코드가 아직 없는 열을 읽는" 창이 생긴다.
  run "${compose[@]}" run --rm --no-deps -T app uv run flask db upgrade

  # 3) 인프라·프록시 — 바뀐 게 없으면 compose 가 건드리지 않는다.
  #    전환 1회: app 이 아직 호스트 포트를 직접 잡고 있으면(proxy 도입 전에 만든
  #    컨테이너) proxy 가 같은 포트를 못 잡는다. 그 경우에만 app 을 옛 방식으로
  #    재생성한다(이때만 몇 초 끊김) — 그 뒤로는 포트가 없어서 이 분기를 안 탄다.
  if [[ -n "$(capture "${compose[@]}" port app 5000 2>/dev/null || true)" ]]; then
    echo "app 이 호스트 포트를 직접 잡고 있다(proxy 전환 전) — 이번 한 번만 app 을 재생성한다"
    run "${compose[@]}" up -d --no-build app
  fi
  run "${compose[@]}" up -d --no-build mysql redis proxy backup

  # 4) app 롤링 교체 — 유일하게 사용자가 보는 서비스라 끊김 없이 바꾼다.
  rolling_replace_app

  # 5) worker·beat 는 짧게 재시작한다 — celery 는 SIGTERM 에 진행 중 태스크를 마치고
  #    내려가고(warm shutdown), 몇 초 비는 동안의 자정 배정·알림은 큐에 남는다.
  run "${compose[@]}" up -d --no-build worker beat

  # /health 는 app 하나만 보니까 worker·beat 가 죽어도 200 이 나온다 — compose 가
  # 아는 서비스 전부가 실제로 running 인지 따로 확인한다.
  local expected_services running_services
  expected_services="$(capture "${compose[@]}" config --services | sort)"
  running_services="$(capture "${compose[@]}" ps --services --filter status=running | sort)"
  if [[ "$expected_services" != "$running_services" ]]; then
    echo "기동하지 않은 서비스: $(comm -23 <(echo "$expected_services") <(echo "$running_services") | tr '\n' ' ')" >&2
    exit 1
  fi

  # 호스트 포트는 env 파일의 APP_PORT 가 진실이라 스크립트에 또 적지 않고,
  # compose 가 실제로 발행한 포트를 물어본다.
  local published port health_url
  published="$(capture "${compose[@]}" port proxy 80)"
  port="${published##*:}"
  health_url="http://127.0.0.1:${port:-0}/health"

  if [[ "$dry_run" == 1 ]]; then
    echo "+ curl -sS --max-time 5 -w '%{http_code}' <APP_PORT 로 만든 /health URL>" \
      "→ HTTP 200 인지 확인 (최대 ${HEALTH_RETRIES}회)"
    echo "== dry-run 끝 — 실제로 실행한 명령은 없다"
    exit 0
  fi

  # `curl -f` 의 종료 코드만 보면 3xx 는 성공으로 끝난다 — /health 가 로그인으로
  # 302 리다이렉트되는 설정 사고가 초록색으로 통과한다. 상태 코드를 직접 비교한다.
  local attempt response status body
  for attempt in $(seq 1 "$HEALTH_RETRIES"); do
    response="$(curl -sS --max-time 5 -w '\n%{http_code}' "$health_url" || true)"
    status="${response##*$'\n'}"
    body="${response%$'\n'*}"
    if [[ "$status" == "200" ]]; then
      echo "$health_url → 200 $body"
      echo "== $target 배포 완료"
      exit 0
    fi
    echo "($attempt/$HEALTH_RETRIES) $health_url → HTTP ${status:-000} (200 아님)"
    [[ "$attempt" == "$HEALTH_RETRIES" ]] || sleep "$HEALTH_RETRY_DELAY"
  done

  echo "$health_url 가 ${HEALTH_RETRIES}회 재시도 뒤에도 200 을 주지 않는다 — 배포 실패" >&2
  exit 1
}

# 표준입력을 끊고 본문을 돈다 — 자식 프로세스가 스크립트 본문을 먹지 못하게.
# 파일 맨 끝이라 bash 는 이 줄까지 다 읽은 뒤에 본문을 실행한다(위 주석 참고).
main "$@" < /dev/null
