# docs/agents

`/setup-matt-pocock-skills` 가 만든 설정. `to-spec` / `to-tickets` / `triage` / `grill-with-docs` 가 이 폴더를 읽는다.

- `issue-tracker.md` — 이슈 트래커 = 로컬 마크다운 (`.scratch/<feature-slug>/`)
- `triage-labels.md` — 트리아지 라벨 (기본 5개)
- `domain.md` — 도메인 문서 레이아웃 (단일 컨텍스트: 루트 `CONTEXT.md` + `docs/adr/`)

## CLAUDE.md 에 붙일 블록

레포 루트에 `CLAUDE.md` 가 아직 없다. 만들 때 아래 블록을 넣는다
(Planner 워커는 `docs/agents/`, `.scratch/` 밖을 못 써서 여기 초안만 남김).

```markdown
## Agent skills

### Issue tracker

Issues live as local markdown under `.scratch/<feature-slug>/` (spec.md + issues/NN-slug.md). See `docs/agents/issue-tracker.md`.

### Triage labels

Default five labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` at the repo root + `docs/adr/`. See `docs/agents/domain.md`.
```
