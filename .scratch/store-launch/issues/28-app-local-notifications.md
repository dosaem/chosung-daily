# 28: 로컬 알림 — 일일 반복·7일 리마인더·순수 예약 계획·KST 취소 규칙·탭 라우팅·S4 설정

**What to build:** 플레이어가 고른 로컬 시각(기본 09:00)에 매일 알림이 오고, 그 날(KST 퍼즐 날짜) 아직 안 풀었으면 20:00 에 리마인더가 한 번 더 온다. 이 기기에서 이미 푼 날짜의 리마인더는 오지 않고 다음 날 것은 그대로 온다. 알림을 탭하면 앱이 꺼져 있었든 뒤에 있었든 오늘 탭으로 가서 최신 퍼즐이 뜬다. S4 설정에서 시각·리마인더 on/off 를 바꾸고 권한 거부 상태를 본다.

**Blocked by:** 23, 25, 26

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.9, US 35~40, 미정 6. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] 예약 계획 순수 함수: (지금, 설정{시각, 리마인더 on}, 완료한 KST 퍼즐 날짜 집합, 기기 시간대) → 원하는 (id, 발화 시각) 집합. 일일 = ID 고정 반복 1개(`matchDateTimeComponents: time`), 리마인더 = 앞으로 7일치 1회성(ID 날짜 기반), 발화 시각의 KST 날짜가 완료 집합에 있으면 제외, 일일과 같은 시각이면 제외, 총 ≤8
- [ ] 단위 테스트: 오늘 제외·내일 유지, 미주 시간대 KST 경계, 두 언어 중 하나 완료, 7일 롤링 보충, 대기 ≤8, 시간대 변경 재계산
- [ ] OS 대기 목록과 diff(취소/추가) 하는 동기화 함수를 앱 시작·포그라운드 복귀·퍼즐 완료·알림 탭·설정 변경·22 의 게스트 토큰 Provider 변경(계정·백업 코드 전환, 담당 티켓 27)을 구독해서 호출 — 27 산출물에 의존하지 않고 22 의 토큰 상태만 구독한다. Android `inexactAllowWhileIdle`, exact alarm 권한 매니페스트 미포함, `timezone` 로컬 존. 권한 상태는 26 의 결과 사용
- [ ] 탭 처리: 실행 중 `onDidReceiveNotificationResponse`, 종료 상태 `getNotificationAppLaunchDetails` → go_router 오늘 탭 + `GET /puzzles/today` 재조회
- [ ] 25 의 S4 알림 자리를 채움: 일일 시각 picker, 리마인더 스위치, 권한 거부 시 "알림 꺼짐 — 시스템 설정에서 켜기"(설정 앱 열기). `audit.native` 통과, 목업 `e4_records` 설정 리스트 대비(알림 행은 목업 없음 — 명세+토큰)
- [ ] 실기기 체크리스트(iOS·Android): 정답 후 같은 날 20:00 없음, 다음 날 20:00 있음, 앱 종료 상태 탭 cold/warm — `docs/RELEASE.md` 에 자기 절 추가(없으면 만든다; 실행은 사람). README Flutter 절에 "서버 푸시 대신 로컬 알림" 근거

## 리뷰 노트 (plan-review r1)

- P2-3/P3-5: Blocked by 에 25 추가(S4 설정 호스트), 26(권한 상태)
- P2-10: `audit.native` 완료 조건 추가
- P1-15/P3-16: 참조 목업 명시
- P1-13: RELEASE.md 없으면 만들고 자기 절만
- (r2) P1-26/P3-21: 알림 재계산 연결 주체는 이 티켓이며 22 의 게스트 토큰 Provider 를 구독하므로 27 에 의존하지 않음을 명시
