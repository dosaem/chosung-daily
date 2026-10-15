import 'dart:async';

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
    expect(store.reserved, {41});
  });

  // 리뷰 r3 D-31-5: 첫 광고의 로드·표시가 끝나기 전에 "결과 보기" 를 다시 열고
  // 닫으면 두 호출이 모두 기록 전의 "아직 안 띄웠다" 를 읽어 같은 퍼즐에서 두
  // 번 뜬다. 기록은 광고가 닫힌 뒤에 남으므로 기록만으로는 못 막는다(US 24).
  test('전면 광고가 떠 있는 동안 시트를 다시 닫아도 퍼즐당 1회다', () async {
    final gate = Completer<void>();
    final ads = FakeAdService()..interstitialGate = gate;
    final store = InMemoryInterstitialStore();
    final container = _container(ads: ads, store: store);
    await container.read(adConsentProvider.future);
    final interstitial = container.read(resultInterstitialProvider)
      ..markSubmitted();

    final first = interstitial.showAfterResultSheet(puzzleId: 41);
    await pumpEventQueue();
    // 시트를 다시 열고 닫았다. 첫 광고는 아직 로드/표시 중이다.
    final second = interstitial.showAfterResultSheet(puzzleId: 41);
    await pumpEventQueue();

    gate.complete();
    expect(await first, isTrue);
    expect(await second, isTrue, reason: '이미 뜬 그 광고의 결과를 같이 받는다');
    expect(ads.interstitialShowCalls, 1, reason: '같은 퍼즐에서 두 번 띄우면 안 된다');
    expect(store.reserved, {41});

    // 광고가 닫힌 뒤의 호출은 기록이 막는다.
    expect(await interstitial.showAfterResultSheet(puzzleId: 41), isFalse);
    expect(ads.interstitialShowCalls, 1);
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
    expect(store.reserved, {41, 42});
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
    expect(store.reserved, isEmpty);
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

  // 리뷰 r1 D-31-1: 오늘 퍼즐은 언어마다 따로다. 설정에서 언어를 바꾸면 다른
  // 퍼즐이 "오늘" 이 되고 되돌릴 수도 있는데, 기억하는 퍼즐이 하나면 왕복할
  // 때마다 같은 퍼즐에서 다시 뜬다.
  test('언어를 왕복해도 퍼즐마다 1회다', () async {
    final ads = FakeAdService();
    final store = InMemoryInterstitialStore();
    final container = _container(ads: ads, store: store);
    await container.read(adConsentProvider.future);
    final interstitial = container.read(resultInterstitialProvider)
      ..markSubmitted();

    // 한국어 퍼즐 41 → 영어 퍼즐 42 를 각각 끝냈다.
    expect(await interstitial.showAfterResultSheet(puzzleId: 41), isTrue);
    expect(await interstitial.showAfterResultSheet(puzzleId: 42), isTrue);

    // 한국어로 돌아와 41 의 "결과 보기" 를 다시 열었다.
    expect(await interstitial.showAfterResultSheet(puzzleId: 41), isFalse);
    expect(await interstitial.showAfterResultSheet(puzzleId: 42), isFalse);
    expect(ads.interstitialShowCalls, 2);
  });

  // 리뷰 r3 D-31-5 정책: 예약은 광고를 요청하기 **전에** 적고 실패해도 풀지
  // 않는다. 풀어 주면 "결과 보기" 를 누를 때마다 실패한 로드를 다시 때린다.
  test('광고가 뜨지 않아도 그 퍼즐의 한 번은 쓴 것이다', () async {
    final ads = FakeAdService(interstitialShows: false);
    final store = InMemoryInterstitialStore();
    final container = _container(ads: ads, store: store);
    await container.read(adConsentProvider.future);
    final interstitial = container.read(resultInterstitialProvider)
      ..markSubmitted();

    expect(await interstitial.showAfterResultSheet(puzzleId: 41), isFalse);
    expect(ads.interstitialShowCalls, 1);
    expect(store.reserved, {41}, reason: '요청 전에 예약했고 실패로 풀지 않는다');

    // 같은 퍼즐의 시트를 다시 닫아도 로드를 또 때리지 않는다.
    expect(await interstitial.showAfterResultSheet(puzzleId: 41), isFalse);
    expect(ads.interstitialShowCalls, 1);
  });

  // 광고가 떠 있는 동안 앱이 죽어도(표시 결과를 못 받는다) 다시 켤 때 또 뜨면
  // 안 된다 — 예약이 요청 전에 적혀 있어야 가능하다.
  test('표시 결과를 받기 전에 이미 예약이 적혀 있다', () async {
    final gate = Completer<void>();
    final ads = FakeAdService()..interstitialGate = gate;
    final store = InMemoryInterstitialStore();
    final container = _container(ads: ads, store: store);
    await container.read(adConsentProvider.future);

    final showing = (container.read(
      resultInterstitialProvider,
    )..markSubmitted()).showAfterResultSheet(puzzleId: 41);
    await pumpEventQueue();

    expect(ads.interstitialShowCalls, 1, reason: '광고는 떠 있다');
    expect(store.reserved, {41}, reason: '표시가 끝나기 전에 예약이 남는다');

    gate.complete();
    expect(await showing, isTrue);
  });
}
