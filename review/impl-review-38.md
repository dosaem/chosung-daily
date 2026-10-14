# 티켓 38 최종 리뷰 — 라운드 1

## 기준과 범위

2026-10-15, 로컬 `main...HEAD`와 `git log main..HEAD`를 직접 확인했다. 구현 커밋은 `fe63626` 하나이며 main이 HEAD의 조상이다. 티켓 원문을 최신 요구로 적용했다(스펙의 기존 `display` 계약보다 우선). `.scratch/store-launch/spec.md` US 12·13·16b, API 표, Flutter 절과 디자인 SCREENS S3/T3, hidden-vowels OVERRIDES를 대조했다. `review/impl-evidence-38.md`의 주장은 코드와 실제 실행 결과로 교차 확인했다. 하위 에이전트·프로덕션·배포·push 없이 리뷰했다.

## 체크박스별 평가

| 요구 | 평가 | 근거 |
|---|---|---|
| 1. 언어 중립 익명 식별자, 개인정보 비노출 | 충족 | `puzzle_metrics.anon_tag()`는 기존 modulo 기반 4자리 태그만 반환하고 응답 스키마에는 `anon_tag`만 둔다. 응답 필드 집합·태그 값 테스트와 언어별 리더보드 분리 테스트가 존재한다. 인증 경로와 저장 데이터 변경은 없다. |
| 1. display 유지/제거 판단 및 API 표 | 충족 | README API 행이 `anon_tag`로 갱신됐고 `### 38.`에서 동시 웹 배포·앱 미출시 및 이미 열린 탭의 위험을 설명한다. 제거 여부는 티켓이 허용한 판단이다. |
| 2. 웹 ko/en 이름 및 is_me 유지 | 충족 | 실제 `app.js`를 실행하는 Node 시나리오가 `게스트 #a3f1`/`Guest #a3f1`, 내 행 클래스, 내 순위 문구를 검사한다. 렌더링은 textContent를 사용하며 새 HTML 삽입 경로가 없다. |
| 3. 앱 ko/en 이름·semantics 및 골든 | 충족 | `ranking.guest` 번역으로 이름을 만들고 행 semantics에 같은 이름을 전달한다. widget 테스트가 양 언어 텍스트와 semantics를 검사하며 기존 골든도 전체 Flutter 테스트에 포함되어 통과했다. |
| 4. en 1 try / 2 tries, ko 유지 | 충족 | easy_localization plural을 적용했고 모든 변경 키의 호출부도 plural로 바꿨다. ranking·내 순위·통계 semantics·streak의 단복수 테스트 및 ko 회귀 검사가 통과했다. 웹도 1/2 분기를 실제 번들로 검증한다. |
| 5. 서버·웹·앱 테스트 및 TDD | 미충족(서버 한글 검사) | 주요 렌더·API 값 테스트는 동작을 검사하지만 서버 본문 전체 한글 검사는 이스케이프 때문에 거짓 통과한다(D-38-1). red 단계는 구현 증거에 기록되어 있으나 단일 구현 커밋만으로 과거 실행 순서까지 독립 확인할 수는 없다. |
| 공유 파일 자기 번호 절/행만 변경 | 미충족 | README의 기존 `### 07.` 영역에 추가한 인용문은 허용된 `### 38.` 바깥이다(D-38-2). API 해당 행 변경은 요구된 범위다. `.env.example`·`docs/RELEASE.md`는 변경하지 않았다. |
| 전체 검증·빌드·웹 detect | 충족 | 아래 명령을 직접 실행해 pytest 1412개·Flutter 403개·ruff·analyze·format·APK build가 모두 통과했고 detect는 0건이었다. 빌드 후 mobile/build 부재도 확인했다. |
| 마이그레이션·범위·시크릿 | 충족 | 마이그레이션 없음(`git diff main...HEAD -- migrations/` 빈 출력). 같은 문제를 가진 복수형 키 확장은 티켓의 허용 범위다. 변경분에서 실제 시크릿 값 기록이나 신규 인증·CSRF·데이터 손상 위험은 발견하지 못했다. |

## 직접 실행한 검증

- 전용 `chosung_daily_test_t38`, `chosung_daily_test_t38_migrations`, Redis DB 14를 TEST 환경변수로 지정했다. 새 DB 생성이나 공용 DB 폴백 없이 실행했으며 pytest 동시 실행은 하지 않았다. 접속 인증 값은 문서에서 생략한다.
- 전체 `uv run pytest -q`: exit 0, `1412 passed in 1490.20s (0:24:50)`. 실패가 없어 재실행하지 않았다.
- `uv run ruff check .`: exit 0, `All checks passed!`.
- `cd mobile && flutter analyze --no-pub`: exit 0, `No issues found!`.
- `cd mobile && flutter test --no-pub`: exit 0, `403: All tests passed!`.
- `cd mobile && dart format --output=none --set-exit-if-changed lib test`: exit 0, 122 files, 0 changed. 코드 수정 금지에 맞춰 output=none으로 검사했다.
- `cd mobile && flutter build apk --debug --no-pub`: exit 0, `Built build/app/outputs/flutter-apk/app-debug.apk`. 검증 뒤 생성된 `mobile/build`를 삭제했다.
- `uv run python review/web-detect-snapshots-38.py /tmp/t38-final-web`로 실제 번들 렌더 기반 로컬 스냅샷을 만들었다. 외부 stylesheet와 script를 제거하는 생성 코드를 확인했다. loopback 서버에서 `impeccable detect --json` ko/en × light/dark 결과 `[]`, exit 0. en light/dark의 `--viewport 320x844` 검사도 `[]`, exit 0. 이는 해당 스냅샷의 정적 UI 검사이며 전체 브라우저 상호작용 E2E를 의미하지 않는다.
- `git diff --check main...HEAD`: exit 0. 리뷰 시작 시 작업 트리는 clean이었다.

## 결함 목록

### D-38-1 — MINOR — JSON escape 때문에 한글 비노출 테스트가 거짓 통과

- 위치: `tests/test_leaderboard.py:85`–90 (핵심 assertion 90행).
- 재현: `uv run python -c 'from app import create_app; import re; a=create_app("testing"); s=a.json.dumps({"display":"게스트 #a3f1"}); print(repr(s)); print(not re.search(r"[가-힣]",s))'`.
- 기대: 한글 접두사를 넣은 서버 JSON이면 한글 비노출 검증이 실패한다.
- 실제: Flask 기본 JSON 직렬화가 한글을 `\uac8c\uc2a4\ud2b8`로 바꾸므로 마지막 출력은 `True`다. 현재 테스트는 `get_data(as_text=True)`의 직렬화된 본문을 검사하여 한글 값이 있어도 통과한다. 오류 상태 응답도 별도 status 검증 없이 통과할 수 있다.
- 영향: 구현 증거가 주장한 “응답 본문 전체” 회귀 보호가 없다. 다만 별도 필드 집합 테스트와 `anon_tag` 단위 테스트가 현재 핵심 계약을 검증하므로 기능을 막는 MAJOR로 분류하지 않았다.
- 수정 방향: status 200과 비어 있지 않은 entries를 확인하고 JSON 디코딩 후 문자열 값을 검사한다.

### D-38-2 — MINOR — 공유 README에서 다른 티켓 절을 수정

- 위치: `README.md:1001`–1003.
- 재현: `git diff main...HEAD -- README.md`.
- 기대: 설계 판단 추가는 자기 번호 `### 38.` 안에만 있고 API 변경은 해당 행에 한정된다.
- 실제: 기존 `### 07.` 절 끝에 38의 결론을 알리는 인용 블록을 추가했다. 구현 증거 §3.4도 이 편집을 인정한다. 최신 설명은 이미 `### 38.`에 있어 그 절 안에서 충분히 제공할 수 있다.
- 영향: 명시된 병렬 공유 파일 편집 경계를 어겼다. 기존 본문 삭제나 기능 변화는 없어 MINOR다.
- 수정 방향: 07절의 새 인용 블록을 제거하고 설명은 38절에 둔다.

## 참고

- 기존 스펙의 한국어 display 문구와 달라진 것은 이번 사용자 결정에 따른 의도된 변경이다.
- 이미 열린 구버전 웹 탭은 배포 후 새로고침 전까지 이름을 표시하지 못할 수 있다. 티켓에서 제거 판단을 허용했고 README에 위험을 명시했으므로 별도 결함으로 올리지 않았다.
- 취향·스타일 제안은 결함에 포함하지 않았다.

판정: PASS
