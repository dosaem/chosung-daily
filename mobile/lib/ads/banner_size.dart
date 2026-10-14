import 'package:chosung/widgets/ad_banner_slot.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

/// [width] 폭의 슬롯에 **실제로 들어가는** 배너 크기.
///
/// [adaptive] 는 SDK 가 그 폭에 대해 돌려준 어댑티브 크기다(없으면 null).
/// 슬롯이 예약한 높이(티켓 24, `AdBannerSlot.reservedHeightFor`)를 넘으면
/// 쓰지 않는다 — 넘치면 레이아웃이 밀리고(OVERRIDES §5 금지) 잘라서 보여주는
/// 것은 AdMob 정책 위반이다. 그때는 그 폭에 들어가는 고정 크기로 요청한다.
///
/// 예약 높이 50/90 은 스펙 "미정 24" 의 잠정값이다. 실제 어댑티브 높이는
/// 플랫폼 채널이 있어야 나오므로(기기·시뮬레이터) 여기서는 "넘으면 안 쓴다"
/// 는 규칙만 지키고, 실측 확인은 `docs/RELEASE.md "### 31."` 의 실기기
/// 체크리스트에 남겼다.
AdSize bannerSizeWithin({
  required double width,
  required AnchoredAdaptiveBannerAdSize? adaptive,
}) {
  final reserved = AdBannerSlot.reservedHeightFor(width);
  if (adaptive != null && adaptive.height <= reserved) return adaptive;
  // 320×50 / 728×90 — 어댑티브 배너의 폭 구간과 같은 경계다.
  return width < AdBannerSlot.tabletMinWidth
      ? AdSize.banner
      : AdSize.leaderboard;
}
