import 'package:flutter/widgets.dart';

/// 본문을 읽기 좋은 폭으로 가두고 가운데 정렬한다(SCREENS "태블릿 레이아웃").
///
/// 티켓 22 의 `MaxWidthBody`(iPad 전용 600px 래퍼)를 대신한다. 달라진 건
/// **폭을 화면이 정할 수 있다**는 점이다 — T4 의 2열은 열마다 480 을 쓰고,
/// T1 의 오른쪽 열은 320 을 쓴다. 기본값은 1열일 때의 600.
class ReadingWidth extends StatelessWidget {
  const ReadingWidth({
    required this.child,
    this.maxWidth = defaultMaxWidth,
    super.key,
  });

  static const defaultMaxWidth = 600.0;

  final double maxWidth;
  final Widget child;

  @override
  Widget build(BuildContext context) => Center(
    child: ConstrainedBox(
      constraints: BoxConstraints(maxWidth: maxWidth),
      child: child,
    ),
  );
}
