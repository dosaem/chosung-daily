# 27: 로컬 알림 — 일일 반복·7일 리마인더·순수 예약 계획·KST 취소 규칙·탭 라우팅

**What to build:** 플레이어가 고른 로컬 시각(기본 09:00)에 매일 알림이 오고, 그 날(KST 퍼즐 날짜) 아직 안 풀었으면 20:00 에 리마인더가 한 번 더 온다. 이 기기에서 이미 푼 날짜의 리마인더는 오지 않고 다음 날 것은 그대로 온다. 알림을 탭하면 앱이 꺼져 있었든 뒤에 있었든 오늘 탭으로 가서 최신 퍼즐이 뜬다. 설정에서 시각·리마인더 on/off 를 바꾸고 권한 거부 상태를 본다.

**Blocked by:** 23, 25

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.9, US 35~40, 미정 6. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] 예약 계획 순수 함수: (지금, 설정{시각, 리마인더 on}, 완료한 KST 퍼즐 날짜 집합, 기기 시간대) → 원하는 (id, 발화 시각) 집합. 일일 = ID 고정 반복 1개(`matchDateTimeComponents: time`), 리마인더 = 앞으로 7일치 1회성(ID 날짜 기반), 발화 시각의 KST 날짜가 완료 집합에 있으면 제외, 일일과 같은 시각이면 제외, 총 ≤8
- [ ] 단위 테스트: 오늘 제외·내일 유지, 미주 시간대 KST 경계, 두 언어 중 하나 완료, 7일 롤링 보충, 대기 ≤8, 시간대 변경 재계산
- [ ] OS 대기 목록과 diff(취소/추가) 하는 동기화 함수를 앱 시작·포그라운드 복귀·퍼즐 완료·알림 탭·설정 변경에서 호출. Android `inexactAllowWhileIdle`, exact alarm 권한 매니페스트 미포함, `timezone` 로컬 존
- [ ] 탭 처리: 실행 중 `onDidReceiveNotificationResponse`, 종료 상태 `getNotificationAppLaunchDetails` → go_router 오늘 탭 + `GET /puzzles/today` 재조회
- [ ] S4 설정: 일일 시각 picker, 리마인더 스위치, 권한 거부 시 "알림 꺼짐 — 시스템 설정에서 켜기"(설정 앱 열기)
- [ ] 실기기 체크리스트(iOS·Android): 정답 후 같은 날 20:00 없음, 다음 날 20:00 있음, 앱 종료 상태 탭 cold/warm — `docs/RELEASE.md` 에 항목 추가(실행은 사람). README Flutter 절에 "서버 푸시 대신 로컬 알림" 근거
