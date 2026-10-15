import 'package:chosung/ads/ad_unit_ids.dart';

/// 빌드 때 주입하는 값들. `--dart-define=API_BASE_URL=https://...` 형태로 넘기고
/// (`.github/workflows/flutter.yml`), 안 넘기면 로컬 개발 기본값을 쓴다.
abstract final class AppEnv {
  /// 로컬 개발 기본값은 Android 에뮬레이터에서 호스트를 가리키는 주소다.
  /// iOS 시뮬레이터·실기기는 `--dart-define` 으로 덮는다.
  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8089/api/v1',
  );

  /// 비어 있으면 Sentry 를 초기화하지 않는다(개발·CI 기본).
  static const sentryDsn = String.fromEnvironment('SENTRY_DSN');

  /// Android 구글 로그인의 `serverClientId` = **웹 클라이언트 ID**(스펙 §A.6
  /// 표). 서버가 이 값을 `aud` 로 검증한다. iOS 는 이 값을 쓰지 않고
  /// `Info.plist` 의 `GIDClientID` 를 쓴다.
  static const googleServerClientId = String.fromEnvironment(
    'GOOGLE_SERVER_CLIENT_ID',
  );

  /// 안 넘겼으면 null — 플러그인에 빈 문자열을 넘기면 "설정은 됐는데 값이
  /// 틀린" 상태가 되어 오류 메시지가 엉뚱해진다.
  static String? get googleServerClientIdOrNull =>
      googleServerClientId.isEmpty ? null : googleServerClientId;

  /// AdMob 유닛 ID. 워크플로가 **플랫폼별 variable 을 한 벌의 이름으로**
  /// 넘기므로(`docs/RELEASE.md "34."`) Dart 쪽에 플랫폼 분기가 없다.
  /// 비어 있으면 테스트 유닛으로 떨어진다(`adUnitIdFor`).
  static const admobBannerAdUnitId = String.fromEnvironment(
    'ADMOB_BANNER_AD_UNIT_ID',
  );
  static const admobInterstitialAdUnitId = String.fromEnvironment(
    'ADMOB_INTERSTITIAL_AD_UNIT_ID',
  );
  static const admobRewardedAdUnitId = String.fromEnvironment(
    'ADMOB_REWARDED_AD_UNIT_ID',
  );

  static String admobAdUnitId(AdFormat format) => switch (format) {
    AdFormat.banner => admobBannerAdUnitId,
    AdFormat.interstitial => admobInterstitialAdUnitId,
    AdFormat.rewarded => admobRewardedAdUnitId,
  };
}
