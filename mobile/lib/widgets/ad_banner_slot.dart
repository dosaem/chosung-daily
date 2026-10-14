import 'package:chosung/theme/app_colors.dart';
import 'package:flutter/material.dart';

/// 배너 광고가 들어갈 자리. **높이를 항상 예약한다** — 로드 전에도 공간을
/// 비워두지 않으면 배너가 뜨는 순간 레이아웃이 점프한다(OVERRIDES §5).
///
/// 광고 SDK·UMP 동의·구독자 제거는 티켓 31 이 채운다. 이 티켓은 자리와
/// 구분선, 그리고 "지금 슬롯 폭" 을 넘겨주는 통로만 만든다.
class AdBannerSlot extends StatelessWidget {
  const AdBannerSlot({super.key, this.builder});

  /// 폰 폭의 어댑티브 배너 높이.
  static const reservedHeight = 50.0;

  /// 태블릿 폭의 어댑티브 배너 높이. 어댑티브 배너는 90dp 가 상한이고
  /// 728×90(IAB leaderboard)이 태블릿 표준이라 그 폭부터 90 을 예약한다.
  /// **잠정값** — 티켓 31 이 SDK 의
  /// `getCurrentOrientationAnchoredAdaptiveBannerAdSize` 실제 값으로
  /// 대체·검증한다(스펙 미정 24).
  static const tabletReservedHeight = 90.0;

  /// 728×90 배너가 들어가는 최소 폭.
  static const tabletMinWidth = 728.0;

  /// 배너와 콘텐츠 사이 여백(OVERRIDES §5: border 1px + 8px).
  static const contentGap = 8.0;

  static double reservedHeightFor(double width) =>
      width < tabletMinWidth ? reservedHeight : tabletReservedHeight;

  /// 티켓 31 이 이 폭으로 어댑티브 배너를 로드한다. 폭이 바뀌면(회전·Split
  /// View) 새 값으로 다시 불린다.
  final Widget Function(BuildContext context, double bannerWidth)? builder;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);

    return LayoutBuilder(
      builder: (context, constraints) {
        final bannerWidth = constraints.maxWidth;

        return Container(
          height: reservedHeightFor(bannerWidth),
          margin: const EdgeInsets.only(top: contentGap),
          decoration: BoxDecoration(
            color: colors.muted,
            border: Border(top: BorderSide(color: colors.border)),
          ),
          child: builder?.call(context, bannerWidth),
        );
      },
    );
  }
}
