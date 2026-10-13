#!/bin/bash
# 덤프 하나를 지정 compose 프로젝트의 MySQL 에 복원한다. 되돌릴 수 없다.
#
#   scripts/restore.sh [-y] <덤프.sql.gz> [compose 프로젝트명]
#
# 프로젝트명을 안 주면 환경변수 COMPOSE_PROJECT_NAME 을 쓴다(prod 는
# chosung-daily-prod, develop 은 chosung-daily-develop — docs/RELEASE.md 표).
# 덤프에 DROP/CREATE DATABASE 가 들어 있어서(backup.sh 의 --add-drop-database)
# 복원하면 덤프 시점 이후 생긴 행은 사라진다.
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
cd "$(cd "$(dirname "$0")/.." && pwd)"

usage() {
  echo "사용법: scripts/restore.sh [-y] <덤프.sql.gz> [compose 프로젝트명]" >&2
  exit 2
}

assume_yes=0
if [ "${1:-}" = "-y" ]; then
  assume_yes=1
  shift
fi

dump="${1:-}"
project="${2:-${COMPOSE_PROJECT_NAME:-}}"

[ -n "$dump" ] || usage
[ -f "$dump" ] || {
  echo "덤프 파일이 없다: $dump" >&2
  exit 1
}
[ -n "$project" ] || {
  echo "compose 프로젝트명을 인자나 COMPOSE_PROJECT_NAME 으로 줘야 한다" >&2
  usage
}

if [ "$assume_yes" -ne 1 ]; then
  # 파이프·CI 에서 모르고 돌아가면 안 된다 — tty 가 아니면 -y 를 요구한다.
  [ -t 0 ] || {
    echo "비대화 실행에서는 -y 를 줘야 한다 (대상: $project)" >&2
    exit 1
  }
  printf '%s 의 MySQL 을 %s 로 덮어쓴다. 되돌릴 수 없다. 계속할까? [y/N] ' "$project" "$dump"
  read -r answer
  case "$answer" in
  y | Y | yes) ;;
  *)
    echo "취소했다" >&2
    exit 1
    ;;
  esac
fi

echo "[restore] $dump -> project=$project ($COMPOSE_FILE)"
# 비밀번호는 mysql 컨테이너 안의 env 를 그대로 쓴다 — 호스트 스크립트가 시크릿을
# 읽거나 인자로 넘기지 않는다(쉘에서 '...' 로 묶어 호스트 확장을 막는다).
gzip -dc "$dump" |
  docker compose -f "$COMPOSE_FILE" -p "$project" exec -T mysql \
    sh -c 'exec mysql -u root -p"$MYSQL_ROOT_PASSWORD"'

echo "[restore] 완료. 앱이 캐시를 들고 있으니 필요하면 app/worker/beat 를 재시작한다:"
echo "  docker compose -f $COMPOSE_FILE -p $project restart app worker beat"
