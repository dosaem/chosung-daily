import 'package:chosung/layout/reading_width.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/widgets/skeleton_box.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// S4 내 기록 탭의 뼈대. 상단 3칸(현재·최고·누적)은 시작할 때 읽은
/// `/me/stats` 로 채운다. 최근 7일 그리드·계정·구독·설정은 티켓 25·27·30.
class RecordsTab extends ConsumerWidget {
  const RecordsTab({super.key});

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
              Text(
                'tabs.records'.tr(),
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 24),
              if (stats == null)
                const SkeletonBox(height: 72)
              else
                Row(
                  children: [
                    _StatCell(
                      label: 'streak.current'.tr(),
                      value: 'streak.days'.tr(
                        namedArgs: {'count': '${stats.currentStreak}'},
                      ),
                    ),
                    _StatCell(
                      label: 'streak.max'.tr(),
                      value: 'streak.days'.tr(
                        namedArgs: {'count': '${stats.maxStreak}'},
                      ),
                    ),
                    _StatCell(
                      label: 'streak.solved'.tr(),
                      value: 'streak.puzzles'.tr(
                        namedArgs: {'count': '${stats.solvedCount}'},
                      ),
                    ),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatCell extends StatelessWidget {
  const _StatCell({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;

    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: text.labelSmall),
          const SizedBox(height: 4),
          Text(value, style: text.titleLarge),
        ],
      ),
    );
  }
}
