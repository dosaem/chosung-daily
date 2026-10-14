import 'dart:async';

import 'package:chosung/analytics/analytics_event.dart';
import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/layout/adaptive_sheet.dart';
import 'package:chosung/layout/app_breakpoint.dart';
import 'package:chosung/puzzle/board_layout.dart';
import 'package:chosung/puzzle/guess_rules.dart';
import 'package:chosung/puzzle/share_text.dart';
import 'package:chosung/puzzle/today_stats_provider.dart';
import 'package:chosung/share/share_sheet.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:chosung/widgets/puzzle_board.dart';
import 'package:chosung/widgets/puzzle_countdown.dart';
import 'package:chosung/widgets/skeleton_box.dart';
import 'package:chosung/widgets/stat_bar.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';

/// S2 결과 시트를 띄운다. compact 는 바텀시트, medium 이상은 가운데
/// 다이얼로그(SCREENS T2) — 그 판정은 [showAdaptiveSheet] 한 곳에만 있다.
Future<void> showResultSheet({
  required BuildContext context,
  required TodayPuzzle puzzle,
  required VoidCallback onShowRanking,
  DateTime Function() now = DateTime.now,
}) => showAdaptiveSheet<void>(
  context: context,
  builder: (context) => ResultSheet(
    puzzle: puzzle,
    onShowRanking: onShowRanking,
    now: now,
  ),
);

/// S2 결과 시트의 내용. 바텀시트와 다이얼로그가 **같은 위젯**을 쓴다.
class ResultSheet extends ConsumerStatefulWidget {
  const ResultSheet({
    required this.puzzle,
    required this.onShowRanking,
    this.now = DateTime.now,
    super.key,
  });

  /// 끝난 퍼즐(`status.isFinished`). 시트가 열려 있는 동안 바뀌지 않는 값이라
  /// provider 를 다시 보지 않고 열 때의 값을 그대로 그린다.
  final TodayPuzzle puzzle;

  /// "순위 보기" 를 눌렀을 때 갈 곳. 시트를 닫는 건 이 위젯이 하고, 라우터는
  /// 부른 쪽이 안다 — 테스트가 라우터 없이 시트를 띄울 수 있게 하려는 분리다.
  final VoidCallback onShowRanking;

  /// 카운트다운이 쓰는 시계. 골든·테스트가 초가 흐르는 숫자를 고정하려고
  /// 끼운다 — 앱에서는 [DateTime.now] 다.
  final DateTime Function() now;

  @override
  ConsumerState<ResultSheet> createState() => _ResultSheetState();
}

class _ResultSheetState extends ConsumerState<ResultSheet> {
  /// 계정 연결 안내를 닫았는가. **이 시트 안에서만 기억한다** — "퍼즐당 1회"
  /// 플래그와 실제 연결 흐름은 티켓 29 가 붙인다.
  bool _noticeDismissed = false;

  bool get _success => widget.puzzle.status == PuzzleStatus.success;

  Future<void> _share() async {
    final puzzle = widget.puzzle;
    final used = attemptsUsed(puzzle);
    final text = buildShareText(
      heading: 'share.heading'.tr(
        namedArgs: {'date': shareDate(puzzle.date)},
      ),
      puzzleLine: 'share.puzzle'.tr(
        namedArgs: {
          'mask': maskShareText(puzzle.mask),
          'length': '${puzzle.length}',
        },
      ),
      resultLine: (_success ? 'share.success' : 'share.fail').tr(
        namedArgs: {'used': '$used', 'max': '$maxAttempts'},
      ),
      attempts: puzzle.attempts,
    );

    await ref.read(shareTextProvider)(text);
    // 공유 시트가 떠 있는 동안 결과 시트가 사라졌으면(뒤로 가기) 버려진 ref 를
    // 다시 읽지 않는다.
    if (!mounted) return;
    await ref.read(analyticsServiceProvider).log(shareEvent);
  }

  void _showRanking() {
    Navigator.of(context).pop();
    widget.onShowRanking();
  }

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final puzzle = widget.puzzle;

    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(24, 12, 24, 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // 손잡이는 아래에서 올라온 시트에만 있다 — 다이얼로그엔 끌어내릴
            // 방향이 없다(SCREENS T2).
            if (!AppBreakpoint.of(context).hasRail) const _SheetHandle(),
            _Header(puzzle: puzzle, success: _success),
            const SizedBox(height: 24),
            _ResultGrid(puzzle: puzzle),
            const SizedBox(height: 24),
            Divider(height: 1, color: colors.border),
            const SizedBox(height: 16),
            _StatsSection(puzzle: puzzle, success: _success),
            const SizedBox(height: 24),
            _CountdownLine(now: widget.now),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: () => unawaited(_share()),
              icon: const Icon(LucideIcons.share2, size: 16),
              label: Text('result.share'.tr()),
            ),
            const SizedBox(height: 12),
            OutlinedButton(
              onPressed: _showRanking,
              child: Text('result.show_ranking'.tr()),
            ),
            if (!_noticeDismissed)
              _LinkAccountNotice(
                onDismiss: () => setState(() => _noticeDismissed = true),
              ),
          ],
        ),
      ),
    );
  }
}

/// 바텀시트 손잡이(목업 `e2_result`). 장식이라 스크린 리더가 읽지 않는다.
class _SheetHandle extends StatelessWidget {
  const _SheetHandle();

  @override
  Widget build(BuildContext context) => Center(
    child: Container(
      width: 48,
      height: 4,
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: AppColors.from(context).border,
        borderRadius: BorderRadius.circular(2),
      ),
    ),
  );
}

/// 결과 헤더. 정답을 제목에 넣는다(SCREENS S2) — 끝난 퍼즐이라 가릴 게 없다.
class _Header extends StatelessWidget {
  const _Header({required this.puzzle, required this.success});

  final TodayPuzzle puzzle;
  final bool success;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;
    final answer = puzzle.answer;
    // 정답은 끝난 퍼즐이면 서버가 항상 보낸다. 그래도 없을 때 "정답은 !" 이
    // 되지 않게 정답 없는 문구를 따로 둔다.
    final title = switch ((success, answer)) {
      (true, final String answer) => 'result.success_title'.tr(
        namedArgs: {'answer': answer},
      ),
      (false, final String answer) => 'result.fail_title'.tr(
        namedArgs: {'answer': answer},
      ),
      (true, _) => 'result.success_title_plain'.tr(),
      (false, _) => 'result.fail_title_plain'.tr(),
    };

    return Column(
      children: [
        // 목업의 detect 가 잡은 "같은 크기의 h 태그" 는 시맨틱 헤딩으로 푼다
        // (SCREENS "목업 파일 매핑").
        Semantics(
          header: true,
          child: Text(
            title,
            style: text.titleLarge,
            textAlign: TextAlign.center,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          success
              ? 'result.success_body'.tr(
                  namedArgs: {'used': '${attemptsUsed(puzzle)}'},
                )
              : 'result.fail_body'.tr(namedArgs: {'max': '$maxAttempts'}),
          style: text.bodySmall?.copyWith(color: colors.mutedForeground),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}

/// 내 시도 요약. 보드와 같은 타일로 그린다(SCREENS S2 — 이모지는 공유 텍스트
/// 전용). 문제 행·빈 행 없이 **제출한 행만** 보여준다.
class _ResultGrid extends StatelessWidget {
  const _ResultGrid({required this.puzzle});

  /// 시트 안 요약 타일. 보드(48/40)보다 작게.
  static const tileSize = 32.0;

  final TodayPuzzle puzzle;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      for (final (index, attempt) in puzzle.attempts.indexed) ...[
        if (index > 0) const SizedBox(height: PuzzleBoard.tileGap),
        Semantics(
          container: true,
          label: 'today.attempt_row'.tr(namedArgs: {'index': '${index + 1}'}),
          child: Wrap(
            alignment: WrapAlignment.center,
            spacing: PuzzleBoard.tileGap,
            runSpacing: PuzzleBoard.tileGap,
            children: [
              for (final cell in attemptCells(puzzle.mask, attempt))
                cell.kind.isGap
                    ? const BoardGap()
                    : BoardTile(cell: cell, size: tileSize),
            ],
          ),
        ),
      ],
    ],
  );
}

/// "오늘의 통계" — 분포 막대 + 내 위치(US 9). 조회 중엔 스켈레톤, 실패하면
/// 인라인 재시도다(OVERRIDES §7 — 시트를 닫게 하지 않는다).
class _StatsSection extends ConsumerWidget {
  const _StatsSection({required this.puzzle, required this.success});

  final TodayPuzzle puzzle;
  final bool success;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final colors = AppColors.from(context);
    final stats = ref.watch(todayStatsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Semantics(
          header: true,
          child: Text('result.stats_title'.tr(), style: text.titleMedium),
        ),
        const SizedBox(height: 12),
        switch (stats) {
          // 오류가 값보다 먼저다 — 실패해도 이전 값이 같이 남아
          // (`copyWithPrevious`) 멀쩡한 화면처럼 보이는 걸 막는다.
          AsyncValue(hasError: true) => _StatsFailed(
            onRetry: () => ref.invalidate(todayStatsProvider),
          ),
          AsyncValue(value: final TodayStats stats) =>
            stats.totalSolved == 0
                ? Text(
                    'result.stats_empty'.tr(),
                    style: text.bodySmall?.copyWith(
                      color: colors.mutedForeground,
                    ),
                  )
                : StatBar(
                    byAttempt: stats.byAttempt,
                    // 못 맞춘 사람은 분포에 자리가 없다 — 강조할 행도 없다.
                    myAttempt: success ? attemptsUsed(puzzle) : null,
                  ),
          _ => const _StatsSkeleton(),
        },
      ],
    );
  }
}

class _StatsSkeleton extends StatelessWidget {
  const _StatsSkeleton();

  @override
  Widget build(BuildContext context) => ExcludeSemantics(
    child: Column(
      children: [
        for (var row = 0; row < maxAttempts; row++) ...[
          if (row > 0) const SizedBox(height: 8),
          const SkeletonBox(height: StatBar.barHeight),
        ],
      ],
    ),
  );
}

class _StatsFailed extends StatelessWidget {
  const _StatsFailed({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);

    return Row(
      children: [
        Expanded(
          child: Text(
            'result.stats_failed'.tr(),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: colors.mutedForeground,
            ),
          ),
        ),
        TextButton(onPressed: onRetry, child: Text('today.retry'.tr())),
      ],
    );
  }
}

/// "다음 퍼즐까지 07:12:33"(US 6). 상시 카운트다운은 S1 이 아니라 여기다.
class _CountdownLine extends StatelessWidget {
  const _CountdownLine({required this.now});

  final DateTime Function() now;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);

    return PuzzleCountdown(
      now: now,
      builder: (context, remaining) => Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(LucideIcons.clock, size: 16, color: colors.mutedForeground),
          const SizedBox(width: 8),
          // 글자 크기를 키운 기기·긴 번역("Next puzzle in …")에서 한 줄을
          // 넘겨도 잘리지 않게 줄바꿈을 허용한다.
          Flexible(
            child: Text(
              'result.countdown'.tr(namedArgs: {'time': remaining}),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: colors.mutedForeground,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// "기록을 지키려면 계정을 연결하세요 →" 자리(US 20). 지금은 **자리와 닫기만**
/// 이고, 눌렀을 때의 연결 흐름과 "퍼즐당 1회" 플래그는 티켓 29 가 붙인다.
class _LinkAccountNotice extends StatelessWidget {
  const _LinkAccountNotice({required this.onDismiss});

  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 16),
        Divider(height: 1, color: colors.border),
        const SizedBox(height: 4),
        Row(
          children: [
            Icon(
              LucideIcons.userCircle,
              size: 16,
              color: colors.mutedForeground,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'result.link_account'.tr(),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: colors.mutedForeground,
                ),
              ),
            ),
            IconButton(
              onPressed: onDismiss,
              tooltip: 'result.dismiss'.tr(),
              icon: const Icon(LucideIcons.x, size: 16),
            ),
          ],
        ),
      ],
    );
  }
}
