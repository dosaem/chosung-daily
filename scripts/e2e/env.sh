#!/usr/bin/env bash
# E2E 스택의 공용 환경 — `scripts/e2e_stack.sh` 가 source 한다. 티켓 43·44 도
# `E2E_TICKET` 만 바꿔서 같은 스택을 쓴다(DB 이름·Redis 번호·포트가 전부 갈린다).
#
# 여기 있는 값은 **전부 로컬 테스트용**이다: 실제 스토어 링크·실제 OAuth 키·실제
# 결제 키를 넣지 않는다. 스토어 링크는 "설정됐을 때" 의 노출 규칙을 보려고 둔
# 형식만 맞는 가짜 URL 이고, 관리자 이메일은 example.com 이다.

E2E_TICKET="${E2E_TICKET:-42}"

# 전용 스키마. 티켓 번호를 이름에 넣어서 다른 워커의 pytest DB(`chosung_daily_test`)
# 와 섞이지 않게 한다.
E2E_DB="${E2E_DB:-chosung_daily_e2e_t${E2E_TICKET}}"
# Redis 는 DB 번호로 가른다 — 0 은 개발, 1 은 pytest 가 쓴다(`TestingConfig`).
E2E_REDIS_DB="${E2E_REDIS_DB:-4}"
# MySQL·Redis 는 이미 떠 있는 것을 쓴다(docker compose 의 mysql, 로컬 redis-server).
E2E_MYSQL_HOST="${E2E_MYSQL_HOST:-127.0.0.1}"
E2E_MYSQL_PORT="${E2E_MYSQL_PORT:-3306}"
E2E_REDIS_HOST="${E2E_REDIS_HOST:-127.0.0.1}"
E2E_REDIS_PORT="${E2E_REDIS_PORT:-6379}"
# DB 를 만들고 권한을 주는 데만 쓰는 관리자 계정(compose 의 mysql 기본값).
E2E_MYSQL_ROOT_USER="${E2E_MYSQL_ROOT_USER:-root}"
E2E_MYSQL_ROOT_PASSWORD="${E2E_MYSQL_ROOT_PASSWORD:-root}"
E2E_MYSQL_CONTAINER="${E2E_MYSQL_CONTAINER:-chosung-daily-mysql-1}"

# 앱 포트 두 개. 두 번째는 **스토어 링크가 비어 있는** 같은 앱이다 — 앱 설치
# 배너·CTA 의 "설정 안 됐으면 아예 안 그린다" 규칙을 브라우저에서 보려면 설정이
# 다른 인스턴스가 하나 더 있어야 한다(한 프로세스로는 둘 중 하나만 볼 수 있다).
E2E_PORT="${E2E_PORT:-50${E2E_TICKET}}"
E2E_PORT_NOSTORE="${E2E_PORT_NOSTORE:-51${E2E_TICKET}}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# 산출물(스크린샷·로그·manifest)은 전부 gitignore 된 이 폴더 아래로만 나간다.
E2E_ARTIFACTS="${E2E_ARTIFACTS:-$REPO_ROOT/e2e-artifacts}"
E2E_RUN_DIR="$E2E_ARTIFACTS/stack"
E2E_MANIFEST="$E2E_ARTIFACTS/seed-manifest.json"

# 운영자 판정용 이메일. 시드가 이 이메일로 Account 를 만들고, 테스트는 그 게스트의
# 백업 코드를 복원 화면에 넣어 운영자 브라우저가 된다(실제 구글 로그인 없이).
E2E_ADMIN_EMAIL="${E2E_ADMIN_EMAIL:-e2e-admin@example.com}"
# 시드가 그 게스트에게 심는 고정 토큰(= 백업 코드). Guest.token 은 평문 UUID 라
# 시드가 값을 정할 수 있다.
E2E_ADMIN_TOKEN="${E2E_ADMIN_TOKEN:-e2e42000-0000-4000-8000-00000000adm1}"

e2e_database_url() {
  echo "mysql+pymysql://chosung:chosung@${E2E_MYSQL_HOST}:${E2E_MYSQL_PORT}/${E2E_DB}?charset=utf8mb4"
}

e2e_redis_url() {
  echo "redis://${E2E_REDIS_HOST}:${E2E_REDIS_PORT}/${E2E_REDIS_DB}"
}

# 앱·Celery 가 공통으로 받는 환경. `with_store=no` 면 스토어 링크를 비워서 내보낸다.
e2e_export_app_env() {
  local with_store="${1:-yes}"
  export FLASK_ENV=development
  export SECRET_KEY="e2e-t${E2E_TICKET}-secret"
  export DATABASE_URL="$(e2e_database_url)"
  export REDIS_URL="$(e2e_redis_url)"
  export ADMIN_EMAILS="$E2E_ADMIN_EMAIL"
  # Gunicorn 접근 로그(접속기록)도 증거로 남긴다. 기본값(/logs)은 못 쓴다.
  export LOG_DIR="$E2E_ARTIFACTS/logs"
  # 광고·결제·로그인은 실제 서비스에 닿지 않는다 — 전부 비워 둔다.
  export SLACK_WEBHOOK_URL=""
  export SENTRY_DSN=""
  if [ "$with_store" = "yes" ]; then
    # 형식만 맞는 테스트 링크. 누르면 스토어로 나가므로 테스트는 href 만 확인한다.
    export STORE_URL_IOS="https://apps.apple.com/app/id6700000042"
    export STORE_URL_ANDROID="https://play.google.com/store/apps/details?id=com.dosaem.chosung.e2e"
    export APP_STORE_ID="6700000042"
  else
    export STORE_URL_IOS=""
    export STORE_URL_ANDROID=""
    export APP_STORE_ID=""
  fi
}
