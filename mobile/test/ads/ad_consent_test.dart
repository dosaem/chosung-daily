import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/ads/ad_gate.dart';
import 'package:chosung/ads/ad_providers.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/permissions/tracking_permission.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

import '../fakes/fake_ad_service.dart';
import '../fakes/fake_permissions.dart';

ProviderContainer _container({
  required FakeAdService ads,
  bool isIos = false,
  TrackingStatus trackingResult = TrackingStatus.authorized,
}) {
  final container = ProviderContainer(
    overrides: [
      isIosProvider.overrideWithValue(isIos),
      adServiceProvider.overrideWithValue(ads),
      trackingAuthorizationProvider.overrideWithValue(
        FakeTrackingAuthorization(result: trackingResult),
      ),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  test('동의를 받으면 광고 SDK 를 초기화한다', () async {
    final ads = FakeAdService(
      consent: const UmpStatus(
        consent: ConsentStatus.obtained,
        privacyOptionsRequired: true,
      ),
    );
    final container = _container(ads: ads);

    final status = await container.read(adConsentProvider.future);

    expect(status?.consent, ConsentStatus.obtained);
    expect(ads.consentRequests, 1);
    expect(ads.initializeCalls, 1);
  });

  test('동의하지 않으면 SDK 를 초기화하지 않는다', () async {
    final ads = FakeAdService(
      consent: const UmpStatus(
        consent: ConsentStatus.required,
        privacyOptionsRequired: true,
      ),
    );
    final container = _container(ads: ads);

    await container.read(adConsentProvider.future);

    expect(ads.consentRequests, 1);
    expect(ads.initializeCalls, 0);
  });

  test('동의 조회가 실패하면 실패 상태를 남기고 초기화하지 않는다', () async {
    final ads = FakeAdService(consentError: Exception('no network'));
    final container = _container(ads: ads);

    final status = await container.read(adConsentProvider.future);

    expect(status?.consent, ConsentStatus.unknown);
    expect(ads.initializeCalls, 0);
    expect(container.read(adGateProvider).canLoadAds, isFalse);
  });

  // "오류 시 이번 세션 광고 없음, 다음 시작 재시도"(스펙 §B.21). 다음 시작 =
  // 이 provider 의 다시 빌드 — 상태를 캐시하지 않으니 그때 다시 묻는다.
  test('다시 시작하면 동의를 다시 묻는다', () async {
    final ads = FakeAdService(consentError: Exception('no network'));
    final container = _container(ads: ads);
    await container.read(adConsentProvider.future);

    ads
      ..consentError = null
      ..consent = const UmpStatus(
        consent: ConsentStatus.obtained,
        privacyOptionsRequired: false,
      );
    container.invalidate(adConsentProvider);
    final status = await container.read(adConsentProvider.future);

    expect(ads.consentRequests, 2);
    expect(status?.consent, ConsentStatus.obtained);
    expect(container.read(adGateProvider).canLoadAds, isTrue);
  });

  group('iOS', () {
    test('ATT 선택 전에는 UMP 폼을 띄우지 않는다', () async {
      final ads = FakeAdService();
      final container = _container(ads: ads, isIos: true);

      expect(await container.read(adConsentProvider.future), isNull);
      expect(ads.consentRequests, 0);
      expect(container.read(adGateProvider).canLoadAds, isFalse);
    });

    test('ATT 결과가 나온 뒤에 UMP 를 돌린다', () async {
      final ads = FakeAdService(
        consent: const UmpStatus(
          consent: ConsentStatus.obtained,
          privacyOptionsRequired: true,
        ),
      );
      final container = _container(
        ads: ads,
        isIos: true,
        trackingResult: TrackingStatus.denied,
      );
      await container.read(adConsentProvider.future);

      await container.read(trackingStatusProvider.notifier).request();
      final status = await container.read(adConsentProvider.future);

      expect(ads.consentRequests, 1);
      expect(status?.consent, ConsentStatus.obtained);
      // ATT 거부도 "선택이 끝났다" 다 — UMP 와 별개 상태(스펙 §B.21).
      expect(container.read(adGateProvider).canLoadAds, isTrue);
    });
  });
}
