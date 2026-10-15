import 'package:chosung/api/api_models.dart';
import 'package:chosung/subscription/entitlement_provider.dart';

import 'fake_api_client.dart';

/// 구독 권한을 고정해 끼운다. `initial` 은 "구독자인가" 이고 null 은
/// "아직 모름" 이다(기본값과 같다). 갱신일·유예 라벨까지 필요한 테스트는
/// `value` 로 서버 응답을 그대로 넣는다.
class FakeEntitlement extends EntitlementNotifier {
  FakeEntitlement({bool? initial, Entitlement? value})
    : _value =
          value ??
          (initial == null
              ? null
              : fakeEntitlement(
                  active: initial,
                  until: initial ? DateTime.utc(2026, 11) : null,
                ));

  final Entitlement? _value;

  @override
  Entitlement? build() => _value;
}
