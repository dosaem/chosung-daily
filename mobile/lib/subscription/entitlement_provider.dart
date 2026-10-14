import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 지금 이 게스트가 광고를 안 봐도 되는가(`/me/stats` 의 `entitlement.active`).
///
/// **null 은 "아직 모른다"** 다 — 시작 직후 `/me/stats` 응답이 오기 전 상태이고,
/// 광고 게이트는 그걸 비구독자로 다룬다(`ad_gate.dart` 참고).
///
/// 이 티켓(31)이 자리를 만들고, 값을 넣는 건 구매(32)와 갱신·타이머(33)다 —
/// 둘이 각자 상태를 들고 있으면 "구매 직후 배너" 와 "권한 만료 뒤 배너" 가
/// 서로 다른 곳을 보게 된다.
class EntitlementNotifier extends Notifier<bool?> {
  @override
  bool? build() => null;

  // 세터로 두지 않는다 — 호출부(`update(active: true)`)가 무엇을 바꾸는지
  // 드러나고, 티켓 33 이 갱신 시각을 같이 넘길 자리도 된다.
  // ignore: use_setters_to_change_properties
  void update({required bool active}) => state = active;
}

final entitlementProvider = NotifierProvider<EntitlementNotifier, bool?>(
  EntitlementNotifier.new,
);
