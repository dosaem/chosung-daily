#!/usr/bin/env bash
# NAS 배포 — deploy.sh <prod|develop> [--dry-run]
#
# 대상 인자 하나가 브랜치·체크아웃 디렉터리·compose 프로젝트명·env 파일을 전부
# 정한다. 하는 일: git pull → compose up -d --build → 마이그레이션 → 5개 서비스
# 기동 확인 → /health 200. 어느 단계에서든 실패하면 즉시 0 이 아닌 코드로 끝나서
# GitHub Actions 가 빨갛게 멈춘다(.github/workflows/deploy.yml).
#
# GitHub Actions 는 이 파일을 ssh 표준입력으로 흘려보낸다(`ssh nas 'bash -s --
# prod' < deploy/deploy.sh`) — NAS 체크아웃의 스크립트를 실행하면 git pull 이
# 실행 중인 자기 자신을 갈아치운다. 이유는 README "설계 판단" §20.
#
# DEPLOY_BASE_DIR 로 체크아웃 상위 디렉터리를 바꿀 수 있다(기본 /volume1/docker).
# 테스트에서 가짜 NAS 를 가리키는 용도 — NAS 에서는 기본값을 쓴다.
set -euo pipefail

COMPOSE_FILE=docker-compose.prod.yml
HEALTH_RETRIES=10
HEALTH_RETRY_DELAY=3

usage() {
  echo "사용법: deploy.sh <prod|develop> [--dry-run]" >&2
}

target="${1:-}"
dry_run=0
[[ "${2:-}" == "--dry-run" ]] && dry_run=1

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

compose=(docker compose -f "$COMPOSE_FILE" -p "$project" --env-file "$env_file")

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

echo "== $target 배포: $branch → $checkout_dir ($project / $env_file)"

if [[ "$dry_run" == 0 ]]; then
  if [[ ! -d "$checkout_dir" ]]; then
    echo "체크아웃 디렉터리가 없다: $checkout_dir" >&2
    exit 1
  fi
  cd "$checkout_dir"

  current_branch="$(git rev-parse --abbrev-ref HEAD)"
  if [[ "$current_branch" != "$branch" ]]; then
    echo "$checkout_dir 가 $branch 가 아니라 $current_branch 에 있다 — 중단" >&2
    exit 1
  fi
fi

run git pull --ff-only origin "$branch"
run "${compose[@]}" up -d --build
run "${compose[@]}" exec -T app uv run flask db upgrade

# /health 는 app 하나만 보니까 worker·beat 가 죽어도 200 이 나온다 — compose 가
# 아는 서비스 전부가 실제로 running 인지 따로 확인한다.
expected_services="$(capture "${compose[@]}" config --services | sort)"
running_services="$(capture "${compose[@]}" ps --services --filter status=running | sort)"
if [[ "$expected_services" != "$running_services" ]]; then
  echo "기동하지 않은 서비스: $(comm -23 <(echo "$expected_services") <(echo "$running_services") | tr '\n' ' ')" >&2
  exit 1
fi

# 호스트 포트는 env 파일의 APP_PORT 가 진실이라 스크립트에 또 적지 않고,
# compose 가 실제로 발행한 포트를 물어본다.
published="$(capture "${compose[@]}" port app 5000)"
port="${published##*:}"
health_url="http://127.0.0.1:${port:-0}/health"

if [[ "$dry_run" == 1 ]]; then
  echo "+ curl -fsS --max-time 5 <APP_PORT 로 만든 /health URL> (최대 ${HEALTH_RETRIES}회)"
  echo "== dry-run 끝 — 실제로 실행한 명령은 없다"
  exit 0
fi

for attempt in $(seq 1 "$HEALTH_RETRIES"); do
  if body="$(curl -fsS --max-time 5 "$health_url")"; then
    echo "$health_url → $body"
    echo "== $target 배포 완료"
    exit 0
  fi
  echo "($attempt/$HEALTH_RETRIES) $health_url 아직 응답 없음"
  [[ "$attempt" == "$HEALTH_RETRIES" ]] || sleep "$HEALTH_RETRY_DELAY"
done

echo "$health_url 가 ${HEALTH_RETRIES}회 재시도 뒤에도 200 을 주지 않는다 — 배포 실패" >&2
exit 1
