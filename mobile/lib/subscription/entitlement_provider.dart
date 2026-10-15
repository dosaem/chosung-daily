import 'package:chosung/api/api_models.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 지금 이 게스트의 구독 권한 — 서버가 돌려준 [Entitlement] 그대로.
///
/// **null 은 "아직 모른다"** 다 — 시작 직후 `/me/stats`·verify 응답이 오기 전
/// 상태이고, 광고 게이트는 그걸 비구독자로 다룬다(`ad_gate.dart` 참고).
///
/// 이 티켓(31)이 자리를 만들고, 값을 넣는 건 구매(32)와 갱신·타이머(33)다 —
/// 둘이 각자 상태를 들고 있으면 "구매 직후 배너" 와 "권한 만료 뒤 배너" 가
/// 서로 다른 곳을 보게 된다.
///
/// 티켓 32 가 `bool?` 에서 응답 전체로 넓혔다. S4 구독 카드가 "광고 제거 ·
/// 10/31 갱신" 과 "유예 10/20 까지" 를 그려야 하는데(SCREENS S4), 권한 여부와
/// 갱신일을 다른 provider 에 두면 둘이 어긋난 순간이 화면에 남는다.
class EntitlementNotifier extends Notifier<Entitlement?> {
  @override
  Entitlement? build() => null;

  // 세터로 두지 않는다 — 호출부(`update(entitlement)`)가 무엇을 바꾸는지
  // 드러난다.
  // ignore: use_setters_to_change_properties
  void update(Entitlement entitlement) => state = entitlement;
}

final entitlementProvider = NotifierProvider<EntitlementNotifier, Entitlement?>(
  EntitlementNotifier.new,
);
