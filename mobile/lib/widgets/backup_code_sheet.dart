import 'package:chosung/account/account_controller.dart';
import 'package:chosung/layout/adaptive_sheet.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 백업 코드 입력(US 18a). 폭에 따라 바텀시트/다이얼로그다(SCREENS T2).
///
/// 성공하면 true 로 닫힌다.
Future<bool?> showBackupCodeSheet({required BuildContext context}) =>
    showAdaptiveSheet<bool>(
      context: context,
      builder: (context) => const BackupCodeSheet(),
    );

/// 웹 "내 기록 백업" 코드를 받아 그 기록으로 갈아탄다. 코드는 그 기기의 게스트
/// 토큰이라 유효성 확인이 곧 `GET /me/stats` 다 — 전용 엔드포인트는 없다.
class BackupCodeSheet extends ConsumerStatefulWidget {
  const BackupCodeSheet({super.key});

  @override
  ConsumerState<BackupCodeSheet> createState() => _BackupCodeSheetState();
}

class _BackupCodeSheetState extends ConsumerState<BackupCodeSheet> {
  final _code = TextEditingController();

  @override
  void initState() {
    super.initState();
    // 입력이 비면 버튼이 꺼진다 — 빈 코드로 서버를 부를 이유가 없다.
    _code.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    await ref.read(accountProvider.notifier).restoreWithBackupCode(_code.text);
    if (!mounted) return;
    // 실패하면 시트를 열어 둔 채로 코드를 고치게 한다.
    if (ref.read(accountProvider).errorFor(const {
          AccountAction.backupCode,
        }) ==
        null) {
      Navigator.of(context).pop(true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.from(context);
    final text = Theme.of(context).textTheme;
    final account = ref.watch(accountProvider);
    final canSubmit = !account.busy && _code.text.trim().isNotEmpty;
    final error = account.errorFor(const {AccountAction.backupCode});

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          left: 24,
          right: 24,
          top: 24,
          // 키보드가 올라와도 입력과 버튼이 가리지 않는다.
          bottom: 24 + MediaQuery.viewInsetsOf(context).bottom,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Semantics(
              header: true,
              child: Text(
                'account.backup_code_title'.tr(),
                style: text.titleMedium,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'account.backup_code_description'.tr(),
              style: text.bodySmall?.copyWith(color: colors.mutedForeground),
            ),
            const SizedBox(height: 16),
            TextField(
              key: backupCodeFieldKey,
              controller: _code,
              autofocus: true,
              enabled: !account.busy,
              textInputAction: TextInputAction.done,
              autocorrect: false,
              enableSuggestions: false,
              onSubmitted: (_) => canSubmit ? _submit() : null,
              decoration: InputDecoration(
                labelText: 'account.backup_code_label'.tr(),
                errorText: error?.tr(),
              ),
            ),
            const SizedBox(height: 16),
            FilledButton(
              key: backupCodeSubmitKey,
              onPressed: canSubmit ? _submit : null,
              child: Text('account.backup_code_submit'.tr()),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: account.busy
                  ? null
                  : () => Navigator.of(context).pop(false),
              child: Text('account.backup_code_cancel'.tr()),
            ),
          ],
        ),
      ),
    );
  }
}

const backupCodeFieldKey = Key('account.backup_code.field');
const backupCodeSubmitKey = Key('account.backup_code.submit');
