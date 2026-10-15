#!/usr/bin/env bash
# 실제 스택(Flask + MySQL + Redis + Celery worker/beat)을 E2E 전용 설정으로
# 띄우고 내리는 스크립트. 티켓 42 가 소유하고 43·44 가 `E2E_TICKET` 만 바꿔 쓴다.
#
#   scripts/e2e_stack.sh up            # DB 생성 + 마이그레이션 + 프로세스 기동
#   scripts/e2e_stack.sh seed          # 단어·퍼즐·운영자 계정 시드 (멱등)
#   scripts/e2e_stack.sh advance-day   # "하루 지났다" 를 데이터로 만든다
#   scripts/e2e_stack.sh status
#   scripts/e2e_stack.sh down          # 프로세스 종료 + DB drop + Redis flush
#
# mock 서버는 쓰지 않는다. MySQL 과 Redis 는 **이미 떠 있는 것**(docker compose 의
# mysql, 로컬 redis-server)을 전용 스키마·전용 DB 번호로 나눠 쓴다 — 컨테이너를
# 한 벌 더 띄우면 같은 머신에서 도는 다른 워커의 pytest 와 포트가 부딪친다.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/e2e/env.sh
source "$SCRIPT_DIR/e2e/env.sh"

cd "$REPO_ROOT"

log() { printf '[e2e-stack] %s\n' "$*"; }
die() { printf '[e2e-stack] 실패: %s\n' "$*" >&2; exit 1; }

mysql_root() {
  docker exec -i "$E2E_MYSQL_CONTAINER" \
    mysql -u"$E2E_MYSQL_ROOT_USER" -p"$E2E_MYSQL_ROOT_PASSWORD" --silent 2>/dev/null
}

redis() { redis-cli -h "$E2E_REDIS_HOST" -p "$E2E_REDIS_PORT" -n "$E2E_REDIS_DB" "$@"; }

# 서버는 KST 벽시계를 그대로 쓴다(앱에 테스트용 시계 주입구를 만들지 않기로 했다 —
# 코디네이터 결정 2026-10-15). 그래서 자정을 넘는 동안 돌면 "오늘" 이 실행 중에
# 바뀌어 streak·퍼즐 날짜 검증이 거짓 실패한다. 한 판이 ~2분(실측 1분 40초)이라
# 자정 ±10분이면 아예 시작하지 않는다.
guard_midnight() {
  # 판정은 `scripts/e2e/guard_midnight.py` 가 한다 — `--now` 를 받아서 pytest 가
  # 같은 판정을 돌릴 수 있게 파일로 뺐다(tests/test_e2e_scripts.py).
  python3 "$SCRIPT_DIR/e2e/guard_midnight.py" \
    || die "KST 자정 ±10분이다 — 실행 중에 '오늘' 이 바뀐다. 20분 뒤에 다시 돌려라."
}

require_services() {
  docker exec "$E2E_MYSQL_CONTAINER" true >/dev/null 2>&1 \
    || die "MySQL 컨테이너($E2E_MYSQL_CONTAINER)가 없다 — docker compose up -d mysql"
  redis ping >/dev/null 2>&1 || die "Redis($E2E_REDIS_HOST:$E2E_REDIS_PORT)가 응답하지 않는다"
}

create_database() {
  log "DB $E2E_DB 준비 (없으면 생성, 권한 부여)"
  mysql_root <<SQL
CREATE DATABASE IF NOT EXISTS \`$E2E_DB\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON \`$E2E_DB\`.* TO 'chosung'@'%';
FLUSH PRIVILEGES;
SQL
}

migrate() {
  log "flask db upgrade"
  e2e_export_app_env yes
  uv run flask db upgrade
}

# pid 파일 하나로 프로세스 하나를 관리한다. 같은 티켓의 스택을 두 번 띄우면
# 포트가 부딪치므로, up 은 먼저 down 과 같은 정리를 한다.
start_proc() {
  local name="$1"; shift
  local pidfile="$E2E_RUN_DIR/$name.pid"
  local logfile="$E2E_RUN_DIR/$name.log"
  "$@" >>"$logfile" 2>&1 &
  echo $! >"$pidfile"
  log "$name 기동 (pid $(cat "$pidfile"), 로그 $logfile)"
}

stop_procs() {
  [ -d "$E2E_RUN_DIR" ] || return 0
  for pidfile in "$E2E_RUN_DIR"/*.pid; do
    [ -e "$pidfile" ] || continue
    local pid name
    pid="$(cat "$pidfile")"
    name="$(basename "$pidfile" .pid)"
    if kill -0 "$pid" 2>/dev/null; then
      log "$name 종료 (pid $pid)"
      # 프로세스 그룹(`kill -- -pid`)으로 보내면 안 된다 — 백그라운드 자식은 이
      # 스크립트와 같은 그룹이라 스크립트 자신이 죽는다. 부모에게 TERM 을 보내고,
      # gunicorn·celery 가 거느린 자식은 아래 pkill 이 표식으로 거둔다.
      kill -TERM "$pid" 2>/dev/null || true
    fi
    rm -f "$pidfile"
  done
  # TERM 을 못 받고 남은 것(고아 gunicorn 워커·celery 자식)을 이 티켓의 표식으로
  # 찾아 지운다. `--name`/`--hostname` 에 심어둔 문자열이 argv 에 그대로 남는다.
  pkill -f "e2e-t${E2E_TICKET}-marker" 2>/dev/null || true
  sleep 1
}

wait_for_health() {
  local port="$1" tries=60
  for _ in $(seq "$tries"); do
    if curl -fsS "http://127.0.0.1:$port/health" >/dev/null 2>&1; then
      log "포트 $port /health 응답 확인"
      return 0
    fi
    sleep 1
  done
  log "포트 $port 기동 실패 — 로그:"; tail -40 "$E2E_RUN_DIR"/app*.log 2>/dev/null || true
  die "포트 $port 의 앱이 ${tries}초 안에 뜨지 않았다"
}

cmd_up() {
  guard_midnight
  require_services
  stop_procs
  mkdir -p "$E2E_RUN_DIR" "$E2E_ARTIFACTS/logs"
  create_database
  migrate

  # 스토어 링크가 **있는** 앱. gunicorn 2 워커 — 단일 프로세스에서만 맞는 전제
  # (프로세스 메모리 캐시 등)가 끼어들지 않게 운영과 같은 모양으로 돌린다.
  e2e_export_app_env yes
  start_proc app uv run gunicorn \
    --name "e2e-t${E2E_TICKET}-marker-app" \
    -c gunicorn.conf.py -b "127.0.0.1:$E2E_PORT" -w 2 --timeout 60 wsgi:app
  # 스토어 링크가 **비어 있는** 같은 앱(배너·CTA 비노출 규칙 확인용).
  e2e_export_app_env no
  start_proc app-nostore uv run gunicorn \
    --name "e2e-t${E2E_TICKET}-marker-nostore" \
    -c gunicorn.conf.py -b "127.0.0.1:$E2E_PORT_NOSTORE" -w 1 --timeout 60 wsgi:app

  e2e_export_app_env yes
  start_proc worker uv run celery -A celery_app.celery worker --loglevel=info \
    --hostname "e2e-t${E2E_TICKET}-marker-worker@%h"
  start_proc beat uv run celery -A celery_app.celery beat --loglevel=info \
    --schedule "$E2E_RUN_DIR/celerybeat-schedule"

  wait_for_health "$E2E_PORT"
  wait_for_health "$E2E_PORT_NOSTORE"
  log "up 완료 — 앱 http://127.0.0.1:$E2E_PORT (스토어 링크 있음) / http://127.0.0.1:$E2E_PORT_NOSTORE (없음)"
}

cmd_seed() {
  guard_midnight
  e2e_export_app_env yes
  log "단어·퍼즐·운영자 계정 시드"
  E2E_ADMIN_EMAIL="$E2E_ADMIN_EMAIL" E2E_ADMIN_TOKEN="$E2E_ADMIN_TOKEN" \
    E2E_MANIFEST="$E2E_MANIFEST" uv run python scripts/e2e/seed.py
  log "manifest: $E2E_MANIFEST"
}

cmd_advance_day() {
  e2e_export_app_env yes
  # manifest 도 같이 내린다 — "어느 날짜에 어느 정답" 의 기록이 DB 와 어긋나면
  # 테스트가 지금 퍼즐의 정답을 못 찾는다.
  E2E_MANIFEST="$E2E_MANIFEST" uv run python scripts/e2e/advance_day.py "$@"
}

cmd_status() {
  printf 'DB        %s\nRedis     %s\n앱        http://127.0.0.1:%s\n앱(링크X) http://127.0.0.1:%s\n' \
    "$E2E_DB" "$(e2e_redis_url)" "$E2E_PORT" "$E2E_PORT_NOSTORE"
  for pidfile in "$E2E_RUN_DIR"/*.pid; do
    [ -e "$pidfile" ] || { echo "프로세스   없음"; break; }
    pid="$(cat "$pidfile")"
    if kill -0 "$pid" 2>/dev/null; then state=살아있음; else state=죽었음; fi
    printf '프로세스   %-12s pid %-8s %s\n' "$(basename "$pidfile" .pid)" "$pid" "$state"
  done
}

cmd_down() {
  stop_procs
  if docker exec "$E2E_MYSQL_CONTAINER" true >/dev/null 2>&1; then
    log "DB $E2E_DB drop"
    mysql_root <<SQL
DROP DATABASE IF EXISTS \`$E2E_DB\`;
SQL
  fi
  if redis ping >/dev/null 2>&1; then
    log "Redis DB $E2E_REDIS_DB flush"
    redis flushdb >/dev/null
  fi
  log "down 완료 (산출물은 $E2E_ARTIFACTS 에 남긴다)"
}

case "${1:-}" in
  up) cmd_up ;;
  seed) cmd_seed ;;
  advance-day) shift; cmd_advance_day "$@" ;;
  status) cmd_status ;;
  down) cmd_down ;;
  *) die "사용법: $0 <up|seed|advance-day|status|down>" ;;
esac
