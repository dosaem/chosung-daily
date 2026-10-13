# 디자인 도구 평가 (2026-10-13)

사용자가 제안한 도구 3개 + 이미 쓰던 2개를 이 프로젝트에서 어떻게 쓸지 정리. 결론은 맨 아래 "파이프라인" 절.

| 도구 | 정체 | 이 프로젝트 판단 |
|---|---|---|
| **UI UX Pro Max** (nextlevelbuilder) | 스타일·팔레트·폰트·UX 규칙 검색기 → 디자인 시스템 MASTER.md 생성. Flutter 스택 가이드 있음 | **채택.** 방향 후보 뽑는 1단계. 이미 `design-system/hidden-vowels/` 생성함 |
| **Google Stitch** (MCP) | 텍스트 → 화면 목업(HTML + 스크린샷). 디자인 시스템 ID 로 화면 간 일관성 유지 | **채택.** 2단계 목업. 주의: `X-Goog-User-Project` 헤더 필요, 토큰 1시간, 기본 모델은 "service unavailable" 잦아서 `GEMINI_3_5_FLASH_LITE` 가 안정적. MCP 클라이언트 타임아웃(2분)보다 생성이 길어서 API 직접 호출(curl, `--max-time 580`)로 돌림 — `stitch/req_*.json` 참고 |
| **impeccable** (pbakaus) | 디자인 언어 스킬 1개 + 명령 24개 + **결정론적 안티패턴 탐지기 59규칙**(LLM 불필요). `ios.md`/`android.md` 네이티브 가이드와 `audit.native`(Flutter 소스 감사) 있음 | **채택.** (a) 목업 HTML 에 `detect` 돌려서 기계 검증, (b) 웹 티켓에서 `/impeccable critique·audit·polish`, (c) Flutter 티켓에서 `audit.native` 체크리스트. 실측: V2 목업에서 초록 타일 위 밝은 글자 2.8:1, 코랄 버튼 위 글자 2.5:1, Inter 과사용을 잡아냄. V1 은 0건 |
| **oh-my-design** (3x-haust) | 브리프→레퍼런스 측정→익명 구조 후보 블라인드 선택→빌드→렌더 리뷰 루프. 기본 스택 React+Vite, 모바일은 390px 뷰포트만. 플러그인 설치됨 | **보류.** Node ≥22.19 필요(현재 22.14), Playwright/browser-rs 의존, Pi 프로토콜 용어가 무거움. Flutter 산출 없음. 웹 페이지(랜딩/`/privacy`) 를 따로 디자인할 때 design-only 모드로 재평가 |
| **oh-my-agent** (first-fluke) | 멀티 에이전트 하네스 전체(Stop 훅 게이트, 아티팩트 검사, 독립 심판). `/oma-design` 은 그 안의 스킬 하나 | **미채택.** Orca 오케스트레이션과 역할이 겹침. Stitch 연동은 README 에서 확인 안 됨. "기계 검증 게이트" 아이디어는 impeccable `detect` + ruff/analyze CI 로 이미 커버 |

## 탐지기 실측 (2026-10-13, `impeccable detect`)

```
v1_editorial_home.html  → 0건
v2_softdark_home.html   → 7건: low-contrast ×5 (#f1f5f9 on #3fa66b 2.8:1, on #f0795a 2.5:1), cramped-padding, overused-font(Inter)
00_test_home.html       → flat-type-hierarchy (h1=h2=body 16px)
```
→ 다크 테마에서 초록·코랄 **면 위 글자는 어두운 색**이어야 한다. `OVERRIDES.md` §2 의 `tile-text-on-correct` 다크값(#052E16)이 이미 그렇게 돼 있음. Inter 대신 Pretendard 를 주 폰트로 쓰는 결정도 유지.

## 파이프라인 (이 프로젝트 + 이후 모든 서비스)

1. **방향** — UI UX Pro Max `--design-system` 으로 후보 2개 → 사용자가 고름 → `MASTER.md` + `OVERRIDES.md`
2. **목업** — Stitch 로 홈 화면 방향 후보 2~3개 → 사용자가 고름 → 같은 디자인 시스템으로 전 화면 생성 → `design/stitch/*.html|png` + 갤러리 아티팩트
3. **기계 검증** — 고른 목업 전부에 `impeccable detect` → 0건 될 때까지 Stitch `edit_screens` 또는 토큰 수정
4. **구현** — UI 티켓은 DESIGN_DIR(`design/`) 을 따르고, 완료 조건에 `impeccable detect`(웹) / `audit.native` 체크리스트(Flutter) 통과를 넣는다
5. **마감** — 웹은 `/impeccable polish`, 앱은 스토어 스크린샷 찍기 전 `/impeccable critique`

`/impeccable init`(PRODUCT.md) 과 `document`(DESIGN.md) 는 레포 루트에 쓰므로 Planner 가 아니라 **구현 첫 티켓**에서 실행한다. 입력은 이 폴더의 SCREENS.md / OVERRIDES.md / spec.md.
