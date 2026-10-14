import 'package:chosung/layout/reading_width.dart';
import 'package:chosung/widgets/skeleton_box.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';

/// S3 순위 탭의 뼈대. 내 순위 카드·LeaderboardRow 목록은 티켓 25 가 채운다.
class RankingTab extends StatelessWidget {
  const RankingTab({super.key});

  @override
  Widget build(BuildContext context) => SafeArea(
    child: ReadingWidth(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'tabs.ranking'.tr(),
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 24),
            for (var i = 0; i < 4; i++) ...[
              const SkeletonBox(height: 44),
              const SizedBox(height: 8),
            ],
          ],
        ),
      ),
    ),
  );
}
