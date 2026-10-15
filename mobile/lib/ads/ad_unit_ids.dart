/// 쓰는 광고 포맷 셋. 유닛 ID 는 포맷·플랫폼마다 다르다.
enum AdFormat { banner, interstitial, rewarded }

/// Google 테스트 광고의 퍼블리셔 ID. 실제 유닛인지 테스트 유닛인지는 이
/// 접두사로 구분한다.
const String testAdPublisherPrefix = 'ca-app-pub-3940256099942544/';

/// https://developers.google.com/admob/android/test-ads (어댑티브 배너 유닛).
const Map<AdFormat, String> _androidTestUnits = {
  AdFormat.banner: '${testAdPublisherPrefix}9214589741',
  AdFormat.interstitial: '${testAdPublisherPrefix}1033173712',
  AdFormat.rewarded: '${testAdPublisherPrefix}5224354917',
};

/// https://developers.google.com/admob/ios/test-ads
const Map<AdFormat, String> _iosTestUnits = {
  AdFormat.banner: '${testAdPublisherPrefix}2435281174',
  AdFormat.interstitial: '${testAdPublisherPrefix}4411468910',
  AdFormat.rewarded: '${testAdPublisherPrefix}1712485313',
};

/// 이 빌드가 쓸 광고 유닛 ID.
///
/// [configured] 는 `--dart-define=ADMOB_*_AD_UNIT_ID`(워크플로가 플랫폼별
/// variable 을 한 벌의 이름으로 넘긴다 — `docs/RELEASE.md "34."`).
///
/// [useTestIds] 는 디버그 빌드다. 개발 중에 실제 유닛을 때리면 무효 트래픽이라
/// AdMob 계정이 정지된다. 설정값이 **비어 있을 때도** 테스트 유닛으로 떨어진다 —
/// 빈 유닛 ID 로 요청하면 광고가 조용히 안 나와서 원인을 찾기 어렵다.
String adUnitIdFor({
  required AdFormat format,
  required bool isIos,
  required bool useTestIds,
  required String configured,
}) {
  if (!useTestIds && configured.isNotEmpty) return configured;
  return (isIos ? _iosTestUnits : _androidTestUnits)[format]!;
}
