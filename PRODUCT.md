# Product

<!-- impeccable:product-schema 1 -->

`/impeccable init` 이 쓴 제품 기록. 시각 세계(DESIGN.md)는 여기에 쓰지 않는다 —
이 프로젝트의 시각 권위는 아래 `## Evidence on Hand` 의 DESIGN_DIR 두 경로다.

## Platform

web

> 이 레포에는 이제 두 UI 가 있다: 웹(`web/templates` + `web/static`, Jinja +
> vanilla JS)과 Flutter 앱(`mobile/`, 티켓 22 에서 들어옴). Platform 은 값을
> 하나만 쓸 수 있어서 **`web` 을 유지**한다 — 이 값이 `ios`/`android`/`adaptive`
> 가 되면 `impeccable detect` 가 네이티브 프로젝트로 보고 꺼지는데, 웹 티켓
> (17·18)의 완료 조건이 detect 0건이라 그 게이트를 잃는다.
>
> **앱(`mobile/`)은 네이티브로 다룬다**: 설계·검수는 `impeccable detect` 가 아니라
> `audit.native` 체크리스트로 하고, 두 OS 로 출시하므로 `reference/ios.md` 와
> `reference/android.md` 를 **둘 다** 읽고 점수를 매긴다(티켓 22 의 기록은
> `review/impl-evidence-22.md`). 앱과 웹은 OS 별로 디자인 언어를 바꾸지 않고
> **같은 OVERRIDES 토큰 하나**를 쓴다(OVERRIDES §1) — 그래서 `adaptive` 의 원래
> 뜻("OS 별로 디자인 언어를 바꾸는 하나의 제품")에도 해당하지 않는다.

## Users

- **플레이어**: 하루 30초를 들여 한 문제를 푸는 사람. 웹(chosung.dosaem.com)에서
  로그인 없이 바로 시작하고, 기기를 바꿔도 연속 기록을 잇고 싶다. 퍼즐 언어는
  한국어(초성)와 영어(자음 뼈대) 중 고른다.
- **운영자**: 프로젝트 주인 1명(허용 이메일 정확히 두 개). 단어 풀과 30일치 퍼즐
  배정을 관리하고, 잔량·배정 실패·백업 실패를 Slack 으로 받는다. 플레이어와 다른
  권한을 가진 별도 역할이다.

## Product Purpose

하루 한 문제, 가려진 단어를 맞추는 게임. 한국어는 초성만, 영어는 모음을 빈칸으로
보여준다. "오늘" 의 경계는 모든 지역에서 KST 자정 하나로 고정한다(ADR 0001).
성공 = 매일 돌아오는 플레이어, 바닥나지 않는 단어 풀, 스토어 심사를 통과하는 앱.

## Positioning

Wordle 류와 달리 **한국어 초성**이라는 가림 방식이 1차 모국어 감각에 걸려 있고,
기록의 주인이 계정이 아니라 **게스트 토큰**이라 로그인 없이 시작해도 기기 전환이
된다(백업 코드 = 게스트 토큰 그 자체). 하루 경계가 KST 하나라 리더보드가
시간대별로 갈라지지 않는다.

## Operating Context

- 웹과 iOS/Android 앱이 같은 Flask 서버(`/api/v1`)를 쓴다. 광고·구독·일일 알림은
  앱에만 있고, 웹은 광고 없이 전부 플레이할 수 있다.
- 플레이는 한 번에 끝나는 짧은 세션이다: 오늘의 퍼즐을 열고 최대 5회 시도하고
  결과를 공유하거나 순위를 본다. 3번째 오답 뒤 힌트가 열린다.
- 운영자는 관리자 페이지(Jinja)에서 CSV 로 단어를 올리고 배정표를 바꾼다.
  알림은 Slack Incoming Webhook 한 곳으로 간다.
- 서버는 NAS 에 compose 로 뜬다(prod/develop 두 프로젝트).

## Capabilities and Constraints

- 스택: Flask + SQLAlchemy/Alembic + MySQL + Redis + Celery(uv, ruff, pytest).
  앱은 Flutter + Riverpod. 이 조합은 고정이다.
- 레이어: api → services → repositories. **서비스 함수 하나 = 커밋 하나**, 외부
  provider 호출은 `app/clients/<provider>.py` 래퍼 한 함수, 도메인 판정은 서비스의
  순수 함수로 분리한다(스펙 §A.17).
- 면접에서 작성자가 직접 설명해야 하는 포트폴리오 코드다 — 과한 추상화를 쓰지
  않고, 설계 판단은 README "설계 판단" 절에 근거와 함께 남긴다.
- 용어는 `CONTEXT.md` 가 정본이다(게스트/계정/연결/가림/퍼즐 고정/권한 등).
  UI 문구가 쓰는 말도 이 용어를 따른다.
- 아직 안 정한 것: `.scratch/store-launch/spec.md` "미정 항목" 참고(스토어 웹훅
  도입 시점, 영어 책 제목 소스, 리마인더 시각의 효과 등).

## Brand Commitments

- 이름: **오늘의 초성 / Hidden Vowels**.
- 방향 한 줄: "매일 30초 집중" — **Editorial Light**(오프화이트 바탕, 검정
  타이포가 주인공). 다크 모드는 Soft Dark.
- `brand` 오렌지는 가는 디테일(불꽃 아이콘, 활성 탭 밑줄, 포커스 링, 선택 칩
  테두리)에만 쓰고 **면 채움·일반 크기 글자색 금지**(대비 미달). 주 버튼은 검정.
- 게임 피드백 색(초록/회색 타일)은 브랜드 색과 절대 섞지 않고, 색만으로 구분하지
  않는다(아이콘·굵기 병행).
- 리더보드에 실명·이메일을 쓰지 않는다 — "게스트 #a3f1" 표시만.

이 세 항목의 구속력 있는 원문은 `OVERRIDES.md` 다. 충돌하면 OVERRIDES 가 이긴다.

## Evidence on Hand

**DESIGN_DIR (시각 권위, 두 경로)**

- `.scratch/store-launch/design/` — `SCREENS.md`(화면 명세 S1~S7), `stitch/`
  (채택 목업 + PNG), `archive/`(폐기한 방향), `TOOLS.md`(제작 경로 실측).
- `.scratch/store-launch/design-system/hidden-vowels/` — `MASTER.md`(UI UX Pro
  Max 베이스) + `OVERRIDES.md`(**토큰·컴포넌트 정본. MASTER·SCREENS 와 충돌하면
  이 파일이 우선**).

**그 밖**

- `.scratch/store-launch/spec.md` — 제품 스펙 r5(문제·해결·유저 스토리·구현 결정).
- `CONTEXT.md`(용어집) · `docs/adr/0001~0003`(결정 기록) · `README.md` "설계 판단".
- 실제 플레이 가능한 웹 구현: `web/templates/index.html`, `web/static/app.js`.

**없는 것(만들어내지 않는다)**: 목업이 없는 화면은 S7(점검/업데이트), 온보딩 2·3장,
ATT 안내, 알림 사전 안내, 삭제 다이얼로그, 광고 개인정보 설정, 백업 코드 입력
시트, 웹 전체(`/account/delete` 포함) — 명세 + 토큰으로 구현하고 detect/critique
로 검증한다(스펙 "디자인 부족 항목"). 사용자 수·후기·매출 같은 지표는 아직 없다.

## Product Principles

1. **로그인 없이 시작된다.** 기록의 주인은 게스트 토큰이고 계정 연결은 선택이다.
   어떤 화면도 플레이 전에 가입을 요구하지 않는다.
2. **하루 경계는 KST 하나.** 날짜 키가 갈라지지 않게 모든 지역에서 같은 자정을 쓴다.
3. **플레이는 30초.** 한 화면에서 끝나고, 설명보다 바로 시작이 먼저다.
4. **운영자가 서버에 들어가지 않아도 돌아간다.** 단어·배정·토글은 관리자 화면에서,
   이상은 Slack 으로 먼저 알린다.
5. **설명할 수 있는 코드만 남긴다.** 추상화 하나를 늘리기 전에 그걸 면접에서
   설명할 수 있는지 먼저 본다.

## Accessibility & Inclusion

- 색만으로 상태를 구분하지 않는다(타일에 아이콘·굵기 병행).
- 본문 대비 4.5:1, 큰 글자 3:1 이상. `brand` 오렌지는 일반 크기 글자색으로 쓰지
  않는다(라이트 ≈3.9:1 로 AA 미달 — OVERRIDES §2).
- 라이트·다크 두 모드를 모두 설계 대상으로 둔다.
