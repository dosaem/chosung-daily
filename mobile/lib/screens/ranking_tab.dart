import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/layout/app_breakpoint.dart';
import 'package:chosung/layout/reading_width.dart';
import 'package:chosung/puzzle/guess_rules.dart';
import 'package:chosung/ranking/leaderboard_controller.dart';
import 'package:chosung/settings/puzzle_language_controller.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:chosung/widgets/leaderboard_row.dart';
import 'package:chosung/widgets/offline_banner.dart';
import 'package:chosung/widgets/skeleton_box.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 테스트가 잡는 자리. 하단 고정 행은 "목록 안의 내 행" 과 생김새가 같아서
/// 키가 없으면 둘을 구분할 수 없다.
abstract final class RankingKeys {
  static const pinnedMeRow = Key('ranking.pinned_me_row');
}

/// S3 순위 탭. 언어별 익명 리더보드 + 내 순위.
///
/// 폭 ≥600 은 T3 의 넓은 표(머리글 + `ReadingWidth` 840), 그 아래는 폰과 같은
/// 1열이다. 퍼즐 언어 칩은 **표시 전용** — 바꾸는 곳은 S4 설정 하나다.
class RankingTab extends ConsumerWidget {
  const RankingTab({super.key});

  /// T3: 표는 840 안에, 폰은 읽기 폭 기본값(600).
  static const _tableMaxWidth = 840.0;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(leaderboardProvider);

    return SafeArea(
      child: switch (state) {
        AsyncValue(hasError: true, :final error) => _ErrorView(
          offline: error is NetworkApiException,
        ),
        // 값이 null 이면 "오늘 그 언어의 퍼즐이 아직 없다" 다 — 빈 상태로 받는다.
        AsyncValue(hasValue: true, :final value) => _Board(board: value),
        _ => const _LoadingSkeleton(),
      },
    );
  }
}

class _Board extends ConsumerWidget {
  const _Board({required this.board});

  final Leaderboard? board;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isTable = AppBreakpoint.of(context).hasRail;
    final entries = board?.entries ?? const <LeaderboardEntry>[];
    final me = board?.me;
    final header = _Header(
      date: board?.date,
      // 퍼즐이 없어 응답이 없을 때도 칩은 내 설정 언어를 보여준다.
      language: board?.language ?? ref.watch(puzzleLanguageProvider).language,
      me: me,
      sideBySide: isTable,
    );

    return ReadingWidth(
      maxWidth: isTable
          ? RankingTab._tableMaxWidth
          : ReadingWidth.defaultMaxWidth,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            header,
            const SizedBox(height: 16),
            if (isTable) ...[const _TableHeader(), const _Hairline()],
            Expanded(
              child: entries.isEmpty
                  ? const _EmptyState()
                  : ListView.separated(
                      padding: EdgeInsets.zero,
                      itemCount: entries.length,
                      separatorBuilder: (_, _) => const _Hairline(),
                      itemBuilder: (context, index) {
                        final entry = entries[index];
                        return LeaderboardRow(
                          rank: entry.rank,
                          name: entry.display,
                          attempts: entry.attempts,
                          seconds: entry.seconds,
                          isMe: entry.isMe,
                        );
                      },
                    ),
            ),
            // 21위 밖이어도 내 줄은 보여야 한다 — 목록 밖에 고정한다(S3·T3).
            if (board != null && board!.isMeOutsideEntries && me != null) ...[
              const _Hairline(),
              LeaderboardRow(
                key: RankingKeys.pinnedMeRow,
                rank: me.rank,
                name: 'ranking.me'.tr(),
                attempts: me.attempts,
                seconds: me.seconds,
                isMe: true,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// 날짜 + 퍼즐 언어 칩, 그리고 내 순위 카드. T3 는 둘을 한 줄에 좌우로 둔다.
class _Header extends StatelessWidget {
  const _Header({
    required this.language,
    required this.me,
    required this.sideBySide,
    this.date,
  });

  final DateTime? date;
  final PuzzleLanguage language;
  final MyRank? me;
  final bool sideBySide;

  @override
  Widget build(BuildContext context) {
    final line = _DateLine(date: date, language: language);
    final card = _MyRankCard(me: me);

    if (!sideBySide) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [line, const SizedBox(height: 12), card],
      );
    }
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(child: line),
        const SizedBox(width: 16),
        Flexible(child: card),
      ],
    );
  }
}

class _DateLine extends StatelessWidget {
  const _DateLine({required this.language, this.date});

  final DateTime? date;
  final PuzzleLanguage language;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;

    return Row(
      children: [
        if (date case final date?)
          Flexible(
            child: Text(
              DateFormat.MMMMd(
                Localizations.localeOf(context).toLanguageTag(),
              ).format(date),
              style: text.titleMedium,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        const SizedBox(width: 8),
        // 표시 전용 칩 — 누를 수 있는 위젯으로 만들지 않는다(전환은 S4 설정).
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: colors.muted,
            border: Border.all(color: colors.border),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            'language.${language.wire}'.tr(),
            style: text.labelSmall?.copyWith(color: colors.mutedForeground),
          ),
        ),
      ],
    );
  }
}

/// "내 순위 · #12 · 2회 · 00:03:41". 못 풀었으면 그렇게 적는다(S3).
class _MyRankCard extends StatelessWidget {
  const _MyRankCard({required this.me});

  final MyRank? me;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;
    final me = this.me;
    final value = me == null
        ? 'ranking.not_played'.tr()
        : [
            '#${me.rank}',
            'ranking.attempts'.tr(namedArgs: {'count': '${me.attempts}'}),
            formatCountdown(Duration(seconds: me.seconds)),
          ].join(' · ');

    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: colors.border),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'ranking.my_rank'.tr(),
              style: text.labelSmall?.copyWith(color: colors.mutedForeground),
            ),
            const SizedBox(width: 8),
            Flexible(
              child: Text(
                value,
                style: text.titleSmall,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// T3 넓은 표의 머리글. 폰에서는 줄이 네 칸인 게 보이므로 쓰지 않는다.
class _TableHeader extends StatelessWidget {
  const _TableHeader();

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final style = Theme.of(
      context,
    ).textTheme.labelSmall?.copyWith(color: colors.mutedForeground);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      child: Row(
        children: [
          SizedBox(
            width: LeaderboardRow.rankWidth,
            child: Text('ranking.column_rank'.tr(), style: style),
          ),
          Expanded(child: Text('ranking.column_name'.tr(), style: style)),
          SizedBox(
            width: LeaderboardRow.attemptsWidth,
            child: Text(
              'ranking.column_attempts'.tr(),
              textAlign: TextAlign.right,
              style: style,
            ),
          ),
          SizedBox(
            width: LeaderboardRow.timeWidth,
            child: Text(
              'ranking.column_time'.tr(),
              textAlign: TextAlign.right,
              style: style,
            ),
          ),
        ],
      ),
    );
  }
}

/// 섹션·행 구분은 헤어라인 1px 뿐이다(OVERRIDES §4).
class _Hairline extends StatelessWidget {
  const _Hairline();

  @override
  Widget build(BuildContext context) =>
      Divider(height: 1, thickness: 1, color: AppColors.from(context).border);
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) => Center(
    child: Text(
      'ranking.empty'.tr(),
      textAlign: TextAlign.center,
      style:
          Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(
            color: AppColors.from(context).mutedForeground,
          ),
    ),
  );
}

class _ErrorView extends ConsumerWidget {
  const _ErrorView({required this.offline});

  final bool offline;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;

    return Column(
      children: [
        if (offline) const OfflineBanner(),
        Expanded(
          child: ReadingWidth(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('ranking.error_title'.tr(), style: text.titleMedium),
                    const SizedBox(height: 8),
                    Text(
                      'ranking.error_body'.tr(),
                      style: text.bodySmall,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 16),
                    OutlinedButton(
                      onPressed: ref.read(leaderboardProvider.notifier).retry,
                      child: Text('ranking.retry'.tr()),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// 로딩은 스켈레톤(OVERRIDES §7 — 스피너 금지).
class _LoadingSkeleton extends StatelessWidget {
  const _LoadingSkeleton();

  @override
  Widget build(BuildContext context) => ReadingWidth(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: ExcludeSemantics(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SkeletonBox(height: 24, width: 160),
            const SizedBox(height: 12),
            const SkeletonBox(height: 44),
            const SizedBox(height: 16),
            for (var row = 0; row < 8; row++) ...[
              const SkeletonBox(height: 40),
              const SizedBox(height: 6),
            ],
          ],
        ),
      ),
    ),
  );
}
