import 'package:chosung/ads/ad_gate.dart';
import 'package:flutter/widgets.dart';

/// 보상형 광고 한 번의 결과. **"못 띄웠다" 와 "안 끝까지 봤다" 를 가른다** —
/// 앞은 버튼을 끄고(다시 눌러도 같은 실패다) 뒤는 다시 누를 수 있어야 한다.
enum RewardedOutcome {
  /// 끝까지 봐서 보상을 얻었다 → 힌트를 연다.
  earned,

  /// 떴지만 보상 전에 닫았다 → 안내만 하고 버튼은 살려 둔다.
  dismissed,

  /// 로드·표시가 실패해 광고 자체를 못 띄웠다 → 이 퍼즐에서는 버튼을 끈다.
  unavailable,
}

/// 로드된 배너 하나. 위젯과 해제를 같이 들고 다닌다 — 화면이 `BannerAd` 를
/// 직접 알면 테스트에서 광고 SDK 를 끼울 수밖에 없다.
abstract interface class LoadedBannerAd {
  /// 예약된 슬롯 안에 그릴 위젯.
  Widget get view;

  /// 네이티브 광고 객체를 놓는다. 폭이 바뀌어 다시 로드할 때와 화면이 사라질
  /// 때 반드시 불러야 한다(안 부르면 네이티브 쪽 배너가 그대로 남는다).
  Future<void> dispose();
}

/// 광고 접점(스펙 §B.20 — 서비스 클래스 하나 + 테스트 no-op).
///
/// UMP 동의·SDK 초기화·세 광고 포맷이 전부 이 경계 뒤에 있다. 화면은
/// `google_mobile_ads` 를 import 하지 않는다 — 위젯 테스트가 플랫폼 채널을
/// 타지 않으려면 끼울 자리가 한 곳이어야 한다.
abstract interface class AdService {
  /// UMP `requestConsentInfoUpdate` → 필요하면 폼 → 동의 상태를 읽어온다.
  /// 실패하면 던진다(호출부가 [UmpStatus.failed] 로 바꾼다).
  Future<UmpStatus> requestConsent();

  /// `MobileAds.initialize`. `canRequestAds` 가 true 일 때만 부른다.
  Future<void> initialize();

  /// S4 "광고 개인정보 설정" → UMP privacy options 폼.
  Future<void> showPrivacyOptionsForm();

  /// 슬롯 폭에 맞춘 어댑티브 배너. 로드가 실패하면 null — 슬롯은 예약된
  /// 높이를 그대로 비워 둔다(OVERRIDES §5).
  Future<LoadedBannerAd?> loadBanner({required double width});

  /// 전면 광고를 로드해서 띄운다. 실제로 떴으면 true.
  Future<bool> showInterstitial();

  /// 보상형 광고를 띄운다.
  Future<RewardedOutcome> showRewarded();
}

/// 아무 광고도 띄우지 않는 구현. 광고 SDK 를 끼우지 않은 트리(위젯 테스트·
/// 골든)가 기본으로 쓰고, 동의 상태도 "모름" 이라 게이트가 전부 닫힌다.
class NoopAdService implements AdService {
  const NoopAdService();

  @override
  Future<UmpStatus> requestConsent() async => const UmpStatus.failed();

  @override
  Future<void> initialize() async {}

  @override
  Future<void> showPrivacyOptionsForm() async {}

  @override
  Future<LoadedBannerAd?> loadBanner({required double width}) async => null;

  @override
  Future<bool> showInterstitial() async => false;

  @override
  Future<RewardedOutcome> showRewarded() async => RewardedOutcome.unavailable;
}
