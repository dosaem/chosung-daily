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
| 9 | Slack Webhook · Sentry 2개(웹·앱) · UptimeRobot | 아직 | Claude(Chrome) | 가입은 사용자, 설정은 Claude |
| 10 | Apple App ID + Sign in with Apple(Services ID) + App Store Server API 키 + Sandbox 테스터 | 아직 | Claude(Chrome) | Apple Developer 가입(연 $99)은 사용자 |
| 11 | Play 앱 생성 + 서비스 계정 + 라이선스 테스터 + 한국 판매자 정보 | 아직 | Claude(Chrome) | Play 개발자 등록($25)·판매자 정보(결제 계좌)는 사용자 |

## D. 앱 (D2)

| # | 항목 | 상태 | 누가 | 비고 |
|---|---|---|---|---|
| 12 | AdMob 앱 2 + 유닛 6 + UMP 메시지 | 아직 | Claude(Chrome) | AdMob 계정 승인 대기 가능 → 앱 티켓은 테스트 유닛 ID 로 먼저 |
| 13 | ASC 앱 생성(이름 중복 확인) + 구독 `adfree_monthly` 양쪽(₩1,500) + Apple Grace Period 16일 | 아직 | Claude(Chrome) | 10·11 뒤. 유료 앱 계약·세금/은행 정보는 사용자 |
| 14 | 업로드 keystore · match · self-hosted 러너 · GitHub secrets | **일부 끝(2026-10-15)** | Claude(로컬 CLI) + 사용자 | keystore 생성(`mobile/android/app/upload-keystore.jks`, 비밀번호는 `mobile/android/key.properties`, 둘 다 gitignore — **사용자가 비밀번호 관리자에 백업**). GitHub secrets 9개(KEYSTORE_*·KEY_*·GOOGLE_PLAY_KEY_JSON·FIREBASE_SERVICE_ACCOUNT·FIREBASE_APP_ID·GOOGLE_SERVICES_JSON_BASE64·GOOGLE_SERVICE_INFO_PLIST_BASE64) + variables 2개(API_BASE_URL_PROD·GOOGLE_SERVER_CLIENT_ID) 설정. 서비스 계정 키는 `~/.config/chosung-daily/*.json`. **남은 것:** match(Apple 로그인 뒤), self-hosted 러너, APP_STORE_CONNECT_API_KEY·MATCH_*·FLUTTER_SENTRY_DSN·ADMOB_*, variable `TESTFLIGHT_TESTER_EMAIL`(testflight-tester 워크플로 기본 테스터, 티켓 41) |

## E. 배포·심사 (D3)

| # | 항목 | 상태 | 누가 | 비고 |
|---|---|---|---|---|
| 15 | NAS compose 프로젝트명·볼륨명 확인, develop 폴더·`.env.develop`·DNS·터널 | 아직 | 사용자(NAS) | Claude 는 NAS 접속 안 함. 절차는 RELEASE "### 19/20." |
| 16 | prod `.env` 새 키(`LEGAL_*`·`LOG_DIR`·`BACKUP_ENCRYPTION_CERT_FILE`·`ACCESS_LOG_RETENTION_DAYS`) | 아직 | 사용자(NAS) | 값 목록은 `.env.example` |
| 17 | 백업 openssl CMS 키쌍 생성(개인키 `BACKUP_DECRYPTION_KEY_FILE` → NAS 밖 두 곳 보관, 공개키 인증서 `BACKUP_ENCRYPTION_CERT_FILE` → NAS) | 아직 | Claude(로컬 생성) + 사용자(보관) | RELEASE "### 36." |
| 18 | Play Data safety · 앱 콘텐츠 설문 · target SDK/Billing 8+ 재확인 · ASC 수출규정 답변이 면제(`ITSAppUsesNonExemptEncryption=false`, 티켓 41)와 일치하는지 첫 제출 때 확인 · **첫 출시 버튼** | 아직 | Claude(설문 초안·입력) → **출시 버튼은 사용자** | |

## 기록

- 2026-10-15 (2차): 7·8 완료, 14 일부. Play 서비스 계정 `play-publisher@chosung-daily.iam.gserviceaccount.com` 은 11번에서 Play Console 에 초대(앱 출시 관리 권한). Orca 브라우저에서 Apple 로그인이 안 돼 나머지는 Chrome 으로 진행.
- 2026-10-15: 1~18 질문·답 완료. 6 → 티켓 39 추가(38 은 리더보드 익명 이름이 이미 사용). 7~14·18 은 Claude 가 Chrome 으로 진행하기로. 메모리 `ask-numbered-all-at-once`, `console-setup-by-claude`.
