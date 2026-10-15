import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/ads/ad_gate.dart';
import 'package:chosung/ads/ad_service.dart';
import 'package:chosung/permissions/tracking_permission.dart';
import 'package:chosung/subscription/entitlement_provider.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 광고 접점. 기본값이 no-op 인 이유는 `firebaseBootstrapProvider` 와 같다 —
/// `main.dart` 가 실제 구현으로 덮고(`test/config/bootstrap_test.dart` 가
/// 지킨다), 위젯 테스트·골든은 덮지 않아 플랫폼 채널을 타지 않는다.
final adServiceProvider = Provider<AdService>(
  (ref) => const NoopAdService(),
);

/// 이번 실행의 UMP 결과. **앱 시작마다 한 번** 돈다(스펙 §B.21) — 값을 기기에
/// 저장하지 않으므로 오류로 끝난 세션은 다음 시작에 자동으로 다시 묻는다.
///
/// null 은 "아직 안 돌렸다" 다. iOS 는 ATT 선택이 나오기 전까지 여기 머문다 —
/// 온보딩 S6 의 ATT 안내 → 시스템 프롬프트 → UMP 폼 순서를 지키려고 [build]
/// 가 [trackingStatusProvider] 를 watch 한다(선택이 나오면 다시 빌드된다).
class AdConsentNotifier extends AsyncNotifier<UmpStatus?> {
  @override
  Future<UmpStatus?> build() async {
    if (ref.watch(trackingStatusProvider) == TrackingStatus.notDetermined) {
      return null;
    }

    final ads = ref.read(adServiceProvider);
    final UmpStatus status;
    try {
      status = await ads.requestConsent();
    } on Exception {
      // 동의 정보를 못 읽었다 → 이번 세션은 광고 없음. 화면이 깨질 이유는
      // 아니라서 오류로 올리지 않고 "광고 없음" 상태로 내린다.
      return const UmpStatus.failed();
    }

    if (status.canRequestAds) await ads.initialize();
    return status;
  }
}

final adConsentProvider = AsyncNotifierProvider<AdConsentNotifier, UmpStatus?>(
  AdConsentNotifier.new,
);

/// 화면이 읽는 광고 게이트 하나. 세 입력(UMP·ATT·구독 권한)이 바뀌면 다시
/// 계산된다 — 티켓 33 이 권한을 갱신하는 순간 배너 슬롯이 사라지는 게 이것이다.
final adGateProvider = Provider<AdGate>(
  (ref) => adGateFor(
    ump: ref.watch(adConsentProvider).value,
    tracking: ref.watch(trackingStatusProvider),
    // 권한 여부만 떼어 넘긴다 — 게이트는 갱신일을 모르고, 모르면 광고
    // 판정이 날짜 계산에 얽히지 않는다.
    entitled: ref.watch(entitlementProvider)?.active,
  ),
);
