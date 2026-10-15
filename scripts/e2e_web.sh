#!/usr/bin/env bash
# 웹 E2E 한 판: 스택을 띄우고 시드하고 브라우저로 돌린 뒤 정리한다.
#
#   scripts/e2e_web.sh                      # 전부 (데스크톱 1280 + 모바일 390)
#   scripts/e2e_web.sh --project=desktop-1280
#   scripts/e2e_web.sh specs/01-first-visit.spec.mjs
#   E2E_KEEP=1 scripts/e2e_web.sh ...       # 끝나고 스택을 남긴다(디버깅)
#
# **DB 를 매번 새로 만든다**(down → up → seed). 시나리오 10(운영자 CSV 업로드)이
# "추가 2개 · 중복 1개" 처럼 빈 DB 를 전제한 수를 단정하고, 시나리오 4 는 저장된
# 날짜를 하루 되돌린다 — 같은 DB 에 두 번 돌리면 둘 다 다른 것을 본다.
#
# 소요: 실측 **2~3분** (스택 기동 ~25초, 시드 ~5초, 브라우저 시나리오 42개
# 1분~2분 30초, 정리 ~5초). 자세한 건 README "E2E" 절.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/e2e/env.sh
source "$SCRIPT_DIR/e2e/env.sh"
WEB_E2E_DIR="$REPO_ROOT/tests/e2e/web"

cd "$REPO_ROOT"

cleanup() {
  if [ "${E2E_KEEP:-0}" = "1" ]; then
    echo "[e2e-web] E2E_KEEP=1 — 스택을 남긴다 (scripts/e2e_stack.sh down 으로 정리)"
    return
  fi
  bash "$SCRIPT_DIR/e2e_stack.sh" down || true
}
trap cleanup EXIT

# Playwright 와 브라우저는 한 번만 받는다 — 레포에 커밋하지 않는다(gitignore).
if [ ! -d "$WEB_E2E_DIR/node_modules" ]; then
  echo "[e2e-web] npm ci (처음 한 번)"
  # `install` 이 아니라 `ci` — `package-lock.json` 이 커밋돼 있으니 버전이 조용히
  # 올라가지 않아야 한다(브라우저 자동화는 버전 하나에 동작이 바뀐다).
  (cd "$WEB_E2E_DIR" && npm ci --no-audit --no-fund)
  (cd "$WEB_E2E_DIR" && npx playwright install chromium)
fi

bash "$SCRIPT_DIR/e2e_stack.sh" down
bash "$SCRIPT_DIR/e2e_stack.sh" up
bash "$SCRIPT_DIR/e2e_stack.sh" seed

echo "[e2e-web] playwright test $*"
(cd "$WEB_E2E_DIR" && npx playwright test "$@")
