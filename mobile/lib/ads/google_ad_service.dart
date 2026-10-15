import 'dart:async';

import 'package:chosung/ads/ad_gate.dart';
import 'package:chosung/ads/ad_service.dart';
import 'package:chosung/ads/ad_unit_ids.dart';
import 'package:chosung/ads/banner_size.dart';
import 'package:chosung/config/app_env.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

/// `google_mobile_ads` 구현. 플랫폼 채널을 타므로 **테스트는 이 클래스를
/// 끼우지 않는다** — `main.dart` 만 이걸 넣고(`adServiceProvider` 기본값은
/// [NoopAdService]), 테스트는 `FakeAdService` 를 쓴다.
///
/// SDK 의 콜백 API 를 전부 Future 로 바꿔 둔다. 광고 하나의 수명(로드 → 표시
/// → 닫힘)이 호출부에서 `await` 한 줄로 보이지 않으면, "전면 광고가 닫힌 뒤"
/// 같은 순서를 화면마다 콜백으로 다시 짜야 한다.
class GoogleAdService implements AdService {
  GoogleAdService({required this.isIos, this.useTestIds = kDebugMode});

  final bool isIos;

  /// 디버그 빌드는 Google 테스트 유닛을 쓴다(실제 유닛을 때리면 무효 트래픽).
  final bool useTestIds;

  @override
  Future<UmpStatus> requestConsent() async {
    await _requestConsentInfoUpdate();
    await _loadAndShowFormIfRequired();

    final consent = ConsentInformation.instance;
    return UmpStatus(
      consent: await consent.getConsentStatus(),
      privacyOptionsRequired:
          await consent.getPrivacyOptionsRequirementStatus() ==
          PrivacyOptionsRequirementStatus.required,
    );
  }

  @override
  Future<void> initialize() => MobileAds.instance.initialize();

  @override
  Future<void> showPrivacyOptionsForm() async {
    final dismissed = Completer<void>();
    // 폼이 오류로 끝나도 설정 화면이 멈추면 안 된다 — 오류는 폼이 직접
    // 보여주고, 여기서는 "닫혔다" 만 기다린다.
    await ConsentForm.showPrivacyOptionsForm((_) => dismissed.complete());
    return dismissed.future;
  }

  @override
  Future<LoadedBannerAd?> loadBanner({required double width}) async {
    final size = bannerSizeWithin(
      width: width,
      adaptive: await AdSize.getLargeAnchoredAdaptiveBannerAdSize(
        width.truncate(),
      ),
    );

    final loaded = Completer<LoadedBannerAd?>();
    final banner = BannerAd(
      size: size,
      adUnitId: _adUnitId(AdFormat.banner),
      request: const AdRequest(),
      listener: BannerAdListener(
        onAdLoaded: (ad) {
          if (!loaded.isCompleted) {
            loaded.complete(_GoogleBannerAd(ad as BannerAd, size));
          }
        },
        onAdFailedToLoad: (ad, error) {
          unawaited(ad.dispose());
          if (!loaded.isCompleted) loaded.complete(null);
        },
      ),
    );
    await banner.load();
    return loaded.future;
  }

  @override
  Future<bool> showInterstitial() async {
    final ad = await _loadInterstitial();
    if (ad == null) return false;

    final finished = Completer<bool>();
    ad.fullScreenContentCallback = FullScreenContentCallback(
      onAdDismissedFullScreenContent: (ad) {
        unawaited(ad.dispose());
        if (!finished.isCompleted) finished.complete(true);
      },
      onAdFailedToShowFullScreenContent: (ad, error) {
        unawaited(ad.dispose());
        if (!finished.isCompleted) finished.complete(false);
      },
    );
    await ad.show();
    return finished.future;
  }

  @override
  Future<RewardedOutcome> showRewarded() async {
    final ad = await _loadRewarded();
    if (ad == null) return RewardedOutcome.unavailable;

    var earned = false;
    final finished = Completer<RewardedOutcome>();
    ad.fullScreenContentCallback = FullScreenContentCallback(
      // 보상은 **닫힐 때** 확정한다 — 중간에 닫으면 보상 콜백이 안 오고,
      // 끝까지 봤으면 닫히기 전에 이미 와 있다.
      onAdDismissedFullScreenContent: (ad) {
        unawaited(ad.dispose());
        if (!finished.isCompleted) {
          finished.complete(
            earned ? RewardedOutcome.earned : RewardedOutcome.dismissed,
          );
        }
      },
      onAdFailedToShowFullScreenContent: (ad, error) {
        unawaited(ad.dispose());
        if (!finished.isCompleted) {
          finished.complete(RewardedOutcome.unavailable);
        }
      },
    );
    await ad.show(onUserEarnedReward: (ad, reward) => earned = true);
    return finished.future;
  }

  Future<void> _requestConsentInfoUpdate() {
    final updated = Completer<void>();
    ConsentInformation.instance.requestConsentInfoUpdate(
      ConsentRequestParameters(),
      updated.complete,
      (error) => updated.completeError(_AdConsentException(error)),
    );
    return updated.future;
  }

  /// 동의가 필요한 지역에서만 폼이 뜬다. 오류면 던진다 — 이번 세션은 광고
  /// 없이 가고 다음 시작에 다시 묻는다(스펙 §B.21).
  Future<void> _loadAndShowFormIfRequired() async {
    final dismissed = Completer<void>();
    await ConsentForm.loadAndShowConsentFormIfRequired((error) {
      if (error == null) {
        dismissed.complete();
      } else {
        dismissed.completeError(_AdConsentException(error));
      }
    });
    return dismissed.future;
  }

  Future<InterstitialAd?> _loadInterstitial() {
    final loaded = Completer<InterstitialAd?>();
    unawaited(
      InterstitialAd.load(
        adUnitId: _adUnitId(AdFormat.interstitial),
        request: const AdRequest(),
        adLoadCallback: InterstitialAdLoadCallback(
          onAdLoaded: loaded.complete,
          onAdFailedToLoad: (error) => loaded.complete(null),
        ),
      ),
    );
    return loaded.future;
  }

  Future<RewardedAd?> _loadRewarded() {
    final loaded = Completer<RewardedAd?>();
    unawaited(
      RewardedAd.load(
        adUnitId: _adUnitId(AdFormat.rewarded),
        request: const AdRequest(),
        rewardedAdLoadCallback: RewardedAdLoadCallback(
          onAdLoaded: loaded.complete,
          onAdFailedToLoad: (error) => loaded.complete(null),
        ),
      ),
    );
    return loaded.future;
  }

  String _adUnitId(AdFormat format) => adUnitIdFor(
    format: format,
    isIos: isIos,
    useTestIds: useTestIds,
    configured: AppEnv.admobAdUnitId(format),
  );
}

/// UMP 쪽 실패. `adConsentProvider` 가 이걸 받아 [UmpStatus.failed] 로 바꾼다.
class _AdConsentException implements Exception {
  const _AdConsentException(this.error);

  final FormError error;

  @override
  String toString() => 'UMP ${error.errorCode}: ${error.message}';
}

class _GoogleBannerAd implements LoadedBannerAd {
  const _GoogleBannerAd(this._ad, this._size);

  final BannerAd _ad;
  final AdSize _size;

  @override
  Widget get view => SizedBox(
    width: _size.width.toDouble(),
    height: _size.height.toDouble(),
    child: AdWidget(ad: _ad),
  );

  @override
  Future<void> dispose() => _ad.dispose();
}
