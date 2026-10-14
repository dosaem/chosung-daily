import 'dart:async';

import 'package:chosung/ads/ad_providers.dart';
import 'package:chosung/ads/ad_service.dart';
import 'package:chosung/ads/result_interstitial.dart';
import 'package:chosung/analytics/analytics_event.dart';
import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/layout/app_breakpoint.dart';
import 'package:chosung/layout/reading_width.dart';
import 'package:chosung/puzzle/guess_rules.dart';
import 'package:chosung/puzzle/today_puzzle_controller.dart';
import 'package:chosung/puzzle/today_puzzle_state.dart';
import 'package:chosung/records/my_stats_controller.dart';
import 'package:chosung/routing/app_routes.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:chosung/widgets/guess_input.dart';
import 'package:chosung/widgets/hint_card.dart';
import 'package:chosung/widgets/offline_banner.dart';
import 'package:chosung/widgets/puzzle_board.dart';
import 'package:chosung/widgets/puzzle_countdown.dart';
import 'package:chosung/widgets/result_sheet.dart';
import 'package:chosung/widgets/skeleton_box.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
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

  /// 보드 위의 인라인 재시도(오프라인 배너·재조회 실패 안내). 오류 카드의
  /// [TodayPuzzleNotifier.retry] 와 달리 스켈레톤으로 돌아가지 않는다 —
  /// 멀쩡한 보드를 깜빡이게 하지 않으려고.
  void _retry() => unawaited(ref.read(todayPuzzleProvider.notifier).refresh());

  Future<void> _submit() async {
    final recorded = await ref
        .read(todayPuzzleProvider.notifier)
        .submit(_guess.text);
    // 보드에 한 행이 쌓였을 때만 비운다 — 409·오프라인은 같은 답을 다시
    // 보낼 수 있어야 한다.
    if (recorded) _guess.clear();
    if (!recorded || !mounted) return;

    // 전면 광고는 "이번 실행에 제출이 있었는가" 뒤에만 뜬다(US 25).
    ref.read(resultInterstitialProvider).markSubmitted();

    // **이 제출로 퍼즐이 끝난 순간**에만 이벤트를 찍고 시트를 띄운다. "결과
    // 보기" 로 다시 열 때는 둘 다 하지 않는다 — `puzzle_complete` 는 퍼즐당
    // 한 번이고, 다른 기기에서 이미 끝낸 퍼즐을 여는 경로(서버 상태가 처음부터
    // finished)에도 찍히면 안 된다.
    if (ref.read(todayPuzzleProvider).value case TodayPuzzleReady(
      :final puzzle,
    ) when puzzle.status.isFinished) {
      await ref
          .read(analyticsServiceProvider)
          .log(
            puzzleCompleteEvent(
              language: puzzle.language,
              success: puzzle.status == PuzzleStatus.success,
              attempts: attemptsUsed(puzzle),
            ),
          );
      if (!mounted) return;
      await _openResult(puzzle);
    }
  }

  /// S2 결과 시트. 폭에 따라 바텀시트/다이얼로그로 갈린다(SCREENS T2).
  ///
  /// 시트를 **닫은 뒤** 전면 광고 차례다(US 24). SCREENS S2 는 "시트가 완전히
  /// 뜬 뒤" 라고 적었지만 티켓 31 이 "결과 시트 닫힘 후" 로 좁혔다 — 결과를
  /// 읽는 중에 전면 광고가 덮으면 확인 자체를 못 한다.
  Future<void> _openResult(TodayPuzzle puzzle) async {
    await showResultSheet(
      context: context,
      puzzle: puzzle,
      onShowRanking: () => context.go(AppRoutes.ranking),
      onLinkAccount: () => context.go(AppRoutes.records),
    );
    if (!mounted) return;
    await ref
        .read(resultInterstitialProvider)
        .showAfterResultSheet(puzzleId: puzzle.puzzleId);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(todayPuzzleProvider);

    return SafeArea(
      child: switch (state) {
        // 보드가 있으면 보드를 지우지 않는다. 재조회 실패는 컨트롤러가
        // `TodayNotice.offline`/`refreshFailed` 로 바꿔 놓으므로 판정은 notice
        // 하나로 한다 — 두 곳에서 같은 걸 판정하면 한쪽이 틀린다. 남은
        // `state.error` 는 `||` 로 같이 본다(`??` 면 안내가 있을 때 오프라인을
        // 건너뛴다).
        AsyncValue(value: final TodayPuzzleReady ready) => _Board(
          ready: ready,
          guess: _guess,
          onSubmit: _submit,
          onRetry: _retry,
          onShowResult: () => unawaited(_openResult(ready.puzzle)),
          offline:
              (ready.notice?.blocksInput ?? false) || _isOffline(state.error),
        ),
        // 보드가 없을 때의 오류가 "퍼즐 없음" 보다 먼저다 — 카운트다운 카드에서
        // 재시도가 실패하면 이전 값이 남아(`copyWithPrevious`) 실패가 안 보인다.
        AsyncValue(hasError: true, :final error) => _CenteredCard(
          offline: _isOffline(error),
          child: const _ErrorCard(),
        ),
        AsyncValue(value: TodayNoPuzzle()) => const _CenteredCard(
          child: _NoPuzzleCard(),
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
    required this.onRetry,
    required this.onShowResult,
    required this.offline,
  });

  /// SCREENS T1: 왼쪽 보드 열 ≤600 + 오른쪽 열 ≤320, 합 920 가운데 정렬.
  static const _sideColumnWidth = 320.0;
  static const double _twoColumnWidth =
      ReadingWidth.defaultMaxWidth + _sideColumnWidth;

  final TodayPuzzleReady ready;
  final TextEditingController guess;
  final Future<void> Function() onSubmit;
  final VoidCallback onRetry;
  final VoidCallback onShowResult;
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
      // 오프라인 문구는 상단 배너가 이미 말한다 — 같은 문장을 두 번 쓰지 않고,
      // 그 경우의 재시도는 배너가 들고 있다.
      if (notice != null && !notice.blocksInput) ...[
        _NoticeLine(
          notice: notice,
          onRetry: notice.showsRetry ? onRetry : null,
        ),
        const SizedBox(height: 8),
      ],
      if (puzzle.status.isFinished)
        _ShowResultButton(onPressed: onShowResult)
      else
        GuessInput(
          puzzle: puzzle,
          controller: guess,
          onSubmit: () => unawaited(onSubmit()),
          enabled: !offline && !ready.submitting,
        ),
    ];
    final hintCard = _HintSlot(
      // 퍼즐이 바뀌면 "광고를 못 불러왔다" 도 같이 잊는다.
      key: ValueKey(puzzle.puzzleId),
      puzzle: puzzle,
    );
    final attemptsLeft = AttemptsLeftLabel(attemptsLeft: puzzle.attemptsLeft);

    return Column(
      children: [
        if (offline) OfflineBanner(onRetry: onRetry),
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

/// HintCard + 힌트 미리 보기 흐름(US 4·32).
///
/// 비구독자는 보상형 광고를 끝까지 본 뒤에 `hint-unlock` 이 나가고, 구독자는
/// 광고 없이 바로 나간다 — 어느 쪽인지는 광고 게이트가 판정한다.
class _HintSlot extends ConsumerStatefulWidget {
  const _HintSlot({required this.puzzle, super.key});

  final TodayPuzzle puzzle;

  @override
  ConsumerState<_HintSlot> createState() => _HintSlotState();
}

class _HintSlotState extends ConsumerState<_HintSlot> {
  /// 광고를 띄우거나 힌트를 여는 중. 두 번 누르면 광고가 두 번 뜬다.
  bool _busy = false;

  String? _notice;

  /// 광고를 한 번 못 띄웠으면 이 퍼즐에서는 버튼을 끈다 — 누를 때마다 다시
  /// 로드해 보면 매번 몇 초를 기다린 끝에 같은 실패를 본다.
  bool _adUnavailable = false;

  Future<void> _preview() async {
    setState(() {
      _busy = true;
      _notice = null;
    });
    try {
      if (ref.read(adGateProvider).hintPreviewNeedsAd) {
        final outcome = await ref.read(adServiceProvider).showRewarded();
        if (outcome != RewardedOutcome.earned) {
          // 광고를 **못 띄운** 경우에만 버튼을 끈다. 중간에 닫은 건 다시
          // 누르면 되는 일이라 안내만 남기고 버튼은 살려 둔다.
          if (mounted) {
            setState(() {
              _adUnavailable = outcome == RewardedOutcome.unavailable;
              _notice = _adUnavailable
                  ? 'hint.ad_unavailable'.tr()
                  : 'hint.ad_not_finished'.tr();
            });
          }
          return;
        }
      }

      final opened = await ref.read(todayPuzzleProvider.notifier).unlockHint();
      if (!opened && mounted) {
        setState(() => _notice = 'hint.unlock_failed'.tr());
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final gate = ref.watch(adGateProvider);
    final blocked = !gate.canPreviewHint || _adUnavailable;

    return HintCard(
      hint: widget.puzzle.hint,
      needsAd: gate.hintPreviewNeedsAd,
      notice: _notice ?? (blocked ? 'hint.ad_unavailable'.tr() : null),
      onPreview: blocked || _busy || widget.puzzle.status.isFinished
          ? null
          : () => unawaited(_preview()),
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
    final stats = ref.watch(myStatsProvider).value;

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

/// 보드를 지우지 않고 그 자리에 띄우는 한 줄(409·제출 실패·재조회 실패).
/// 다시 조회해야 풀리는 안내엔 재시도를 같이 둔다(OVERRIDES §7).
class _NoticeLine extends StatelessWidget {
  const _NoticeLine({required this.notice, this.onRetry});

  final TodayNotice notice;
  final VoidCallback? onRetry;

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
        if (onRetry case final onRetry?)
          TextButton(onPressed: onRetry, child: Text('today.retry'.tr())),
      ],
    );
  }
}

/// 완료 상태. 자동으로 뜬 결과 시트를 닫았어도 여기서 다시 열 수 있다.
class _ShowResultButton extends StatelessWidget {
  const _ShowResultButton({required this.onPressed});

  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => FilledButton(
    onPressed: onPressed,
    child: Text('today.show_result'.tr()),
  );
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

/// 자정 전환 직후. 카운트다운은 결과 시트(S2)와 같은 [PuzzleCountdown] 이다.
class _NoPuzzleCard extends ConsumerWidget {
  const _NoPuzzleCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('today.none_title'.tr(), style: text.titleMedium),
        const SizedBox(height: 8),
        PuzzleCountdown(
          builder: (context, remaining) => Text(
            'today.none_body'.tr(namedArgs: {'time': remaining}),
            style: text.bodySmall,
          ),
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
              'streak.days'.plural(days, name: 'count'),
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ],
        ),
      ),
    );
  }
}
