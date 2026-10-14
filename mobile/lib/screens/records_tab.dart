import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/layout/adaptive_sheet.dart';
import 'package:chosung/layout/app_breakpoint.dart';
import 'package:chosung/layout/reading_width.dart';
import 'package:chosung/notifications/notification_settings.dart';
import 'package:chosung/notifications/notification_settings_controller.dart';
import 'package:chosung/notifications/system_notification_settings.dart';
import 'package:chosung/permissions/notification_permission.dart';
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
import 'package:lucide_icons/lucide_icons.dart';

/// 뒤 티켓이 채울 자리. 담당 티켓 번호를 주석으로 달아 두고, 키는 그 티켓과
/// 태블릿 열 배치 테스트가 같이 쓴다(SCREENS T4 — 자리의 열은 바뀌지 않는다).
abstract final class RecordsSlot {
  /// 티켓 29: AccountCard(구글·애플 연결 / 전환됨).
  static const account = Key('records.slot.account');

  /// 티켓 32: 구독 카드(현지화 가격 · 갱신일 · 관리).
  static const subscription = Key('records.slot.subscription');

  /// 티켓 29: 백업 코드로 다른 기기 기록 불러오기.
  static const backupCode = Key('records.slot.backup_code');

  /// 일일 알림 시각(권한 거부면 "알림 꺼짐" 안내, 티켓 30).
  static const dailyNotification = Key('records.slot.daily_notification');

  /// 리마인더 on/off(티켓 30).
  static const reminder = Key('records.slot.reminder');

  /// 권한이 꺼져 있을 때만 보이는 안내(티켓 30).
  static const notificationOff = Key('records.slot.notification_off');

  /// 일일 알림 시각 목록(시트/다이얼로그). 뒤에 깔린 설정 행에도 같은 시각
  /// 문자열이 있어서, 테스트가 목록 안쪽만 보려면 손잡이가 필요하다.
  static const reminderPicker = Key('records.reminder_picker');

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

/// 오른쪽 열의 설정 리스트(T4). 광고 개인정보(티켓 31)만 자리로 남아 있다.
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
        const _NotificationRows(),
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

/// 알림 두 줄(S4): 일일 알림 시각 · 리마인더 on/off. 권한이 꺼져 있으면 그
/// 사이에 안내 한 줄이 끼어든다.
///
/// 값을 읽기 전에는 두 조작을 다 잠근다 — 지금 값을 모르는 채 picker 를 열면
/// 엉뚱한 시각이 선택된 것처럼 보이고, 스위치는 눌린 뒤 되돌아간다.
class _NotificationRows extends ConsumerWidget {
  const _NotificationRows();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(notificationSettingsProvider).value;
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SettingsRow(
          key: RecordsSlot.dailyNotification,
          label: 'records.daily_notification'.tr(),
          value: settings == null
              ? null
              : MaterialLocalizations.of(
                  context,
                ).formatTimeOfDay(settings.dailyTime),
          onTap: settings == null
              ? null
              : () => _pickTime(context, ref, settings),
        ),
        const _NotificationsOffNotice(),
        const _Hairline(),
        SettingsRow(
          key: RecordsSlot.reminder,
          label: 'records.reminder'.tr(),
          // 스위치가 탭을 먹으므로 행 자체는 누를 수 없다(SettingsRow.trailing).
          trailing: Switch.adaptive(
            value: settings?.reminderEnabled ?? false,
            onChanged: settings == null
                ? null
                : (enabled) => ref
                      .read(notificationSettingsProvider.notifier)
                      .setReminderEnabled(enabled: enabled),
          ),
        ),
        // 리마인더가 저녁 8시라는 건 화면 어디에도 안 적혀 있으면 알 수가 없다.
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(
            'records.reminder_hint'.tr(),
            style: text.bodySmall?.copyWith(color: colors.mutedForeground),
          ),
        ),
      ],
    );
  }

  Future<void> _pickTime(
    BuildContext context,
    WidgetRef ref,
    NotificationSettings settings,
  ) async {
    final picked = await showAdaptiveSheet<TimeOfDay>(
      context: context,
      builder: (context) => _ReminderPicker(selected: settings.dailyTime),
    );
    if (picked == null || picked == settings.dailyTime) return;

    await ref.read(notificationSettingsProvider.notifier).setDailyTime(picked);
  }
}

/// 권한이 꺼져 있을 때만 보이는 한 줄. 누르면 OS 알림 설정으로 보낸다 —
/// 거부된 뒤에는 앱이 프롬프트를 다시 띄울 수 없어서 그게 유일한 길이다.
///
/// 색으로만 말하지 않는다: 종에 사선이 그어진 아이콘 + 문장이 같이 있다.
class _NotificationsOffNotice extends ConsumerWidget {
  const _NotificationsOffNotice();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (ref.watch(notificationPermissionProvider).isGranted) {
      return const SizedBox.shrink();
    }
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;

    return InkWell(
      key: RecordsSlot.notificationOff,
      onTap: ref.read(openNotificationSettingsProvider),
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: SettingsRow.minHeight),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(4, 4, 4, 12),
          child: Row(
            children: [
              Icon(
                LucideIcons.bellOff,
                size: 14,
                color: colors.mutedForeground,
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  'records.notification_off'.tr(),
                  style: text.bodySmall,
                ),
              ),
              Icon(
                LucideIcons.chevronRight,
                size: 16,
                color: colors.mutedForeground,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// OVERRIDES §6 `ReminderPicker`. 폭에 따라 시트/다이얼로그로 뜬다(T2).
///
/// 30분 단위 목록이다 — 분 단위 휠보다 고르기 쉽고(터치 타깃 하나), 스크린
/// 리더가 그냥 읽고, `LanguagePicker` 와 같은 모양이라 설정 안에서 조작이
/// 한 가지로 보인다. 목록은 현재 값이 보이는 자리에서 열린다.
class _ReminderPicker extends StatefulWidget {
  const _ReminderPicker({required this.selected});

  static const _stepMinutes = 30;
  static const _itemExtent = 56.0;

  /// 목록이 열렸을 때 고른 시각 위로 몇 칸을 더 보여줄지.
  static const _leadingItems = 2;

  /// 00:00 부터 30분 간격으로 하루치.
  static final List<TimeOfDay> choices = [
    for (
      var minutes = 0;
      minutes < Duration.minutesPerDay;
      minutes += _stepMinutes
    )
      TimeOfDay(hour: minutes ~/ 60, minute: minutes % 60),
  ];

  final TimeOfDay selected;

  @override
  State<_ReminderPicker> createState() => _ReminderPickerState();
}

class _ReminderPickerState extends State<_ReminderPicker> {
  late final ScrollController _controller;

  @override
  void initState() {
    super.initState();
    // 목록을 현재 값이 보이는 자리에서 연다 — 48칸짜리 목록이 늘 00:00 에서
    // 열리면 매번 아침까지 스크롤해야 한다.
    final selectedIndex = _ReminderPicker.choices.indexOf(widget.selected);
    _controller = ScrollController(
      initialScrollOffset:
          _ReminderPicker._itemExtent *
          (selectedIndex - _ReminderPicker._leadingItems).clamp(
            0,
            _ReminderPicker.choices.length - 1,
          ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final materialLocalizations = MaterialLocalizations.of(context);

    return SafeArea(
      key: RecordsSlot.reminderPicker,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Text(
              'records.daily_notification_picker'.tr(),
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
          Flexible(
            child: RadioGroup<TimeOfDay>(
              // 저장된 값이 30분 눈금에 없으면(이전 버전에서 고른 값) 아무것도
              // 선택되지 않은 채로 연다 — 엉뚱한 칸을 고른 것처럼 보이지 않는다.
              groupValue: _ReminderPicker.choices.contains(widget.selected)
                  ? widget.selected
                  : null,
              onChanged: (picked) => Navigator.of(context).pop(picked),
              child: ListView.builder(
                controller: _controller,
                itemExtent: _ReminderPicker._itemExtent,
                itemCount: _ReminderPicker.choices.length,
                itemBuilder: (context, index) => RadioListTile<TimeOfDay>(
                  value: _ReminderPicker.choices[index],
                  title: Text(
                    materialLocalizations.formatTimeOfDay(
                      _ReminderPicker.choices[index],
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),
        ],
      ),
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
