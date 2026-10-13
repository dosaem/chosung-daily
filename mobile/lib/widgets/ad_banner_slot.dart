import 'package:chosung/theme/app_colors.dart';
import 'package:flutter/material.dart';

/// 배너 광고가 들어갈 자리. **높이를 항상 예약한다** — 로드 전에도 공간을
/// 비워두지 않으면 배너가 뜨는 순간 레이아웃이 점프한다(OVERRIDES §5).
///
/// 광고 SDK·UMP 동의·구독자 제거는 티켓 29 가 채운다. 이 티켓은 자리와
/// 구분선만 만든다.
class AdBannerSlot extends StatelessWidget {
  const AdBannerSlot({super.key, this.child});

  /// 어댑티브 배너의 기본 높이. 티켓 29 가 실제 배너 크기로 바꾼다.
  static const reservedHeight = 50.0;

  /// 배너와 콘텐츠 사이 여백(OVERRIDES §5: border 1px + 8px).
  static const contentGap = 8.0;

  final Widget? child;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);

    return Container(
      height: reservedHeight,
      margin: const EdgeInsets.only(top: contentGap),
      decoration: BoxDecoration(
        color: colors.muted,
        border: Border(top: BorderSide(color: colors.border)),
      ),
      child: child,
    );
  }
}
