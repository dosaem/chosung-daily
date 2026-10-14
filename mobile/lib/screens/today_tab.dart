import 'package:chosung/layout/reading_width.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:chosung/widgets/skeleton_box.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';

/// S1 오늘 탭의 뼈대. 상단 줄(앱 이름 + StreakBadge)만 이 티켓이 만들고,
/// PuzzleBoard·HintCard·GuessInput 은 티켓 23 이 채운다.
class TodayTab extends ConsumerWidget {
  const TodayTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stats = ref.watch(startupStatsProvider);

    return SafeArea(
      child: ReadingWidth(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'app.name'.tr(),
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  if (stats != null) StreakBadge(days: stats.currentStreak),
                ],
              ),
              const SizedBox(height: 24),
              const SkeletonBox(height: 48),
              const SizedBox(height: 6),
              const SkeletonBox(height: 48),
            ],
          ),
        ),
      ),
    );
  }
}

/// 불꽃 아이콘만 brand 색, 숫자는 `foreground`(OVERRIDES §2·§22).
class StreakBadge extends StatelessWidget {
  const StreakBadge({required this.days, super.key});

  final int days;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);

    return Row(
      children: [
        Icon(LucideIcons.flame, size: 20, color: colors.brand),
        const SizedBox(width: 4),
        Text(
          'streak.days'.tr(namedArgs: {'count': '$days'}),
          style: Theme.of(context).textTheme.titleMedium,
        ),
      ],
    );
  }
}
