# 사용자 할 일·결정 목록 (번호 고정)

2026-10-15 사용자에게 번호를 붙여 한 번에 물은 결과. 번호는 바꾸지 않고 상태만 갱신한다.
작업 방식(사용자 결정 2026-10-15): **콘솔·대시보드 설정은 Claude 가 Chrome 조종으로 직접 한다.** 사용자는 운영자 계정으로 로그인해 두고, 결제·유료 가입·약관 동의·CAPTCHA 와 **마지막 출시 버튼** 만 직접 누른다. 운영자 계정은 `dosaem90@gmail.com` / `hsseo@dosaem.com` 둘 중 하나. 발급된 키·URL 은 이 문서에 적지 않는다(`.env` 로 직행).

상태: `결정됨` / `아직` / `Claude 진행 중` / `사용자 차례` / `끝`

## A. 결정 (법적 문서)

| # | 항목 | 결정 (2026-10-15) | 반영 위치 |
|---|---|---|---|
| 1 | 통신판매업 신고 | **면제(직전년도 거래 50회 미만)로 미신고.** 연간 유료 구독 50건 넘기기 전에 신고. 신고 시 자택 주소가 공정위 사이트에 공개되므로 그때 별도 주소 검토 | `LEGAL_MAIL_ORDER_REG_NO` 비움, RELEASE "### 16." 체크박스는 "면제 — 50건 전 재검토" 로 |
| 2 | 사업장 주소 표시 | **시·구까지만(현행 유지)** + "상세 주소는 요청 시 이메일로 제공" | `LEGAL_BUSINESS_ADDRESS` 에 축약 주소를 사람이 넣음 |
| 3 | 전화번호 | **미표시(현행 유지)** | `LEGAL_BUSINESS_PHONE` 비움 |
| 4 | 보호책임자 | **직책 "운영자" + 이메일(현행 유지)**, 성명 비공개 | `LEGAL_PRIVACY_OFFICER` 비움 |
| 5 | 전문가 검토 | **안 받고 일단 출시.** 매출 생기면 재검토 | RELEASE "### 16." 의 전문가 검토 체크박스는 "보류" |

## B. 준비물 (D0, 티켓 시작 전)

| # | 항목 | 상태 | 누가 | 비고 |
|---|---|---|---|---|
| 6 | 단어 CSV ko/en 각 120개 이상 | 아직 → **티켓 39 로 워커가 후보 생성** | 워커 → 사람 검수·업로드 | `issues/39-word-candidates-csv.md` |
| 7 | Firebase 프로젝트 + Android/iOS 앱 등록 파일 2개 | **끝(2026-10-15)** | Claude(gcloud+Orca) | GCP/Firebase 프로젝트 `chosung-daily`(dosaem90 소유, hsseo@dosaem.com 편집자 + 소유자 초대 메일 → **사용자 수락 필요**). 앱 2개 등록, Analytics 연결(Default Account for Firebase). 파일은 `mobile/android/app/google-services.json`·`mobile/ios/Runner/GoogleService-Info.plist`(gitignore) |
| 8 | GCP 클라이언트 ID 3종(iOS / Android SHA-1 / 웹 `serverClientId`) | **끝(2026-10-15)** | Claude(Orca) | OAuth 브랜딩(Hidden Vowels, 외부) + 웹·iOS·Android(upload)·Android(debug) 클라이언트 4개. 값은 `~/.config/chosung-daily/launch-secrets.env`, 로컬 `.env` 에 `GOOGLE_WEB_CLIENT_ID`·`GOOGLE_IOS_CLIENT_ID`. **남은 것:** Play App Signing SHA-1 (11번 뒤) 을 Firebase·GCP Android 클라이언트에 추가, prod `.env` 전환 |

## C. 콘솔 (D1, 백엔드 중)

| # | 항목 | 상태 | 누가 | 비고 |
|---|---|---|---|---|
| 9 | Slack Webhook · Sentry 2개(웹·앱) · UptimeRobot | **끝(2026-10-16)** | Claude(Chrome, hsseo@dosaem.com 프로필) | Sentry 조직 `dosaem`: 프로젝트 `chosung-web`(Flask, DSN → 로컬 `.env` SENTRY_DSN)·`chosung-app`(Flutter, DSN → GitHub secret FLUTTER_SENTRY_DSN). UptimeRobot: `https://chosung.dosaem.com/health` HTTP 모니터 5분, Up, 이메일 알림. Slack: 워크스페이스 Dosaem 앱 `Hidden Vowels Ops` → Incoming Webhook `#새-채널` 연결, URL 은 로컬 `.env` SLACK_WEBHOOK_URL + launch-secrets. **끝.** prod `.env` 반영은 16번 |
| 10 | Apple App ID + Sign in with Apple(Services ID) + App Store Server API 키 + Sandbox 테스터 | **대부분 끝(2026-10-15)** | Claude(Chrome) | App ID `com.dosaem.chosung`(Sign in with Apple 켬) 등록. 웹 Services ID·키는 기존 것(`.env`) 재사용, `APPLE_APP_BUNDLE_ID` 추가. ASC API 키는 기존 `dosaem-fastlane` 재사용 → GitHub secret `APP_STORE_CONNECT_API_KEY`. 사용권 계약 업데이트 동의 완료. **남은 것(사용자):** Sandbox 테스터 생성(비밀번호 필요), 유료 앱 계약 서명(은행·세금 정보), EU 거래자 자격 |
| 11 | Play 앱 생성 + 서비스 계정 + 라이선스 테스터 + 한국 판매자 정보 | **일부 끝(2026-10-16)** | Claude(Orca) | 개발자 계정 DOSAEM 에 앱 `Hidden Vowels`(`com.dosaem.chosung`, 게임, 무료) 생성. 서비스 계정 `play-publisher@…` 초대·활성(초안 수정, 프로덕션 출시, 테스트 트랙 출시). **막힘:** 라이선스 테스터 이메일 목록 저장이 "변경사항을 저장할 수 없습니다" — 홈의 "Android 개발자 인증" 미완료 영향 추정(사용자 확인). 판매자 정보(결제 프로필)는 사용자 |

## D. 앱 (D2)

| # | 항목 | 상태 | 누가 | 비고 |
|---|---|---|---|---|
| 12 | AdMob 앱 2 + 유닛 6 + UMP 메시지 | **대부분 끝(2026-10-16)** | Claude(Chrome) | 사용자가 가입. 앱 2개(Android `~9527970764`, iOS `~4523056090`, 둘 다 "검토 필요 — 스토어 추가로 한도 해제": 출시 후 스토어 연결) + 광고 유닛 6개(배너·전면·보상형 ×2) → GitHub variables `ADMOB_*_AD_UNIT_ID_*` 6개 등록, 값은 `~/.config/chosung-daily/launch-secrets.env`. 앱 코드의 AdMob 앱 ID 는 아직 Google 테스트 ID(`AndroidManifest.xml`·`Info.plist`) → 티켓 31 에서 교체. **남은 것:** UMP(유럽·미국 주 규정) 메시지 페이지가 로딩만 됨 — AdMob 배너 "결제 프로필 미작성" 영향 추정 → **사용자가 지급 정보 입력** 후 재시도 |
| 13 | ASC 앱 생성(이름 중복 확인) + 구독 `adfree_monthly` 양쪽(₩1,500) + Apple Grace Period 16일 | **일부 끝(2026-10-15)** | Claude(Chrome) | ASC 앱 `Hidden Vowels`(ID 6823092579, 기본 언어 한국어, SKU chosung-daily) 생성, 구독 그룹 Ad-Free + `adfree_monthly`(1개월, Apple ID 6823093744) 생성. **2026-10-16 완료:** 가격 ₩1,500(KRW 기준 175개국 자동 환산), 전체 국가 사용 가능, 표시 이름 ko "광고 제거"/en "Ad-Free", 청구 유예 16일(모든 갱신, 프로덕션+샌드박스). **남은 것:** 구독 그룹 표시 이름 현지화(심사 전), Play 구독 상품은 첫 AAB 업로드 뒤, 유료 앱 계약(사용자) |
| 14 | 업로드 keystore · match · self-hosted 러너 · GitHub secrets | **일부 끝(2026-10-15)** | Claude(로컬 CLI) + 사용자 | keystore 생성(`mobile/android/app/upload-keystore.jks`, 비밀번호는 `mobile/android/key.properties`, 둘 다 gitignore — **사용자가 비밀번호 관리자에 백업**). GitHub secrets 9개(KEYSTORE_*·KEY_*·GOOGLE_PLAY_KEY_JSON·FIREBASE_SERVICE_ACCOUNT·FIREBASE_APP_ID·GOOGLE_SERVICES_JSON_BASE64·GOOGLE_SERVICE_INFO_PLIST_BASE64) + variables 2개(API_BASE_URL_PROD·GOOGLE_SERVER_CLIENT_ID) 설정. 서비스 계정 키는 `~/.config/chosung-daily/*.json`. **남은 것:** match(Apple 로그인 뒤), self-hosted 러너, APP_STORE_CONNECT_API_KEY·MATCH_*·FLUTTER_SENTRY_DSN·ADMOB_*, variable `TESTFLIGHT_TESTER_EMAIL`(testflight-tester 워크플로 기본 테스터, 티켓 41) |

## E. 배포·심사 (D3)

| # | 항목 | 상태 | 누가 | 비고 |
|---|---|---|---|---|
| 15 | NAS compose 프로젝트명·볼륨명 확인, develop 폴더·`.env.develop`·DNS·터널 | **확인만(2026-10-16)** | Claude(ssh nas) | NAS 체크아웃 `/volume1/docker/chosung-daily` 는 옛 커밋(64ea73a, 티켓 이전) — 티켓 19/20 배포 때 갱신. `/volume1/backup` 은 권한 없음 → 백업·로그 폴더를 `/volume1/docker/chosung-daily-backups/{,logs}` 로. develop 폴더·DNS·터널은 아직 |
| 16 | prod `.env` 새 키(`LEGAL_*`·`LOG_DIR`·`BACKUP_ENCRYPTION_CERT_FILE`·`ACCESS_LOG_RETENTION_DAYS`) | **끝(2026-10-16)** | Claude(ssh nas) | NAS `.env` 에 33개 키 추가(백업 `.env.bak-20261016`): COMPOSE/APP_PORT, ADMIN_EMAILS, SLACK·SENTRY, GOOGLE_WEB/IOS_CLIENT_ID, APPLE_APP_BUNDLE_ID, LEGAL_*(두샘·서한샘·등록번호·"경기도 구리시"·hsseo@dosaem.com, 전화·책임자·통판 비움), SUBSCRIPTION/APP_STORE_*(ASC 키 KJUAA3YP22 재사용, Apple ID 6823092579), PLAY_*(`/backups/play-publisher.json`), BACKUP_DIR·CERT·LOG_DIR·365. **남은 것:** `APP_STORE_ROOT_CERT_PATHS`(Apple Root CA .cer 다운로드 → 사용자 OK 필요), `GOOGLE_CLIENT_ID/SECRET` 를 새 프로젝트 웹 클라이언트로 교체할지(현재 옛 값 유지) |
| 17 | 백업 키 생성 → NAS 밖 두 곳 보관, 공개키 인증서를 NAS 에 | **생성 끝(2026-10-16)** | Claude(로컬) + 사용자(보관) | 구현은 age 가 아니라 openssl CMS(RELEASE "### 36."). 키쌍 `~/.config/chosung-daily/chosung-backup-{key,cert}.pem`, 인증서는 NAS `/volume1/docker/chosung-daily-backups/backup-cert.pem`. **사용자:** 개인키 `chosung-backup-key.pem` 을 비밀번호 관리자 + 오프라인 사본에 보관(잃으면 백업 복구 불가) |
| 18 | Play Data safety · 앱 콘텐츠 설문 · target SDK/Billing 8+ 재확인 · ASC 수출규정 답변이 면제(`ITSAppUsesNonExemptEncryption=false`, 티켓 41)와 일치하는지 첫 제출 때 확인 · **첫 출시 버튼** | 아직 | Claude(설문 초안·입력) → **출시 버튼은 사용자** | |

## F. 출시 후·운영 (2026-10-16 추가)

| # | 항목 | 상태 | 누가 | 비고 |
|---|---|---|---|---|
| 19 | LLM 출제 파이프라인 — 구현 · `ANTHROPIC_API_KEY` 발급 · 첫 실행 → 통과율·단어당 비용 | **끝(2026-10-16)** — 후보 검수는 사용자 | Claude(구현·실행) → **사용자(`/admin/candidates` 에서 승인·거절)** | main 머지(d6de6c0)·prod 배포, 키는 NAS `.env`(백업 `.env.bak-20261016-llm`), 플래그 on. **첫 실행 실측(claude-sonnet-5-5):** ko 40개 → 38 통과·2 탈락(힌트에 정답 음절, 통과율 95%), 토큰 1,399/5,684, $0.0596, 42초 · en 40개 → 40 통과(100%), 토큰 1,078/2,493, $0.0271, 26초 · **합계 $0.0867, 통과 후보 1개당 $0.0011** (월 예산 $5 ≈ 4,500단어). 승인 대기 78개 → `https://chosung.dosaem.com/admin/candidates` |
| 20 | 티켓 50 무중단 배포 (사용자 결정: 1단계 + 2단계 Caddy 롤링 같이) | **끝(2026-10-16)** — develop 에서 Actions 자동 배포로 전환·롤링 검증(app-2 healthy → 옛 app stop, 8094 200), main 머지 | Claude | 브랜치 `feat/50-zero-downtime`(워크트리 `~/orca/worktrees/chosung-daily-47`), 티켓 `.scratch/store-launch/issues/50-zero-downtime-deploy.md`, README 설계 판단 50, RELEASE §50. develop 에 올려 Actions 배포로 전환 검증 → 통과하면 main 머지 |
| 21 | Cloudflare 터널 `develop-chosung.dosaem.com` 경로 포트 **8090 → 8094** 수정 | **끝(2026-10-16)** | Claude(Chrome) | 8090 은 알리미가 씀. `https://develop-chosung.dosaem.com/health` 200 확인 |
| 22 | 영어 단어 CSV(`en-general-01-reviewed.csv`, 161개) 업로드 + `/admin/schedule` ko/en 30일 확인 | **끝(2026-10-16)** | Claude(Chrome + ssh nas) | ko 162·en 161 일치. 오늘(10-16) 퍼즐이 두 언어 다 비어 있어서(단어를 자정 뒤에 올림) prod 컨테이너에서 `uv run flask schedule-puzzles --language {ko,en} --days 30` 실행 → ko 4일·en 30일 배정, EN 오늘 퍼즐 API 확인 |
| 23 | AdMob 계정 승인 → UMP(동의 메시지) 생성 | 승인 대기 | Claude(Chrome) | 승인 전엔 UMP 페이지가 비어 있음 |
| 24 | Play 라이선스 테스터 목록 저장 실패("변경사항을 저장할 수 없습니다") | 보류 | Claude(Chrome) | 다시 시도 |
| 25 | `MATCH_GIT_BASIC_AUTHORIZATION` 은 gh 토큰 — 전용 PAT 로 교체 | 아직 | 사용자(토큰 발급) → Claude(secret 교체) | |
| 26 | 에러 알림 자동화 — Sentry → 우리 서버 웹훅 → Slack 알림 + GitHub 이슈 → Claude Code GitHub Action 이 원인 분석·수정 PR | **구현·배포 끝(2026-10-16)** — Sentry→Slack→GitHub 이슈 #1 까지 실제 왕복 확인. **끝** — 키 교체 뒤 Claude Action 이 이슈 #1 을 "테스트 이벤트, PR 없음" 으로 정확히 분석(43초, $0.19). 처음 실패 원인은 프로모션 크레딧이 Claude Code 실행엔 적용 안 돼서(billing_error) | Claude | 사용자가 붙여넣은 Sentry 4건(04:03 UTC)은 prod 재배포 중 마이그레이션 2개가 동시에 돌아 생긴 일회성(04:10 이후 에러 0). 재발 방지는 티켓 50 |
| 27 | LLM 심사관(검증까지 AI) — 생성 배치를 LLM 이 심사해 승인/거절, 운영자는 감독 | **끝(2026-10-16)** — prod 배포·첫 심사 완료 | Claude | 사용자 결정 "검증까지 AI 로". **첫 심사 실측:** ko 38 → 승인 37·거절 1(햇빛: 초성 ㅎㅂ 이 햇볕과 겹쳐 정답이 둘로 갈림), en 40 → 승인 40. 심사 비용 $0.022 + $0.061, 단어 풀 342 → 419. 생성+심사 합계 $0.17, **단어 1개당 $0.0022**. 감독은 `/admin/candidates` 최근 처리 표 |
| 28 | 웹 출시 품질 업데이트 + 대결 링크 — 스펙 `.scratch/web-launch-polish/spec.md` | **스펙 리뷰 중(2026-10-16)** | Claude(스펙·리뷰) → **사용자(`/to-tickets`)** | 사용자 결정: 차별 기능 = 대결 링크, 범위 = 앱 목업 수준 전부, 방식 = 스펙·티켓. 경쟁 비교 `.scratch/store-launch/competitive-analysis.md`. **주의: Orca 워커 48(경쟁 앱 조사)·49(반영)가 동시에 돌고 있어 결과와 맞춰야 함** |
| 29 | 용량 계획 — 지금 NAS(DS423+·워커 1개)가 어디까지 버티고 그 뒤 어떻게 할지 | **예측 끝(2026-10-16)** — 1단계(설정) 적용 여부 결정 대기 | Claude → **사용자(1단계 적용 OK?)** | `.scratch/store-launch/capacity-plan.md`. DAU 1만까지 설정으로, 자정 p95 300ms 3일 연속 또는 집 회선 다운 1회면 서울 VPS 1대로 compose 이전(월 2~3만원) |

## 기록

- 2026-10-16 (8차): 사용자 결정 — 19 키 `launch-secrets.env` 경유, 머지+prod 배포, 20 은 1+2단계. LLM 파이프라인 main 머지·prod 배포·첫 실행(위 19 실측). **Actions Deploy 가 전부 실패하고 있었음**: Synology 비대화형 ssh PATH 에 `/usr/local/bin`(docker) 없음 → `docker: command not found`(127). git merge 만 되고 컨테이너는 옛것 — 수동 배포로 복구, 스크립트 PATH 보강은 티켓 50 에 포함.

- 2026-10-16 (7차): LLM 출제 파이프라인 구현 완료(19) — word_rules 분리(기존 테스트 17개 무변경), `word_candidate`·`llm_call` 테이블, Anthropic requests 래퍼 + JSON 스키마 출력, Celery 태스크 + 안전장치 4겹(플래그·대기 상한 60·월 5달러·언어 락), `/admin/candidates` 검수 화면, README 운영 절·설계 판단. 키가 없어 실제 호출은 안 했고 HTTP 경계만 가짜로 둔 테스트로 검증. develop 인스턴스 health OK(8094). 남은 것 20~25.

- 2026-10-16 (6차): ASC 비즈니스 완료 — 세금 양식 3개 제출(W-8BEN·Foreign Status 활성화, 한국 양식 대기), 대한민국 전자상거래법 연락처(hsseo@dosaem.com) 활성화, DSA 심사 중, 은행 처리 중 → 유료 앱 계약 "처리 중". 배너 0개. **다음 확인(2026-10-17 이후):** 유료 앱 계약 활성화됨 여부, AdMob 계정 승인 → UMP.

- 2026-10-16 (5차, 사용자): ASC 은행 계좌(신한, 처리 중 24h), 대한민국 세금 양식 제출(대기 중), EU DSA 거래자 자격 제출(심사 중, 사업자등록증 EN 업로드), Sandbox 테스터 생성, Play 판매자 정보. **남은 것:** W-8BEN 양식 본체, "대한민국 법" 규정 준수 배너, 은행 처리 완료 후 유료 앱 계약 활성화 확인, AdMob 승인 대기.

- 2026-10-16 (4차, 사용자 완료): 유료 앱 계약 서명 → 상태 "사용자 정보 대기 중"(**은행 계좌 + 세금 양식 대한민국/미국 설문지 남음**, 구독 판매 전 필수). Play 서비스 계정 권한 8개(재무 데이터 보기 추가). Play 판매자 정보 입력. GCP 소유자 수락 확인. 키 파일 4개를 `~/Desktop/chosung-daily-keys/` 에 모음(비밀번호 관리자 첨부 후 삭제). **남은 사용자 항목:** ASC 은행·세금 양식, 대한민국 법 정보·EU 거래자(ASC 비즈니스 배너), Sandbox 테스터(실기기 테스트 전), AdMob 계정 승인 대기(→ UMP 는 Claude), 라이선스 테스터(보류).

- 2026-10-16 (3차): 7 완료(NAS .env 33키 + Apple Root CA G2/G3 → APP_STORE_ROOT_CERT_PATHS), 12 AdMob 지급 프로필 완료 확인(계정 승인 24h 대기, UMP 페이지는 승인 전 빈 화면). ASC 법인 정보(현지 이름) 저장 완료 → **유료 앱 계약 서명은 금융 계약이라 Claude 차단, 사용자가 직접**(비즈니스 탭 "유료 앱 계약 서명"). Play 서비스 계정 "재무 데이터 보기" 권한 부여도 권한 부여라 차단 → 사용자가 열린 다이얼로그에서 체크·적용·저장. Sandbox 테스터(비밀번호)·Play 판매자 정보(계좌)·키 백업(비밀번호 관리자)은 사용자.

- 2026-10-16 (2차): Chrome 은 hsseo@dosaem.com 프로필(Profile 7, Claude 확장 있음) 창으로 전환 — 이후 Chrome 작업은 그 프로필에서. ASC 구독 설정 완료(13).

- 2026-10-16: Play 앱·서비스 계정 완료(11), AdMob 가입 필요(12), Apple 세션 만료로 ASC 구독 가격 보류(13). Chrome 창 찾기 문제로 Google 쪽은 Orca 브라우저(hsseo@dosaem.com 로그인됨)로 진행.

- 2026-10-15 (2차): 7·8 완료, 14 일부. Play 서비스 계정 `play-publisher@chosung-daily.iam.gserviceaccount.com` 은 11번에서 Play Console 에 초대(앱 출시 관리 권한). Orca 브라우저에서 Apple 로그인이 안 돼 나머지는 Chrome 으로 진행.
- 2026-10-15: 1~18 질문·답 완료. 6 → 티켓 39 추가(38 은 리더보드 익명 이름이 이미 사용). 7~14·18 은 Claude 가 Chrome 으로 진행하기로. 메모리 `ask-numbered-all-at-once`, `console-setup-by-claude`.
