# 티켓 09 최종 리뷰 — 라운드 1

검토 대상 HEAD: `2168a15`, 로컬 main: `21856d8`, merge-base: `72a2a3c`.
`git diff main...HEAD` 및 `git log main..HEAD --oneline`의 구현 커밋 5개를 검토했다.
티켓 09, 스펙 §A.15·§A.16·US45·미정 9, CONTEXT, SCREENS 웹 절, MASTER 및 우선 규칙 OVERRIDES와 구현 증거를 대조했다.

## 체크박스별 판정

| 티켓 체크박스 | 충족 여부 | 직접 확인한 근거 |
|---|---|---|
| 공용 토큰 CSS, 라이트/다크, 그림자 없음, Pretendard, 메인 스타일 유지 | 충족 | `tokens.css` 색상·간격·폰트 값을 OVERRIDES와 직접 대조했다. 브라우저 라이트/다크 배경·전경도 일치한다. 기존 `style.css`·`index.html` diff 없음. 문서 레이아웃의 별도 편차는 D-09-3. |
| Jinja ko/en 개인정보처리방침 및 필수 공시 | 미충족 | 4개 URL 모두 200이고 수집 항목 6개, 보유 기간, 업체 5개, 국외 이전, 아동, 삭제 링크, 연락처가 존재한다. 그러나 국외 이전 거부 방법이 서비스 사양과 충돌한다(D-09-1). 언어 협상에도 경계 오류가 있다(D-09-2). |
| 구독 자동 갱신·스토어 해지·EULA 선택 자리 | 충족 | 두 언어 약관에 자동 갱신, App Store/Google Play 해지 경로, 삭제와 해지의 구분, Apple 표준 EULA 링크와 커스텀 선택 안내가 있다. 미정 9의 최종 선택은 이 티켓의 완료 조건이 아니다. |
| pytest 렌더 테스트·두 페이지 detect 0건 | 충족 | 전체 실행 307 passed / 8 환경 오류 후 오류 8개 재실행 모두 통과. 추가 테스트 129개는 실제 렌더·정적 파일·순수 함수 검사이며 렌더를 mock하지 않는다. ko/en × 두 페이지의 렌더 HTML과 실제 공용 CSS를 detect로 독립 검사하여 0건. |
| README 경로·갱신 책임·설계 판단 | 충족 | 법적 문서 절에 경로 및 운영자 갱신 책임, 갱신 트리거가 있다. 설계 판단 끝에 자기 번호 `### 09.` 추가, API 표 끝에 자기 경로 2행 추가. |

## 직접 실행한 검증

접속값은 구현 증거의 로컬 테스트 설정을 사용했고 이 문서에는 인증값을 기록하지 않는다.
`TEST_DATABASE_URL`은 기존 `chosung_daily_test_t09`, `TEST_REDIS_URL`은 로컬 Redis DB 11,
`TEST_MIGRATION_DATABASE_URL`은 기존 `chosung_daily_test_t09_migrations`를 지정했다.
새 DB 생성이나 기본 테스트 DB로의 전환은 하지 않았다.

| 명령/검사 | 결과 |
|---|---|
| 위 환경변수 지정 후 `uv run pytest -q` | `307 passed, 8 errors in 203.04s`. 오류 8개 모두 fixture의 `db.create_all()` 연결 단계에서 MySQL 1040 `Too many connections`. 다른 워커 테스트도 병렬 실행 중이었다. |
| 동일 환경에서 `uv run pytest -q --lf --tb=short` | `8 passed in 10.10s`, exit 0. 최초 오류 항목만 1회 재실행했으며 전체를 한 번에 315 passed로 재실행했다고 주장하지 않는다. |
| `uv run ruff check .` | `All checks passed!`, exit 0. |
| `FLASK_ENV=testing uv run flask --app wsgi db heads` | `4e72a4045fbc (head)` 1개. 이 티켓의 마이그레이션 변경은 없다. |
| `git diff main...HEAD --check` | exit 0. |
| Flask test client: `/privacy?lang=ko`, `/privacy?lang=en`, `/terms?lang=ko`, `/terms?lang=en` | 모두 200, Content-Language 및 본문 언어 일치. |
| 로컬 Chrome/Playwright, 768px, 4 URL × light/dark | CSS 로드 완료 후 light 배경/전경 `rgb(250,250,249)` / `rgb(15,23,42)`, dark `rgb(20,26,38)` / `rgb(241,245,249)`. 문서 외곽 폭은 모두 528px. |

### detect 재검증 방법과 한계

사용 바이너리: `/Users/saem/.impeccable/bin/0.1.14/impeccable`.
Flask test client로 4개 문서를 실제 렌더하고, `/tmp/t09-final-review/`의 임시 HTML에
`tokens.css`와 `legal.css` 원문을 순서대로 `<style>`에 넣었다. stylesheet 링크는 제거했다.
이는 Jinja 링크 해석 실패 및 외부 CDN 호출을 피하면서 실제 공용 CSS 기준으로 검사하기 위한 것이다.

```sh
/Users/saem/.impeccable/bin/0.1.14/impeccable detect /tmp/t09-final-review/privacy-ko.html /tmp/t09-final-review/privacy-en.html /tmp/t09-final-review/terms-ko.html /tmp/t09-final-review/terms-en.html
```

출력 없음, exit 0. 대조군 `detect .scratch/store-launch/design/archive/v2_softdark_home.html`은
7건, exit 2로 탐지 동작을 확인했다. 개발 서버는 loopback `127.0.0.1:5099`에만 띄웠고,
브라우저의 외부 요청은 차단했다. CDN 글꼴 다운로드와 외부 약관 링크의 도착지는 검증하지 않았다.
프로덕션·NAS·실제 외부 서비스에 접근하지 않았다.

## 결함 목록

### D-09-1 — MAJOR: 게스트 플레이를 국외 이전 거부 방법으로 잘못 안내

- 위치: `web/templates/legal/privacy.ko.html:108`, `web/templates/legal/privacy.en.html:115`.
- 재현 입력: `/privacy?lang=ko` 또는 `/privacy?lang=en`을 열고 4절의 거부 방법을 읽는다. 이어 스펙 §B.21 광고 게이트, §B.24 분석, §C.30 Sentry 및 티켓 24의 Analytics 이벤트 조건과 대조한다.
- 기대: 계정 연결을 하지 않아도 앱 광고·분석 및 오류 추적의 전송은 발생할 수 있음을 정확하게 구분한다. 계정 연결 여부만으로 전체 국외 이전을 거부할 수 있다고 안내하지 않는다.
- 실제: 두 언어 모두 계정을 연결하지 않고 게스트로 플레이하면 국외 이전을 피할 수 있다고 안내한다. 같은 방침의 광고 ID·제3자 절은 AdMob 직접 전송과 Analytics/Sentry 처리를 설명하며, 사양의 광고 게이트는 UMP 상태이지 계정 연결 여부가 아니다. 퍼즐 완료·공유 분석 이벤트도 연결된 계정에만 한정되지 않는다.
- 영향: 이용자가 실제로 전송을 중단하지 못하는 방법을 거부 절차로 믿게 된다. 법적 문서 티켓의 핵심 공시 내용에 대한 기능적 오류로, 법률 적합성 판단이나 문체 제안이 아니다. 기존 키워드 포함 테스트는 이 모순을 잡지 못한다.

### D-09-2 — MINOR: 지역 언어 태그가 있으면 낮은 q값의 언어를 선택

- 위치: `app/utils/ui_language.py:28`.
- 재현 명령(개발 서버 실행 후):

```sh
curl -s -D - -H 'Accept-Language: en-US,ko;q=0.1' http://127.0.0.1:5099/privacy
curl -s -D - -H 'Accept-Language: ko-KR,en;q=0.1' http://127.0.0.1:5099/terms
```

- 기대: 첫 요청은 영어, 둘째는 한국어. 구현은 지역 태그를 지원한다고 명시하고 ko/en 본문을 제공한다.
- 실제: 첫 요청은 `Content-Language: ko`, 둘째는 `en`이고 HTML 언어도 동일하게 뒤바뀐다. `resolve_ui_language(None, header)` 및 Flask test client로 직접 재현했다.
- 원인: 설치된 Werkzeug `LanguageAccept.best_match`는 완전 일치를 먼저 반환하고 완전 일치가 없을 때만 주 언어로 fallback한다. 따라서 지원 언어의 낮은 q값 완전 일치가 높은 q값 지역 태그보다 먼저 선택된다. 기존 테스트에는 지역 태그와 반대 언어의 낮은 q값을 조합한 사례가 없다. `?lang=`으로 우회 가능하다.

### D-09-3 — MINOR: 문서 외곽 폭과 모바일 패딩이 명시된 디자인 규칙을 벗어남

- 위치: `web/static/legal.css:20`.
- 재현 입력: 브라우저 viewport를 768px로 설정하고 네 법적 문서 URL 중 하나를 열어 stylesheet 로드를 기다린 뒤 다음 값을 읽는다.

```js
document.querySelector('.doc').getBoundingClientRect().width
getComputedStyle(document.querySelector('.doc')).boxSizing
```

- 기대: OVERRIDES §10 및 SCREENS 웹 절의 중앙 문서 최대 폭 480px.
- 실제: `528`, `content-box`. 내용 최대 폭 480px에 좌우 패딩 24px씩이 더해진다. ko/en × 두 페이지 × light/dark에서 모두 확인했다.
- 추가 재현: viewport 375px에서 computed padding은 24px이며 OVERRIDES §4의 모바일 패딩 16px와 다르다. 실제 전체 폭은 375px로 가로 넘침은 없었다.
- 영향: 읽기 기능은 유지되지만 필수 디자인 수치와 구현 증거의 “최대 480px·다르게 한 것 없음” 주장이 맞지 않는다. 취향에 따른 레이아웃 제안이 아니다.

## 보안·범위·테스트 품질 및 참고

- 새 라우트는 공개 GET 렌더만 수행한다. 계정 변경·삭제·DB 쓰기가 없으므로 새로운 CSRF 변경 경로는 없다. 사용자 `lang` 입력은 ko/en 허용 목록으로 제한되고 템플릿 경로로 그대로 들어가지 않는다. 인증 우회·입력 삽입·데이터 손상 변경은 발견하지 못했다.
- 변경 파일에서 운영 시크릿·실제 사용자 토큰 노출은 발견하지 못했다. 구현 증거의 접속 예시는 `.env.example`과 같은 로컬 개발용 자격 정보이며 운영자 메일은 의도된 공개 연락처다.
- 공용 파일의 다른 티켓 번호 절·행은 수정하지 않았다. `.env.example`, `docs/RELEASE.md`, `.scratch/` 변경 없음. 메인 페이지 스타일 변경 없음.
- `/account/delete`의 미구현은 티켓 14 소유이므로 이 티켓 결함으로 세지 않는다.
- 테스트는 실제 Jinja 응답을 검증하므로 전체가 항상 통과하는 가짜 테스트는 아니다. 다만 `test_privacy_states_backup_retention`의 단순 `"14"` 검사는 “under 14” 아동 문구만으로도 통과하고, 토큰 테스트는 OVERRIDES 파일 자체가 아니라 복사된 기대값을 비교한다. 현재 본문·토큰 값은 직접 대조했으며 이 검증 강도 한계는 별도 출시 차단 결함으로 중복 집계하지 않는다.
- 취향·스타일 제안 없음. 결함 집계: BLOCKER 0, MAJOR 1, MINOR 2. MAJOR 수정 후 재검토가 필요하다.

판정: FAIL
