import 'package:chosung/ads/banner_size.dart';
import 'package:chosung/widgets/ad_banner_slot.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

AnchoredAdaptiveBannerAdSize adaptive({
  required int width,
  required int height,
}) => AnchoredAdaptiveBannerAdSize(null, width: width, height: height);

void main() {
  test('예약 높이에 들어가는 어댑티브 크기는 그대로 쓴다', () {
    final size = bannerSizeWithin(
      width: 390,
      adaptive: adaptive(width: 390, height: 50),
    );

    expect(size.width, 390);
    expect(size.height, 50);
  });

  // 24 의 예약 높이는 잠정값이다(스펙 미정 24). SDK 가 더 높은 값을 주면
  // 슬롯이 넘치거나 배너가 잘린다 — 둘 다 금지라 고정 크기로 떨어뜨린다.
  test('예약 높이를 넘는 어댑티브 크기는 들어가는 고정 크기로 떨어뜨린다', () {
    final size = bannerSizeWithin(
      width: 390,
      adaptive: adaptive(width: 390, height: 90),
    );

    expect(size, AdSize.banner);
    expect(size.height, lessThanOrEqualTo(AdBannerSlot.reservedHeightFor(390)));
  });

  test('SDK 가 크기를 못 주면(null) 고정 크기로 요청한다', () {
    expect(bannerSizeWithin(width: 390, adaptive: null), AdSize.banner);
    expect(bannerSizeWithin(width: 940, adaptive: null), AdSize.leaderboard);
  });

  test('태블릿 콘텐츠 열은 90 까지 들어간다', () {
    final size = bannerSizeWithin(
      width: 940,
      adaptive: adaptive(width: 940, height: 90),
    );

    expect(size.height, 90);
    expect(size.width, 940);
  });
}
