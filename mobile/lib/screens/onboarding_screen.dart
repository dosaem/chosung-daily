import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/layout/reading_width.dart';
import 'package:chosung/onboarding/onboarding_controller.dart';
import 'package:chosung/onboarding/onboarding_pages.dart';
import 'package:chosung/onboarding/onboarding_sample.dart';
import 'package:chosung/permissions/notification_permission.dart';
import 'package:chosung/permissions/tracking_permission.dart';
import 'package:chosung/puzzle/board_layout.dart';
import 'package:chosung/routing/app_routes.dart';
import 'package:chosung/settings/puzzle_language_controller.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:chosung/widgets/puzzle_board.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons/lucide_icons.dart';

/// 테스트가 잡는 자리들. 글자는 번역에 따라 바뀌지만 이 키는 안 바뀐다.
abstract final class OnboardingKeys {
  static const pages = Key('onboarding.pages');

  /// 아래 점 하나. 개수가 곧 장 수라 iOS/Android 분기를 여기서 본다.
  static Key dot(int index) => Key('onboarding.dot.$index');

  static Key languageChip(PuzzleLanguage language) =>
      Key('onboarding.chip.${language.wire}');
}

/// S6 온보딩. 첫 실행에 한 번 나오고, S4 설정 "하는 법" 으로 다시 볼 수 있다.
///
/// 태블릿에도 rail 없이 읽기 폭 가운데로만 선다(SCREENS T0) — 타일·글자 크기는
/// 폰과 같다. 온보딩은 "읽고 넘기는" 화면이라 폭이 넓어져도 2열로 나눌 내용이
/// 없다.
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({this.isReplay = false, super.key});

  /// 설정에서 다시 연 경우. 끝내면 홈이 아니라 설정으로 돌아가고, 완료
  /// 플래그는 이미 true 라 다시 쓰지 않는다.
  final bool isReplay;

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  /// OVERRIDES §7 전환 모션.
  static const _slide = Duration(milliseconds: 200);

  final _controller = PageController();

  /// 장 구성은 플랫폼으로만 갈리고 실행 중에 바뀌지 않는다 — 한 번 정한다.
  late final List<OnboardingPage> _pages = onboardingPages(
    isIos: ref.read(isIosProvider),
  );

  int _index = 0;

  /// OS 권한 프롬프트를 기다리는 동안 버튼을 잠근다 — 두 번 누르면 프롬프트가
  /// 닫히는 사이에 다음 장으로 두 번 넘어간다.
  bool _busy = false;

  bool _languageFailed = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _next() async {
    if (_index >= _pages.length - 1) return _finish();

    // 모션 감소면 즉시 넘긴다(OVERRIDES §7).
    if (MediaQuery.disableAnimationsOf(context)) {
      _controller.jumpToPage(_index + 1);
      return;
    }
    await _controller.nextPage(duration: _slide, curve: Curves.easeOut);
  }

  Future<void> _finish() async {
    if (!widget.isReplay) {
      await ref.read(onboardingSeenProvider.notifier).complete();
    }
    if (!mounted) return;

    // 첫 실행은 홈으로 "간다"(뒤로 가기로 온보딩에 돌아올 자리를 남기지
    // 않는다). 다시 보기는 설정 위에 얹힌 화면이라 닫기만 한다 — 다만 이
    // 경로로 바로 들어오면(딥링크·복원) 닫을 자리가 없어서 설정으로 보낸다.
    if (!widget.isReplay) {
      context.go(AppRoutes.today);
    } else if (context.canPop()) {
      context.pop();
    } else {
      context.go(AppRoutes.records);
    }
  }

  /// 권한 프롬프트를 띄우고, 허용이든 거부든 다음 장으로 넘어간다 — 거부해도
  /// S4 설정에서 다시 켤 수 있어서 여기서 길을 막을 이유가 없다.
  Future<void> _ask(Future<void> Function() prompt) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await prompt();
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    if (mounted) await _next();
  }

  Future<void> _pickLanguage(PuzzleLanguage language) async {
    final changed = await ref
        .read(puzzleLanguageProvider.notifier)
        .change(language);
    if (mounted) setState(() => _languageFailed = !changed);
  }

  @override
  Widget build(BuildContext context) {
    final page = _pages[_index];

    return Scaffold(
      body: SafeArea(
        child: ReadingWidth(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _Header(
                  showChips: page.showsLanguageChips,
                  onPick: _busy ? null : _pickLanguage,
                  showFailure: page.showsLanguageChips && _languageFailed,
                  exitLabel: widget.isReplay
                      ? 'onboarding.close'.tr()
                      : 'onboarding.skip'.tr(),
                  onExit: _busy ? null : _finish,
                ),
                Expanded(
                  child: PageView(
                    key: OnboardingKeys.pages,
                    controller: _controller,
                    onPageChanged: (index) => setState(() => _index = index),
                    children: [
                      for (final page in _pages) _PageBody(page: page),
                    ],
                  ),
                ),
                _Dots(count: _pages.length, index: _index),
                const SizedBox(height: 16),
                ..._actions(page),
              ],
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _actions(OnboardingPage page) => switch (page) {
    OnboardingPage.oneADay || OnboardingPage.fiveTries => [
      FilledButton(
        onPressed: _busy ? null : _next,
        child: Text('onboarding.next'.tr()),
      ),
    ],
    OnboardingPage.keepStreak => [
      FilledButton(
        onPressed: _busy
            ? null
            : () => _ask(
                ref.read(notificationPermissionProvider.notifier).request,
              ),
        child: Text('onboarding.notification_allow'.tr()),
      ),
      TextButton(
        onPressed: _busy ? null : _next,
        child: Text('onboarding.notification_later'.tr()),
      ),
    ],
    OnboardingPage.tracking => [
      FilledButton(
        onPressed: _busy
            ? null
            : () => _ask(ref.read(trackingStatusProvider.notifier).request),
        child: Text('onboarding.tracking_continue'.tr()),
      ),
    ],
  };
}

/// 상단 줄 — 1장의 언어 칩과 "건너뛰기"(다시 보기에선 "닫기").
class _Header extends StatelessWidget {
  const _Header({
    required this.showChips,
    required this.onPick,
    required this.showFailure,
    required this.exitLabel,
    required this.onExit,
  });

  final bool showChips;
  final ValueChanged<PuzzleLanguage>? onPick;
  final bool showFailure;
  final String exitLabel;
  final VoidCallback? onExit;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Row(
        children: [
          if (showChips) _LanguageChips(onPick: onPick),
          const Spacer(),
          TextButton(onPressed: onExit, child: Text(exitLabel)),
        ],
      ),
      if (showFailure)
        Text(
          'records.language_change_failed'.tr(),
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: AppColors.from(context).destructive,
          ),
        ),
    ],
  );
}

/// 퍼즐 언어 칩 두 개. 고른 쪽은 brand 테두리로만 표시한다 — brand 는 면으로
/// 칠하지 않는다(OVERRIDES §2).
class _LanguageChips extends ConsumerWidget {
  const _LanguageChips({required this.onPick});

  final ValueChanged<PuzzleLanguage>? onPick;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final setting = ref.watch(puzzleLanguageProvider);
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;

    return Row(
      children: [
        for (final language in PuzzleLanguage.values)
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: InkWell(
              key: OnboardingKeys.languageChip(language),
              // 쓰기가 끝나기 전엔 다시 못 누른다 — S4 설정과 같은 규칙이다.
              onTap: setting.changing || onPick == null
                  ? null
                  : () => onPick!(language),
              borderRadius: BorderRadius.circular(10),
              child: Semantics(
                selected: setting.language == language,
                button: true,
                child: Container(
                  constraints: const BoxConstraints(minHeight: 44),
                  alignment: Alignment.center,
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: setting.language == language
                          ? colors.brand
                          : colors.border,
                    ),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    'language.${language.wire}'.tr(),
                    style: text.bodySmall?.copyWith(
                      fontWeight: setting.language == language
                          ? FontWeight.w600
                          : FontWeight.w400,
                    ),
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

/// 한 장의 본문 — 그림 → 제목 → 설명 순서(목업 e6_onboarding).
class _PageBody extends ConsumerWidget {
  const _PageBody({required this.page});

  final OnboardingPage page;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final language = ref.watch(puzzleLanguageProvider).language;
    final sample = onboardingSample(language);
    final text = Theme.of(context).textTheme;
    final colors = AppColors.from(context);

    final (illustration, title, body) = switch (page) {
      OnboardingPage.oneADay => (
        _SampleRow(cells: sample.mask, isQuestion: true),
        'onboarding.one_a_day_title'.tr(),
        'onboarding.one_a_day_body.${language.wire}'.tr(),
      ),
      OnboardingPage.fiveTries => (
        _FeedbackSample(cells: sample.attempt),
        'onboarding.five_tries_title'.tr(),
        'onboarding.five_tries_body'.tr(),
      ),
      OnboardingPage.keepStreak => (
        const _StreakSample(),
        'onboarding.keep_streak_title'.tr(),
        'onboarding.keep_streak_body'.tr(),
      ),
      OnboardingPage.tracking => (
        Icon(LucideIcons.megaphone, size: 48, color: colors.brand),
        'onboarding.tracking_title'.tr(),
        'onboarding.tracking_body'.tr(),
      ),
    };

    // 내용은 세로 가운데에 선다(목업 e6_onboarding). 글자 크기를 키우거나
    // 화면이 짧으면 그대로 스크롤로 넘어간다 — 가운데 정렬 때문에 잘리지 않게
    // 스크롤 뷰 안에서 "최소 높이 = 보이는 높이" 로 잡는다.
    return LayoutBuilder(
      builder: (context, constraints) => SingleChildScrollView(
        child: ConstrainedBox(
          constraints: BoxConstraints(minHeight: constraints.maxHeight),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const SizedBox(height: 24),
              illustration,
              const SizedBox(height: 32),
              Semantics(
                header: true,
                child: Text(
                  title,
                  style: text.headlineMedium,
                  textAlign: TextAlign.center,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                body,
                style: text.bodyMedium?.copyWith(color: colors.mutedForeground),
                textAlign: TextAlign.center,
              ),
              if (page == OnboardingPage.keepStreak) ...[
                const SizedBox(height: 24),
                const _NotificationPrePrompt(),
              ],
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}

/// 예시 타일 한 줄. 실제 보드와 같은 위젯·같은 크기를 쓴다 — 온보딩에서 본
/// 모양이 첫 퍼즐에서 그대로 나와야 설명이 설명 구실을 한다.
class _SampleRow extends StatelessWidget {
  const _SampleRow({required this.cells, this.isQuestion = false});

  final List<BoardCell> cells;
  final bool isQuestion;

  @override
  Widget build(BuildContext context) => Wrap(
    alignment: WrapAlignment.center,
    spacing: PuzzleBoard.tileGap,
    runSpacing: PuzzleBoard.tileGap,
    children: [
      for (final cell in cells)
        BoardTile(
          cell: cell,
          // 폭이 넓어져도 타일은 폰과 같은 크기다(SCREENS "태블릿 레이아웃").
          size: tileSize(cells.length),
          isQuestion: isQuestion,
        ),
    ],
  );
}

/// 2장 — 시도 행 + 색이 뜻하는 것. 색만으로 설명하지 않게 글로도 적는다.
class _FeedbackSample extends StatelessWidget {
  const _FeedbackSample({required this.cells});

  final List<BoardCell> cells;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;

    return Column(
      children: [
        _SampleRow(cells: cells),
        const SizedBox(height: 16),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 16,
          runSpacing: 8,
          children: [
            _Legend(
              color: colors.tileCorrect,
              label: 'onboarding.five_tries_correct'.tr(),
              style: text.bodySmall,
            ),
            _Legend(
              color: colors.tileWrong,
              label: 'onboarding.five_tries_wrong'.tr(),
              style: text.bodySmall,
            ),
          ],
        ),
      ],
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend({required this.color, required this.label, this.style});

  final Color color;
  final String label;
  final TextStyle? style;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Container(
        width: 16,
        height: 16,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(4),
        ),
      ),
      const SizedBox(width: 8),
      Text(label, style: style),
    ],
  );
}

/// 3장 — 불꽃 + 연속 일수. 숫자는 `foreground` 다(OVERRIDES §2).
class _StreakSample extends StatelessWidget {
  const _StreakSample();

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(LucideIcons.flame, size: 40, color: colors.brand),
        const SizedBox(width: 8),
        Text(
          'onboarding.keep_streak_sample'.tr(),
          style: Theme.of(context).textTheme.displaySmall,
        ),
      ],
    );
  }
}

/// 알림 권한 **사전** 안내(US 35). 시스템 프롬프트는 "알림 켜기" 를 누른
/// 뒤에만 뜬다 — 설명 없이 먼저 띄우면 거부당한 뒤 다시 물을 길이 없다.
class _NotificationPrePrompt extends StatelessWidget {
  const _NotificationPrePrompt();

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        // 라이트 모드에선 면을 깔지 않는다 — 헤어라인으로만 구분(OVERRIDES §4).
        border: Border.all(color: colors.border),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
          Text(
            'onboarding.notification_title'.tr(),
            style: text.titleMedium,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 4),
          Text(
            'onboarding.notification_body'.tr(),
            style: text.bodySmall?.copyWith(color: colors.mutedForeground),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

/// 몇 번째 장인지. 지금 장만 길쭉한 brand 막대다 — 활성 탭 밑줄과 같은 부류의
/// 가는 디테일이라 brand 를 쓴다(OVERRIDES §2, 목업 e6_onboarding).
class _Dots extends StatelessWidget {
  const _Dots({required this.count, required this.index});

  final int count;
  final int index;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);

    return Semantics(
      label: 'onboarding.progress'.tr(
        namedArgs: {'current': '${index + 1}', 'total': '$count'},
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          for (var dot = 0; dot < count; dot++)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: Container(
                key: OnboardingKeys.dot(dot),
                width: dot == index ? 24 : 8,
                height: 8,
                decoration: BoxDecoration(
                  color: dot == index ? colors.brand : colors.border,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
