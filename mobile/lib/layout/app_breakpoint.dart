import 'package:flutter/widgets.dart';

/// 폭 구간(스펙 §B.19, SCREENS "태블릿 레이아웃").
///
/// **기기 종류·OS 가 아니라 지금 이 순간의 폭으로만 판정한다.** 같은 iPad 가
/// 회전과 Split View 크기 조절로 세 구간을 모두 지나가므로, "iPad 인가" 를
/// 물으면 Split View 1/3(약 320dp)에서 폰 레이아웃을 못 돌려준다.
enum AppBreakpoint {
  /// 폰. 하단 탭 바 + 폰 레이아웃 그대로.
  compact,

  /// iPad 세로 Split View·작은 태블릿 세로. rail + 1열.
  medium,

  /// iPad 세로 전체·가로, 태블릿 가로. rail + 화면별 2열/넓은 표.
  expanded
  ;

  static const mediumMinWidth = 600.0;
  static const expandedMinWidth = 840.0;

  static AppBreakpoint fromWidth(double width) => switch (width) {
    < mediumMinWidth => compact,
    < expandedMinWidth => medium,
    _ => expanded,
  };

  static AppBreakpoint of(BuildContext context) =>
      fromWidth(MediaQuery.sizeOf(context).width);

  /// medium 이상은 하단 탭 바 대신 왼쪽 NavigationRail 을 쓴다.
  bool get hasRail => this != compact;

  /// 2열·넓은 표로 재배치하는 구간(각 화면 티켓 25~32 가 쓴다).
  bool get isExpanded => this == expanded;
}
