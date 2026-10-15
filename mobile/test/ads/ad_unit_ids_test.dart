import 'package:chosung/ads/ad_unit_ids.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('릴리스 빌드는 --dart-define 으로 받은 유닛을 쓴다', () {
    expect(
      adUnitIdFor(
        format: AdFormat.banner,
        isIos: false,
        useTestIds: false,
        configured: 'ca-app-pub-1/android-banner',
      ),
      'ca-app-pub-1/android-banner',
    );
  });

  test('디버그 빌드는 설정값이 있어도 Google 테스트 유닛을 쓴다', () {
    final id = adUnitIdFor(
      format: AdFormat.interstitial,
      isIos: true,
      useTestIds: true,
      configured: 'ca-app-pub-1/real-interstitial',
    );

    expect(id, isNot('ca-app-pub-1/real-interstitial'));
    expect(id, startsWith(testAdPublisherPrefix));
  });

  // 워크플로가 variable 을 못 넘겼을 때 실제 유닛 자리에 빈 문자열이 들어가면
  // 광고 요청이 조용히 실패한다 — 테스트 유닛으로 떨어뜨려 눈에 보이게 한다.
  test('설정값이 비어 있으면 릴리스에서도 테스트 유닛으로 떨어진다', () {
    expect(
      adUnitIdFor(
        format: AdFormat.rewarded,
        isIos: false,
        useTestIds: false,
        configured: '',
      ),
      startsWith(testAdPublisherPrefix),
    );
  });

  test('테스트 유닛은 플랫폼·포맷마다 다른 값이다', () {
    final ids = {
      for (final isIos in [true, false])
        for (final format in AdFormat.values)
          adUnitIdFor(
            format: format,
            isIos: isIos,
            useTestIds: true,
            configured: '',
          ),
    };

    expect(ids, hasLength(AdFormat.values.length * 2));
  });
}
