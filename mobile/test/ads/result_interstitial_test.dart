import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/ads/ad_gate.dart';
import 'package:chosung/ads/ad_providers.dart';
import 'package:chosung/ads/interstitial_store.dart';
import 'package:chosung/ads/result_interstitial.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/permissions/tracking_permission.dart';
import 'package:chosung/subscription/entitlement_provider.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

import '../fakes/fake_ad_service.dart';
import '../fakes/fake_entitlement.dart';
import '../fakes/fake_permissions.dart';
import '../fakes/in_memory_interstitial_store.dart';

const _consented = UmpStatus(
  consent: ConsentStatus.obtained,
  privacyOptionsRequired: false,
);

ProviderContainer _container({
  required FakeAdService ads,
  required InMemoryInterstitialStore store,
  bool? entitled = false,
  UmpStatus consent = _consented,
}) {
  ads.consent = consent;
  final container = ProviderContainer(
    overrides: [
      isIosProvider.overrideWithValue(false),
      trackingAuthorizationProvider.overrideWithValue(
        FakeTrackingAuthorization(saved: TrackingStatus.notSupported),
      ),
      adServiceProvider.overrideWithValue(ads),
      interstitialStoreProvider.overrideWithValue(store),
      entitlementProvider.overrideWith(
        () => FakeEntitlement(initial: entitled),
      ),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  // US 25: 앱을 켜자마자 광고로 시작하지 않는다. 다른 기기에서 이미 끝낸
  // 퍼즐을 열어 "결과 보기" 를 눌러도 같다.
  test('첫 제출 전에는 전면 광고를 띄우지 않는다', () async {
    final ads = FakeAdService();
    final container = _container(ads: ads, store: InMemoryInterstitialStore());
    await container.read(adConsentProvider.future);

    final shown = await container
        .read(resultInterstitialProvider)
        .showAfterResultSheet(puzzleId: 41);

    expect(shown, isFalse);
    expect(ads.interstitialShowCalls, 0);
  });

  test('제출한 뒤 결과 시트를 닫으면 1회 띄운다', () async {
    final ads = FakeAdService();
    final store = InMemoryInterstitialStore();
    final container = _container(ads: ads, store: store);
    await container.read(adConsentProvider.future);
    final interstitial = container.read(resultInterstitialProvider)
      ..markSubmitted();

    expect(await interstitial.showAfterResultSheet(puzzleId: 41), isTrue);
    expect(ads.interstitialShowCalls, 1);
    expect(store.puzzleId, 41);
  });

  test('같은 퍼즐에서 시트를 다시 열어도 두 번 띄우지 않는다', () async {
    final ads = FakeAdService();
    final container = _container(ads: ads, store: InMemoryInterstitialStore());
    await container.read(adConsentProvider.future);
    final interstitial = container.read(resultInterstitialProvider)
      ..markSubmitted();

    await interstitial.showAfterResultSheet(puzzleId: 41);
    expect(await interstitial.showAfterResultSheet(puzzleId: 41), isFalse);
    expect(ads.interstitialShowCalls, 1);
  });

  // 플래그는 기기에 남는다 — 앱을 다시 켜도 그 퍼즐에는 다시 안 뜬다.
  test('이미 띄운 퍼즐은 다시 시작해도 건너뛴다', () async {
    final ads = FakeAdService();
    final container = _container(
      ads: ads,
      store: InMemoryInterstitialStore(puzzleId: 41),
    );
    await container.read(adConsentProvider.future);

    final shown = await (container.read(
      resultInterstitialProvider,
    )..markSubmitted()).showAfterResultSheet(puzzleId: 41);

    expect(shown, isFalse);
    expect(ads.interstitialShowCalls, 0);
  });

  test('다음 퍼즐에서는 다시 띄운다', () async {
    final ads = FakeAdService();
    final store = InMemoryInterstitialStore(puzzleId: 41);
    final container = _container(ads: ads, store: store);
    await container.read(adConsentProvider.future);

    final shown = await (container.read(
      resultInterstitialProvider,
    )..markSubmitted()).showAfterResultSheet(puzzleId: 42);

    expect(shown, isTrue);
    expect(store.puzzleId, 42);
  });

  test('구독자는 전면 광고가 없다 (US 26)', () async {
    final ads = FakeAdService();
    final store = InMemoryInterstitialStore();
    final container = _container(ads: ads, store: store, entitled: true);
    await container.read(adConsentProvider.future);

    final shown = await (container.read(
      resultInterstitialProvider,
    )..markSubmitted()).showAfterResultSheet(puzzleId: 41);

    expect(shown, isFalse);
    expect(ads.interstitialShowCalls, 0);
    expect(store.puzzleId, isNull);
  });

  test('동의가 없으면 전면 광고도 없다', () async {
    final ads = FakeAdService();
    final container = _container(
      ads: ads,
      store: InMemoryInterstitialStore(),
      consent: const UmpStatus.failed(),
    );
    await container.read(adConsentProvider.future);

    final shown = await (container.read(
      resultInterstitialProvider,
    )..markSubmitted()).showAfterResultSheet(puzzleId: 41);

    expect(shown, isFalse);
    expect(ads.interstitialShowCalls, 0);
  });

  // 로드 실패를 "띄웠다" 로 기록하면 그 퍼즐의 기회를 날린다.
  test('광고가 뜨지 않으면 퍼즐 플래그를 남기지 않는다', () async {
    final ads = FakeAdService(interstitialShows: false);
    final store = InMemoryInterstitialStore();
    final container = _container(ads: ads, store: store);
    await container.read(adConsentProvider.future);

    final shown = await (container.read(
      resultInterstitialProvider,
    )..markSubmitted()).showAfterResultSheet(puzzleId: 41);

    expect(shown, isFalse);
    expect(ads.interstitialShowCalls, 1);
    expect(store.puzzleId, isNull);
  });
}
