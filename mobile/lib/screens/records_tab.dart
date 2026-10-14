import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/layout/adaptive_sheet.dart';
import 'package:chosung/layout/app_breakpoint.dart';
import 'package:chosung/layout/reading_width.dart';
import 'package:chosung/records/history_controller.dart';
import 'package:chosung/records/my_stats_controller.dart';
import 'package:chosung/routing/app_routes.dart';
import 'package:chosung/settings/legal_links.dart';
import 'package:chosung/settings/puzzle_language_controller.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:chosung/widgets/settings_row.dart';
import 'package:chosung/widgets/seven_day_grid.dart';
import 'package:chosung/widgets/skeleton_box.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 뒤 티켓이 채울 자리. 담당 티켓 번호를 주석으로 달아 두고, 키는 그 티켓과
/// 태블릿 열 배치 테스트가 같이 쓴다(SCREENS T4 — 자리의 열은 바뀌지 않는다).
abstract final class RecordsSlot {
  /// 티켓 29: AccountCard(구글·애플 연결 / 전환됨).
  static const account = Key('records.slot.account');

  /// 티켓 32: 구독 카드(현지화 가격 · 갱신일 · 관리).
  static const subscription = Key('records.slot.subscription');

  /// 티켓 29: 백업 코드로 다른 기기 기록 불러오기.
  static const backupCode = Key('records.slot.backup_code');

  /// 티켓 30: 일일 알림 시각(권한 거부면 "알림 꺼짐" 안내).
  static const dailyNotification = Key('records.slot.daily_notification');

  /// 티켓 30: 리마인더 on/off.
  static const reminder = Key('records.slot.reminder');

  /// 티켓 31: 광고 개인정보 설정(UMP privacy options 가 required 일 때만 표시).
  static const adPrivacy = Key('records.slot.ad_privacy');

  /// "하는 법"(온보딩 3장 다시 보기, 티켓 28).
  static const howTo = Key('records.slot.how_to');

  /// 티켓 29: 계정 삭제 + 확인 다이얼로그.
  static const deleteAccount = Key('records.slot.delete_account');
}

/// S4 내 기록 탭. streak 3칸 · 최근 7일 · 설정 리스트.
///
/// expanded(≥840)는 SCREENS T4 의 2열이다 — 왼쪽은 기록과 계정·구독·백업 코드,
/// 오른쪽은 설정과 계정 삭제. 뒤 티켓(28~32)이 채우는 자리도 이 열 안에 있다.
class RecordsTab extends ConsumerWidget {
  const RecordsTab({super.key});

  /// T4: 열마다 최대 480.
  static const _columnMaxWidth = 480.0;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isExpanded = AppBreakpoint.of(context).isExpanded;
    const left = _RecordsColumn(
      storageKey: PageStorageKey('records.column.left'),
      children: [
        _StreakCard(),
        SizedBox(height: 24),
        _RecentDays(),
        SizedBox(height: 24),
        _AccountSlots(),
      ],
    );
    const right = _RecordsColumn(
      storageKey: PageStorageKey('records.column.right'),
      children: [_SettingsList(), SizedBox(height: 8), _DeleteAccountSlot()],
    );

    return SafeArea(
      child: isExpanded
          ? Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(
                  maxWidth: _columnMaxWidth * 2,
                ),
                child: const Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: left),
                    Expanded(child: right),
                  ],
                ),
              ),
            )
          // 폰·medium: 폰 순서 그대로 1열(SCREENS S4·T4).
          : const ReadingWidth(
              child: _RecordsColumn(
                storageKey: PageStorageKey('records.column.single'),
                children: [
                  _StreakCard(),
                  SizedBox(height: 24),
                  _RecentDays(),
                  SizedBox(height: 24),
                  _AccountSlots(),
                  SizedBox(height: 24),
                  _SettingsList(),
                  SizedBox(height: 8),
                  _DeleteAccountSlot(),
                ],
              ),
            ),
    );
  }
}

/// 한 열. 2열일 때 두 열이 따로 스크롤된다 — 설정이 길어져도 기록이 밀려
/// 올라가지 않는다.
///
/// [storageKey] 는 폭이 바뀔 때 읽던 위치를 돌려주는 자리다(SCREENS "태블릿
/// 레이아웃" — 현재 탭과 스크롤 위치는 유지된다). 1열↔2열은 스크롤 위젯 트리를
/// 교체하므로, 이 키가 없으면 새 Scrollable 이 0 에서 시작해 화면 맨 위로
/// 돌아간다. 열마다 키가 다른 이유는 열의 내용이 다르기 때문이다 — 1열의
/// 위치를 2열 왼쪽에 끼워 넣으면 엉뚱한 곳이 열린다.
class _RecordsColumn extends StatelessWidget {
  const _RecordsColumn({required this.storageKey, required this.children});

  final PageStorageKey<String> storageKey;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    key: storageKey,
    padding: const EdgeInsets.all(16),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: children,
    ),
  );
}

/// 현재 · 최고 · 누적 3칸(S4 상단). 값은 `/me/stats` 고, 플레이 결과가 생기면
/// 다시 읽은 값이다 — 시작 snapshot 만 읽으면 방금 올린 기록이 안 보인다.
class _StreakCard extends ConsumerWidget {
  const _StreakCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stats = ref.watch(myStatsProvider).value;
    if (stats == null) return const SkeletonBox(height: 72);

    return Row(
      children: [
        _StatCell(
          label: 'streak.current'.tr(),
          value: 'streak.days'.tr(
            namedArgs: {'count': '${stats.currentStreak}'},
          ),
        ),
        _StatCell(
          label: 'streak.max'.tr(),
          value: 'streak.days'.tr(namedArgs: {'count': '${stats.maxStreak}'}),
        ),
        _StatCell(
          label: 'streak.solved'.tr(),
          value: 'streak.puzzles'.tr(
            namedArgs: {'count': '${stats.solvedCount}'},
          ),
        ),
      ],
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

/// 최근 7일 그리드. 못 읽으면 그리드 자리에 한 줄 + 재시도를 둔다 —
/// 기록을 못 읽었다고 화면 전체를 오류로 덮지 않는다(OVERRIDES §7).
class _RecentDays extends ConsumerWidget {
  const _RecentDays();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final history = ref.watch(historyProvider);
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'records.recent_days'.tr(),
          style: text.labelSmall?.copyWith(color: colors.mutedForeground),
        ),
        const SizedBox(height: 8),
        switch (history) {
          AsyncValue(hasError: true) => Row(
            children: [
              Expanded(
                child: Text(
                  'records.history_error'.tr(),
                  style: text.bodySmall,
                ),
              ),
              TextButton(
                onPressed: () => ref.invalidate(historyProvider),
                child: Text('records.retry'.tr()),
              ),
            ],
          ),
          AsyncValue(:final List<HistoryDay> value) => SevenDayGrid(
            days: value,
          ),
          _ => const ExcludeSemantics(child: SkeletonBox(height: 44)),
        },
      ],
    );
  }
}

/// 왼쪽 열의 자리들(T4) — 계정·구독·백업 코드. 전부 비활성이다.
class _AccountSlots extends StatelessWidget {
  const _AccountSlots();

  @override
  Widget build(BuildContext context) {
    final pending = 'records.slot_pending'.tr();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // 티켓 29 가 AccountCard 로 바꾼다.
        SettingsRow(
          key: RecordsSlot.account,
          label: 'records.account'.tr(),
          value: pending,
        ),
        const _Hairline(),
        // 티켓 32 가 구독 카드(현지화 가격)로 바꾼다.
        SettingsRow(
          key: RecordsSlot.subscription,
          label: 'records.subscription'.tr(),
          value: pending,
        ),
        const _Hairline(),
        // 티켓 29 가 백업 코드 입력 시트를 붙인다.
        SettingsRow(
          key: RecordsSlot.backupCode,
          label: 'records.backup_code'.tr(),
          value: pending,
        ),
      ],
    );
  }
}

/// 오른쪽 열의 설정 리스트(T4). 여기서 도는 건 퍼즐 언어·법적 문서·라이선스·
/// 버전뿐이고, 알림·광고 개인정보·하는 법은 자리만 있다.
class _SettingsList extends ConsumerWidget {
  const _SettingsList();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = AppColors.from(context);
    final pending = 'records.slot_pending'.tr();
    final uiLanguage = Localizations.localeOf(context).languageCode;
    final open = ref.read(webLinkLauncherProvider);
    final version = ref.watch(appVersionProvider).value;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'records.settings'.tr(),
          style: Theme.of(
            context,
          ).textTheme.labelSmall?.copyWith(color: colors.mutedForeground),
        ),
        const SizedBox(height: 4),
        const _PuzzleLanguageRow(),
        const _Hairline(),
        // 티켓 30 이 시각 선택과 권한 상태를 채운다.
        SettingsRow(
          key: RecordsSlot.dailyNotification,
          label: 'records.daily_notification'.tr(),
          value: pending,
        ),
        const _Hairline(),
        // 티켓 30 이 on/off 스위치를 채운다.
        SettingsRow(
          key: RecordsSlot.reminder,
          label: 'records.reminder'.tr(),
          value: pending,
        ),
        const _Hairline(),
        // 티켓 31 이 UMP privacy options 가 required 일 때만 보이게 한다.
        SettingsRow(
          key: RecordsSlot.adPrivacy,
          label: 'records.ad_privacy'.tr(),
          value: pending,
        ),
        const _Hairline(),
        // 온보딩(S6)을 처음부터 다시 본다 — 완료 플래그는 그대로다.
        SettingsRow(
          key: RecordsSlot.howTo,
          label: 'records.how_to'.tr(),
          onTap: () => context.push(AppRoutes.howTo),
        ),
        const _Hairline(),
        SettingsRow(
          label: 'records.privacy'.tr(),
          onTap: () => open(
            legalDocumentUrl(
              document: LegalDocument.privacy,
              uiLanguage: uiLanguage,
            ),
          ),
        ),
        const _Hairline(),
        SettingsRow(
          label: 'records.terms'.tr(),
          onTap: () => open(
            legalDocumentUrl(
              document: LegalDocument.terms,
              uiLanguage: uiLanguage,
            ),
          ),
        ),
        const _Hairline(),
        SettingsRow(
          label: 'records.licenses'.tr(),
          onTap: () => showLicensePage(
            context: context,
            applicationName: 'app.name'.tr(),
            applicationVersion: version,
          ),
        ),
        const _Hairline(),
        SettingsRow(label: 'records.version'.tr(), value: version ?? '—'),
      ],
    );
  }
}

/// 퍼즐 언어 행. 고르면 `PATCH /me` 뒤 홈·순위를 다시 읽는다. 실패하면 그
/// 아래 한 줄로 알린다 — 토스트로 흘려보내지 않는다(OVERRIDES §7).
class _PuzzleLanguageRow extends ConsumerStatefulWidget {
  const _PuzzleLanguageRow();

  @override
  ConsumerState<_PuzzleLanguageRow> createState() => _PuzzleLanguageRowState();
}

class _PuzzleLanguageRowState extends ConsumerState<_PuzzleLanguageRow> {
  bool _failed = false;

  Future<void> _pick() async {
    final current = ref.read(puzzleLanguageProvider).language;
    final picked = await showAdaptiveSheet<PuzzleLanguage>(
      context: context,
      builder: (context) => _LanguagePicker(selected: current),
    );
    if (picked == null || !mounted) return;

    final changed = await ref
        .read(puzzleLanguageProvider.notifier)
        .change(picked);
    if (mounted) setState(() => _failed = !changed);
  }

  @override
  Widget build(BuildContext context) {
    final setting = ref.watch(puzzleLanguageProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SettingsRow(
          label: 'records.puzzle_language'.tr(),
          value: 'language.${setting.language.wire}'.tr(),
          // 쓰기가 끝나기 전엔 다시 못 연다 — 두 요청이 겹치면 서버와 화면이
          // 서로 다른 언어로 끝날 수 있다.
          onTap: setting.changing ? null : _pick,
        ),
        if (_failed)
          Padding(
            padding: const EdgeInsets.only(left: 4, bottom: 8),
            child: Text(
              'records.language_change_failed'.tr(),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: AppColors.from(context).destructive,
              ),
            ),
          ),
      ],
    );
  }
}

/// OVERRIDES §6 `LanguagePicker`. 폭에 따라 시트/다이얼로그로 뜬다(T2).
class _LanguagePicker extends StatelessWidget {
  const _LanguagePicker({required this.selected});

  final PuzzleLanguage selected;

  @override
  Widget build(BuildContext context) => SafeArea(
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Text(
            'records.puzzle_language'.tr(),
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ),
        RadioGroup<PuzzleLanguage>(
          groupValue: selected,
          onChanged: (picked) => Navigator.of(context).pop(picked),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (final language in PuzzleLanguage.values)
                RadioListTile<PuzzleLanguage>(
                  value: language,
                  title: Text('language.${language.wire}'.tr()),
                ),
            ],
          ),
        ),
        const SizedBox(height: 8),
      ],
    ),
  );
}

/// 오른쪽 열 맨 아래(T4). 티켓 29 가 확인 다이얼로그를 붙인다.
class _DeleteAccountSlot extends StatelessWidget {
  const _DeleteAccountSlot();

  @override
  Widget build(BuildContext context) => SettingsRow(
    key: RecordsSlot.deleteAccount,
    label: 'records.delete_account'.tr(),
    value: 'records.slot_pending'.tr(),
    destructive: true,
  );
}

/// 행 구분은 헤어라인 1px 뿐이다(OVERRIDES §4).
class _Hairline extends StatelessWidget {
  const _Hairline();

  @override
  Widget build(BuildContext context) =>
      Divider(height: 1, thickness: 1, color: AppColors.from(context).border);
}
