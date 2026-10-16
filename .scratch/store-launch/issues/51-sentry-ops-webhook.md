# 51: 에러 알림 자동화 — Sentry → Slack + GitHub 이슈 → Claude Code Action

**What to build:** Sentry 에 새 에러가 생기면 Slack 에 요약이 오고, GitHub 에 `sentry` 라벨 이슈가 열리며, Claude Code GitHub Action 이 그 이슈를 읽어 원인 분석 덧글과 수정 PR 을 연다. Sentry 에서 해결하면 이슈가 닫힌다. 사용자 결정(2026-10-16, A안).

**Blocked by:** None.

**Status:** 서버·Sentry 설정 끝(2026-10-16) — GitHub PAT·Claude GitHub 앱 설치(사용자), 워크플로 파일 남음

- [x] `POST /api/v1/ops/sentry` — HMAC-SHA256 서명 검증, 큐 넣고 202, 비밀키 없으면 503
- [x] `ops_alert_service` — issue created/unresolved/resolved · event_alert, Slack 요약, GitHub 이슈 생성/덧글/닫기, 중복 방지(Redis + 제목 식별자)
- [x] `tasks.handle_sentry_hook` — GitHub 일시 오류 재시도, 끝내 실패하면 Slack 만
- [x] Sentry 내부 통합 "chosung ops webhook" 생성(Issue&Event Read, Issues 웹훅, Alert Action on), Client Secret → NAS `.env`
- [ ] GitHub fine-grained PAT(이 레포 Issues: Read and write) → NAS `.env` `GITHUB_ISSUES_TOKEN` — **사용자가 발급**
- [ ] `.github/workflows/claude-sentry.yml` — `sentry` 라벨 이슈 열리면 Claude Code Action 실행 (Claude GitHub 앱 설치는 사용자)
- [ ] 실제 Sentry 테스트 이벤트로 왕복 확인 → user-todo 26 갱신
