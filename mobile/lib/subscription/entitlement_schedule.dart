/// 다음 `/me/stats` 재조회 시각. `null` 은 **걸 타이머가 없다**는 뜻이다.
///
/// 입력은 셋 — 지금, 서버가 알려준 [nextCheckAt](`entitlement.next_check_at` =
/// `last_verified_at + 1h`), 앱이 포그라운드인가 — 이고 판정은 셋이다
/// (스펙 §A.8 재조회 (a), US 30c):
///
/// - **백그라운드면 없음.** 안 보이는 앱의 광고 상태를 맞출 이유가 없고,
///   복귀할 때 한 번 부르면 떠나 있던 사이의 변화가 전부 반영된다. 멈추지
///   않으면 OS 가 앱을 깨우지 않는 동안 쌓인 타이머가 복귀 순간 한꺼번에
///   터진다.
/// - **[nextCheckAt] 이 없으면 없음.** 구독 행이 아예 없는 게스트다 — 다시
///   물어봐도 서버가 볼 행이 없고, 권한이 생기는 길은 구매 응답(티켓 32)이다.
/// - **그 밖에는 [nextCheckAt], 이미 지났으면 지금.** 경계는 **포함**이다
///   (`now >= next_check_at` — 미정 19). 서버 `is_recheck_due` 도 같은 경계라
///   정각에 부른 호출이 곧 스토어 재조회다. "지났으니 지금" 으로 들어오는 건
///   백그라운드에 있던 사이 그 시각이 지나간 경우다.
DateTime? nextEntitlementCheck({
  required DateTime now,
  required DateTime? nextCheckAt,
  required bool foreground,
}) {
  if (!foreground || nextCheckAt == null) return null;
  return nextCheckAt.isAfter(now) ? nextCheckAt : now;
}
