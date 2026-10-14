import 'dart:async';

import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/layout/app_breakpoint.dart';
import 'package:chosung/layout/reading_width.dart';
import 'package:chosung/puzzle/guess_rules.dart';
import 'package:chosung/puzzle/today_puzzle_controller.dart';
import 'package:chosung/puzzle/today_puzzle_state.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:chosung/widgets/guess_input.dart';
import 'package:chosung/widgets/hint_card.dart';
import 'package:chosung/widgets/offline_banner.dart';
import 'package:chosung/widgets/puzzle_board.dart';
import 'package:chosung/widgets/skeleton_box.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';

/// S1 오늘 탭. 로딩·오류·오프라인·퍼즐 없음·플레이 중·완료를 한 자리에서 고른다.
class TodayTab extends ConsumerStatefulWidget {
  const TodayTab({super.key});

  @override
  ConsumerState<TodayTab> createState() => _TodayTabState();
}

class _TodayTabState extends ConsumerState<TodayTab> {
  /// 입력 중인 텍스트는 레이아웃보다 오래 살아야 한다 — 폭이 바뀌면
  /// (회전·Split View) 입력창이 다른 열로 옮겨 가지만 치던 답은 그대로여야
  /// 한다(SCREENS "태블릿 레이아웃"). 그래서 컨트롤러를 분기 위에 둔다.
  final _guess = TextEditingController();

  @override
  void dispose() {
    _guess.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final recorded = await ref
        .read(todayPuzzleProvider.notifier)
        .submit(_guess.text);
    // 보드에 한 행이 쌓였을 때만 비운다 — 409·오프라인은 같은 답을 다시
    // 보낼 수 있어야 한다.
    if (recorded) _guess.clear();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(todayPuzzleProvider);

    return SafeArea(
      child: switch (state) {
        // 재조회가 실패해도(state.error) 앞의 보드는 남는다 — 그 경우 오프라인
        // 배너만 얹고 보드를 지우지 않는다.
        AsyncValue(value: final TodayPuzzleReady ready) => _Board(
          ready: ready,
          guess: _guess,
          onSubmit: _submit,
          offline: ready.notice?.blocksInput ?? _isOffline(state.error),
        ),
        AsyncValue(value: TodayNoPuzzle()) => const _CenteredCard(
          child: _NoPuzzleCard(),
        ),
        AsyncValue(hasError: true, :final error) => _CenteredCard(
          offline: _isOffline(error),
          child: const _ErrorCard(),
        ),
        _ => const _LoadingSkeleton(),
      },
    );
  }

  bool _isOffline(Object? error) => error is NetworkApiException;
}

/// 보드가 있는 화면. 폭에 따라 1열(폰·medium) / 2열(expanded, SCREENS T1)이다.
class _Board extends StatelessWidget {
  const _Board({
    required this.ready,
    required this.guess,
    required this.onSubmit,
    required this.offline,
  });

  /// SCREENS T1: 왼쪽 보드 열 ≤600 + 오른쪽 열 ≤320, 합 920 가운데 정렬.
  static const _sideColumnWidth = 320.0;
  static const double _twoColumnWidth =
      ReadingWidth.defaultMaxWidth + _sideColumnWidth;

  final TodayPuzzleReady ready;
  final TextEditingController guess;
  final Future<void> Function() onSubmit;
  final bool offline;

  @override
  Widget build(BuildContext context) {
    final puzzle = ready.puzzle;
    final isExpanded = AppBreakpoint.of(context).isExpanded;

    final board = <Widget>[
      _TopBar(),
      const SizedBox(height: 16),
      _DateLine(puzzle: puzzle),
      const SizedBox(height: 24),
      PuzzleBoard(puzzle: puzzle),
    ];
    final notice = ready.notice;
    final input = <Widget>[
      const SizedBox(height: 24),
      if (notice != null) ...[
        _NoticeLine(notice: notice),
        const SizedBox(height: 8),
      ],
      if (puzzle.status.isFinished)
        const _ShowResultButton()
      else
        GuessInput(
          puzzle: puzzle,
          controller: guess,
          onSubmit: () => unawaited(onSubmit()),
          enabled: !offline && !ready.submitting,
        ),
    ];
    // 보상형 버튼(onWatchAd)은 광고 SDK 가 들어오는 티켓 31 이 넣는다.
    final hintCard = HintCard(hint: puzzle.hint);
    final attemptsLeft = AttemptsLeftLabel(attemptsLeft: puzzle.attemptsLeft);

    return Column(
      children: [
        if (offline) const OfflineBanner(),
        Expanded(
          child: isExpanded
              // expanded: 왼쪽 열(보드·입력) + 오른쪽 열(힌트·남은 기회).
              ? Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(
                      maxWidth: _twoColumnWidth,
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: _Column(children: [...board, ...input]),
                        ),
                        SizedBox(
                          width: _sideColumnWidth,
                          child: _Column(
                            children: [
                              hintCard,
                              const SizedBox(height: 12),
                              attemptsLeft,
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                )
              // 폰·medium: 폰 순서 그대로 1열(SCREENS S1·T1).
              : ReadingWidth(
                  child: _Column(
                    children: [
                      ...board,
                      const SizedBox(height: 24),
                      hintCard,
                      ...input,
                      const SizedBox(height: 8),
                      attemptsLeft,
                    ],
                  ),
                ),
        ),
      ],
    );
  }
}

/// 한 열. 작은 폰에서 키보드가 올라와도 잘리지 않게 스크롤된다.
class _Column extends StatelessWidget {
  const _Column({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    padding: const EdgeInsets.all(16),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: children,
    ),
  );
}

/// 앱 이름(좌) + StreakBadge(우).
class _TopBar extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stats = ref.watch(startupStatsProvider);

    return Row(
      children: [
        // 글자 크기를 키운 기기·긴 번역에서도 StreakBadge 를 밀어내지 않는다.
        Expanded(
          child: Text(
            'app.name'.tr(),
            style: Theme.of(context).textTheme.titleLarge,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        if (stats != null) StreakBadge(days: stats.currentStreak),
      ],
    );
  }
}

/// "10월 13일 · 일반 단어" + 칩 "KST 00:00 새 퍼즐".
///
/// 상시 카운트다운은 여기가 아니라 결과 시트(S2, 티켓 26)다 — 플레이 중에
/// 초가 흐르는 숫자가 보드 옆에 있으면 시선을 가져간다.
class _DateLine extends StatelessWidget {
  const _DateLine({required this.puzzle});

  final TodayPuzzle puzzle;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;
    // 날짜는 서버가 KST 로 계산해 보낸 값이다. 로케일 데이터는 앱의
    // `localizationDelegates`(GlobalMaterialLocalizations)가 채운다.
    final date = DateFormat.MMMMd(
      Localizations.localeOf(context).toLanguageTag(),
    ).format(puzzle.date);

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Expanded(
          child: Text(
            '$date · ${puzzle.category.labelKey.tr()}',
            style: text.bodySmall?.copyWith(color: colors.mutedForeground),
          ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: colors.muted,
            border: Border.all(color: colors.border),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            'today.new_puzzle_chip'.tr(),
            style: text.labelSmall?.copyWith(color: colors.mutedForeground),
          ),
        ),
      ],
    );
  }
}

/// 보드를 지우지 않고 그 자리에 띄우는 한 줄(409·오프라인·제출 실패).
class _NoticeLine extends StatelessWidget {
  const _NoticeLine({required this.notice});

  final TodayNotice notice;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);

    return Row(
      children: [
        Icon(LucideIcons.info, size: 16, color: colors.mutedForeground),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            notice.messageKey.tr(),
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ),
      ],
    );
  }
}

/// 완료 상태. 시트는 티켓 26 이 붙인다 — 그때까지 버튼은 자리만 잡는다.
class _ShowResultButton extends StatelessWidget {
  const _ShowResultButton();

  @override
  Widget build(BuildContext context) =>
      FilledButton(onPressed: null, child: Text('today.show_result'.tr()));
}

/// 오류·퍼즐 없음 카드는 보드가 없으니 읽기 폭 안에서 가운데 둔다.
class _CenteredCard extends StatelessWidget {
  const _CenteredCard({required this.child, this.offline = false});

  final Widget child;
  final bool offline;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      if (offline) const OfflineBanner(),
      Expanded(
        child: ReadingWidth(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Center(child: child),
          ),
        ),
      ),
    ],
  );
}

class _ErrorCard extends ConsumerWidget {
  const _ErrorCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('today.error_title'.tr(), style: text.titleMedium),
        const SizedBox(height: 8),
        Text(
          'today.error_body'.tr(),
          style: text.bodySmall,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 16),
        OutlinedButton(
          onPressed: ref.read(todayPuzzleProvider.notifier).retry,
          child: Text('today.retry'.tr()),
        ),
      ],
    );
  }
}

/// 자정 전환 직후. 다음 KST 자정까지 남은 시간을 1초마다 다시 그린다.
class _NoPuzzleCard extends ConsumerStatefulWidget {
  const _NoPuzzleCard();

  @override
  ConsumerState<_NoPuzzleCard> createState() => _NoPuzzleCardState();
}

class _NoPuzzleCardState extends ConsumerState<_NoPuzzleCard> {
  Timer? _ticker;
  Duration _remaining = timeUntilNextPuzzle(DateTime.now());

  @override
  void initState() {
    super.initState();
    _ticker = Timer.periodic(
      const Duration(seconds: 1),
      (_) => setState(() => _remaining = timeUntilNextPuzzle(DateTime.now())),
    );
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('today.none_title'.tr(), style: text.titleMedium),
        const SizedBox(height: 8),
        Text(
          'today.none_body'.tr(
            namedArgs: {'time': formatCountdown(_remaining)},
          ),
          style: text.bodySmall,
        ),
        const SizedBox(height: 16),
        OutlinedButton(
          onPressed: ref.read(todayPuzzleProvider.notifier).retry,
          child: Text('today.retry'.tr()),
        ),
      ],
    );
  }
}

/// 로딩은 스켈레톤(OVERRIDES §7 — 스피너 금지). 타일 자리와 입력 줄을 잡아
/// 두면 보드가 들어올 때 레이아웃이 뛰지 않는다.
class _LoadingSkeleton extends StatelessWidget {
  const _LoadingSkeleton();

  @override
  Widget build(BuildContext context) => ReadingWidth(
    child: Padding(
      padding: const EdgeInsets.all(16),
      // 스켈레톤은 장식이다 — 스크린 리더가 빈 상자 여러 개를 읽지 않게 가린다.
      child: ExcludeSemantics(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SkeletonBox(height: 28, width: 140),
            const SizedBox(height: 24),
            const SkeletonBox(height: 16),
            const SizedBox(height: 24),
            const SkeletonBox(height: 48),
            const SizedBox(height: 16),
            for (var row = 0; row < maxAttempts; row++) ...[
              const SkeletonBox(height: 40),
              const SizedBox(height: 6),
            ],
          ],
        ),
      ),
    ),
  );
}

/// 불꽃 아이콘만 brand 색, 숫자는 `foreground`(OVERRIDES §2·§22).
class StreakBadge extends StatelessWidget {
  const StreakBadge({required this.days, super.key});

  final int days;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);

    return Semantics(
      // 숫자만 읽히면 무슨 숫자인지 알 수 없다.
      label: 'today.streak'.tr(namedArgs: {'count': '$days'}),
      child: ExcludeSemantics(
        child: Row(
          children: [
            Icon(LucideIcons.flame, size: 20, color: colors.brand),
            const SizedBox(width: 4),
            Text(
              'streak.days'.tr(namedArgs: {'count': '$days'}),
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ],
        ),
      ),
    );
  }
}
