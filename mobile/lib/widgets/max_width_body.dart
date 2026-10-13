import 'package:flutter/material.dart';

/// 스펙 §B.19: iPad 는 가운데 정렬 최대 600px.
///
/// 모든 화면의 본문을 이걸로 감싼다 — 태블릿에서 폰 레이아웃이 그대로 늘어나
/// 한 줄이 화면을 가로지르는 걸 막는다.
class MaxWidthBody extends StatelessWidget {
  const MaxWidthBody({required this.child, super.key});

  static const maxWidth = 600.0;

  final Widget child;

  @override
  Widget build(BuildContext context) => Center(
    child: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: maxWidth),
      child: child,
    ),
  );
}
