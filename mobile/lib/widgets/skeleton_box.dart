import 'package:chosung/theme/app_colors.dart';
import 'package:flutter/material.dart';

/// 로딩은 스켈레톤으로 보여준다 — 스피너 금지(OVERRIDES §7).
class SkeletonBox extends StatelessWidget {
  const SkeletonBox({
    required this.height,
    super.key,
    this.width,
    this.radius = 8,
  });

  final double height;
  final double? width;
  final double radius;

  @override
  Widget build(BuildContext context) => Container(
    height: height,
    width: width,
    decoration: BoxDecoration(
      color: AppColors.from(context).muted,
      borderRadius: BorderRadius.circular(radius),
    ),
  );
}
