# 오늘의 초성 / Hidden Vowels — 출시 수준 업그레이드 + 스토어 앱

**Status:** ready-for-agent
**Feature slug:** `store-launch`
**작성:** 2026-10-13, Phase 1 Planner (인터뷰 `/grill-me` → `/to-spec`). **r5** — 리뷰 라운드 1~3 + 확인 라운드 반영, Sol r5 재확인 통과(MAJOR 0). **plan-add r1(2026-10-14)**: 구현 중 사용자 요구 2건(법적 문서 법 기준 보완, 태블릿 레이아웃) 반영 — §A.15·§B.19·§B.21·US 15a·45a·미정 9·21~24, 티켓 16·24 추가(`review/plan-add-r1-response.md`). 응답: `review/spec-review-r1-response.md`, `review/spec-review-r2-response.md`, `review/spec-review-r3-response.md`, `review/spec-review-r4-response.md`
**관련 문서 (이 폴더):** `CONTEXT.md`(용어집) · `adr/0001~0003` · `design/SCREENS.md`(화면 명세) · `design/stitch/`(목업) · `design-system/hidden-vowels/OVERRIDES.md`(토큰, SCREENS 와 충돌 시 우선) · `design/TOOLS.md`
**DESIGN_DIR:** `.scratch/store-launch/design/` + `.scratch/store-launch/design-system/hidden-vowels/`
**BASELINE:** `~/Code/BuildUrPalace` (복사 목록 `~/.claude/baselines/buildurpalace.md`), 읽기만
**현행 API 의 정의:** 레포 `README.md` "API 목록" 표 + `app/schemas/*.py` 가 "기존" 필드의 기준. 모든 API 는 `/api/v1` prefix (웹 페이지 라우트 `/`, `/privacy`, `/terms`, `/account/delete`, `/admin/*` 제외).

용어는 `CONTEXT.md` 를 따른다.

---

## Problem Statement

chosung.dosaem.com 은 "하루 한 문제 초성 맞추기"가 돌아가는 Flask 웹 서비스지만, 포트폴리오 수준에 머물러 있다.
플레이어 입장에서는: 한국어만 되고, 디자인이 투박하고, 다크모드·오프라인·로딩 상태가 없고, 앱이 없어서 알림도 없고, 기기를 바꾸면 기록을 잃기 쉽다(백업 코드를 알아야 함).
운영자(프로젝트 주인) 입장에서는: 수익이 0원이고(광고·구독 없음), 단어가 20개뿐이라 몇 주면 바닥나며 채우려면 SSH 로 CLI 를 쳐야 하고, 장애·백업·에러 추적이 없어서 죽어도 모르며, 배포가 수동이고, 개인정보처리방침·약관·계정 삭제가 없어서 스토어 심사를 통과할 수 없다.

## Solution

같은 Flask 백엔드를 "돈을 벌 수 있는 서비스" 수준으로 올리고, 그 위에 iOS/Android 스토어 앱(Flutter)을 얹는다.

- **플레이어**: 한국어(초성)·영어(자음 뼈대) 두 퍼즐 언어 중 고르고, 웹에서는 광고 없이 끝까지 플레이한 뒤 앱 설치를 권유받고, 앱에서는 배너·전면·보상형 광고를 보거나 월 광고 제거 구독(스토어 현지화 가격, 한국 ₩1,500)을 하며, 매일 로컬 알림을 받고, 구글/애플 계정(또는 백업 코드)으로 어느 기기에서든 같은 기록을 잇고, 언제든 계정과 기록을 삭제할 수 있다(앱·웹). 다크모드·로딩·오프라인·점검 상태가 전부 설계된 Editorial Light 디자인을 본다.
- **운영자**: 구글 로그인으로 관리자 페이지에 들어가 LLM 으로 만든 CSV 를 올리고 30일치 퍼즐을 미리 보고 바꾸며, 단어 잔량·배정 실패·백업 실패를 Slack 으로 받는다. Sentry·업타임 모니터·매일 백업·GitHub Actions 자동 배포(develop/main)·develop 인스턴스가 갖춰진다.
- **면접 설명 책임**: 백엔드는 모든 코드를 직접 설명한다(과한 추상화 금지, 설계 판단은 README "설계 판단" 절에 근거와 함께, 서비스 함수 하나 = 커밋 하나, 외부 호출 래퍼와 **도메인 판정 함수**는 분리). Flutter 는 **상태 흐름(Riverpod)·SDK 선택 이유·테스트 경계**까지는 설명할 수 있어야 하고 그 이상(위젯 세부)은 의무가 아니다. README 에 Flutter 절을 짧게 둔다.

## User Stories

### 플레이 (웹·앱 공통)
1. As a 게스트, I want 오늘의 퍼즐을 내가 고른 퍼즐 언어(ko/en)로 받고 싶다, so that 한국어를 모르는 사람도 매일 플레이할 수 있다.
2. As a 게스트, I want 영어 퍼즐에서 모음이 빈 타일로 가려진 자음 뼈대(`_PPL_`)를 보고 싶다, so that 초성과 같은 감각으로 단어를 추리할 수 있다.
3. As a 게스트, I want 글자별 🟩/⬜ 피드백을 색뿐 아니라 아이콘·굵기로도 구분하고 싶다, so that 색각 이상이 있어도 결과를 읽을 수 있다.
3a. As a 게스트, I want 앱을 껐다 켜거나 다른 기기에서 열어도 오늘 제출한 시도 행이 그대로 보이길 원한다, so that 기록이 서버에 있다는 걸 믿는다.
3b. As a 게스트, I want 내가 보고 있던 퍼즐이 바뀐 경우(자정 경과, 다른 기기에서 언어 변경) 제출이 엉뚱한 문제에 들어가지 않고 "새 퍼즐이 있어요" 로 새로고침되길 원한다, so that 시도를 억울하게 잃지 않는다.
4. As a 게스트, I want 3번째 오답 전에도 광고를 보고 힌트를 미리 열고 싶다(앱), so that 막혔을 때 시도를 아끼고 계속할 수 있다.
5. As a 게스트, I want 힌트 미리 보기가 내 시도 횟수와 순위에 영향을 주지 않기를 원한다, so that 광고를 본 사람이 불리하거나 유리해지지 않는다.
5a. As a 게스트, I want 힌트를 한 번 열었으면 재진입해도 계속 보이길 원한다, so that 광고를 다시 볼 필요가 없다.
6. As a 게스트, I want 퍼즐이 KST 자정에 바뀐다는 것과 남은 시간을 화면에서 보고 싶다, so that 해외에서도 언제 새 문제가 나오는지 안다. (ADR 0001)
7. As a 게스트, I want 자정 직후 퍼즐이 아직 없을 때 카운트다운과 재시도 버튼을 보고 싶다, so that 빈 화면이나 에러로 혼란스럽지 않다.
8. As a 게스트, I want 로딩 중엔 스켈레톤을, 네트워크 오류엔 인라인 재시도를, 오프라인엔 상단 배너를 보고 싶다, so that 지금 무슨 상태인지 늘 안다.
9. As a 게스트, I want 결과 화면에서 시도 횟수별 정답자 분포와 내 위치를 보고 싶다, so that 오늘 문제의 난이도를 체감한다.
10. As a 게스트, I want 결과를 네이티브 공유 시트(앱)/클립보드(웹)로 공유하고 싶다, so that 친구에게 자랑하거나 도전하게 한다.
11. As a 게스트, I want 공유 텍스트에 웹 링크가 붙기를 원한다, so that 받은 사람이 바로 플레이할 수 있다.
12. As a 게스트, I want 오늘의 리더보드를 퍼즐 언어별로 보고 싶다, so that 같은 문제를 푼 사람들과만 비교된다.
13. As a 게스트, I want 리더보드에서 모든 사람이 "게스트 #xxxx"(내 행만 강조)로 보이길 원한다, so that 누구의 이메일도 노출되지 않는다.
14. As a 게스트, I want 연속 기록이 퍼즐 언어와 무관하게 "그 날 하나라도 맞추면" 이어지길 원한다, so that 언어를 바꿔도 streak 이 끊기지 않는다.
15. As a 게스트, I want 다크모드가 기기 설정을 따르길 원한다, so that 밤에 눈이 아프지 않다.
15a. As a 태블릿(iPad·Android) 사용자, I want 폰 화면을 가운데 띄운 게 아니라 왼쪽 rail 과 넓은 표·2열로 보길 원한다, so that 가로로 든 iPad 에서도 한 화면이 자연스럽다.
16. As a 게스트, I want UI 문구가 기기 언어(ko/en)로 나오길 원한다, so that 영어권에서도 앱을 이해한다.
16a. As a 게스트, I want 최근 7일의 성공/실패/진행 중/미플레이를 내 기록에서 보고 싶다, so that 한 주 흐름을 한눈에 본다.
16b. As a 게스트, I want 리더보드에 21위 밖이어도 내 순위가 보이길 원한다, so that 내 위치를 안다.

### 계정
17. As a 게스트, I want 웹에서 구글/애플 로그인으로 계정을 연결하고 싶다(현행), so that 다른 기기에서도 같은 기록을 본다.
18. As a 게스트, I want 앱에서 네이티브 로그인 버튼(iOS: 구글·애플, Android: 구글)으로 계정을 연결하고 싶다, so that 브라우저를 오가지 않고 연결된다. (ADR 0002)
18a. As a 애플 계정으로 연결한 게스트, I want Android 앱에서 백업 코드(웹 "내 기록 백업")를 입력해 내 기록으로 전환하고 싶다, so that Android 에 애플 로그인이 없어도 기기를 옮긴다.
19. As a 게스트, I want 이미 연결된 계정으로 새 기기에서 로그인하면 그 기록으로 전환되길 원한다, so that 기기 교체가 자연스럽다.
20. As a 게스트, I want 첫 완료 후 "기록을 지키려면 연결하세요" 안내를 한 번만 보고 싶다, so that 귀찮지 않으면서도 기록을 잃지 않는다.
21. As a 게스트, I want 앱 설정 **또는 웹 `/account/delete`** 에서 계정과 모든 기록을 삭제할 수 있길 원한다, so that 내 데이터를 내가 통제한다 (애플·Play 심사 필수).
22. As a 게스트, I want 계정 삭제가 확인 다이얼로그를 거치고 되돌릴 수 없음과 "구독은 스토어에서 따로 해지" 를 알려주길 원한다, so that 실수로 지우거나 결제가 계속되는 일이 없다.
22a. As a 애플 계정 게스트, I want 계정을 삭제하면 애플 쪽 연결(Sign in with Apple)도 실제로 철회되길 원한다, so that 애플 설정에 유령 앱이 남지 않는다.

### 수익화 (앱)
23. As a 게스트, I want 게임 화면 하단에 배너 광고 공간이 항상 예약돼 있길 원한다, so that 광고가 뜨면서 화면이 튀지 않는다.
24. As a 게스트, I want 전면 광고가 결과 확인 **후** 퍼즐당 최대 1회만 뜨길 원한다, so that 플레이를 방해받지 않는다.
25. As a 게스트, I want 첫 제출 전엔 절대 전면 광고가 안 뜨길 원한다, so that 앱을 켜자마자 광고로 시작하지 않는다.
26. As a 게스트, I want 월 자동갱신 구독으로 모든 광고를 끄고 싶다(가격은 스토어가 내 나라 통화로 보여줌), so that 집중해서 플레이한다.
27. As a 게스트, I want 구독이 내 게스트(계정)에 귀속돼 다른 기기에서도 광고가 꺼지길 원한다, so that 기기마다 다시 사지 않는다. (ADR 0003)
28. As a 게스트, I want 구독 화면에서 "구매 복원"을 누를 수 있길 원한다, so that 재설치 후에도 권한을 되찾는다 (애플 필수).
29. As a 게스트, I want 구독 화면에 약관·개인정보처리방침 링크와 자동 갱신 안내가 있길 원한다, so that 조건을 알고 결제한다 (애플 필수).
30. As a 게스트, I want 구독을 해지해도 만료일까지는 광고가 없길 원한다, so that 낸 돈만큼 쓴다.
30a. As a 구독자, I want 자동 갱신 직후에도 광고가 켜지지 않길 원한다, so that 돈을 냈는데 광고를 보는 일이 없다.
30b. As a 결제 실패 구독자, I want 스토어 유예 기간(Billing Grace Period) 동안은 광고가 없길 원한다, so that 카드만 바꾸면 끊김 없이 이어진다.
30c. As an 운영자, I want 환불(철회)을 서버가 **확인하는 즉시** 권한이 사라지고, 앱을 쓰고 있는 구독자라면 **최대 1시간** 안에 확인되길 원한다, so that 환불 후 무료 이용이 길어지지 않는다 (실시간 반영은 웹훅 범위 — 미정 1).
30d. As a 게스트, I want 결제 중 앱이 죽거나 네트워크가 끊겨도 다시 열면 구매가 마무리되길 원한다, so that 돈만 나가고 권한이 없는 일이 없다.
31. As a 구독자, I want 배너 영역 자체가 사라지고 콘텐츠가 그 자리를 채우길 원한다, so that 구독한 보람이 보인다.
32. As a 구독자, I want 힌트 미리 보기를 광고 없이 쓰길 원한다, so that 구독 혜택이 하나 더 있다.
33. As an iOS 게스트, I want 광고 전에 ATT(앱 추적 투명성) 안내와 시스템 프롬프트를 보길 원한다, so that 맞춤 광고 여부를 내가 정한다.
34. As an EEA 게스트, I want UMP 동의 폼을 보고 나중에 설정에서 선택을 바꾸길 원한다, so that GDPR 에 맞게 광고 동의를 통제한다.
34a. As an App Review 심사자, I want 프로덕션 빌드에서 Sandbox 계정으로 구독을 사서 광고가 꺼지는 걸 보고 싶다, so that 심사에서 IAP 를 통과시킨다.

### 알림 (앱)
35. As a 게스트, I want 온보딩에서 알림 권한을 사전 안내 뒤에 요청받길 원한다, so that 왜 필요한지 알고 허용한다.
36. As a 게스트, I want 매일 내가 고른 로컬 시각(기본 09:00)에 "오늘 퍼즐 풀었어요?" 알림을 받고 싶다, so that 하루도 빼먹지 않는다.
37. As a 게스트, I want 그 날(KST 퍼즐 날짜) 아직 안 풀었으면 로컬 20:00 에 리마인더를 한 번 더 받고 싶다, so that 연속 기록을 지킨다.
38. As a 게스트, I want 이 기기에서 이미 푼 퍼즐의 리마인더는 안 오고 다음 퍼즐의 리마인더는 그대로 오길 원한다, so that 불필요한 알림도 없고 빠지는 알림도 없다.
39. As a 게스트, I want 설정에서 알림 시각 변경과 리마인더 on/off 를 하고 싶다, so that 내 생활에 맞춘다.
39a. As a 알림을 거부한 게스트, I want 설정에서 "알림 꺼짐 — 시스템 설정에서 켜기" 를 보길 원한다, so that 왜 안 오는지 안다.
40. As a 게스트, I want 알림을 탭하면 (앱이 꺼져 있었든 뒤에 있었든) 바로 오늘 퍼즐 화면으로 가고 최신 퍼즐이 로드되길 원한다, so that 한 번에 플레이한다.

### 웹 → 앱
41. As a 웹 방문자, I want 웹에서 광고 없이 끝까지 플레이하고 싶다, so that 공유 링크로 들어와도 바로 즐긴다.
42. As a 웹 방문자, I want 결과 화면에서 App Store / Google Play 배지와 "앱에서 연속 기록·알림" 안내를 보고 싶다, so that 앱을 설치할 이유를 안다.
43. As an iOS Safari 방문자, I want Smart App Banner 를 보고 싶다, so that 한 번에 앱으로 간다.
44. As a 웹 방문자, I want 모든 화면 폭에서 중앙 정렬 카드(최대 480px)로 보길 원한다, so that 데스크톱·태블릿에서도 깨지지 않는다.
45. As a 웹 방문자, I want `/privacy`, `/terms`, `/account/delete` 를 같은 도메인에서 쓰고 싶다, so that 앱·스토어·구독 화면·Data safety 양식의 링크가 한 곳을 가리킨다.
45a. As a 게스트, I want 개인정보처리방침·이용약관이 한국 법(개인정보 보호법·전자상거래법)과 스토어 구독 정책이 요구하는 항목을 빠짐없이 담길 원한다, so that 내 권리와 환불·해지 조건을 문서에서 확인할 수 있다.

### 온보딩·설정·운영 상태 (앱)
46. As a 첫 실행 게스트, I want 3장 온보딩(하루 한 문제 / 5번의 기회 / 매일 이어가기)과 언어 선택 칩을 보고 싶다, so that 규칙을 알고 시작한다.
47. As a 게스트, I want 설정에서 온보딩("하는 법")을 다시 보고 싶다, so that 규칙을 잊어도 된다.
48. As a 게스트, I want 설정에서 퍼즐 언어·알림·구독 관리·광고 개인정보 설정(필요한 지역)·계정·백업 코드·법적 문서·오픈소스 라이선스·버전을 한 곳에서 보고 싶다, so that 헤매지 않는다.
49. As a 게스트, I want 서버가 점검 중이면 점검 화면을, 앱이 너무 오래됐으면 업데이트 화면을 보고 싶다, so that 깨진 상태로 플레이하지 않는다.

### 운영자
50. As an 운영자, I want 구글 로그인 + 허용 이메일(`dosaem90@gmail.com`, `hsseo@dosaem.com`)로만 관리자 페이지에 들어가고 싶다, so that 별도 비밀번호 없이 안전하다.
51. As an 운영자, I want 언어·카테고리·정답·힌트 열이 있는 CSV 를 업로드하고 싶다, so that LLM 으로 만든 단어를 한 번에 넣는다.
52. As an 운영자, I want 업로드 결과(추가/중복/오류 행)를 바로 보고 싶다, so that 잘못된 행을 고친다.
53. As an 운영자, I want 단어를 검색·수정·삭제하고 싶다, so that 오타나 부적절한 단어를 고친다.
54. As an 운영자, I want 언어별 다음 30일 퍼즐 배정표를 보고 특정 날짜의 단어를 바꾸고 싶다, so that 기념일·주말에 맞는 문제를 낸다.
55. As an 운영자, I want 언어별 단어 풀 잔량(며칠치)을 보고 싶다, so that 떨어지기 전에 채운다.
56. As an 운영자, I want 잔량이 14일치 미만이면 Slack 으로 알림받고 싶다, so that 자정에 퍼즐이 비는 사고를 막는다.
57. As an 운영자, I want 자정 배정 실패(언어별)·백업 실패·헬스체크 실패·애플 secret 만료 임박을 Slack 으로 받고 싶다, so that 장애를 유저보다 먼저 안다.
58. As an 운영자, I want 영어 책 제목을 Google Books 로 검색해서 단어로 추가하고 싶다, so that 영어 일요일 라운드도 채운다.
59. As an 운영자, I want 서버 설정으로 점검 모드와 최소 앱 버전을 켜고 싶다, so that 마이그레이션 중 앱을 막는다.
60. As an 운영자, I want 서버·워커·앱 에러를 Sentry 에서 보고 싶다, so that 재현 없이 원인을 안다.
61. As an 운영자, I want DAU·리텐션·퍼널을 Firebase Analytics 에서 보고 싶다, so that 광고 수익과 행동을 연결한다.
62. As an 운영자, I want MySQL 이 매일 04:00 KST 백업되고 14일 보존되길 원한다, so that 데이터 사고에서 복구한다.
63. As an 운영자, I want 복구 절차 문서와 로컬 리허설 스크립트가 있길 원한다, so that 백업이 진짜 복구되는지 안다.
64. As an 운영자, I want `main` 푸시가 NAS prod 에, `develop` 푸시가 NAS develop 에 자동 배포되길 원한다, so that SSH 로 손 배포를 안 한다.
65. As an 운영자, I want develop 인스턴스가 prod 와 같은 NAS 에서 이름·포트·볼륨이 분리돼 **동시에** 돌길 원한다, so that 새 버전을 프로덕션 DB 없이 테스트한다.
66. As an 운영자, I want 앱이 `develop` 푸시에 Firebase App Distribution + TestFlight, `main` 푸시에 Play internal + TestFlight 로 올라가길 원한다, so that BuildUrPalace 와 같은 방식으로 배포한다.
67. As an 운영자, I want 스토어 메타데이터·스크린샷 자산이 레포에 있고 워크플로로 업로드되길 원한다, so that 심사 제출이 반복 가능하다.
68. As an 운영자, I want 애플 client_secret JWT 가 만료되기 전에 자동 재발급되길 원한다, so that 150일 뒤 애플 로그인이 조용히 죽지 않는다.
69. As an 운영자, I want 백엔드 린트(ruff 엄격)와 Flutter 린트(`very_good_analysis`)가 CI 에서 돌길 원한다, so that AI 가 짠 코드 품질을 기계로 거른다.
70. As an 운영자(면접자), I want 모든 백엔드 설계 판단이 README "설계 판단" 절에 근거와 함께 남길 원한다, so that 면접에서 직접 설명한다.

## Implementation Decisions

### A. 도메인·데이터 (백엔드)

1. **퍼즐 언어 도입 (마이그레이션 1개 + 서비스 언어 인지화).** 단어에 `language`(ko/en), 오늘의 퍼즐은 **(날짜, 언어) 당 하나**(유니크 `(puzzle_date, language)`). 게스트는 `puzzle_language` 선호(기본 ko; `POST /guests {puzzle_language}` 로 생성 시 초기화, `PATCH /me` 로 변경). 언어가 들어가는 키: 퍼즐 캐시 `puzzle:{date}:{lang}`, 통계 `stats:{date}:{lang}`, 리더보드 `lb:{date}:{lang}`, DailyStats 키. **rate limit 키에는 언어 없음.** 기존 행은 마이그레이션에서 `ko`. expand–contract 3단계 대신 **마이그레이션 1개 + 코드 변경 1회**(트래픽이 운영자뿐). 완료 조건: 기존 테스트가 ko 기본값으로 통과(리더보드 응답 필드 변경에 맞춘 테스트 수정은 허용) **그리고** 신규: 같은 날 ko/en 두 퍼즐 공존·조회/캐시 분리·마이그레이션 전후 ko 데이터 보존.
   - 자정 배정은 **언어별 각각 호출·각각 커밋**. 한 언어 실패는 Slack 알림 후 다음 언어 진행.
   - 티켓 분할 지침: §A.1 은 "마이그레이션+모델" / "서비스·API 언어 인지화" / "자정 배정·캐시" 로 나눈다(한 세션 초과 위험).
2. **가림(mask)·제출 일관성.** ko = 초성 추출(현행), en = 모음(a,e,i,o,u) 빈칸. 포맷 `mask: [{t: "r"|"h"|"s", c}]` (`r` 보임, `h` 빈 타일, `s` 구분자=공백·하이픈, 타일 사이 간격). `length` = `s` 제외 글자 수. 정답 비교는 `s` 제거 글자열끼리, 영어는 대소문자 무시, guess 의 공백·하이픈 제거 후 길이 검증. `feedback` 은 `s` 제외 위치 1:1. 가림은 단어 저장 시 계산(`chosung` 컬럼 → `mask` 일반화; 응답 `chosung` 은 ko 호환용으로 유지, 신규 클라이언트는 `mask`).
   - **퍼즐 고정**: 읽기 응답(`GET /puzzles/today`)에 `puzzle_id` 가 들어가고, **쓰기 요청(제출·힌트 미리 보기)은 `puzzle_id` 를 반드시 보낸다.** 서버는 그 ID 가 "요청 시점 오늘(KST) × 게스트 현재 언어" 의 퍼즐과 다르면 **시도를 소비하지 않고 409 `PUZZLE_CHANGED`** 를 돌려주고, 클라이언트는 `GET /puzzles/today` 로 새로고침해 "새 퍼즐이 있어요" 를 띄운다. 통계·리더보드 조회는 `?language=` 를 명시(기본 게스트 선호).
   - **시도 이력 복원**: `GET /puzzles/today` 가 순서 있는 `attempts: [{guess, feedback}]` 를 돌려준다. 웹·앱은 로컬 저장 이력을 버리고 서버 이력으로 보드를 그린다(언어 변경·계정 전환 시 로컬 상태 폐기). 완료 조건: 시도 후 새 클라이언트로 조회해 같은 보드.
   - **힌트 표시 규칙**: `hint` 는 `show_hint(3번째 오답 후) OR hint_unlocked` 일 때 채운다 — `GET /puzzles/today` 와 `POST guesses` 응답 둘 다.
3. **"오늘"은 KST 고정** (ADR 0001).
4. **연속 기록은 언어 무관.** `_record_solve`: `last_solved_date == today` 면 no-op, `== yesterday` 면 +1, 그 외 1. `solved_count` = 퍼즐 수.
5. **힌트 미리 보기.** `HintUnlock(guest_id, puzzle_id, unlocked_at, PK(guest_id, puzzle_id))`. `POST /puzzles/today/hint-unlock {puzzle_id}` → `GuestStats FOR UPDATE` 경로 → 행 삽입 → `{hint}`. 끝난 퍼즐 409 `ALREADY_FINISHED`, 이미 열림 409 `HINT_ALREADY_UNLOCKED`. AdMob SSV 없음(README 근거). 구독자는 광고 없이 호출.
6. **앱 로그인 = id_token 교환** (ADR 0002). `POST /auth/token-exchange {provider, id_token, authorization_code?}` (Bearer) → JWKS 검증 → `link_or_switch_account` → `{token}`. **provider × 플랫폼**:

   | provider | 플랫폼 | 앱 설정 | 서버 `aud` | 비고 |
   |---|---|---|---|---|
   | google | iOS | iOS 클라이언트 ID | iOS 클라이언트 ID | |
   | google | Android | `serverClientId` = 웹 클라이언트 ID | 웹 클라이언트 ID | Android 클라이언트 ID 는 SHA-1 검증용 |
   | apple | iOS | `sign_in_with_apple` | 번들 ID | **`authorization_code` 도 함께 보낸다** (§A.7 revoke 용) |
   | apple | Android | 지원 안 함 | — | Out of Scope. Android 는 백업 코드로 전환(US 18a) |

   **애플 토큰 보관**: 서버가 `authorization_code` 를 Apple 토큰 엔드포인트에서 교환(client_id = iOS 는 번들 ID, 웹은 Services ID; client_secret = 각각의 JWT)해 `refresh_token` 을 `Account.provider_refresh_token`(SECRET_KEY 파생 키로 Fernet 암호화) 에 저장하고, **발급 client 를 `Account.provider_client_id` 에 함께 저장**한다(iOS 번들 ID 또는 Services ID). 웹 콜백도 `authorize_access_token` 결과의 `refresh_token` 과 Services ID 를 같은 컬럼들에 저장(현행 코드 변경). 같은 애플 계정으로 다시 로그인·전환(`existing` 경로)하면 두 컬럼을 새 값으로 **덮어쓴다**. 교환으로 받은 id_token 의 `sub` 가 앱이 보낸 id_token 의 `sub` 와 같은지 확인한다.
7. **계정 삭제.** `DELETE /me`(Bearer) 와 웹 `POST /account/delete`(세션 + **CSRF 토큰**: 세션에 심은 1회용 토큰을 폼 hidden 으로 받아 검증, 불일치 403 `FORBIDDEN`; GET 은 절대 삭제하지 않음). 같은 서비스 함수: Attempt, GuestStats, Account, HintUnlock, Subscription, 오늘 리더보드 `ZREM`, Guest 삭제 — 한 커밋. 삭제 후 토큰 401. **애플 revoke**: 저장된 `refresh_token` 과 **`provider_client_id` 에 맞는 client_id·client_secret** 으로 Apple revoke 호출(US 22a; iOS 연결은 번들 ID, 웹 연결은 Services ID). 실패하면 삭제는 진행하되 `AppleRevocationRetry(refresh_token_enc, client_id, created_at)` 에 남기고 Beat 가 매일 재시도, 7일 후 폐기. 웹 삭제 후 프론트는 localStorage 토큰을 버리고 새 게스트를 발급한다(웹 티켓 완료 조건). 로그인 안 된 브라우저는 안내 + 운영자 메일. 이 URL = Play Data safety 삭제 URL.
8. **구독** (ADR 0003). 테이블 `Subscription(guest_id, store apple|google, store_key, product_id, environment Sandbox|Production, status, expires_at, grace_expires_at, last_verified_at, unique(store, store_key))` — `store_key` = Apple `originalTransactionId` / Google `purchaseToken`(Google 은 `linkedPurchaseToken` 이 오면 옛 행을 `replaced` 로 표시하고 새 행 생성).
   - **상태 정규화** `status ∈ {active, grace, hold, expired, revoked, replaced}`. 매핑: Apple 1 Active→active, 4 Billing Grace Period→grace(+`gracePeriodExpiresDate`→`grace_expires_at`), 3 Billing Retry→hold, 2 Expired→expired, 5 Revoked→revoked. Google ACTIVE/CANCELED(미만료)→active, IN_GRACE_PERIOD→grace, ON_HOLD→hold, EXPIRED→expired, 환불/revoked→revoked.
   - **구독 권한(순수 함수, 판정표)**: `revoked|hold|expired|replaced` → 없음. `grace` → `grace_expires_at > now`. `active` → `expires_at + 24h > now` (24h 는 "갱신됐는데 서버가 아직 모름" 만 흡수; 확인된 revoked/hold 에는 적용 안 함). pending 구매는 권한 없음.
   - **재조회**: (a) `/me/stats` 호출 시 `status ∈ {active, grace, hold}` 인 구독은 **`last_verified_at` 이 1시간보다 오래됐으면 만료 구간과 무관하게** 스토어 재조회(만료 ±24h 안이면 1시간 상한 없이 재조회); 타임아웃 3초, 실패 시 저장값 유지. 응답 `entitlement.next_check_at` = `last_verified_at + 1h`. **앱은 시작·포그라운드 복귀 때 `/me/stats` 를 부르고, 포그라운드에 머무는 동안 `next_check_at` 에 맞춰 타이머로 `/me/stats` 를 다시 불러 `entitlement` 를 광고 상태에 즉시 반영한다**(권한 사라지면 배너 슬롯 복구·전면 광고 재개). 백그라운드에서는 타이머를 멈추고 복귀 때 즉시 호출. 그래서 포그라운드 세션에서 철회 감지 지연은 최대 1시간 + 타이머 오차다. 철회가 확인되면 그 응답부터 권한 없음. (b) 앱은 시작·포그라운드 복귀 때 스토어 구매 동기화(`restorePurchases`/`queryPurchases`)로 받은 영수증을 `POST /subscriptions/verify` 로 다시 보낸다 — ±24h 밖에서 복구된 결제도 이 경로로 즉시 반영. (c) Beat 매일: `active|grace|hold` 중 만료 3일 이내 재조회. 웹훅은 미정.
   - **검증·완료 순서(앱 ↔ 서버)**: 구매 스트림 수신 → (pending 이면 대기) → `POST /subscriptions/verify {store, receipt}` (서버는 `store_key` 로 멱등; 상품 ID·번들/패키지 확인; 공식 라이브러리로 검증; Sandbox: JWS `environment` 로 엔드포인트 선택, Production 4040010 → Sandbox 1회) → 서버 성공 응답(entitlement) 후에만 `completePurchase`(iOS finish / Android acknowledge). 실패·앱 종료 시 다음 시작에서 미완료 구매를 다시 올린다(Play 3일 내 acknowledge 미완 자동 환불 방지).
   - 복원/전환 시 같은 `store_key` 는 현재 게스트로 재지정. 표시 가격은 스토어 상품의 **현지화 가격**(`ProductDetails.price`)을 쓰고 ₩1,500 은 한국 Tier 설정값일 뿐 상수로 박지 않는다.
   - 티켓 분할 지침: "DB·검증 엔드포인트" / "권한 판정·재조회·Beat" / "Flutter 구매 흐름(스트림·완료·복원)" / "Sandbox 수동 검증 체크리스트" 로 나눈다.
9. **알림 = 앱 로컬 알림, 서버 변경 없음.** `flutter_local_notifications` + `timezone`. 규칙:
   - **일일 알림** = 반복 예약 1개(ID 고정, 로컬 `HH:mm`, 기본 09:00, "오늘 퍼즐 풀었어요?", `matchDateTimeComponents: time`).
   - **리마인더** = **앞으로 7일치 1회성 예약**(ID = 날짜 기반 고정, 로컬 20:00, "아직 안 풀었어요 — 연속 기록을 지켜요", `matchDateTimeComponents` 없음). iOS 의 `time` 반복 트리거는 날짜를 버려서 "내일부터" 가 성립하지 않으므로 반복 예약을 쓰지 않는다. 대기 알림 최대 8개(64개 상한 무관). 7일 넘게 앱을 안 열면 리마인더가 멈추는 건 감수.
   - **예약 계획 = 순수 함수**: 입력(지금, 설정, 완료한 KST 퍼즐 날짜 집합, 기기 시간대) → 출력 "원하는 (id, 발화 시각) 집합". 앱 시작·포그라운드 복귀·퍼즐 완료·알림 탭·설정 변경 때마다 다시 계산해 OS 대기 목록과 diff(취소/추가). 복귀 시 기기 시간대를 다시 읽어 재계산한다.
   - **취소 규칙(KST 기준)**: 퍼즐 완료(정답 또는 5회 소진) 시 "발화 시각이 속한 **KST 날짜** == 방금 끝낸 `puzzle_date`" 인 리마인더만 집합에서 뺀다. 다른 날짜(이미 새 KST 퍼즐 대상)는 그대로. 두 언어 중 하나만 완료해도 그 날짜는 제외(streak 과 동일 기준).
   - 일일 알림과 리마인더 시각이 같으면 일일 알림만. 시간대·DST 변경은 `timezone` 로컬 존으로 자동. 권한 거부 시 S4 에 "알림 꺼짐 — 시스템 설정에서 켜기"(US 39a).
   - Android: `AndroidScheduleMode.inexactAllowWhileIdle`, **exact alarm 권한 매니페스트에 넣지 않음**(Play 정책), Android 13+ `POST_NOTIFICATIONS` 는 S6 3장 사전 안내 뒤 요청.
   - 탭: 실행 중 `onDidReceiveNotificationResponse`, 종료 상태 `getNotificationAppLaunchDetails` → 둘 다 `go_router` 로 오늘 탭 + `GET /puzzles/today` 재조회.
   - 단위 테스트(순수 함수): 오늘 제외·내일 유지, 미주 유저 KST 경계, 두 언어 중 하나 완료, 7일 롤링 보충, 대기 ≤8. **실기기 체크(iOS·Android 각각)**: 정답 후 같은 날 20:00 에 리마인더 없음, 다음 날 20:00 에 있음, 앱 종료 상태에서도 동일. README 에 "서버 푸시 대신 로컬 알림" 근거.
10. **앱 설정** `GET /config`: 최소 앱 버전, 점검 플래그·메시지, 지원 언어, 스토어 링크. DB 설정 행(관리자 토글).
11. **운영자.** `ADMIN_EMAILS`(정확히 `dosaem90@gmail.com`, `hsseo@dosaem.com`). 기존 구글 OAuth 세션의 연결 이메일로 판정, **CSRF 토큰**(§A.7 과 같은 메커니즘). Jinja. 기능: 단어 CRUD/검색, CSV 업로드(`language,category,answer,hint`), 언어별 30일 배정표+교체(캐시 무효화), 잔량, 점검·최소 버전 토글, Google Books 검색 추가. 티켓 분할: "운영자 인증+단어 CRUD+CSV" / "배정표·잔량·토글·Books".
12. **운영자 알림 = Slack Webhook.** 잔량 14일 미만(언어별), 언어별 배정 실패, 백업 실패, 구독 재조회 실패 누적, 애플 secret 만료 7일 전, Apple revoke 재시도 7일 초과 폐기.
13. **애플 client_secret 갱신은 요청 경로에서.** `/auth/apple/login` **과 `/auth/apple/callback`** 진입 시 접근자가 "<7일 남음이면 재서명 후 Authlib 클라이언트 `client_secret` 교체"(gunicorn 워커가 늘어도 각 프로세스가 스스로 갱신). `/health` 가 `apple_secret_expires_at` 노출, Beat 주 1회 7일 전 Slack 알림만.
14. **영어 책 제목 검색** = Google Books API, 카카오와 같은 서비스 함수 시그니처. 가림은 §A.2.
15. **법적 문서·계정 삭제 페이지** `/privacy`, `/terms`, `/account/delete`(ko/en). 개인정보처리방침 포함: 수집 항목(게스트 토큰, 계정 이메일, 애플 refresh token, 시도 기록, 구독 식별자, 광고 ID), 보유 기간, 제3자 제공·위탁(Google, Apple, AdMob, Firebase Analytics, Sentry), 국외 이전, 만 14세 미만, 삭제 방법, 연락처. **(plan-add r1)** 위 목록은 최소 집합이다. 법 기준 필수 기재사항 — 개인정보 보호법 제30조(처리방침 필수 항목)·제28조의8(국외 이전 고지)·제31조(보호책임자), 전자상거래법 제10조·제13조(사업자 신원·거래조건·청약철회), Apple 3.1.2(a)·Google Play 구독 고지 — 는 티켓 16 의 `docs/legal-checklist.md` 가 조문→문서 절 표로 지키고 테스트가 ko/en 양쪽 존재를 확인한다. 사업자 정보는 설정값(`LEGAL_*`)으로만 들어가고 코드 기본값이 없다. 자택 주소·전화번호·보호책임자 성명의 공개 범위는 미정 21(사용자 확인).
16. **웹 프론트.** Jinja 1장 + vanilla JS. 토큰 CSS 변수, 다크모드, 퍼즐 언어 칩(`PATCH /me` 후 재조회), UI 문자열 ko/en, 서버 `attempts` 로 보드 복원(로컬 history 제거), `puzzle_id` 동봉·409 시 새로고침, 스켈레톤/오프라인/퍼즐 없음, 앱 CTA + Smart App Banner, 공유 `?utm_source=share`, `/account/delete` 링크, 백업 코드 유지.
17. **백엔드 원칙.** 레이어 그대로, 서비스 함수 하나 = 커밋 하나, 외부 provider 마다 `clients/<provider>.py`(JWKS, Apple 토큰/revoke, App Store, Play, Slack, Google Books) — **외부 호출 래퍼(함수 하나)** 와 **도메인 판정 함수(구독 상태 매핑·권한 판정표, 알림 예약 계획 등 순수 함수)** 를 분리해 후자를 테스트·설명 대상으로 삼는다. 스토어 검증은 공식 라이브러리.

### A'. API 변경표

인증 `B` = Bearer 게스트 토큰, `S` = 웹 세션 쿠키(+CSRF 토큰), `-` = 없음. prefix `/api/v1`. "기존" = README API 표 + `app/schemas`.

| 메서드 | 경로 | 인증 | 요청 | 응답 핵심 필드 | 새 에러 코드 |
|---|---|---|---|---|---|
| POST | `/guests` | - | `{puzzle_language?}` | `{token}` | |
| GET | `/config` | - | | `min_app_version {ios, android}`, `maintenance {enabled, message}`, `languages`, `store_urls` | |
| PATCH | `/me` | B | `{puzzle_language}` | `{puzzle_language}` | `VALIDATION_ERROR` |
| GET | `/me/stats` | B | | 기존 + `puzzle_language`, `entitlement {active, until, status, source, next_check_at}` (§A.8 재조회 규칙: `last_verified_at` 1h TTL, 만료 ±24h 는 무상한) | |
| GET | `/me/history?days=7` | B | | `[{date, results: {ko: success\|fail\|in_progress\|none, en: …}}]` | |
| DELETE | `/me` | B | | 204 | |
| POST | `/account/delete` (웹) | S | 확인 폼 + `csrf_token` | 리다이렉트 `/` | `UNAUTHORIZED`, `FORBIDDEN` |
| GET | `/puzzles/today` | B | (게스트 선호 언어) | 기존 + `puzzle_id`, `language`, `mask`, `attempts [{guess, feedback}]`, `hint_unlocked`; `hint` 는 show_hint OR unlocked | |
| POST | `/puzzles/today/guesses` | B | `{puzzle_id, guess}` | 기존(`feedback` 는 `s` 제외 위치, `hint` 규칙 동일) | `PUZZLE_CHANGED`(409, 시도 미소비) |
| POST | `/puzzles/today/hint-unlock` | B | `{puzzle_id}` | `{hint}` | `PUZZLE_CHANGED`, `ALREADY_FINISHED`, `HINT_ALREADY_UNLOCKED`(409) |
| GET | `/puzzles/today/stats?language=` | B | | 기존 + `language` | |
| GET | `/puzzles/today/leaderboard?language=&limit=20` | B | | `entries [{rank, display, attempts, seconds, is_me}]`, `me {rank, attempts, seconds} \| null` (ZRANK). 기존 `guest_id`·`solved_in_seconds` 제거 | |
| POST | `/auth/token-exchange` | B | `{provider, id_token, authorization_code?}` | `{token}` | `INVALID_ID_TOKEN`(401), `ACCOUNT_ALREADY_LINKED` |
| POST | `/subscriptions/verify` | B | `{store, receipt}` (iOS JWS / Android purchaseToken) | `entitlement {…}` | `RECEIPT_INVALID`(400), `STORE_UNAVAILABLE`(503) |
| GET | `/health` | - | | `{status, db, redis, apple_secret_expires_at}` DB 실패 503 / Redis 실패 200+`degraded` | |
| GET | `/privacy`, `/terms`, `/account/delete` | - / S | | HTML | |
| GET/POST | `/admin/*` | S + 운영자 + CSRF | | HTML | `FORBIDDEN`(403) |

리더보드 `display` = `"게스트 #" + guest.id 16진 4자리`.

### B. Flutter 앱

18. **스택.** Flutter + Riverpod, `go_router`, `dio`, `flutter_secure_storage`, `google_sign_in` 7.x(`authenticate()`), `sign_in_with_apple`(iOS), `google_mobile_ads`(배너/전면/보상형 + UMP), `app_tracking_transparency`, `in_app_purchase`(StoreKit2 활성화; **Android 는 release 빌드 merged manifest 에서 Play Billing Library 8+ 확인** — 7 은 2026-08-31 로 제출 마감), `flutter_local_notifications` + `timezone`, `firebase_core/analytics`, `sentry_flutter`, `easy_localization`, `flutter_native_splash`, `flutter_launcher_icons`. Hive/freezed 없음. `very_good_analysis`.
19. **식별자·이름.** `com.dosaem.chosung`, Team `J8QUD7B666`, Play 조직 계정 첫 업로드. "오늘의 초성" / "Hidden Vowels". **태블릿(폭 ≥600dp — iPad·Android 태블릿, plan-add r1)**: 하단 탭 바 대신 NavigationRail, 콘텐츠는 읽기 폭(기본 600dp)으로 제한하되 폭 ≥840 에선 화면별 2열·넓은 표로 재배치(SCREENS "태블릿 레이아웃" T0~T4). 기기 종류가 아니라 **현재 폭**으로 판정해 회전·iPad Split View 폭 변화에 상태를 유지한 채 대응. 배너 슬롯은 콘텐츠 열 하단(rail 제외 폭). "폰 레이아웃 + rail + 폭에 따른 재배치" 수준 — 태블릿 전용 화면 없음. 뼈대는 티켓 24, 화면별 재배치는 각 화면 티켓(25~32), iPad 스크린샷(35)은 이 레이아웃으로 찍는다. (이전 문구 "iPad 중앙 정렬 최대 600px" 는 폐기 — 22 가 만든 래퍼는 24 가 대체.)
20. **접점.** `ApiClient` 인터페이스(§A' 1:1) + Dio 구현. 광고·결제·알림·분석 서비스 클래스 각 1개(테스트 no-op). **알림 예약 계획·구독 UI 판정은 순수 함수**로 분리.
21. **화면** = `design/SCREENS.md` S1~S7 + 목업. 버튼·타일은 **OVERRIDES 토큰 이름**으로 참조(`primary-button`, `tile-empty`), 충돌 시 OVERRIDES 우선. 탭 3개(폭 ≥600dp 는 rail — §B.19), 배너 슬롯 상시 예약(구독자 제거), 전면 결과 시트 후 1회/퍼즐, 보상형 = 힌트 미리 보기. 온보딩 3장 + iOS ATT 안내 + 알림 사전 안내. 점검/강제 업데이트는 `/config`. S4: 계정(iOS 구글·애플 / Android 구글), **백업 코드 입력**(US 18a), 구독(현지화 가격), **광고 개인정보 설정**(UMP `privacyOptionsRequirementStatus == required` 일 때만 표시), 알림(시각·리마인더·권한 상태), 삭제 다이얼로그(구독 별도 해지 문구). S5 혜택 문구 "광고 없이 힌트 미리 보기".
   - **광고 게이트**: 앱 시작마다 UMP `requestConsentInfoUpdate` → 필요 시 폼 → `canRequestAds` 가 true 일 때만 광고 SDK 초기화·로드. iOS 는 ATT 프롬프트(S6 안내 후) → UMP 순. 동의 오류 시 이번 세션 광고 없음, 다음 시작에 재시도. ATT 와 UMP 는 별개 상태.
22. **디자인 토큰** = OVERRIDES → `ThemeData`. Pretendard, Lucide. StreakBadge 숫자 `foreground`.
23. **광고 ID** `--dart-define`, 디버그 테스트 ID. 상품 ID `adfree_monthly`.
24. **분석 이벤트 4개** + Firebase 기본.
25. **배포.** `--dart-define=API_BASE_URL`. BASELINE 워크플로·fastlane·서명 복사+치환. `app_privacy_details.json` 재작성. 스크린샷 Habitopia 방식. **제출 직전 D3 에서 Play target SDK·Billing 버전 요구를 제출일 기준으로 재확인.**

### C. 인프라·운영

26. **compose 파라미터화 + develop 인스턴스.** `docker-compose.prod.yml` 에서 고정 `container_name` 과 `name:` 제거, 호스트 포트 `${APP_PORT}`, env file 환경별, 볼륨은 compose 프로젝트별(`-p`). **prod 프로젝트명은 현행 `chosung-daily-prod` 를 그대로 유지**(`-p chosung-daily-prod --env-file .env`, 8089) — 그래야 기존 named volume `chosung-daily-prod_mysql-data`/`_redis-data` 가 그대로 붙는다. develop: `-p chosung-daily-develop --env-file .env.develop`(8090, 체크아웃 디렉터리 `/volume1/docker/chosung-daily-develop`; DB 는 named volume, bind mount 금지 — DSM ACL). 완료 조건(로컬): ① 현행 compose 로 띄운 프로젝트에 기록을 넣고 새 compose 설정으로 다시 `up` 했을 때 **같은 볼륨이 붙어 기록·토큰이 유지**된다(`docker volume ls` 이름 일치) ② 두 프로젝트를 동시에 띄워 이름·포트·DB 볼륨이 분리되고 한쪽 쓰기가 다른 쪽에 안 보인다. `docs/RELEASE.md` 첫 배포 체크에 "NAS 의 실제 프로젝트명/볼륨명 확인 후 `up`" 을 넣는다.
27. **자동 배포.** `deploy/deploy.sh <prod|develop>` 가 브랜치(main/develop)·디렉터리·포트·env·프로젝트명(`chosung-daily-prod`/`chosung-daily-develop`)을 고르고 `git pull` + `compose up -d --build` + app 컨테이너에서 `flask db upgrade` + 재기동 확인 + `/health`. GitHub Actions → Tailscale → `ssh nas`.
28. **백업.** 독립 컨테이너 매일 04:00 KST mysqldump, 14일, 실패 Slack. `scripts/restore.sh`.
29. **헬스체크** DB 503 / Redis degraded 200. UptimeRobot(사람).
30. **Sentry** 백엔드·Flutter.
31. **CI 강화** ruff `PL,RUF,SIM,PT`, Flutter analyze+test 잡.
32. **문서.** README "설계 판단" 추가 항목: 퍼즐 언어 모델(마이그레이션 1단계), 가림 포맷·puzzle_id 고정·시도 이력 응답, KST 고정, id_token 교환·aud 매트릭스·애플 refresh token 보관, 구독 상태 판정표·유예·Sandbox·완료 순서, 힌트 미리 보기 공정성, 로컬 알림 선택 근거와 취소 규칙, 애플 secret 요청 경로 갱신, 운영자 인증·CSRF, Slack. **Flutter 절(짧게)**: 상태 흐름·SDK 선택·테스트 경계. `docs/RELEASE.md`. `CONTEXT.md`·`docs/adr/` 루트 이관. `/impeccable init`.

### D. 사람이 해야 하는 일 (순서)

**D0. 티켓 시작 전** — 단어 CSV(ko/en 각 ≥120, 심사 전 en 30일 배정 확인) · Firebase 프로젝트 + 앱 등록(`google-services.json`, `GoogleService-Info.plist`) · GCP iOS 클라이언트 ID, Android 클라이언트(SHA-1 3종), 웹 클라이언트 ID 를 `serverClientId` 로 · Google Books 키(선택)
**D1. 백엔드 티켓 중** — Slack Webhook · Sentry 2개 · UptimeRobot · Apple App ID + Sign in with Apple(iOS 번들 ID 를 Services ID 그룹에 추가) · App Store Server API 키 · Sandbox 테스터 · Play 앱 생성·서비스 계정·라이선스 테스터 · 한국 판매자 정보 요건 · **통신판매업 신고 대상 여부 확인(미정 22)·개인정보 보호책임자 지정·주소/전화 공개 결정(미정 21)**
**D2. 앱 티켓 중** — AdMob 앱 2 + 유닛 6 + UMP 메시지(privacy options 포함) · ASC 앱(이름 중복 확인) · 구독 상품 `adfree_monthly` 양 스토어(한국 ₩1,500 Tier) · **Billing Grace Period: Apple 켬(16일), Play base plan 기본 유예 유지** · EULA 결정 · 개인정보 라벨 · keystore·match·러너·GitHub secrets
**D3. 배포·심사 전** — NAS 의 기존 compose 프로젝트명·볼륨명 확인(`docker volume ls`) · NAS develop 폴더·`.env.develop`·DNS·터널 · prod `.env` 새 키 · Play Data safety(삭제 URL) · 앱 콘텐츠 설문 · **제출일 기준 target SDK / Billing 8+ 재확인** · 첫 프로덕션 출시 버튼
모든 가입·콘솔은 운영자 계정 두 개 중 하나(`dosaem90@gmail.com` / `hsseo@dosaem.com`).

## Testing Decisions

- **좋은 테스트** = 외부 동작만. 백엔드 = HTTP 요청→응답·DB 행·Redis 키. Mock 은 provider 경계 한 곳.
- **백엔드 접점 = Flask test client + 실제 MySQL/Redis** (픽스처 확장: `today_puzzle(language)`, `subscribed_guest(status, expires_at)`, `admin_session`). 프라이어 아트: `tests/test_puzzle_api.py`, `test_guess_flow.py`, `test_oauth_routes.py`, `test_rate_limit.py`, `test_redis_failure_fallback.py`, `test_concurrency.py`, `test_leaderboard.py`.
- **외부 provider** monkeypatch(JWKS 는 테스트 키 쌍으로 진짜 검증). 네트워크 금지.
- **필수 케이스**: 같은 날 ko→en streak 유지·solved_count +2 / en 가림·공백·대소문자 / `puzzle_id` 불일치 409 + 시도 미소비(자정 경과·다른 기기 언어 변경) / `attempts` 이력으로 보드 복원 / 힌트 unlocked 재진입 시 `hint` 채워짐 / 리더보드 `me` 21위 밖 / 힌트 미리 보기·제출 동시(FOR UPDATE) / 구독 판정표: active 유예 24h, grace 3일째 권한 있음, hold 없음, revoked 확인 즉시 없음, **만료 20일 전 구독의 provider 상태만 revoked 로 바꾼 뒤 `last_verified_at` 1시간 경과 후 `/me/stats` 에서 권한 제거**, 만료 2일 뒤 복구(verify 재전송) 즉시 반영, 재조회 1시간 상한, Sandbox 4040010 폴백, `store_key` 멱등 중복 전달, linkedPurchaseToken 교체 / 복원 시 재지정 / 삭제: 401 + ZREM + 애플 revoke 호출(refresh token; iOS 연결 계정은 번들 ID, 웹 연결 계정은 Services ID 로)·실패 시 재시도 행 / 웹 삭제 CSRF 없으면 403 / rate limit 언어 무관 / 언어별 배정 en 고갈 시 ko 배정 / `/health` / 운영자 아닌 이메일 403 / 애플 secret 재서명(login·callback).
- **회귀**: 기존 테스트 ko 기본값 통과(리더보드 필드 변경 테스트 수정 허용) + 마이그레이션 전후 ko 데이터 보존.
- **Celery**: 서비스 함수 직접 호출 + 배선: 언어별 배정, 구독 재조회, 잔량·secret 알림, revoke 재시도.
- **Flutter**: analyze 0 + 위젯 테스트(가짜 `ApiClient`): 홈 상태 4종, 제출→409→새로고침, 결과 시트, 구독자 배너 제거, 점검/업데이트 분기, 온보딩 언어, 백업 코드 전환, **태블릿 폭 분기(390/744/1024)와 폭 변경 시 상태 유지**. **순수 함수 단위 테스트**: 알림 예약 계획(오늘 제외·내일 유지, 미주 KST 경계, 두 언어 중 하나, 7일 롤링, 대기 ≤8), 구매 상태→UI 판정, **구독 재확인 타이머(가짜 시계: 포그라운드에 둔 채 `next_check_at` 경과 시 `/me/stats` 가 자동 호출되고 권한 해제가 광고 상태에 반영됨)**, UMP 상태(required/불필요/거부/오류)→광고 게이트. 실기기 체크리스트: 알림 탭 cold/warm, 정답 후 같은 날 리마인더 없음·다음 날 있음(iOS·Android), Sandbox 구매·복원·pending, UMP 재선택.
- **웹**: pytest 렌더 + `impeccable detect` 0건 + 수동 체크리스트(삭제 후 새 게스트 발급 포함).
- **인프라(코드 티켓)**: 로컬에서 현행→새 compose 전환 시 볼륨·기록 유지 확인, prod/develop 두 프로젝트 동시 기동·분리 확인, `deploy.sh` 양쪽 인자로 동작, 백업 덤프 생성, `restore.sh` 복원. NAS 실행·리허설은 `docs/RELEASE.md` 사람 체크리스트.
- **디자인 게이트**: 웹 detect 0건, Flutter `audit.native` 체크리스트.

## Out of Scope

- 스토어 웹훅 — 폴링 + 앱 시작 동기화 + 유예로 시작
- 서버 푸시(FCM, 기기 토큰)
- Android 에서 Apple 로그인(애플 계정 게스트의 Android 전환은 백업 코드로)
- "어제 퍼즐"·아카이브·"기회 +1"
- 다국어 3개 이상, 로컬 자정 기준 하루
- 소셜·채팅, 웹 광고, 웹 구독 결제
- 관리자 사용자 관리·통계 대시보드, A/B, 세션 리플레이, Loki
- RevenueCat 등 결제 SaaS(공식 스토어 라이브러리는 허용), Playwright E2E in CI, oh-my-design/oh-my-agent

## 디자인 부족 항목

- S1(라이트/다크)~S6 는 목업 + SCREENS + OVERRIDES 토큰 있음. 목업 없음: S7 점검/업데이트, 온보딩 2·3장·ATT 안내, 알림 사전 안내, 삭제 다이얼로그, 광고 개인정보 설정 항목, 백업 코드 입력 시트, 웹 전체(`/account/delete` 포함) — 명세+토큰으로 구현, detect/critique 검증.
- 앱 아이콘·스플래시·스크린샷은 OVERRIDES §8 의 확정 콘셉트(라이트 배경 타일 3칸, 라이트 모드 스크린샷)와 참고 좌표만 있고 SVG 는 없음 — 티켓 35 에서 제작.
- 태블릿(T0~T4)은 SCREENS 의 ASCII 와이어만 있고 목업 없음 — 명세+토큰으로 구현, `audit.native` 태블릿 폭 포함.
- 목업의 brand 색 버튼·대시 테두리 빈 타일·brand 글자 숫자는 OVERRIDES 가 우선(검정 주 버튼, 면 채움 빈 타일, foreground 숫자).

## 미정 항목

1. 스토어 웹훅 도입 시점 — 구독자 생기면
2. "어제 퍼즐" 보상형 — 다음 Phase
3. 영어 책 제목 소스 — Google Books, 품질 나쁘면 Open Library
4. ASC 앱 이름 "Hidden Vowels" 중복 — 막히면 "Hidden Vowels: Daily Word"
5. Playwright E2E in CI — 보류
6. 리마인더 20:00·기본 09:00 의 효과(특히 미주) — Analytics 2주 후 결정
7. UMP 메시지 문구·EEA 외 표시 — AdMob 콘솔(사람)
8. develop 포트 8090 — NAS 실측(사람)
9. Apple 표준 EULA vs 커스텀 — D2. **(plan-add r1)** 티켓 16 에서 결정·근거 기록(권장: 표준 EULA 유지, 약관 §EULA 절에 링크 — 09 현행)
10. `chosung` 호환 필드 제거 시점 — 클라이언트 전부 `mask` 전환 후
11. Apple revoke 재시도 7일 폐기 정책이 적절한지 — 운영 데이터 보고
12. (r3 MINOR, 티켓에서 확정) `GET /puzzles/today` 의 `attempts[].feedback` 정답 행은 전부 `true` 로 채워 보내는 쪽 권장(웹이 "항상 채워짐" 전제) — API 티켓에서 확정
13. (r3 MINOR) en 의 `Attempt.guess` 는 구분자 제거 글자열이라 보드 복원 시 클라이언트가 `mask` 의 `s` 위치에 간격을 다시 끼운다 — 클라이언트 티켓에서 확정
15. (r4 MINOR, Fable) ADR 0003 본문은 1h TTL 재조회를 아직 "만료 ±24h" 로만 적고 있음 — 구현 첫 티켓의 ADR 이관 때 §A.8 기준으로 문구 갱신
16. (r4 MINOR, Fable) `-p` 없이 `docker compose up` 하면 새 볼륨이 생기므로 `.env`/`.env.develop` 에 `COMPOSE_PROJECT_NAME` 을 넣어 두는 안전장치 — 인프라 티켓에서 반영
17. (r4 MINOR, Fable) iOS 번들 ID 용 Apple client_secret 설정값(예: `APPLE_APP_BUNDLE_ID`)과 그 secret 도 §A.13 자동 갱신 대상에 포함 — 백엔드 로그인 티켓에서 반영
18. (r4 MINOR, Fable) 만료 ±24h 구간의 재조회가 무상한이라 호출마다 스토어 API 를 때릴 수 있음 — 필요하면 5분 상한 추가, 구독 티켓에서 결정
19. (r5 MINOR, Sol) 1h TTL 경계 표현 정렬 — 서버 재조회 조건을 `now >= next_check_at` 으로 명시하고, Flutter 가짜 시계 테스트에 정확히 `next_check_at` 시각을 포함해 경계에서 조회를 건너뛰는 해석을 막는다 — 구독 티켓에서 반영
20. (티켓 작성 중 발견) §B.24 "분석 이벤트 4개" 의 명칭·파라미터가 스펙에 없음 — 티켓 24 에서 `puzzle_complete(language, success, attempts)`, `share`, `paywall_view`, `subscribe_start` 로 확정하고 여기 결과 기록
21. (plan-add r1, 사용자 확인) 법적 문서의 사업장 주소(자택)·전화번호·보호책임자 성명 공개 범위 — 티켓 16 워커가 법적 근거를 붙여 `orca orchestration ask`, 답 전에는 미표시. 결과는 `docs/RELEASE.md` "### 16."
22. (plan-add r1, 사람 D1) 통신판매업 신고 대상 여부(구독 판매 전) — 면제 기준 확인 후 신고하면 `LEGAL_MAIL_ORDER_REG_NO`. 티켓 16 은 신고번호가 비면 그 행을 렌더하지 않는다
23. (plan-add r1) 해외 사용자 최소 고지(EU/영국·캘리포니아 권리 안내) 포함 여부 — 티켓 16 에서 결정·근거 기록(권장: 짧은 "해외 사용자" 절 1개를 ko/en 모두에)
24. (plan-add r1) 태블릿 expanded(≥840) 2열의 세부 폭(T1 600+320, T4 480+480)·Split View 최소 폭 처리 — 티켓 24·화면 티켓에서 확정하고 README Flutter 절에 기록
25. **해소(2026-10-14, 사용자 확정)** 앱 아이콘·스크린샷 톤 — 계획 리뷰 r1 의 사용자 확인 항목(다크 배경 `#0F172A` + 흰 "ㅊ" vs Editorial Light). 결정: 라이트 배경 `#FAFAF9` 에 글자 없는 타일 3칸(양끝 brand `#EA580C`, 가운데 `tile-wrong` `#D6D3D1`), 스플래시 동일, 스크린샷 라이트 모드. 근거: 스토어는 앱당 아이콘 하나라 "ㅊ" 은 영어 사용자에게 뜻이 없음. OVERRIDES §8·티켓 35 반영. 30px 가독성은 35 에서 확인(필요 시 가운데 칸 `#A8A29E`)
14. (r3 MINOR) Google 상태 매핑 빈칸 — **티켓 12 에서 fixture 로 확정**(`tests/fixtures/store/play_*.json`, `tests/test_subscription_status.py`): `PAUSED → hold`, `PENDING`·`PENDING_PURCHASE_CANCELED` → 행 없음(권한 없음), `ACTIVE`·`CANCELED` → active, `IN_GRACE_PERIOD` → grace 이고 `grace_expires_at` = `expires_at` = `lineItems[].expiryTime`(Google 은 유예 종료 시각을 따로 주지 않고 유예 중에는 `expiryTime` 이 유예 종료까지 연장돼 온다), `EXPIRED` → expired, 알 수 없는 state 는 `ValueError`. **`revoked` 라벨은 v2 응답만으로는 붙이지 않는다** — `SubscriptionPurchaseV2` 에 철회 전용 필드가 없고 그 신호는 Voided Purchases API / RTDN `SUBSCRIPTION_REVOKED` 에만 있다(미정 1 과 함께 도입). 그때까지 Google 환불·철회는 "만료일 전 EXPIRED" 로 관측돼 `expired` 로 기록되며, 판정표에서 expired·revoked 가 같은 칸이라 권한 결과는 동일하다(24h 유예 없이 즉시 권한 없음 — `test_a_refunded_google_subscription_loses_the_entitlement_immediately`). 순수 함수 `google_subscription_status(purchase, *, revoked=False)` 에 플래그 자리를 뒀다.
12. **확정(티켓 04)**: `GET /puzzles/today` 의 `attempts[].feedback` 는 정답 행도 포함해 **항상 `length` 길이로 채워 보낸다**(정답 행은 전부 `true`). 피드백은 저장하지 않고 `Attempt.guess` 와 정답을 다시 비교해 만든다 — 비교 규칙이 제출·조회 두 곳에 두 벌로 생기지 않게. 제출 응답(`POST guesses`)은 현행대로 정답일 때 `feedback: null` 이다. 근거는 README "04. 시도 이력을 서버가 돌려주는 이유".

- (티켓 10 반영) 미정 17 확정: 앱 애플 로그인은 설정값 `APPLE_APP_BUNDLE_ID` 하나만 추가하고 서명 키(`APPLE_TEAM_ID`·`APPLE_KEY_ID`·`APPLE_PRIVATE_KEY`)는 웹과 공유한다(Sign in with Apple 키 하나가 App ID 와 그 Services ID 를 모두 서명). client_secret 생성은 `apple_client_secret(app, client_id)` 로 인자화해 웹은 Services ID, 앱은 번들 ID 로 서명한다 — §A.13 자동 갱신(티켓 11)은 이 **두 client 의 secret 을 모두** 대상으로 해야 한다.

## Further Notes

- 운영자 계정은 정확히 두 개: `dosaem90@gmail.com`, `hsseo@dosaem.com`.
- 면접 설명 범위: 백엔드 전부 + Flutter 는 상태 흐름·SDK 선택·테스트 경계(README Flutter 절). (r3 MINOR 메모: 제출하는 코드 전체는 작성자가 설명할 수 있어야 하고, 설계 판단 문서만 핵심 중심으로 쓴다는 뜻.)
- 티켓: `.scratch/store-launch/issues/01~36`(의존성 순, 2026-10-13; 계획 리뷰 r1 반영으로 구 24→24·25, 구 29→30·31 분할; **plan-add r1(2026-10-14)** 로 16(법적 문서 보완)·24(태블릿 뼈대) 삽입 — 구 16→23, 구 23~34→25~36, 대응표는 `review/plan-add-r1-response.md`. 머지·진행 중 티켓(01~13·15·17·19~22) 본문의 번호는 구 번호 그대로다). 미정 항목 중 9·21·22·23(16)·12(04)·13(17)·14(12)·18(13)·19(13·33)·20(26)·24(24)·25(35, 30px 확인) 은 해당 티켓에서 확정. Flutter 루트는 `mobile/`. 앱 아이콘·스플래시·스크린샷은 OVERRIDES §8 그대로 — **2026-10-14 사용자 확정: 라이트 배경 `#FAFAF9` 에 글자 없는 타일 3칸(양끝 brand, 가운데 `tile-wrong`), 스크린샷은 라이트 모드 기준**(이전 "다크 배경 + ㅊ, 다크모드 스크린샷" 폐기, 미정 25). 콘셉트를 또 바꾸려면 OVERRIDES §8 을 먼저 고친다.
- 디자인 파이프라인·스펙 리뷰 규칙은 `~/.claude/CLAUDE.md`·NAS README 에 기록. 리뷰 응답: `review/spec-review-r1-response.md`, `review/spec-review-r2-response.md`.
- BASELINE 읽기만. ENV.md 의 PostgreSQL/Flyway 기술은 무시(MySQL/Alembic).
- 티켓 하나 = 워커 하나가 한 세션. §A.1, §A.8, §A.11 은 본문의 분할 지침대로 쪼갠다. 의존성은 `issues/NN-*.md` "Blocked by".
