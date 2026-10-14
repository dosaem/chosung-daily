import 'package:chosung/ads/ad_gate.dart';
import 'package:chosung/ads/ad_service.dart';
import 'package:flutter/material.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

/// 테스트용 [AdService]. 광고를 "띄웠다" 를 기록하고, 결과(동의 상태·로드
/// 성공·보상 획득)를 테스트가 넣는다. 플랫폼 채널은 타지 않는다.
class FakeAdService implements AdService {
  FakeAdService({
    this.consent = const UmpStatus(
      consent: ConsentStatus.notRequired,
      privacyOptionsRequired: false,
    ),
    this.consentError,
    this.bannerLoads = true,
    this.interstitialShows = true,
    this.rewardEarned = true,
  });

  UmpStatus consent;
  Exception? consentError;

  /// 배너 로드가 성공하는가. false 면 슬롯이 비어 있어야 한다.
  bool bannerLoads;

  /// 전면 광고가 실제로 떴는가(로드 실패·표시 실패면 false).
  bool interstitialShows;

  /// 보상형을 끝까지 봤는가. false = 로드 실패 또는 중간에 닫음.
  bool rewardEarned;

  int consentRequests = 0;
  int initializeCalls = 0;
  int privacyOptionsForms = 0;
  int interstitialShowCalls = 0;
  int rewardedShowCalls = 0;

  /// `loadBanner` 가 받은 폭들 — 폭이 바뀔 때 몇 번 다시 요청하는지 본다.
  final List<double> bannerWidths = [];

  /// 해제된 배너 수. 다시 로드할 때 이전 광고를 버리는지 본다.
  int bannerDisposals = 0;

  @override
  Future<UmpStatus> requestConsent() async {
    consentRequests++;
    if (consentError case final error?) throw error;
    return consent;
  }

  @override
  Future<void> initialize() async => initializeCalls++;

  @override
  Future<void> showPrivacyOptionsForm() async => privacyOptionsForms++;

  @override
  Future<LoadedBannerAd?> loadBanner({required double width}) async {
    bannerWidths.add(width);
    if (!bannerLoads) return null;
    return _FakeBanner(this, width);
  }

  @override
  Future<bool> showInterstitial() async {
    interstitialShowCalls++;
    return interstitialShows;
  }

  @override
  Future<bool> showRewarded() async {
    rewardedShowCalls++;
    return rewardEarned;
  }
}

class _FakeBanner implements LoadedBannerAd {
  _FakeBanner(this._owner, this.width);

  final FakeAdService _owner;
  final double width;

  @override
  Widget get view => SizedBox(key: const Key('fake-banner'), width: width);

  @override
  Future<void> dispose() async => _owner.bannerDisposals++;
}
