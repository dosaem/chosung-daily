import 'package:chosung/subscription/entitlement_provider.dart';

/// 구독 권한을 고정해 끼운다. "구독자" 테스트는 이걸 true 로 덮고,
/// "아직 모름" 은 null 로 둔다(기본값과 같다).
class FakeEntitlement extends EntitlementNotifier {
  FakeEntitlement({this.initial});

  final bool? initial;

  @override
  bool? build() => initial;
}
